# Gayanara SQL Practice Lab

An interactive, portfolio-oriented SQL learning environment built around the **Gayanara** dataset — a simulated Indonesian online-fashion store (sourced from Ngulik Data). The application pairs structured, progressively-difficult SQL exercises with a local execution backend that runs your query and checks the result against a trusted reference query.

> **Live frontend:** [https://subhanaristiadi.github.io/gayanara-sql-practice-lab/](https://subhanaristiadi.github.io/gayanara-sql-practice-lab/)

---

## Overview

Gayanara SQL Practice Lab is a personal SQL practice tool. Each exercise presents:

- a **business question** and the analytical task to complete,
- the **metric definitions and filters** that apply,
- the **expected output table** (column names, grain, sort order) — a specification of the result, not a hidden answer key,
- the relevant **database schema**, and
- a collapsible **reference SQL** you can reveal only after attempting the task.

You write your PostgreSQL query in the in-app editor, save it to your browser, and (when the local backend is running) **Submit Query** to execute it and see whether the result matches the reference.

The project has three distinct parts that must not be confused:

| Part | Where it lives | Publicly reachable? |
|---|---|---|
| **Frontend** (`index.html`) | GitHub Pages | ✅ Yes — anyone can open the live URL |
| **Backend** (`server.py`) | Your local machine (`127.0.0.1:8765`) | ❌ No — runs only locally |
| **Database** (`gayanara`) | Your local PostgreSQL 16 | ❌ No — runs only locally |

The frontend being public **does not** mean the backend or the database is hosted online. Cloud deployment of those two is a future phase, not part of the current release.

### Full Dataset can be accessed/downloaded on: https://ngulikdata.com/datasets/gayanara

### How query submission and validation work

1. You click **Submit Query** in `index.html`.
2. The page POSTs your SQL *and* the exercise's reference SQL to the local backend endpoint `POST /validate`.
3. `server.py` runs **both** queries in separate `BEGIN READ ONLY` PostgreSQL transactions (10-second statement timeout, 10,000-row cap) and returns the two result sets — **no credentials or internal details are sent to the browser**.
4. The frontend compares the two result sets in the browser and reports a status:
   - **Correct** — your result matches the reference.
   - **Correct Result — Required Technique Not Used** — the result matches, but a technique the exercise asks you to practice (e.g. `RANK()`, `NTILE(4)`, `LAG()`, `CROSS JOIN`) was not detected in your SQL. This is a hint, not a rejection.
   - **Incorrect** — the query executed but the result differs; diagnostics (column/row counts, differing rows, extra/missing duplicates) are shown.
   - **Execution Error** — PostgreSQL rejected your query; the readable server-side error is shown and your SQL is preserved for correction.
   - **Validation Unavailable** — the backend or database is unreachable.

Result comparison is intentionally flexible: it accepts equivalent implementations (subqueries vs CTEs, `FILTER` vs `CASE WHEN`), compares the **entire** result (not a sample), distinguishes `NULL` from `0`, applies a small numeric tolerance for `ROUND()`/floating-point differences, preserves duplicate-row counts, and compares row order only when the exercise explicitly requires a sort order.

---

## Live Demo

**Frontend (public):** <https://subhanaristiadi.github.io/gayanara-sql-practice-lab/>

The frontend is publicly accessible through GitHub Pages. Anyone can open this URL to:

- browse all exercises and categories,
- search and filter,
- read each exercise's task, requirements, expected output, schema, and reference SQL,
- write SQL and save answers / notes to **their own** browser (via `localStorage`),
- track progress, and import/export their progress as JSON.

**What the live site does NOT do (by current design):**

- The **Submit Query** feature does **not** work on the live website. When `index.html` is served over `https://`, the application targets its own origin for the API. Because the backend and database are not hosted on GitHub Pages, those requests fail and Submit Query reports **Validation Unavailable**. This behavior is confirmed from the code (`getBackendBase()` in `index.html`) — it was not confirmed by a live browser test.
- The live site cannot reach a backend running on **your** (the visitor's) computer. A `https://` page cannot connect to `http://127.0.0.1` on the visitor's machine (mixed-content + same-origin restrictions).

Full local instructions for running the backend and using Submit Query are in **[Running the Application Locally](#running-the-application-locally)**.

---

## Features

All of the following are confirmed from the source code:

- **Structured exercises** — 20 parent topics containing 41 independently-answerable sub-exercises across 13 categories, from Beginner to Advanced (data quality → core KPIs → trends → geography/payment → product/brand → stock → customer analytics → cohort/retention → promotion → logistics → reviews → advanced SQL → executive insights).
- **Progressive learning path** with per-category progress bars.
- **Write SQL in-app** — a monospace editor with a `-- Write your PostgreSQL query here` placeholder.
- **Copy SQL** to the clipboard (for manual execution in pgAdmin 4 if you prefer).
- **Submit Query** — executes your query against the local PostgreSQL database and validates the result against the reference (requires the local backend; see above).
- **Flexible result validation** — accepts equivalent SQL, compares full results, respects required sort order, distinguishes `NULL` vs `0`, and applies a numeric tolerance.
- **Validation status banner** — Correct / Correct Result — Required Technique Not Used / Incorrect / Execution Error / Validation Unavailable / Running.
- **Save Answer / Reset** with a confirmation on reset.
- **Personal notes** per sub-exercise.
- **Completion tracking** per sub-exercise, with overall / parent / category progress.
- **View Data Schema** — a collapsible, per-exercise schema reference (relevant tables and columns only).
- **View Source SQL Reference** — a collapsible reference query (hidden by default so the answer is not revealed).
- **Search and filters** — by title, question, source filename, SQL concept, category; and by difficulty, category, and completion status.
- **Progress persistence** — answers, notes, completion, and validation results are stored in `localStorage` and survive refresh.
- **Import / Export** progress as a JSON file, and **Reset All** with explicit confirmation.
- **Works from the local filesystem** (`file://`) — no build step, no external libraries.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Single-file HTML5 + CSS3 + vanilla JavaScript (ES2017+, async/await) — no framework, no build system, no external dependencies |
| Backend | Python 3 (standard-library `http.server` + `psycopg2`) |
| Database | PostgreSQL 16 (local install in use: **16.15**) |
| Target SQL dialect | PostgreSQL 16 |
| Deployment (frontend only) | GitHub Pages |

Python dependency:

- `psycopg2-binary` (PostgreSQL adapter)

---

## Project Structure

```
gayanara/
├── README.md                          ← this file
├── customers.csv                      dataset source files
├── products.csv
├── orders.csv
├── order_items.csv
├── reviews.csv
│
├── docs/                              dataset & project documentation
│   ├── gayanara_business_questions.md
│   ├── gayanara_data_reference.md
│   └── gayanara_project_instructions.md
│
├── gayanara_sql_project/              the underlying SQL analytics project
│   ├── schema.sql                     table definitions (5 tables)
│   ├── load.sql                       CSV loader (\copy)
│   ├── readme.md                      setup & analytical roadmap
│   └── analysis/                      20 reference analysis scripts (01…20)
│
└── sql_practice_lab/                  the practice application
    ├── index.html                     the frontend (exercises, editor, validation UI)
    ├── server.py                      local backend (query execution + /health)
    ├── reference_queries.json         one reference query per sub-exercise (41)
    ├── generate_reference.py          optional: pre-cache reference results to disk
    └── backend_setup.md               backend-specific setup & API reference
```

File purpose (confirmed to exist):

- `index.html` — the entire frontend: exercise definitions, reference SQL (embedded for `file://` use), schema reference, editor, and the comparison engine.
- `server.py` — the local HTTP backend that executes SQL in read-only transactions and returns results.
- `reference_queries.json` — the 41 reference queries used for validation (one per sub-exercise).
- `generate_reference.py` — optional utility that runs the reference queries and writes results to `reference_results/` (the directory is created only when you run it).
- `backend_setup.md` — backend configuration, API endpoints, and troubleshooting.

> Note: a `reference_results/` directory does **not** exist until you run `generate_reference.py`. The default validation flow does not require it — the backend re-runs the reference query on each submission, so results always reflect the current database.

---

## Prerequisites

- **Python 3.8 or later** (3.13 was used during development).
- **PostgreSQL 16** running locally (local install in use: **16.15**).
- The **`gayanara`** database, loaded with the five source CSVs (see [Database Setup](#database-setup)).
- **`psycopg2-binary`** (installed via `pip`).
- A **modern web browser** (Chrome, Edge, Firefox, or Safari).
- `psql` available for the database load step (shipped with PostgreSQL).

---

## Database Setup

The `gayanara` database is built from the files in `gayanara_sql_project/` and the CSVs in the project root. The source of truth for this step is `gayanara_sql_project/readme.md` and `gayanara_sql_project/schema.sql` / `load.sql`.

- **Tables and expected row counts** (from `gayanara_sql_project/readme.md`):
  `customers` (800), `products` (300), `orders` (3,000), `order_items` (4,986), `reviews` (1,500).
- **Data period:** 2022-01-01 to 2025-02-28.

Steps:

1. **Create the database** (once). For example, with the standard PostgreSQL utility:
   ```powershell
   createdb gayanara
   ```
   (or create a database named `gayanara` in pgAdmin 4.)

2. **Load the schema and data.** `load.sql` uses `\copy` and reads the CSVs from the **current working directory**, so run these from the **project root** (where the CSVs live). The schema/loader files live one level down in `gayanara_sql_project/`:
   ```powershell
   psql -d gayanara -f gayanara_sql_project/schema.sql
   psql -d gayanara -f gayanara_sql_project/load.sql
   ```
   > If your `psql` client working directory differs, or your CSVs are stored elsewhere, update the paths inside `load.sql` — the loader reads files from the client machine, not the server.

3. **Confirm the load.**
   ```powershell
   psql -d gayanara -c "SELECT (SELECT COUNT(*) FROM orders) AS orders, (SELECT COUNT(*) FROM order_items) AS order_items;"
   ```

> **To verify:** this project does not ship a one-click import script. If you cannot confirm the `gayanara` database name, the table set, or the CSV locations on your machine, check `gayanara_sql_project/readme.md` and `load.sql` before proceeding. No schema or data is included in this README to avoid inventing definitions.

---

## Installation and Configuration (Windows / PowerShell)

1. **Open a terminal in the project root.**
   ```powershell
   cd C:\path\to\gayanara\sql_practice_lab
   ```
   (You can also `cd` here from the project root; the backend lives in `sql_practice_lab/`.)

2. **Install the Python dependency.**
   ```powershell
   python -m pip install psycopg2-binary
   ```

3. **Confirm your database connection settings.** The backend reads connection details from environment variables (defaults below). The one you almost always must set is the **password**.

4. **Set `GAYANARA_DB_PASSWORD` for this session** (replace with *your* password — never a placeholder that matches a real secret you intend to commit):
   ```powershell
   $env:GAYANARA_DB_PASSWORD = "YOUR_DB_PASSWORD"
   ```
   > This sets the variable for the current PowerShell session only. It is not written to disk and is not committed.

5. **Other supported variables and defaults** (all optional unless noted):
   ```powershell
   $env:GAYANARA_DB_HOST   = "127.0.0.1"   # default
   $env:GAYANARA_DB_PORT   = "5432"        # default
   $env:GAYANARA_DB_NAME   = "gayanara"    # default
   $env:GAYANARA_DB_USER   = "postgres"    # default
   $env:GAYANARA_LAB_PORT  = "8765"        # default
   ```

6. **Start the backend.**
   ```powershell
   python server.py
   ```
   Keep this window open while you use Submit Query (see [Running the Application Locally](#running-the-application-locally)).

> **Never** put a database password in `index.html`, any JavaScript, or a committed configuration file. Environment variables (or a git-ignored local config) are the supported way to supply secrets.

---

## Using the Live Website

- **Without a local backend**, visitors can use everything read/interactive in the browser: browse/search/filter exercises, read tasks and expected output, view the schema and reference SQL, write and **save** SQL/notes (stored in *the visitor's* `localStorage`), track completion, and import/export progress JSON.
- **Submit Query requires** both a running local backend (`server.py`) **and** the local `gayanara` PostgreSQL database.
- **The live GitHub Pages site cannot connect to a backend on the visitor's computer.** When the page is loaded from `https://`, the app targets its own origin for the API; since there is no backend on GitHub Pages, Submit Query reports **Validation Unavailable**. This is a limitation of the current configuration, not a bug — and it was derived from the `getBackendBase()` code path, not verified with a live browser test.
- To use Submit Query, open `index.html` **locally** (`file://`) with the backend running on `127.0.0.1:8765` — see below.

---

## Running the Application Locally

1. **Ensure PostgreSQL is running** and the `gayanara` database is loaded (see [Database Setup](#database-setup)).
2. **Open PowerShell in the project directory.**
   ```powershell
   cd C:\path\to\gayanara\sql_practice_lab
   ```
3. **Configure the environment variables** (at minimum the password).
   ```powershell
   $env:GAYANARA_DB_PASSWORD = "YOUR_DB_PASSWORD"
   ```
4. **Start the backend.**
   ```powershell
   python server.py
   ```
   The console prints the target database, the listening URL (`http://127.0.0.1:8765`), and the limits.
5. **Confirm the database connection.** On a healthy start you will see a line like:
   ```
   DB connected: PostgreSQL 16.15
   ```
   If you instead see `WARNING: Cannot connect to database: ...`, fix the password/user and restart.
6. **Verify the health endpoint.** In a second terminal, or a browser:
   ```powershell
   Invoke-WebRequest "http://127.0.0.1:8765/health" -UseBasicParsing
   ```
   A healthy response is `{"status": "ok", "database": "gayanara"}`.
7. **Open the frontend.** With the backend running, open the local file:
   ```powershell
   start .\index.html
   ```
   (Opening `index.html` via `file://` makes the app target `http://127.0.0.1:8765`.)
8. **Pick an exercise and submit a query.** Navigate to a sub-exercise, write SQL, and click **Submit Query**.
9. **Read the result and validation status.** The banner shows the status and, for Incorrect results, diagnostics; Execution Error shows the SQL error; and the footer line reports execution time and row/column counts.
10. **Keep the backend terminal open.** Submit Query requires the process to be alive.
11. **Stop / restart as needed.** Press `Ctrl+C` in the backend terminal to stop. Restart with `python server.py` (re-setting the password variable if you reopened the terminal).

> The backend stops when the computer shuts down or when the process is terminated — it is not a service. Every session that uses Submit Query needs it running.

---

## Example SQL Query

A simple, valid query against a real table (`orders`) and column (`order_status`):

```sql
SELECT order_status, COUNT(*) AS orders
FROM orders
GROUP BY order_status
ORDER BY orders DESC;
```

**How to submit it through the application:**

1. Open `index.html` locally with the backend running.
2. Choose the sub-exercise whose task matches this question (for example, the order status distribution sub-exercise), or any exercise where you simply want to test execution.
3. Paste the query into the **Your SQL Answer** editor.
4. Click **Submit Query**.
5. Read the banner. The exact row values depend on the current contents of your `gayanara` database, so the expected numbers are intentionally **not** stated here — run it to see your result.

> Tip: if you only want to run queries in pgAdmin 4 instead, use **Copy SQL** and paste into pgAdmin. The application does not claim pgAdmin equivalence, and validation status is separate from whether you "saved" an answer.

---

## Environment Variables

All supported by `server.py` (confirmed from the source):

| Variable | Purpose | Default |
|---|---|---|
| `GAYANARA_DB_HOST` | PostgreSQL host | `127.0.0.1` |
| `GAYANARA_DB_PORT` | PostgreSQL port | `5432` |
| `GAYANARA_DB_NAME` | Database name | `gayanara` |
| `GAYANARA_DB_USER` | Database user | `postgres` |
| `GAYANARA_DB_PASSWORD` | Database password — **required** for most setups | *(empty)* |
| `GAYANARA_LAB_PORT` | Port the backend listens on | `8765` |

Additional backend behavior (fixed in code, not configurable by variable):

- Statement timeout: **10,000 ms** per query.
- Maximum returned rows: **10,000** (results are flagged `truncated` when this cap is hit).
- The server binds to **`127.0.0.1` only** (localhost).

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `fe_sendauth: no password supplied` | `GAYANARA_DB_PASSWORD` is not set for the backend session. Set it (Step H.4) and restart `server.py`. |
| Wrong/invalid credentials | Confirm `GAYANARA_DB_USER`, `GAYANARA_DB_NAME`, host, and port against your PostgreSQL setup. The backend prints the target on start. |
| Backend says "Cannot connect to database" | PostgreSQL service not started, or the port/host is wrong. Start PostgreSQL and re-check `GAYANARA_DB_HOST`/`PORT`. |
| Port 8765 already in use | Set a different port: `$env:GAYANARA_LAB_PORT = "8766"`, and point the frontend at it via `BACKEND_BASE` in `index.html` (e.g. `const BACKEND_BASE = "http://127.0.0.1:8766";`). |
| Submit Query shows **Validation Unavailable** | The backend isn't running, the DB password is wrong, or you're using the live website (which has no reachable backend). Run `python server.py`, confirm `/health` returns ok, and open `index.html` locally. |
| **Execution Error** banner | Your SQL was rejected by PostgreSQL. Read the error text in the banner, fix the query, and resubmit. |
| "Query exceeded the 10-second timeout" | The query is too heavy for the dataset/limits. Simplify it (e.g. avoid unbounded self-joins) or raise `STATEMENT_TIMEOUT_MS` in `server.py` if you accept the risk. |
| "Result was truncated at 10,000 rows" | Your result exceeded the row cap. Add `LIMIT` / filters so the comparison is meaningful. |
| "No reference SQL available for this sub-exercise" | The sub-exercise has no entry in `reference_queries.json` / the embedded `REF_SQL`. This should not happen for the shipped set (41 sub-exercises all have references); check that your `index.html` is not out of sync with `reference_queries.json`. |
| Submit Query not working on the live site | Expected — see [Using the Live Website](#using-the-live-website). Use the local workflow instead. |

Useful checks:

```powershell
# Is the backend up and is the DB reachable?
Invoke-WebRequest "http://127.0.0.1:8765/health" -UseBasicParsing

# Is PostgreSQL up?
psql -d gayanara -c "SELECT 1;"

# Is the DB port busy by something else?
Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue
```

> Some troubleshooting items describe behavior observed in this environment; others (e.g. specific error text under unusual network conditions) may need to be checked against `server.py` if you modify it.

---

## Security Notes

- **Never commit passwords or secrets.** Connection details are read from environment variables at runtime; nothing secret is stored in `index.html`, JavaScript, or committed config.
- **The backend is bound to `127.0.0.1` only** (`server.py` listens on `HTTPServer(("127.0.0.1", LAB_PORT)`), so it is not reachable from other machines by default. Keep it that way for local use.
- **All queries run in a `BEGIN READ ONLY` transaction** — the backend will not perform writes, DDL, or DML through this interface, and a 10-second timeout plus a 10,000-row cap bound resource use.
- **A dedicated read-only PostgreSQL role is strongly preferred** over using the `postgres` superuser. Even with read-only transactions, the *role* you connect as determines what the database will allow; a role limited to `SELECT` on the five `gayanara` tables is the least-privilege option. (The app does not itself create such a role — that is a database-admin task you should perform in PostgreSQL if you want the strongest isolation.)
- **The backend must stay running** for Submit Query to work; stopping it makes validation unavailable until it is restarted.
- **The public frontend cannot reach the developer's local PostgreSQL.** GitHub Pages serves static files only and cannot proxy to a private database; there is no server-side proxy in the current deployment. This is why live-site Submit Query reports Validation Unavailable.

---

## Current Scope and Limitations

- The **frontend is live** on GitHub Pages at the URL above.
- The **Python backend runs locally** (`127.0.0.1:8765`); it is not hosted online.
- **PostgreSQL 16 runs locally**; the `gayanara` database is not hosted online.
- **Interactive SQL execution and answer validation depend on the local backend + database.** They work when you run the documented local workflow.
- **Cloud deployment of the backend and database has not been completed.** Do not present the live site as offering online SQL execution to the public.
- Live-website Submit Query reports **Validation Unavailable** in the current configuration (see [Using the Live Website](#using-the-live-website)).

---

## Future Improvements

The following are **possibilities for a future phase**, not features that exist today:

- Hosting the Python backend online (e.g. on a PaaS) so Submit Query works from the live site.
- Hosting PostgreSQL in a managed cloud database.
- Enabling **secure, public** SQL execution with a dedicated read-only role, credentials managed on the server, and no secrets in the browser.
- Strengthening the API: per-client rate limiting, stronger query resource limits, an allow-list of permitted statements, and structured audit logging.
- Optional pre-cached reference results served from `reference_results/` for faster, offline-capable validation.
