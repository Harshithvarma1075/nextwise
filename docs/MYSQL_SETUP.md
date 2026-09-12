# MySQL setup and Phase 3 loading

## Prerequisites

Install and start **MySQL 8.0.16 or later** locally. MySQL 8.0.16+ is required because the schema uses enforced `CHECK` constraints in addition to foreign keys and unique indexes.

Create the application database once. Replace `your_mysql_admin_user` with a local MySQL administrator account:

```sql
CREATE DATABASE nxtwise_recommender
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

You may create a least-privilege application account instead of using the administrator account:

```sql
CREATE USER 'nxtwise_app'@'localhost' IDENTIFIED BY 'choose-a-strong-local-password';
GRANT ALL PRIVILEGES ON nxtwise_recommender.* TO 'nxtwise_app'@'localhost';
FLUSH PRIVILEGES;
```

## Local configuration

Copy `.env.example` to `.env` at the repository root. Do not commit `.env`. Set these values:

```dotenv
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=nxtwise_recommender
MYSQL_USER=nxtwise_app
MYSQL_PASSWORD=your-local-password
```

## Schema and load

Do **not** run the schema manually unless you want to inspect it. The loader creates the tables from `backend/app/db/schema.sql`, then loads the Phase 2 processed files transactionally and verifies row counts and foreign-key integrity.

From `D:\nextwise`, run:

```powershell
& 'C:\Users\Harshith Varma\AppData\Local\Python\pythoncore-3.14-64\python.exe' backend\app\db\loader.py --processed-dir data\processed
```

Expected load counts are 6,000 users, 2,465 products, and 675,004 interactions. A completed run prints the verified database counts. Re-running is safe: the loader uses parameterized upserts and the natural event uniqueness constraint.

## Authentication troubleshooting

If the loader reports MySQL error `1045` / `Access denied`, MySQL is running but rejected the configured user. Log in with a MySQL administrator account and either create the documented account or reset/grant the existing one:

```sql
CREATE USER IF NOT EXISTS 'nxt_app'@'localhost' IDENTIFIED BY 'your-local-password';
ALTER USER 'nxt_app'@'localhost' IDENTIFIED BY 'your-local-password';
GRANT ALL PRIVILEGES ON nxtwise_recommender.* TO 'nxt_app'@'localhost';
FLUSH PRIVILEGES;
```

Then set the same username and password in `.env` and rerun the loader. Do not share the password in chat or commit `.env`.

## Safety and data health

- Source CSVs are never read by the database loader; it only loads Phase 2 validated processed files.
- Users and products load before interactions in one transaction.
- Foreign keys prevent orphan interactions.
- The natural unique key prevents duplicate `(user_id, item_id, event_type, timestamp_unix)` event records.
- If any batch fails, the loader rolls back the transaction.
- Sparse ML matrices and recommender artifacts never enter MySQL.
