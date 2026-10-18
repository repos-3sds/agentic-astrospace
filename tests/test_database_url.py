import pytest

from astrospace.db.database import _database_url


@pytest.mark.parametrize("marker", ["K_SERVICE", "CLOUD_RUN_JOB"])
def test_cloud_run_refuses_to_boot_on_sqlite(monkeypatch, marker):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    monkeypatch.setenv(marker, "agentic-astrospace")
    with pytest.raises(RuntimeError):
        _database_url()


def test_local_dev_still_falls_back_to_sqlite(monkeypatch):
    for name in ("DATABASE_URL", "SUPABASE_DB_URL", "K_SERVICE", "CLOUD_RUN_JOB"):
        monkeypatch.delenv(name, raising=False)
    assert _database_url().startswith("sqlite:///")


def test_postgres_urls_use_psycopg(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "agentic-astrospace")
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@h/db")
    assert _database_url() == "postgresql+psycopg://u:p@h/db"
