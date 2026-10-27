"""
Generate reference results for all 41 sub-exercises.
Run after starting the database: python generate_reference.py

This script reads reference_queries.json and executes each query
against the Gayanara database, saving results to reference_results/.
"""

import json
import os
import sys
import time

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 required. Run: pip install psycopg2-binary")
    sys.exit(1)

# ── Configuration ─────────────────────────────────────────────────────
DB_HOST = os.environ.get("GAYANARA_DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("GAYANARA_DB_PORT", "5432"))
DB_NAME = os.environ.get("GAYANARA_DB_NAME", "gayanara")
DB_USER = os.environ.get("GAYANARA_DB_USER", "postgres")
DB_PASSWORD = os.environ.get("GAYANARA_DB_PASSWORD", "")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.join(SCRIPT_DIR, "reference_results")
QUERIES_FILE = os.path.join(SCRIPT_DIR, "reference_queries.json")
MAX_ROWS = max(1, min(int(os.environ.get("MAX_ROWS", "5000")), 10000))
# Must match server.py so generated reference results are never longer than
# what the app can actually return during validation.
TIMEOUT_MS = 10_000


def connect():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD, connect_timeout=5,
    )


def execute_query(conn, sql):
    cur = conn.cursor()
    cur.execute("SET statement_timeout = %s", (TIMEOUT_MS,))
    cur.execute(sql)
    if cur.description is None:
        return [], []
    columns = [d[0] for d in cur.description]
    rows = cur.fetchmany(MAX_ROWS)
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
    return columns, safe_rows


def main():
    if not os.path.isfile(QUERIES_FILE):
        print(f"ERROR: {QUERIES_FILE} not found.")
        sys.exit(1)

    with open(QUERIES_FILE, "r", encoding="utf-8") as f:
        queries = json.load(f)

    print(f"Generating reference results for {len(queries)} sub-exercises...")
    print(f"Database: {DB_NAME}@{DB_HOST}:{DB_PORT}")
    print(f"Output: {REF_DIR}\n")

    os.makedirs(REF_DIR, exist_ok=True)

    conn = connect()
    print(f"Connected to {DB_NAME}\n")

    success = 0
    failed = 0
    for sub_id, sql in queries.items():
        try:
            start = time.time()
            columns, rows = execute_query(conn, sql)
            elapsed = round(time.time() - start, 2)
            result = {
                "sub_id": sub_id,
                "columns": columns,
                "rows": rows,
                "rowCount": len(rows),
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            with open(os.path.join(REF_DIR, f"{sub_id}.json"), "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"  ✓ {sub_id}: {len(rows)} rows, {elapsed}s")
            success += 1
        except Exception as e:
            print(f"  ✗ {sub_id}: {str(e).strip()[:100]}")
            failed += 1

    conn.close()
    print(f"\nDone: {success} succeeded, {failed} failed out of {len(queries)}")
    if failed:
        print("Check the failed queries and re-run after fixing.")


if __name__ == "__main__":
    main()
