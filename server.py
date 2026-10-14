"""
Gayanara SQL Practice Lab — Local Query Execution Backend

Run:  python server.py
Requires: psycopg2 (pip install psycopg2-binary)

Environment variables (set in .env or environment):
  GAYANARA_DB_HOST      (default: 127.0.0.1)
  GAYANARA_DB_PORT      (default: 5432)
  GAYANARA_DB_NAME      (default: gayanara)
  GAYANARA_DB_USER      (default: postgres)
  GAYANARA_DB_PASSWORD  (default: empty; REQUIRED for most setups)
  GAYANARA_LAB_PORT     (default: 8765)

Security:
  - Runs in a READ ONLY transaction (no writes, no DDL, no DML)
  - 10-second statement timeout
  - Maximum 10000 rows returned
  - Binds only to 127.0.0.1 (localhost)
  - No credentials exposed to the browser
"""

import json
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2 is required. Install with: pip install psycopg2-binary")
    sys.exit(1)

# ── Configuration ─────────────────────────────────────────────────────
DB_HOST = os.environ.get("GAYANARA_DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("GAYANARA_DB_PORT", "5432"))
DB_NAME = os.environ.get("GAYANARA_DB_NAME", "gayanara")
DB_USER = os.environ.get("GAYANARA_DB_USER", "postgres")
DB_PASSWORD = os.environ.get("GAYANARA_DB_PASSWORD", "")
LAB_PORT = int(os.environ.get("GAYANARA_LAB_PORT", "8765"))

MAX_ROWS = 10000
STATEMENT_TIMEOUT_MS = 10_000  # 10 seconds

# ── Reference results directory ───────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.join(SCRIPT_DIR, "reference_results")

DB_CONFIG = {
    "host": DB_HOST,
    "port": DB_PORT,
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "connect_timeout": 5,
}


def get_db_connection():
    """Return a new read-only PostgreSQL connection."""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    return conn


def execute_query(sql):
    """
    Execute a SQL query in a READ ONLY transaction.
    Returns (columns, rows) or raises an exception.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN READ ONLY")
        cur.execute(f"SET statement_timeout = {STATEMENT_TIMEOUT_MS}")
        cur.execute(sql)
        if cur.description is None:
            conn.rollback()
            return [], []
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchmany(MAX_ROWS)
        # Convert all values to JSON-safe types
        safe_rows = []
        for row in rows:
            safe_row = []
            for val in row:
                if val is None:
                    safe_row.append(None)
                elif isinstance(val, (int, float, str, bool)):
                    safe_row.append(val)
                else:
                    safe_row.append(str(val))
            safe_rows.append(safe_row)
        conn.rollback()
        return columns, safe_rows
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class Handler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for the practice lab backend."""

    def log_message(self, fmt, *args):
        pass  # Suppress default logging

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            # Check DB connectivity
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
                conn.close()
                self._send_json({"status": "ok", "database": DB_NAME})
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, 503)
        elif self.path.startswith("/reference/"):
            # Serve a reference result file
            sub_id = self.path[len("/reference/"):]
            safe_id = os.path.basename(sub_id)  # prevent path traversal
            fpath = os.path.join(REF_DIR, f"{safe_id}.json")
            if os.path.isfile(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._send_json(data)
            else:
                self._send_json({"error": "Reference result not found"}, 404)
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path == "/query":
            # Execute a single user query.
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                data = json.loads(body)
                sql = data.get("sql", "").strip()
                if not sql:
                    self._send_json({"error": "Empty SQL"}, 400)
                    return

                start = time.time()
                columns, rows = execute_query(sql)
                elapsed_ms = round((time.time() - start) * 1000)

                self._send_json({
                    "columns": columns,
                    "rows": rows,
                    "rowCount": len(rows),
                    "truncated": len(rows) >= MAX_ROWS,
                    "elapsed_ms": elapsed_ms,
                })
            except psycopg2.errors.QueryCanceled:
                self._send_json({"error": "Query exceeded the 10-second timeout"}, 408)
            except psycopg2.ProgrammingError as e:
                self._send_json({"error": "SQL execution error", "detail": str(e).strip()[:500]}, 422)
            except psycopg2.OperationalError as e:
                self._send_json({"error": "Database connection problem", "detail": str(e).strip()[:300]}, 503)
            except Exception as e:
                self._send_json({"error": "Execution failed", "detail": str(e).strip()[:500]}, 500)

        elif self.path == "/validate":
            # Execute BOTH the user query and the reference query, return both.
            # Comparison happens in the browser so it can surface rich feedback.
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                data = json.loads(body)
                user_sql = data.get("user_sql", "").strip()
                ref_sql = data.get("ref_sql", "").strip()
                if not user_sql:
                    self._send_json({"error": "Empty user SQL"}, 400)
                    return
                if not ref_sql:
                    self._send_json({"error": "No reference SQL available for this sub-exercise"}, 400)
                    return

                # Run reference first so a reference failure is not blamed on the user.
                start = time.time()
                ref_columns, ref_rows = execute_query(ref_sql)
                user_columns, user_rows = execute_query(user_sql)
                elapsed_ms = round((time.time() - start) * 1000)

                self._send_json({
                    "user": {"columns": user_columns, "rows": user_rows, "rowCount": len(user_rows),
                             "truncated": len(user_rows) >= MAX_ROWS},
                    "reference": {"columns": ref_columns, "rows": ref_rows, "rowCount": len(ref_rows),
                                  "truncated": len(ref_rows) >= MAX_ROWS},
                    "elapsed_ms": elapsed_ms,
                })
            except psycopg2.errors.QueryCanceled:
                self._send_json({"error": "A query exceeded the 10-second timeout"}, 408)
            except psycopg2.ProgrammingError as e:
                self._send_json({"error": "SQL execution error", "detail": str(e).strip()[:500]}, 422)
            except psycopg2.OperationalError as e:
                self._send_json({"error": "Database connection problem", "detail": str(e).strip()[:300]}, 503)
            except Exception as e:
                self._send_json({"error": "Execution failed", "detail": str(e).strip()[:500]}, 500)
        elif self.path == "/run_reference":
            # Run a specific sub-exercise's reference SQL and save it
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                data = json.loads(body)
                sub_id = data.get("sub_id", "")
                sqls = data.get("sqls", [])  # list of SQL strings
                if not sub_id or not sqls:
                    self._send_json({"error": "sub_id and sqls required"}, 400)
                    return

                results = []
                for sql in sqls:
                    columns, rows = execute_query(sql)
                    results.append({"columns": columns, "rows": rows, "rowCount": len(rows)})

                os.makedirs(REF_DIR, exist_ok=True)
                fpath = os.path.join(REF_DIR, f"{sub_id}.json")
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump({"sub_id": sub_id, "results": results}, f, ensure_ascii=False, indent=2)

                self._send_json({"status": "ok", "sub_id": sub_id, "files": [fpath]})
            except Exception as e:
                self._send_json({"error": "Reference generation failed", "detail": str(e)[:500]}, 500)
        else:
            self._send_json({"error": "Not found"}, 404)


def main():
    print(f"Gayanara SQL Practice Lab Backend")
    print(f"  Database: {DB_NAME}@{DB_HOST}:{DB_PORT} (user: {DB_USER})")
    print(f"  Listening on http://127.0.0.1:{LAB_PORT}")
    print(f"  Max rows: {MAX_ROWS}, Timeout: {STATEMENT_TIMEOUT_MS}ms")
    print(f"  Reference dir: {REF_DIR}")
    print()
    # Test connectivity
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT version()")
        ver = cur.fetchone()[0]
        conn.close()
        print(f"  DB connected: {ver.split()[0]} {ver.split()[1]}")
    except Exception as e:
        print(f"  WARNING: Cannot connect to database: {e}")
        print(f"  Set GAYANARA_DB_PASSWORD environment variable and restart.")
        print(f"  The server will start but queries will fail until credentials are valid.")
    print()

    server = HTTPServer(("127.0.0.1", LAB_PORT), Handler)
    print(f"  Server started. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
