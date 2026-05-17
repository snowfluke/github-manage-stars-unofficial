from ghstars import categorize, presets
from ghstars.categorize import Category, Repo


def _repo(name, desc="", lang=None, topics=None, archived=False, fork=False):
    return Repo(
        name=name, id=0, description=desc, language=lang,
        topics=list(topics or []), stars=0, archived=archived,
        is_fork=fork, updated_at="",
    )


class TestCategoryMatch:
    def test_pattern_match(self):
        c = Category(name="x", patterns=[r"\bclaude\b"])
        assert c.matches("anthropics/claude-code mcp server", None)

    def test_no_match(self):
        c = Category(name="x", patterns=[r"\bsvelte\b"])
        assert not c.matches("not relevant", None)

    def test_language_match(self):
        c = Category(name="rust", language="rust")
        assert c.matches("anything here", "Rust")

    def test_language_no_match_when_different(self):
        c = Category(name="rust", language="rust")
        assert not c.matches("anything here", "Go")


class TestCategorizeFlow:
    def test_archived_short_circuits(self):
        cats = [
            Category(name="Archived"),
            Category(name="Claude", patterns=[r"claude"]),
            Category(name="Other"),
        ]
        repo = _repo("anthropics/claude-code", archived=True)
        buckets = categorize.categorize([repo], cats)
        assert buckets["Archived"] == [repo]
        assert buckets["Claude"] == []

    def test_first_match_wins(self):
        cats = [
            Category(name="Specific", patterns=[r"claude-code"]),
            Category(name="General", patterns=[r"claude"]),
            Category(name="Other"),
        ]
        repo = _repo("anthropics/claude-code")
        buckets = categorize.categorize([repo], cats)
        assert buckets["Specific"] == [repo]
        assert buckets["General"] == []

    def test_fallback_to_other(self):
        cats = [
            Category(name="Claude", patterns=[r"claude"]),
            Category(name="Other"),
        ]
        repo = _repo("random/unrelated-thing", desc="nothing matches")
        buckets = categorize.categorize([repo], cats)
        assert buckets["Other"] == [repo]
        assert buckets["Claude"] == []

    def test_synthetic_other_bucket_added(self):
        cats = [Category(name="Claude", patterns=[r"claude"])]  # no fallback declared
        repo = _repo("random/thing")
        buckets = categorize.categorize([repo], cats)
        assert "Other" in buckets
        assert buckets["Other"] == [repo]

    def test_topics_match(self):
        cats = [Category(name="OCR", patterns=[r"\bocr\b"]), Category(name="Other")]
        repo = _repo("any/repo", topics=["ocr", "computer-vision"])
        buckets = categorize.categorize([repo], cats)
        assert buckets["OCR"] == [repo]


class TestPresetsSanity:
    """Every preset must satisfy GitHub's documented + observed constraints."""
    def test_count_within_limit(self):
        assert len(presets.DEFAULT_CATEGORIES) <= 32

    def test_unique_names_case_insensitive(self):
        names = [c.name.lower() for c in presets.DEFAULT_CATEGORIES]
        assert len(names) == len(set(names)), "duplicate preset names"

    def test_name_lengths(self):
        for c in presets.DEFAULT_CATEGORIES:
            assert len(c.name) <= 32, f"{c.name!r} too long"

    def test_patterns_compile(self):
        import re
        for c in presets.DEFAULT_CATEGORIES:
            for p in c.patterns:
                re.compile(p)  # raises if invalid

    def test_has_other_and_archived(self):
        names = {c.name for c in presets.DEFAULT_CATEGORIES}
        assert "Archived" in names
        assert "Other" in names


class TestRepoFromDict:
    def test_full(self):
        r = Repo.from_dict({
            "name": "foo/bar",
            "id": 42,
            "desc": "hello",
            "lang": "Python",
            "topics": ["a", "b"],
            "stars": 100,
            "archived": False,
            "fork": True,
            "updated": "2026-01-01T00:00:00Z",
        })
        assert r.name == "foo/bar"
        assert r.id == 42
        assert r.topics == ["a", "b"]
        assert r.is_fork is True

    def test_missing_fields_have_safe_defaults(self):
        r = Repo.from_dict({"name": "x/y"})
        assert r.id == 0
        assert r.description == ""
        assert r.topics == []
        assert r.stars == 0

    def test_search_blob_lowercases(self):
        r = Repo.from_dict({"name": "Foo/BAR", "desc": "WHATEVER", "topics": ["TopicA"]})
        blob = r.search_blob
        assert blob == blob.lower()
        assert "foo/bar" in blob
        assert "whatever" in blob
        assert "topica" in blob
