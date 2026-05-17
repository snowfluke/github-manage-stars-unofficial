from ghstars.validators import (
    MAX_LIST_NAME_LENGTH,
    MAX_LISTS_PER_ACCOUNT,
    validate_category_set,
    validate_list_name,
)


class TestListName:
    def test_valid(self):
        assert validate_list_name("My Stack") is None

    def test_empty(self):
        assert "empty" in validate_list_name("")

    def test_whitespace_only(self):
        assert "empty" in validate_list_name("   ")

    def test_too_long(self):
        name = "x" * (MAX_LIST_NAME_LENGTH + 1)
        err = validate_list_name(name)
        assert err and "33 chars" in err

    def test_exactly_max_length_ok(self):
        name = "x" * MAX_LIST_NAME_LENGTH
        assert validate_list_name(name) is None

    def test_duplicate_case_insensitive(self):
        err = validate_list_name("rust", existing={"Rust"})
        assert err and "duplicate" in err

    def test_not_duplicate(self):
        assert validate_list_name("Go", existing={"Rust"}) is None


class TestCategorySet:
    def _make(self, names):
        return [{"name": n, "description": "", "patterns": []} for n in names]

    def test_empty_ok(self):
        assert validate_category_set([]) == []

    def test_too_many(self):
        cats = self._make([f"x{i}" for i in range(MAX_LISTS_PER_ACCOUNT + 1)])
        errors = validate_category_set(cats)
        assert any("limit" in e for e in errors)

    def test_duplicates_detected(self):
        errors = validate_category_set(self._make(["A", "a", "B"]))
        assert any("duplicate" in e for e in errors)

    def test_long_name(self):
        errors = validate_category_set(self._make(["x" * 40]))
        assert any("40 chars" in e for e in errors)

    def test_missing_name(self):
        errors = validate_category_set([{"name": "", "description": "x", "patterns": []}])
        assert any("missing name" in e for e in errors)

    def test_patterns_not_list(self):
        cats = [{"name": "A", "description": "", "patterns": "not a list"}]
        errors = validate_category_set(cats)
        assert any("patterns must be a list" in e for e in errors)
