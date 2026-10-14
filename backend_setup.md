# Gayanara SQL Practice Lab — Backend Setup

The **Submit Query** feature requires a local backend that:
1. Runs the user's SQL against your PostgreSQL 16 Gayanara database.
2. Runs the reference SQL for the current sub-exercise.
3. Returns both result sets to the browser for comparison.

## Prerequisites

- Python 3.8+
- `psycopg2-binary` (PostgreSQL driver)
- PostgreSQL 16 running locally with the `gayanara` database loaded

## Install

```bash
pip install psycopg2-binary
```

## Configure

Set these environment variables before starting the server (or use the defaults):

| Variable | Default | Description |
|---|---|---|
| `GAYANARA_DB_HOST` | `127.0.0.1` | PostgreSQL host |
| `GAYANARA_DB_PORT` | `5432` | PostgreSQL port |
| `GAYANARA_DB_NAME` | `gayanara` | Database name |
| `GAYANARA_DB_USER` | `postgres` | Database user |
| `GAYANARA_DB_PASSWORD` | *(empty)* | **Required** for most setups |
| `GAYANARA_LAB_PORT` | `8765` | Port the lab backend listens on |

On Windows:
```powershell
$env:GAYANARA_DB_PASSWORD = "your_password"
python server.py
```

Or create a `config.ps1` / `.env` file and load it before starting.

## Start the server

```bash
python server.py
```

Expected output:
```
Gayanara SQL Practice Lab Backend
  Database: gayanara@127.0.0.1:5432 (user: postgres)
  Listening on http://127.0.0.1:8765
  Max rows: 10000, Timeout: 10000ms
  ...
  DB connected: PostgreSQL 16.x
  Server started. Press Ctrl+C to stop.
```

If you see `WARNING: Cannot connect to database`, the password or user is wrong.
Fix the environment variable and restart.

## Usage

1. Open `index.html` in your browser (as before).
2. Navigate to any sub-exercise.
3. Write your SQL in the editor.
4. Click **Submit Query**.

The backend will:
- Run your query in a **READ ONLY** transaction.
- Run the reference query in a separate READ ONLY transaction.
- Return both result sets to the browser.
- The browser compares them and shows the result (Correct / Incorrect / Execution Error).

## Security

- The server binds to `127.0.0.1` only (no network access).
- All queries run in a `BEGIN READ ONLY` transaction — no writes, no DDL.
- `statement_timeout = 10000` (10 seconds) per query.
- Maximum 10,000 rows returned per query.
- No credentials are exposed to the browser.
- The database user should have only `SELECT` privileges on the `gayanara` database if possible.

## Optional: Pre-generate reference results

If you prefer to cache reference results on disk instead of re-running them on every submission:

```bash
python generate_reference.py
```

This reads `reference_queries.json`, executes each query, and saves the results to `reference_results/<sub_id>.json`. The server can then serve these cached results via `GET /reference/<sub_id>` instead of re-running the reference query.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Check backend + DB connectivity |
| `POST` | `/query` | Execute a single user query. Body: `{"sql": "..."}` |
| `POST` | `/validate` | Execute user + reference query. Body: `{"user_sql": "...", "ref_sql": "..."}` |
| `GET` | `/reference/<sub_id>` | Serve cached reference result (if generated) |

## Troubleshooting

- **"Validation Unavailable" in the browser** → The backend is not running, or the DB password is wrong. Check the terminal where `server.py` is running.
- **"Database connection problem"** → The password or user is incorrect. Check the environment variable.
- **"Query exceeded the 10-second timeout"** → The query is too complex. Simplify it or increase `STATEMENT_TIMEOUT_MS` in `server.py`.
- **Port already in use** → Change `GAYANARA_LAB_PORT` to a different port (e.g. 8766) and update `BACKEND_BASE` in `index.html` to match.
