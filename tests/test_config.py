from app.config import _setting


def test_setting_reads_a_file_under_secrets_dir(tmp_path, monkeypatch):
    (tmp_path / "DB_HOST").write_text("db.internal\n", encoding="utf-8")
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.setenv("SECRETS_DIR", str(tmp_path))
    assert _setting("DB_HOST") == "db.internal"
    monkeypatch.setenv("DB_HOST", "from-env")
    assert _setting("DB_HOST") == "from-env"
    assert _setting("MISSING", "fallback") == "fallback"
