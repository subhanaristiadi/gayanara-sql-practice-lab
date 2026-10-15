# Gayanara SQL Practice Lab — Backend Setup

This guide describes the current Render + Neon deployment and the optional local development setup.

## Current online deployment

- **Website:** https://subhanaristiadi.github.io/gayanara-sql-practice-lab/
- **Backend health check:** https://gayanara-sql-practice-lab-api-subhan.onrender.com/health
- **Repository:** https://github.com/subhanaristiadi/gayanara-sql-practice-lab

GitHub Pages serves the frontend, Render runs the Flask API, and Neon hosts PostgreSQL. When a user clicks **Submit Query**, the browser sends the submitted SQL and exercise ID. The API retrieves the matching reference query from the server-side `reference_queries.json` file.

## 1. Render configuration

The repository contains `render.yaml`. It configures the service with:

- **Runtime:** Python
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn server:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 35`
- **Health check:** `/health`
- **Plan:** Free

Keep the service on the Free plan unless you intentionally choose a paid plan. A Free web service may sleep after 15 minutes without inbound traffic; the first request after it sleeps can take longer.

### Environment variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Neon connection string for the dedicated `gayanara_reader` role |
| `CORS_ALLOWED_ORIGINS` | Exact frontend origin: `https://subhanaristiadi.github.io` |
| `REQUIRE_NON_SUPERUSER` | Keep `true` for the public deployment |
| `MAX_ROWS` | Maximum query rows returned; configured as 5000 in Render |
| `STATEMENT_TIMEOUT_MS` | Query timeout; configured as 10000 ms |
| `LOCK_TIMEOUT_MS` | Database lock wait limit; configured as 2000 ms |

Set these values in the Render service's Environment settings. Never put the full `DATABASE_URL` in source code, a committed file, README, screenshot, or chat message.

## 2. Neon database role

The API should connect as `gayanara_reader`, not as the Neon owner/admin role. The application role should:

- be a non-superuser;
- have CONNECT on the database and USAGE on schema `public`;
- have SELECT access to `customers`, `products`, `orders`, `order_items`, and `reviews`;
- have no database/schema creation privileges or table write privileges.

Use the Neon direct (non-pooled) connection string for this setup, with SSL required. Put it only in Render's `DATABASE_URL` setting. Do not share the password or complete connection string.

## 3. Verify the deployed API

Open:

https://gayanara-sql-practice-lab-api-subhan.onrender.com/health

A healthy response looks like:

```json
{"status":"ok","database":"neondb"}
```

If it returns an error, open the service's **Logs** in Render. Check that `DATABASE_URL` uses `gayanara_reader` and that this role can read all five tables.

Then open the website, go to **Core Sales KPIs → Order-Level KPIs (Revenue, Orders, AOV)**, and submit a valid query for that exercise. A successful validation shows **Correct**. This is a basic smoke test, not a full test of all 41 exercises.

## 4. Local development (optional)

Local development needs Python 3, PostgreSQL, and a database populated with the five Gayanara tables.

From the repository folder, install dependencies:

```bash
pip install -r requirements.txt
```

By default, `server.py` connects to `127.0.0.1:5432`, database `gayanara`, user `postgres`, and reads the password from `GAYANARA_DB_PASSWORD`. Set the variables to match your local PostgreSQL setup before running the backend. Do not commit local credentials.

PowerShell example for non-secret settings:

```powershell
$env:GAYANARA_DB_HOST = "127.0.0.1"
$env:GAYANARA_DB_PORT = "5432"
$env:GAYANARA_DB_NAME = "gayanara"
$env:GAYANARA_DB_USER = "postgres"
python server.py
```

Set `GAYANARA_DB_PASSWORD` privately in the same PowerShell session before running the server. If you use `DATABASE_URL` instead, the backend will prefer that connection string.

For local testing, change the `BACKEND_BASE` value in your **local copy** of `index.html` to `http://127.0.0.1:8765`. Do not commit that local-only URL to the public branch. Open the local `index.html` in a browser and keep the backend terminal running. Stop the backend with `Ctrl+C`.

## 5. API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Basic API status |
| GET | `/health` | Check backend-to-database connectivity |
| POST | `/validate` | Run user SQL and compare it to the reference; body: `{"user_sql":"SELECT ...","sub_id":"ex-03-s1"}` |
| POST | `/query` | Run one query; body: `{"sql":"SELECT ..."}` |
| GET | `/reference/<sub_id>` | Return the reference query for an exercise |

Equivalent `/api/...` routes are available where implemented.

## 6. Built-in safeguards

The backend:

- accepts one SELECT statement or SELECT-based CTE;
- uses read-only database transactions;
- verifies that the configured role is not a superuser and has no table write privileges;
- limits query duration, lock wait, output rows/bytes, request size, concurrency, and request rate;
- retrieves reference SQL from `reference_queries.json` instead of trusting a reference query sent by the browser;
- restricts cross-origin browser requests to the configured origin.

These controls reduce risk but do not make public SQL execution risk-free. Keep the database role restricted to this practice dataset and monitor Render and Neon usage.

## Troubleshooting

| Problem | Check |
|---|---|
| `/health` returns 503 | Review Render logs, `DATABASE_URL`, SSL, role privileges, and table/schema names. |
| First request is slow | The Render Free service may have been sleeping. Wait for it to wake, then retry. |
| Website shows Validation Unavailable | Hard-refresh the site, confirm the Render service is Live, then check browser Network and Render logs. |
| Query is rejected | Submit one read-only SELECT statement; avoid writes, DDL, transaction commands, and multiple statements. |
| Query times out | Simplify the query or process fewer rows. Avoid raising public limits just to bypass a timeout. |

Never share database passwords, full connection strings, private keys, or screenshots containing visible secrets when requesting help.
