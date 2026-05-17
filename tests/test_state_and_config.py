"""State + settings round-trip and validation."""
import json

from ghstars.config import (
    MAX_REASONABLE_JITTER,
    MIN_ALLOWED_JITTER,
    Settings,
    load_settings,
    save_settings,
)


class TestSettingsValidation:
    def test_defaults_ok(self):
        assert Settings().validate() == []

    def test_jitter_min_too_small(self):
        issues = Settings(jitter_min=MIN_ALLOWED_JITTER - 0.1).validate()
        assert any("below the floor" in i for i in issues)

    def test_jitter_min_greater_than_max(self):
        issues = Settings(jitter_min=5.0, jitter_max=2.0).validate()
        assert any("jitter_max must be >=" in i for i in issues)

    def test_jitter_max_huge(self):
        issues = Settings(jitter_max=MAX_REASONABLE_JITTER + 1).validate()
        assert any("huge" in i for i in issues)

    def test_negative_retries(self):
        issues = Settings(retry_attempts=-1).validate()
        assert any("retry_attempts" in i for i in issues)


class TestSettingsRoundtrip:
    def test_roundtrip(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GHSTARS_CONFIG_HOME", str(tmp_path))
        from importlib import reload
        from ghstars import config as cfg
        reload(cfg)
        s = cfg.Settings(jitter_min=2.0, jitter_max=4.0, retry_attempts=6)
        cfg.save_settings(s)
        loaded = cfg.load_settings()
        assert loaded.jitter_min == 2.0
        assert loaded.jitter_max == 4.0
        assert loaded.retry_attempts == 6

    def test_load_when_file_missing_returns_defaults(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GHSTARS_CONFIG_HOME", str(tmp_path))
        from importlib import reload
        from ghstars import config as cfg
        reload(cfg)
        loaded = cfg.load_settings()
        assert loaded == cfg.Settings()

    def test_load_ignores_unknown_keys(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GHSTARS_CONFIG_HOME", str(tmp_path))
        from importlib import reload
        from ghstars import config as cfg
        reload(cfg)
        cfg.ensure_dirs()
        cfg.SETTINGS_FILE.write_text(json.dumps({
            "jitter_min": 1.7,
            "this_key_does_not_exist": 999,
        }))
        loaded = cfg.load_settings()
        assert loaded.jitter_min == 1.7
        # other fields keep defaults
        assert loaded.jitter_max == cfg.Settings().jitter_max


class TestStateRoundtrip:
    def test_roundtrip(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GHSTARS_CONFIG_HOME", str(tmp_path))
        from importlib import reload
        from ghstars import config as cfg
        from ghstars import state as state_mod
        reload(cfg)
        reload(state_mod)

        s = state_mod.State(username="alice")
        s.created_lists["My Stack"] = 123
        s.created_lists["Inspiration"] = 456
        s.assigned_repos.add("foo/bar")
        s.assigned_repos.add("baz/qux")
        s.save()

        loaded = state_mod.State.load("alice")
        assert loaded.username == "alice"
        assert loaded.created_lists == {"My Stack": 123, "Inspiration": 456}
        assert loaded.assigned_repos == {"foo/bar", "baz/qux"}

    def test_load_missing_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GHSTARS_CONFIG_HOME", str(tmp_path))
        from importlib import reload
        from ghstars import config as cfg
        from ghstars import state as state_mod
        reload(cfg)
        reload(state_mod)
        loaded = state_mod.State.load("never-seen-user")
        assert loaded.created_lists == {}
        assert loaded.assigned_repos == set()

    def test_reset_clears(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GHSTARS_CONFIG_HOME", str(tmp_path))
        from importlib import reload
        from ghstars import config as cfg
        from ghstars import state as state_mod
        reload(cfg)
        reload(state_mod)

        s = state_mod.State(username="alice")
        s.created_lists["x"] = 1
        s.assigned_repos.add("y/z")
        s.save()
        s.reset()
        loaded = state_mod.State.load("alice")
        assert loaded.created_lists == {}
        assert loaded.assigned_repos == set()
