# Gayanara SQL Practice Lab

An interactive SQL practice website built around the **Gayanara** dataset, a simulated Indonesian online fashion store from Ngulik Data. Exercises progress from foundational SQL to joins, CTEs, window functions, customer analytics, and data-quality checks.

## Dataset Source

The Gayanara dataset was sourced from **Ngulik Data**. It represents a simulated Indonesian online fashion store and is used for SQL practice and business analytics.

**Original dataset:** [Gayanara — Ngulik Data](https://ngulikdata.com/datasets/gayanara)

All analysis in this project is based on the dataset provided for this project. Business interpretations and findings are limited to the available data and documented business rules.

## Live Demo

- **Website:** https://subhanaristiadi.github.io/gayanara-sql-practice-lab/
- **Backend health:** https://gayanara-sql-practice-lab-api-subhan.onrender.com/health

The services are hosted separately: GitHub Pages serves the frontend, Render runs the Python API, and Neon hosts PostgreSQL.

## What the app includes

- 41 sub-exercises organized by topic and difficulty.
- Business questions, requirements, metric definitions, and expected output specifications.
- A SQL editor with automatic result comparison.
- Browser-based saving for answers, notes, and progress.
- Import and export of progress as JSON.

Progress is stored in your browser's local storage. It is not synced between devices or browsers.

## Technology

| Component | Technology | Purpose |
|---|---|---|
| Frontend | HTML, CSS, JavaScript | Exercise interface and result comparison |
| API | Python, Flask, Gunicorn | Executes and validates submitted SQL |
| Database | PostgreSQL on Neon | Stores the Gayanara dataset |
| Frontend hosting | GitHub Pages | Publishes the website |
| API hosting | Render | Runs the backend service |

## How Submit Query works

1. The browser sends your SQL and the current exercise ID to the Render API.
2. The API finds the matching reference query in `reference_queries.json` on the server.
3. The API runs the reference and user queries under read-only database transactions and returns their results.
4. The browser compares the result sets and displays **Correct**, **Incorrect**, or an error status, with row/column counts and diagnostics where applicable.

The application does not currently display the entire query result as a separate results table. The comparison checks results, not just the number of rows. Since this is a learning project, matching output does not prove that the SQL is the only correct solution.

## Database

The project uses five tables:

- `customers` — one row per customer
- `products` — one row per product
- `orders` — one row per order
- `order_items` — one row per product line
- `reviews` — one row per review

The exercises use the documented relationships between these tables. Standard sales KPIs exclude orders with status `cancelled` or `returned`. Each exercise describes its own metric definitions and filters.

## Run locally (optional)

The hosted website can be used without installing anything. To run your own local backend, you need Python 3, a PostgreSQL database loaded with the five Gayanara tables, and the dependencies in `requirements.txt`.

1. Download or clone this repository.
2. From the repository folder, install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set the local database connection variables for `server.py`. Its local defaults are database `gayanara` on `127.0.0.1:5432`, user `postgres`, and password from `GAYANARA_DB_PASSWORD`.
4. Start the backend:

   ```bash
   python server.py
   ```

5. In your local copy of `index.html`, set `BACKEND_BASE` to `http://127.0.0.1:8765`, then open `index.html` in your browser. Keep the terminal open while submitting queries.

Do not commit passwords or a local-only backend URL to the public repository. Full setup instructions are in [backend_setup.md](backend_setup.md).

## Deployment overview

- GitHub Pages serves `index.html`.
- Render deploys the Python API using `render.yaml`.
- Render's `DATABASE_URL` setting contains the Neon connection string.
- The API should use the dedicated `gayanara_reader` database role, not the Neon owner/admin role.
- `CORS_ALLOWED_ORIGINS` should be `https://subhanaristiadi.github.io`.

The Render Free service may sleep after inactivity, so its first request after a quiet period can take longer. Check Render and Neon dashboards for current usage and plan limits.

## Important repository files

- `index.html` — frontend and exercise definitions
- `server.py` — Flask API and query safeguards
- `reference_queries.json` — reference SQL mapped to exercise IDs
- `requirements.txt` — Python dependencies
- `render.yaml` — Render deployment configuration
- `.env.example` — example environment-variable names; no real credentials
- `backend_setup.md` — backend setup and troubleshooting
- `docs/NEON_RENDER_DEPLOYMENT.md` — extended deployment reference

## Security notes

- Never commit database passwords, connection strings, private keys, or database dumps.
- Use a dedicated non-superuser database role with the minimum required SELECT access.
- The API accepts one read-only SELECT statement (including SELECT-based CTEs) and applies execution, row, request-size, concurrency, and rate limits. These reduce risk but do not make public SQL execution risk-free.
- Do not connect the public API to a database containing sensitive or private data.
- Reference SQL and exercise definitions are part of this public learning repository; do not treat them as secrets.

## Scope and limitations

This is a learning and portfolio project, not a production analytics platform. It has no user accounts or cross-device progress sync. The simulated dataset does not support dependable profitability analysis, delivery-duration/SLA analysis, historical inventory reconstruction, or causal claims about promotion uplift.
