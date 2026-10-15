# Gayanara SQL Practice Lab — Render + Neon deployment

This package keeps the current frontend on GitHub Pages, deploys the API on Render, and uses Neon PostgreSQL for the cloud database.

## Recommended deployment order

**Create and load Neon first; upload the code to GitHub only after the read-only database role is ready.** This prevents the public page from pointing at an API whose database has not been configured.

After Neon is ready:

1. Back up the repository or create a local branch.
2. Replace `server.py` and `index.html` with the versions in this package.
3. Add `requirements.txt`, `render.yaml`, `.gitignore`, `.env.example`, `run_gayanara_server.bat`, and this deployment guide to the repository root. Keep the existing `reference_queries.json` in the same directory.
4. Commit/push or upload the files to the repository. The GitHub Pages page may briefly show `Validation Unavailable` while Render is being deployed.

## 1. Create Neon database

1. Open https://console.neon.tech and create a new project, for example `gayanara-sql-practice`.
2. Select Singapore (`aws-ap-southeast-1`) if it is available. The Render configuration in `render.yaml` uses Singapore too, to keep the application and database geographically close.
3. Keep the owner connection string private. Do not put it in `index.html`, GitHub, the README, or this chat.
4. Create tables using the existing, verified Gayanara SQL source files in your local project. Do not invent a new schema.

From Windows PowerShell, run the existing schema and data loader from the Gayanara source root so the `\copy` commands can locate the local CSVs. Use the Neon host/database/user from the Neon dashboard and let `psql` prompt for the password:

```powershell
cd C:\Users\subha\Documents\subhanaris\dataset_ngulikdata\gayanara
psql "host=YOUR_NEON_HOST port=5432 dbname=YOUR_NEON_DATABASE user=YOUR_NEON_OWNER sslmode=require" -W -f .\gayanara_sql_project\schema.sql
psql "host=YOUR_NEON_HOST port=5432 dbname=YOUR_NEON_DATABASE user=YOUR_NEON_OWNER sslmode=require" -W -f .\gayanara_sql_project\load.sql
```

Replace the `YOUR_NEON_*` placeholders with values shown in Neon. If the actual schema/loader files are elsewhere, use their real paths. `load.sql` is expected to load CSVs from the current working directory; confirm its paths before running. If the source loader uses different relative paths or needs an encoding adjustment, resolve that before loading. Confirm your Neon plan shows the project in Singapore before choosing Render Singapore; if Neon does not offer that region for this project, select the same region supported by both services and update `render.yaml` before deploy.

Verify the five tables and row counts using Neon SQL Editor or `psql` before proceeding. Do not continue if data loading errors occurred.

## 2. Create a dedicated read-only application role

Connect as the Neon owner/admin role in Neon SQL Editor and execute the following, after confirming the database name and the five table names. Change the password placeholder to a strong unique password; do not use an actual password copied from an example.

```sql
CREATE ROLE gayanara_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD 'REPLACE_WITH_A_NEW_STRONG_PASSWORD';
GRANT CONNECT ON DATABASE YOUR_NEON_DATABASE TO gayanara_reader;
GRANT USAGE ON SCHEMA public TO gayanara_reader;
GRANT SELECT ON TABLE
  public.customers,
  public.products,
  public.orders,
  public.order_items,
  public.reviews
TO gayanara_reader;
```

Replace `YOUR_NEON_DATABASE` with the actual database name. If the project uses a schema other than `public`, change it accordingly. Do not grant ownership, superuser, write, schema-creation, or table-modification privileges to `gayanara_reader`.

Build the **reader role's** connection string from the Neon dashboard details. Verify it can run `SELECT COUNT(*) FROM orders;` but cannot run `INSERT`, `UPDATE`, or `DELETE`. Use this reader connection string as Render's `DATABASE_URL`, not the owner connection string.

## 3. Update the GitHub repository

Upload/commit the replacement `server.py`, patched `index.html`, and supporting configuration files. Do not upload `.env`, real connection strings, database passwords, or database dumps.

The patched frontend initially uses the expected API URL:

`https://gayanara-sql-practice-lab-api-subhan.onrender.com`

If Render gives your service a different URL, replace the `BACKEND_BASE` constant in `index.html` with the exact HTTPS URL that Render shows, then commit and push `index.html` so GitHub Pages rebuilds.

## 4. Deploy the API on Render

1. Open https://dashboard.render.com.
2. Select **New → Blueprint** if you want to use `render.yaml`, or **New → Web Service** and connect the repository.
3. If using a Web Service manually, use:
   - Name: `gayanara-sql-practice-lab-api-subhan`
   - Runtime: Python
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn server:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 35`
   - Health check path: `/health`
   - Plan: Free for initial testing
4. Add `DATABASE_URL` with the **read-only Neon role** connection string in Render's Environment settings. Never commit this value.
5. Set `CORS_ALLOWED_ORIGINS` to exactly `https://subhanaristiadi.github.io`.
6. Confirm `REQUIRE_NON_SUPERUSER=true`.
7. Deploy and wait for successful build/deploy logs.

Render free web services sleep after 15 minutes without inbound traffic and may take about a minute to wake. The first request after inactivity can be slow. Check current limits and billing in the Render dashboard. See https://render.com/docs/free and https://render.com/docs/web-services.

## 5. Verify deployment

Open the exact Render service URL and add `/health`, for example:

`https://YOUR-RENDER-SERVICE.onrender.com/health`

Expected shape:

```json
{"status":"ok","database":"YOUR_NEON_DATABASE"}
```

If it returns status 503, check Render logs and verify `DATABASE_URL` belongs to the non-superuser read-only role and that it can connect to Neon.

Then:

1. Verify the GitHub Pages URL still opens.
2. Submit a SELECT query from a sub-exercise.
3. Confirm actual query rows appear in the Query Results table.
4. Confirm Correct/Incorrect validation works.
5. Test invalid SQL and an attempted disallowed statement.
6. Open browser DevTools Network and confirm requests go to the Render URL.
7. Confirm the API does not return database credentials or server stack traces.

## Security notes

- The backend resolves reference SQL from `reference_queries.json`; it does not trust `ref_sql` supplied in a browser request.
- The API restricts query syntax to a single read-only SELECT/CTE, checks PostgreSQL's parsed syntax tree, uses read-only transactions, limits statement time, rows, request size, request rate, and concurrent execution.
- The database connection must use a dedicated non-superuser role with SELECT access only to the five practice tables.
- SQL read-only protection alone is not a complete security boundary; keep the database privileges restrictive and monitor Render/Neon usage.
- `reference_queries.json` and reference SQL are public in this public repository and should not be considered secrets.

## Free tier notes

Render Free web services spin down after 15 minutes of inactivity and have monthly usage limitations. Neon Free currently advertises 1 GB storage per project and 100 CU-hours of compute per project per month; limits may change. Check https://render.com/docs/free and https://neon.com/blog/neon-free-plan-1-gb-per-project before deployment.
