# Gayanara SQL Practice Lab — Project Context

Last reviewed: 2026-11-03

## 1. Project relationship

The Gayanara dataset is used in two connected portfolio components:

1. **Gayanara SQL Analytics Project** — the analytical foundation: PostgreSQL 16 database, data exploration and validation, SQL business analysis, and evidence-based business insights.
2. **Gayanara SQL Practice Lab** — an interactive web application built from the same dataset and business-question roadmap. It turns the SQL exercises into a browser-based learning and validation experience.

The web app complements the analytics project; it does not replace the database source of truth, dataset documentation, or analytical methodology.

## 2. Repository and live application

- Repository: https://github.com/subhanaristiadi/gayanara-sql-practice-lab
- Frontend: https://subhanaristiadi.github.io/gayanara-sql-practice-lab/
- Backend health endpoint: https://gayanara-sql-practice-lab-api-subhan.onrender.com/health
- Dataset source: https://ngulikdata.com/datasets/gayanara

Repository reviewed: public repository, default branch `main`.

## 3. Verified application capabilities

According to the repository README and current project documentation, the app includes:

- 56 SQL sub-exercises organized by topic and difficulty.
- Business questions, requirements, metric definitions, and expected output specifications.
- SQL editor with query execution and tabular query results.
- Automatic comparison of submitted exercise answers against server-side reference results.
- Browser-based saving of answers, notes, and progress.
- JSON import/export of learning progress.

Progress is stored in browser local storage. It is not synchronized across devices or browsers. The app has no user accounts or cross-device progress synchronization.

### Query and answer-validation flow

1. The browser sends submitted SQL and the current exercise ID to the Render API.
2. The API looks up the matching reference query in the server-side `reference_queries.json`.
3. The API runs the user and reference queries in read-only database transactions.
4. The browser compares returned result sets and displays Correct, Incorrect, or an error status.

The documented comparison contract checks column count, column names by position, row count, and cell values. A matching result does not establish that the submitted SQL is the only valid solution.

## 4. Technology and deployment architecture

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | HTML, CSS, JavaScript | Exercise interface, SQL editor, displaying query results, answer comparison |
| Frontend hosting | GitHub Pages | Publishes the website |
| Backend API | Python, Flask, Gunicorn | Executes and validates submitted SQL |
| Backend hosting | Render | Runs the API service |
| Database | PostgreSQL on Neon | Stores the Gayanara practice dataset |

The app is therefore not a standalone static HTML application: the hosted frontend depends on the API for live SQL execution and submission validation.

### Current deployment configuration documented in the repository

- Render service name: `gayanara-sql-practice-lab-api-subhan`
- Render region: Singapore
- Render plan in `render.yaml`: Free
- Health check: `/health`
- Frontend origin allowed by CORS: `https://subhanaristiadi.github.io`
- Database connection: Render environment variable `DATABASE_URL`
- Expected database role: dedicated non-superuser read-only role `gayanara_reader`

The Render service may spin down after inactivity; the first request afterward can be delayed. Confirm current service status, usage, and provider limits in the hosting dashboards rather than assuming availability.

## 5. Backend safety controls documented by the repository

The backend documentation states that the API:

- accepts one read-only SELECT statement, including SELECT-based CTEs;
- uses read-only database transactions;
- checks that the configured database role is not a superuser and lacks table write privileges;
- applies query-time, lock-wait, output-row/output-size, request-size, concurrency, and rate limits;
- retrieves reference SQL from server-side `reference_queries.json`, rather than trusting reference SQL supplied by the browser;
- restricts browser cross-origin requests to the configured frontend origin.

These controls reduce risk but do not make a public SQL execution endpoint risk-free. Keep the database restricted to this practice dataset, use least-privilege credentials, and never expose credentials in frontend code or the public repository.

## 6. Repository files reviewed

- `README.md` — app overview, features, technology, local setup, deployment, security, limitations.
- `index.html` — frontend and exercise definitions.
- `server.py` — Flask API and query safeguards.
- `reference_queries.json` — server-side reference SQL mapped to exercise IDs.
- `render.yaml` — Render deployment configuration.
- `requirements.txt` — Python dependencies.
- `backend_setup.md` — backend setup, endpoints, security, troubleshooting.
- `docs/NEON_RENDER_DEPLOYMENT.md` — Neon + Render deployment guidance.
- `docs/BUSINESS_QUESTION_COVERAGE.md` — mapping of app exercises to business questions and remaining coverage gaps.
- `docs/DEPLOYMENT_READINESS.md` — deployment checks and items not yet verified.
- `check_reference_sync.py` — checks alignment between reference SQL definitions and reference-query JSON.
- `test_validation_contract.py` — regression tests for output-comparison rules.

## 7. Relationship to the Gayanara analytics source of truth

Continue to use the five original CSVs and the Gayanara data reference as the data source of truth:

- `customers.csv`
- `products.csv`
- `orders.csv`
- `order_items.csv`
- `reviews.csv`

The database model and business rules in the main Gayanara project instructions remain authoritative. In particular:

- Valid sales exclude `cancelled` and `returned` orders unless an analysis explicitly studies those statuses.
- Order-level revenue uses `orders.total_amount_idr`.
- Product/category/brand revenue uses `order_items.subtotal_idr` for valid orders.
- Units sold uses `SUM(order_items.quantity)` for valid orders.
- AOV is valid revenue divided by valid order count.
- Do not add shipping cost to revenue or subtract discounts again from item subtotals.
- Avoid row multiplication in one-to-many joins.
- Current product stock is a snapshot, not historical inventory.
- The dataset does not support reliable profitability, delivery duration/SLA, historical stockout duration, or causal promotion-uplift claims.

The app's exercise-specific definitions and expected output contracts should be respected when discussing app behavior. Where an exercise's logic appears inconsistent with the main project source-of-truth rules, inspect and reconcile it explicitly; do not silently change the analytical methodology.

## 8. Business-question coverage status

The repository's `docs/BUSINESS_QUESTION_COVERAGE.md` reports 15 added sub-exercises mapped to the shared 62-question business catalog. It also identifies follow-up coverage needs, including:

- highest-rated products with a minimum review-count threshold;
- missing review-text percentage;
- text-based review themes;
- explicit product/customer-experience prioritization;
- potential duplicate-record checks;
- broader anomaly screening;
- five-insight executive synthesis;
- explicit geographic growth-opportunity analysis.

Do not describe all 62 business questions as fully covered without checking each question's exercise SQL, metric definition, grain, and expected output.

## 9. Development and maintenance rules

When helping with this combined project:

1. Treat the original CSVs, Gayanara data reference, and main project instructions as the analytical source of truth.
2. Treat the GitHub repository as the source of truth for current app implementation, exercise definitions, deployment configuration, and validation behavior.
3. Do not assume the app's deployed backend or Neon database is currently healthy merely because URLs are documented; verify live status when operational status matters.
4. When changing an exercise, keep its question, metric definition, SQL, expected output columns, and corresponding server-side reference query synchronized.
5. Run the repository checks when relevant:
   - `python check_reference_sync.py`
   - `python test_validation_contract.py`
6. Do not put database passwords, full connection strings, private keys, or database dumps in source control.
7. Clearly distinguish analytical findings from app implementation details and deployment assumptions.

## 10. Scope

The Practice Lab is a learning and portfolio application, not a production analytics platform. Its browser-local progress is not cross-device synchronized. The Gayanara data limitations listed above still apply to any analysis or business recommendation surfaced through the app.
