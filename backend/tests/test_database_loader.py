import csv

import pytest

from backend.app.db.loader import database_rows, chunked, load_dotenv, read_csv_rows, settings_from_environment


def test_chunked_preserves_rows_and_batch_boundaries():
    assert list(chunked([(1,), (2,), (3,)], 2)) == [[(1,), (2,)], [(3,)]]


def test_chunked_rejects_nonpositive_batch_size():
    with pytest.raises(ValueError, match="positive"):
        list(chunked([], 0))


def test_read_csv_rows_validates_schema_and_values(tmp_path):
    valid = tmp_path / "users_processed.csv"
    with valid.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["user_id", "age", "gender"])
        writer.writeheader()
        writer.writerow({"user_id": "1", "age": "25", "gender": "F"})
    assert list(read_csv_rows(valid, ("user_id", "age", "gender"))) == [("1", "25", "F")]

    invalid = tmp_path / "invalid.csv"
    invalid.write_text("user_id,age\n1,25\n", encoding="utf-8")
    with pytest.raises(ValueError, match="required processed schema"):
        list(read_csv_rows(invalid, ("user_id", "age", "gender")))


def test_database_settings_reject_placeholder_credentials(monkeypatch):
    monkeypatch.setenv("MYSQL_HOST", "localhost")
    monkeypatch.setenv("MYSQL_PORT", "3306")
    monkeypatch.setenv("MYSQL_DATABASE", "nxtwise_recommender")
    monkeypatch.setenv("MYSQL_USER", "replace_me")
    monkeypatch.setenv("MYSQL_PASSWORD", "replace_me")
    with pytest.raises(ValueError, match="Missing valid database"):
        settings_from_environment()


def test_load_dotenv_does_not_override_existing_environment(tmp_path, monkeypatch):
    dotenv = tmp_path / ".env"
    dotenv.write_text("MYSQL_HOST=file-host\nMYSQL_PORT=3307\n", encoding="utf-8")
    monkeypatch.setenv("MYSQL_HOST", "environment-host")
    load_dotenv(dotenv)
    assert __import__("os").environ["MYSQL_HOST"] == "environment-host"
    assert __import__("os").environ["MYSQL_PORT"] == "3307"


def test_database_rows_converts_boolean_csv_values_for_mysql():
    rows = [("1", "item", "View", "100", "2025-01-01 00:00:00+00:00", "False")]
    assert list(database_rows("interactions", rows)) == [
        ("1", "item", "View", "100", "2025-01-01 00:00:00+00:00", 0)
    ]
    with pytest.raises(ValueError, match="invalid discount"):
        list(database_rows("interactions", [("1", "item", "View", "100", "time", "maybe")]))
