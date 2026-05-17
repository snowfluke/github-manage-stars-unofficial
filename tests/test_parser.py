"""Parser tests using small inline HTML snippets that mirror real GitHub output."""
from ghstars import parser


DELETE_LIST_PAGE = """
<html><body>
  <form action="/search" method="get">
    <input name="authenticity_token" value="WRONG_TOKEN_SEARCH"/>
  </form>
  <form action="/stars/alice/lists/old" method="post">
    <input name="_method" value="delete"/>
    <input name="authenticity_token" value="RIGHT_TOKEN"/>
  </form>
</body></html>
"""

NEW_LIST_PAGE = """
<html><body>
  <form action="/stars/alice/lists" method="post">
    <input name="authenticity_token" value="NEW_LIST_TOKEN"/>
    <input name="user_list[name]"/>
    <input name="user_list[description]"/>
    <input name="user_list[private]"/>
  </form>
</body></html>
"""

REPO_FRAGMENT_WITH_LISTS = """
<div class="js-user-list-menu-content-root"
     data-repository-id="123456">
  <form class="js-user-list-menu-form" action="/foo/bar/lists" method="post">
    <input name="_method" value="put"/>
    <input name="authenticity_token" value="REPO_TOKEN"/>
    <input name="repository_id" value="123456"/>
    <input name="list_ids[]" value=""/>
    <action-list>
      <ul role="listbox">
        <li>
          <button data-input-name="list_ids[]" data-value="42" aria-selected="false">
            <span class="ActionListItem-label">My Stack</span>
          </button>
        </li>
        <li>
          <button data-input-name="list_ids[]" data-value="99" aria-selected="true">
            <span class="ActionListItem-label">AI Agents</span>
          </button>
        </li>
      </ul>
    </action-list>
  </form>
</div>
"""

PROFILE_STARS_FRAGMENT = """
<html><body>
  <div class="profile-stars">
    <a href="/stars/alice/lists/my-stack">My stack 5 repositories</a>
    <a href="/stars/alice/lists/inspiration">Inspiration 12 repositories</a>
    <a href="/stars/alice/lists/new">New list</a>
    <a href="/some-other-link">Unrelated</a>
  </div>
</body></html>
"""


class TestPredicates:
    def test_delete_form_detected(self):
        form = parser.find_form(DELETE_LIST_PAGE, parser.is_delete_form)
        assert form is not None
        assert parser.extract_csrf_from_form(form) == "RIGHT_TOKEN"

    def test_new_list_form_detected(self):
        form = parser.find_form(NEW_LIST_PAGE, parser.is_new_list_form)
        assert form is not None
        assert parser.extract_csrf_from_form(form) == "NEW_LIST_TOKEN"

    def test_repo_lists_form_detected(self):
        form = parser.find_form(REPO_FRAGMENT_WITH_LISTS, parser.is_repo_lists_form)
        assert form is not None
        assert parser.extract_csrf_from_form(form) == "REPO_TOKEN"

    def test_predicates_dont_cross_match(self):
        # The delete page does NOT have a new-list form
        assert parser.find_form(DELETE_LIST_PAGE, parser.is_new_list_form) is None
        # The new-list page does NOT have a delete form
        assert parser.find_form(NEW_LIST_PAGE, parser.is_delete_form) is None


class TestRepoFragmentParse:
    def test_parses_lists(self):
        ctx = parser.parse_repo_list_fragment(REPO_FRAGMENT_WITH_LISTS)
        assert ctx.csrf == "REPO_TOKEN"
        assert len(ctx.lists) == 2
        names = {l["name"] for l in ctx.lists}
        assert names == {"My Stack", "AI Agents"}
        checked = next(l for l in ctx.lists if l["name"] == "AI Agents")
        assert checked["checked"] is True
        unchecked = next(l for l in ctx.lists if l["name"] == "My Stack")
        assert unchecked["checked"] is False

    def test_empty_fragment(self):
        ctx = parser.parse_repo_list_fragment("<div></div>")
        assert ctx.csrf is None
        assert ctx.lists == []


class TestParseUserLists:
    def test_extracts_lists(self):
        lists = parser.parse_user_lists(PROFILE_STARS_FRAGMENT, "alice")
        slugs = {l.slug for l in lists}
        # 'new' should be filtered out as a reserved slug
        assert slugs == {"my-stack", "inspiration"}

    def test_strips_repo_count_suffix(self):
        lists = parser.parse_user_lists(PROFILE_STARS_FRAGMENT, "alice")
        names = {l.name for l in lists}
        assert "My stack" in names
        assert "Inspiration" in names
        # Counts shouldn't sneak in
        for n in names:
            assert "repositor" not in n.lower()
