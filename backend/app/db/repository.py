"""Read-only, parameterized MySQL access for the recommendation API."""
from __future__ import annotations

from datetime import timezone
from datetime import timezone
from typing import Any, Iterable

from backend.app.db.loader import connect, load_dotenv, settings_from_environment


class DatabaseUnavailableError(RuntimeError):
    """Raised when the API cannot safely query the configured catalog database."""


class CatalogRepository:
    def _connection(self):
        try:
            load_dotenv()
            return connect(settings_from_environment())
        except Exception as exc:
            raise DatabaseUnavailableError("Catalog database is unavailable") from exc

    def ping(self) -> None:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception as exc:
            raise DatabaseUnavailableError("Catalog database health check failed") from exc
        finally:
            connection.close()

    def list_users(self, limit: int, search: str | None = None) -> list[dict[str, Any]]:
        if not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        if search is not None and (not search.isdigit() or len(search) > 20):
            raise ValueError("search must contain up to 20 digits")
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                if search:
                    cursor.execute("SELECT user_id, age, gender FROM users WHERE CAST(user_id AS CHAR) LIKE %s ORDER BY user_id LIMIT %s", (f"{search}%", limit))
                else:
                    cursor.execute("SELECT user_id, age, gender FROM users ORDER BY user_id LIMIT %s", (limit,))
                rows = cursor.fetchall()
            return [{"user_id": int(row[0]), "age": int(row[1]), "gender": str(row[2])} for row in rows]
        except Exception as exc:
            raise DatabaseUnavailableError("Could not retrieve users") from exc
        finally:
            connection.close()

    def get_user(self, user_id: int) -> dict[str, Any] | None:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id, age, gender FROM users WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
            return None if row is None else {"user_id": int(row[0]), "age": int(row[1]), "gender": str(row[2])}
        except Exception as exc:
            raise DatabaseUnavailableError("Could not retrieve user") from exc
        finally:
            connection.close()

    def recent_activity(self, user_id: int, limit: int) -> list[dict[str, Any]]:
        if not isinstance(limit, int) or not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20")
        query = """SELECT i.event_type, i.event_timestamp, p.item_id, p.product_name, p.category_l2
                   FROM interactions i JOIN products p ON p.item_id = i.item_id
                   WHERE i.user_id = %s
                   ORDER BY i.timestamp_unix DESC, i.interaction_id DESC LIMIT %s"""
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, (user_id, limit))
                rows = cursor.fetchall()
            activity = []
            for row in rows:
                timestamp = row[1]
                if not hasattr(timestamp, "replace"):
                    raise DatabaseUnavailableError("Catalog activity has an invalid timestamp")
                activity.append({"event_type": str(row[0]), "event_timestamp": timestamp.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"), "item_id": str(row[2]), "product_name": str(row[3]), "category_l2": str(row[4])})
            return activity
        except DatabaseUnavailableError:
            raise
        except Exception as exc:
            raise DatabaseUnavailableError("Could not retrieve recent activity") from exc
        finally:
            connection.close()

    def get_products_by_ids(self, item_ids: Iterable[str]) -> list[dict[str, Any]]:
        normalized = [str(item_id) for item_id in item_ids]
        if not normalized:
            return []
        if len(normalized) != len(set(normalized)):
            raise ValueError("item IDs must be unique")
        placeholders = ", ".join(["%s"] * len(normalized))
        query = f"SELECT item_id, price, category_l1, category_l2, product_name, product_description, gender, promoted_status FROM products WHERE item_id IN ({placeholders})"
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, tuple(normalized))
                rows = cursor.fetchall()
            products = {str(row[0]): {"item_id": str(row[0]), "price": float(row[1]), "category_l1": str(row[2]), "category_l2": str(row[3]), "product_name": str(row[4]), "product_description": str(row[5]), "gender": str(row[6]), "promoted_status": str(row[7])} for row in rows}
            missing = set(normalized).difference(products)
            if missing:
                raise DatabaseUnavailableError("Model output contains products unavailable in the catalog")
            return [products[item_id] for item_id in normalized]
        except DatabaseUnavailableError:
            raise
        except Exception as exc:
            raise DatabaseUnavailableError("Could not retrieve products") from exc
        finally:
            connection.close()
