"""CORS origin assembly.

A Capacitor WebView calls the API from `https://localhost`, so it is a genuine
cross-origin caller and is blocked without an explicit entry. The failure shows
up only on device, and the app's own fallback ("Supabase is not configured
yet") makes it read as a configuration problem rather than a CORS one — so this
is worth pinning down rather than leaving to review.
"""
import importlib

import pytest


def _origins(monkeypatch, allowed: str | None):
    """Re-import main with ALLOWED_ORIGINS set, and read what CORS resolved to."""
    if allowed is None:
        monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("ALLOWED_ORIGINS", allowed)

    import main

    main = importlib.reload(main)
    for middleware in main.app.user_middleware:
        if "CORS" in str(middleware):
            return list(middleware.kwargs.get("allow_origins") or [])
    pytest.fail("CORS middleware is not installed")


NATIVE = {"https://localhost", "capacitor://localhost"}


class TestCorsOrigins:
    def test_native_origins_are_present_by_default(self, monkeypatch):
        assert NATIVE <= set(_origins(monkeypatch, None))

    def test_dev_origins_are_present_by_default(self, monkeypatch):
        resolved = set(_origins(monkeypatch, None))
        assert {"http://localhost:4200", "http://localhost:8000"} <= resolved

    def test_native_origins_survive_a_production_allowlist(self, monkeypatch):
        """The regression this guards.

        ALLOWED_ORIGINS replaces the dev defaults. While the native origins were
        bundled in with them, setting it to a real domain silently broke every
        native build — which is exactly what shipped to Cloud Run.
        """
        resolved = _origins(monkeypatch, "https://app.example.com")
        assert "https://app.example.com" in resolved
        assert NATIVE <= set(resolved)

    def test_a_production_allowlist_drops_the_dev_origins(self, monkeypatch):
        """Localhost dev origins have no business being allowed in production."""
        resolved = _origins(monkeypatch, "https://app.example.com")
        assert "http://localhost:4200" not in resolved

    def test_no_duplicates_when_an_origin_is_listed_twice(self, monkeypatch):
        resolved = _origins(monkeypatch, "https://localhost,https://app.example.com")
        assert len(resolved) == len(set(resolved))

    def test_blank_entries_are_ignored(self, monkeypatch):
        resolved = _origins(monkeypatch, "https://app.example.com, ,")
        assert "" not in resolved
        assert "https://app.example.com" in resolved

    @pytest.fixture(autouse=True)
    def _restore(self, monkeypatch):
        """Leave `main` as the rest of the suite expects to find it."""
        yield
        monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
        import main

        importlib.reload(main)
