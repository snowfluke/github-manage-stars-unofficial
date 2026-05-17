import json

from ghstars import credentials


class TestParseCookieHeader:
    def test_curl_b_flag(self):
        text = "-b 'a=1; b=2; c=3'"
        out = credentials.parse_curl_cookie_header(text)
        assert out == {"a": "1", "b": "2", "c": "3"}

    def test_double_quoted(self):
        out = credentials.parse_curl_cookie_header('-b "user_session=abc; _gh_sess=xyz"')
        assert out == {"user_session": "abc", "_gh_sess": "xyz"}

    def test_raw_cookie_header(self):
        out = credentials.parse_curl_cookie_header("Cookie: user_session=abc; logged_in=yes")
        assert out == {"user_session": "abc", "logged_in": "yes"}

    def test_bare(self):
        out = credentials.parse_curl_cookie_header("foo=bar")
        assert out == {"foo": "bar"}

    def test_values_with_equals(self):
        out = credentials.parse_curl_cookie_header("token=abc=def==; x=1")
        assert out["token"] == "abc=def=="
        assert out["x"] == "1"

    def test_skips_malformed(self):
        out = credentials.parse_curl_cookie_header("a=1; bad-no-equals; b=2")
        assert out == {"a": "1", "b": "2"}


class TestMissingRequired:
    def test_all_present(self):
        cookies = {"user_session": "a", "_gh_sess": "b"}
        assert credentials.missing_required(cookies) == []

    def test_missing_user_session(self):
        assert "user_session" in credentials.missing_required({"_gh_sess": "x"})

    def test_missing_all(self):
        assert set(credentials.missing_required({})) == set(credentials.REQUIRED_COOKIES)


class TestSaveLoadClear:
    def test_roundtrip(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GHSTARS_CONFIG_HOME", str(tmp_path))
        # Reload config so it picks up the new env
        from importlib import reload
        from ghstars import config as cfg
        reload(cfg)
        from ghstars import credentials as creds_mod
        reload(creds_mod)

        creds = creds_mod.Credentials(cookies={"user_session": "a", "_gh_sess": "b", "dotcom_user": "alice"})
        path = creds_mod.save(creds)
        assert path.exists()

        loaded = creds_mod.load()
        assert loaded is not None
        assert loaded.cookies == creds.cookies
        assert loaded.username == "alice"

        assert creds_mod.clear() is True
        assert creds_mod.load() is None
        assert creds_mod.clear() is False  # already gone
