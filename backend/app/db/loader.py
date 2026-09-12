"""Transactional MySQL loader for validated Phase 2 processed CSVs."""
from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    database: str
    user: str
    password: str


TABLES = {
    "users": ("users_processed.csv", ("user_id", "age", "gender")),
    "products": (
        "items_processed.csv",
        ("item_id", "price", "category_l1", "category_l2", "product_name", "product_description", "gender", "promoted_status"),
    ),
    "interactions": (
        "interactions_processed.csv",
        ("user_id", "item_id", "event_type", "timestamp_unix", "event_timestamp", "discount_applied"),
    ),
}

UPSERTS = {
    "users": """
        INSERT INTO users (user_id, age, gender) VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE age = VALUES(age), gender = VALUES(gender)
    """,
    "products": """
        INSERT INTO products (item_id, price, category_l1, category_l2, product_name, product_description, gender, promoted_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE price = VALUES(price), category_l1 = VALUES(category_l1), category_l2 = VALUES(category_l2),
            product_name = VALUES(product_name), product_description = VALUES(product_description), gender = VALUES(gender),
            promoted_status = VALUES(promoted_status)
    """,
    "interactions": """
        INSERT INTO interactions (user_id, item_id, event_type, timestamp_unix, event_timestamp, discount_applied)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE event_timestamp = VALUES(event_timestamp), discount_applied = VALUES(discount_applied)
    """,
}


def load_dotenv(path: Path = Path(".env")) -> None:
    """Load simple KEY=VALUE pairs without adding a configuration dependency."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def settings_from_environment() -> DatabaseSettings:
    values = {key: os.getenv(key, "").strip() for key in ("MYSQL_HOST", "MYSQL_PORT", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD")}
    missing = [key for key, value in values.items() if not value or value == "replace_me"]
    if missing:
        raise ValueError(f"Missing valid database environment value(s): {', '.join(missing)}")
    try:
        port = int(values["MYSQL_PORT"])
    except ValueError as error:
        raise ValueError("MYSQL_PORT must be an integer") from error
    if not 1 <= port <= 65535:
        raise ValueError("MYSQL_PORT must be between 1 and 65535")
    return DatabaseSettings(values["MYSQL_HOST"], port, values["MYSQL_DATABASE"], values["MYSQL_USER"], values["MYSQL_PASSWORD"])


def read_csv_rows(path: Path, columns: tuple[str, ...]) -> Iterable[tuple[str, ...]]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing processed file: {path}")
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or set(columns).difference(reader.fieldnames):
            raise ValueError(f"{path.name} does not have the required processed schema")
        for row in reader:
            if any(row[column] in (None, "") for column in columns):
                raise ValueError(f"{path.name} has an empty value required for database loading")
            yield tuple(row[column] for column in columns)


def chunked(rows: Iterable[tuple[str, ...]], size: int) -> Iterable[list[tuple[str, ...]]]:
    if size < 1:
        raise ValueError("batch size must be positive")
    batch: list[tuple[str, ...]] = []
    for row in rows:
        batch.append(row)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def database_rows(table_name: str, rows: Iterable[tuple[str, ...]]) -> Iterable[tuple[object, ...]]:
    """Convert validated CSV text to the small set of MySQL-specific values required."""
    for row in rows:
        if table_name == "interactions":
            *event_values, discount_applied = row
            if discount_applied not in {"True", "False"}:
                raise ValueError("interactions_processed.csv has an invalid discount_applied value")
            yield (*event_values, 1 if discount_applied == "True" else 0)
        else:
            yield row


def apply_schema(connection, schema_path: Path) -> None:
    if not schema_path.is_file():
        raise FileNotFoundError(f"Missing schema file: {schema_path}")
    statements = [statement.strip() for statement in schema_path.read_text(encoding="utf-8").split(";") if statement.strip()]
    with connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)


def load_processed_data(connection, processed_dir: Path, batch_size: int = 10_000) -> dict[str, int]:
    """Upsert validated files in FK order; rollback the complete load on any error."""
    counts: dict[str, int] = {}
    try:
        with connection.cursor() as cursor:
            for table_name in ("users", "products", "interactions"):
                filename, columns = TABLES[table_name]
                loaded = 0
                rows = database_rows(table_name, read_csv_rows(processed_dir / filename, columns))
                for batch in chunked(rows, batch_size):
                    cursor.executemany(UPSERTS[table_name], batch)
                    loaded += len(batch)
                counts[table_name] = loaded
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return counts


def verify_database(connection, expected_counts: dict[str, int]) -> dict[str, int]:
    with connection.cursor() as cursor:
        actual: dict[str, int] = {}
        for table in ("users", "products", "interactions"):
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            actual[table] = int(cursor.fetchone()[0])
        cursor.execute("""
            SELECT COUNT(*) FROM interactions i
            LEFT JOIN users u ON i.user_id = u.user_id
            LEFT JOIN products p ON i.item_id = p.item_id
            WHERE u.user_id IS NULL OR p.item_id IS NULL
        """)
        orphan_count = int(cursor.fetchone()[0])
    if orphan_count:
        raise RuntimeError(f"Database integrity check found {orphan_count} interactions")
    for table, expected in expected_counts.items():
        if actual[table] < expected:
            raise RuntimeError(f"Database has fewer {table} rows ({actual[table]}) than loaded ({expected})")
    return actual


def connect(settings: DatabaseSettings):
    try:
        import pymysql
    except ImportError as error:
        raise RuntimeError("PyMySQL is required; install requirements.txt before database loading") from error
    return pymysql.connect(
        host=settings.host, port=settings.port, user=settings.user, password=settings.password,
        database=settings.database, charset="utf8mb4", autocommit=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Load processed Amazon retail data into MySQL.")
    parser.add_argument("--processed-dir", type=Path, required=True)
    parser.add_argument("--schema", type=Path, default=Path("backend/app/db/schema.sql"))
    parser.add_argument("--batch-size", type=int, default=10_000)
    args = parser.parse_args()
    load_dotenv()
    settings = settings_from_environment()
    connection = connect(settings)
    try:
        apply_schema(connection, args.schema)
        counts = load_processed_data(connection, args.processed_dir, args.batch_size)
        print(verify_database(connection, counts))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
