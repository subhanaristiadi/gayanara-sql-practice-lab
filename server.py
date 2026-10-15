"""Gayanara SQL Practice Lab API for local use and Render deployment.

Local:
    python server.py

Render start command:
    gunicorn server:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 35

For public deployment, set DATABASE_URL to a Neon connection string for a
non-superuser, read-only role. Never use the Neon owner/admin role here.
"""
from __future__ import annotations

import json
import math
import os
import re
import threading
import time
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg2
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pglast.parser import parse_sql_json
from werkzeug.middleware.proxy_fix import ProxyFix

BASE_DIR = Path(__file__).resolve().parent
REFERENCE_FILE = BASE_DIR / "reference_queries.json"

PORT = int(os.getenv("PORT", os.getenv("GAYANARA_LAB_PORT", "8765")))
MAX_ROWS = max(1, min(int(os.getenv("MAX_ROWS", "5000")), 10000))
STATEMENT_TIMEOUT_MS = max(1000, min(int(os.getenv("STATEMENT_TIMEOUT_MS", "10000")), 30000))
LOCK_TIMEOUT_MS = max(500, min(int(os.getenv("LOCK_TIMEOUT_MS", "2000")), 10000))
MAX_SQL_CHARS = 20000
MAX_REQUEST_BYTES = 50000
MAX_RESULT_BYTES = 2_000_000
RENDER_ENV = os.getenv("RENDER", "").lower() == "true"
REQUIRE_NON_SUPERUSER = os.getenv(
    "REQUIRE_NON_SUPERUSER", "true" if RENDER_ENV else "false"
).lower() in {"true", "1", "yes"}
ALLOW_NULL_ORIGIN = os.getenv(
    "ALLOW_NULL_ORIGIN", "false" if RENDER_ENV else "true"
).lower() in {"true", "1", "yes"}

DEFAULT_CORS_ORIGINS = (
    "https://subhanaristiadi.github.io,"
    "http://127.0.0.1:5500,http://localhost:5500,"
    "http://127.0.0.1:8765,http://localhost:8765"
)
CORS_ALLOWED_ORIGINS = {
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
}

FORBIDDEN_AST_NODES = {
    "InsertStmt", "UpdateStmt", "DeleteStmt", "MergeStmt", "CreateStmt",
    "CreateTableAsStmt", "AlterTableStmt", "DropStmt", "TruncateStmt",
    "CopyStmt", "CallStmt", "DoStmt", "TransactionStmt", "VariableSetStmt",
    "VariableShowStmt", "GrantStmt", "GrantRoleStmt", "RevokeStmt",
    "RevokeRoleStmt", "LockStmt", "VacuumStmt", "ExplainStmt",
    "RefreshMatViewStmt", "ReindexStmt", "ClusterStmt", "CreateFunctionStmt",
    "CreateProcedureStmt", "ExecuteStmt", "PrepareStmt", "DeallocateStmt",
}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES
# Render terminates TLS and forwards one proxy hop. This lets the limiter use
# the original client IP instead of treating all visitors as one proxy.
if RENDER_ENV:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)
QUERY_SEMAPHORE = threading.BoundedSemaphore(value=3)

try:
    with REFERENCE_FILE.open("r", encoding="utf-8") as fp:
        raw_references = json.load(fp)
    if not isinstance(raw_references, dict):
        raise ValueError("reference_queries.json must contain a JSON object.")
    REFERENCE_QUERIES = {
        str(key): value.strip()
        for key, value in raw_references.items()
        if isinstance(key, str) and isinstance(value, str) and value.strip()
    }
except Exception as exc:
    raise RuntimeError(f"Unable to load trusted reference queries: {exc}") from exc


def _contains_forbidden_node(value: Any) -> bool:
    """Inspect PostgreSQL's parsed AST, including data-modifying CTEs."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_AST_NODES:
                return True
            if key == "intoClause" and child:
                return True  # SELECT ... INTO creates a table.
            if key == "lockingClause" and child:
                return True  # Reject SELECT FOR UPDATE/SHARE locks.
            if _contains_forbidden_node(child):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_node(item) for item in value)
    return False


class QueryRejected(Exception):
    pass


def validate_readonly_sql(sql: str) -> None:
    if not isinstance(sql, str) or not sql.strip():
        raise QueryRejected("Enter a SQL query before submitting.")
    if len(sql) > MAX_SQL_CHARS:
        raise QueryRejected(f"Query is too long. The limit is {MAX_SQL_CHARS:,} characters.")
    try:
        tree = json.loads(parse_sql_json(sql))
    except Exception as exc:
        # Show a short parser hint, not a stack trace.
        detail = str(exc).splitlines()[0][:240]
        raise QueryRejected(f"PostgreSQL could not parse this SQL: {detail}") from None

    statements = tree.get("stmts", []) if isinstance(tree, dict) else []
    if len(statements) != 1:
        raise QueryRejected("Submit exactly one SQL statement at a time.")
    root = statements[0].get("stmt", {})
    if not isinstance(root, dict) or set(root.keys()) != {"SelectStmt"}:
        raise QueryRejected("Only read-only SELECT queries and SELECT-based CTEs are allowed.")
    if _contains_forbidden_node(root):
        raise QueryRejected("This query includes a disallowed operation. Use a read-only SELECT query.")


def _database_connection():
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        conn = psycopg2.connect(database_url, connect_timeout=5, sslmode="require")
    else:
        # Local development fallback. Cloud deployment should use DATABASE_URL.
        conn = psycopg2.connect(
            host=os.getenv("GAYANARA_DB_HOST", "127.0.0.1"),
            port=int(os.getenv("GAYANARA_DB_PORT", "5432")),
            dbname=os.getenv("GAYANARA_DB_NAME", "gayanara"),
            user=os.getenv("GAYANARA_DB_USER", "postgres"),
            password=os.getenv("GAYANARA_DB_PASSWORD", ""),
            connect_timeout=5,
        )

    # Set the session default before any query starts a transaction.
    conn.set_session(readonly=True, autocommit=False)
    if REQUIRE_NON_SUPERUSER:
        try:
            table_names = ("customers", "products", "orders", "order_items", "reviews")
            select_checks = ", ".join(
                f"has_table_privilege(current_user, 'public.{table}', 'SELECT')"
                for table in table_names
            )
            write_privileges = ("INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")
            write_checks = ", ".join(
                f"has_table_privilege(current_user, 'public.{table}', '{privilege}')"
                for table in table_names for privilege in write_privileges
            )
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT r.rolsuper, "
                    "has_database_privilege(current_user, current_database(), 'CREATE'), "
                    "has_schema_privilege(current_user, 'public', 'CREATE'), "
                    + select_checks + ", " + write_checks + " "
                    "FROM pg_roles AS r WHERE r.rolname = current_user"
                )
                row = cur.fetchone()
            if not row:
                raise RuntimeError("Unable to verify the configured PostgreSQL role.")
            if row[0]:
                raise RuntimeError(
                    "The configured database role is a superuser. Use the dedicated read-only role."
                )
            if row[1] or row[2]:
                raise RuntimeError(
                    "The configured database role can create database objects. Use a role with SELECT-only privileges."
                )
            select_flags = row[3:3 + len(table_names)]
            write_flags = row[3 + len(table_names):]
            if not all(select_flags):
                raise RuntimeError(
                    "The configured database role must have SELECT access to all five Gayanara tables in public."
                )
            if any(write_flags):
                raise RuntimeError(
                    "The configured database role has write-related table privileges. Use a SELECT-only role."
                )
            conn.rollback()
        except Exception as exc:
            conn.close()
            if isinstance(exc, RuntimeError):
                raise
            raise RuntimeError(
                "Could not verify the read-only role or required public tables. Confirm all five tables exist "
                "in schema public and grant the application role SELECT-only access."
            ) from None
    return conn


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, Decimal):
        # String decimals preserve precision; the frontend comparator can still
        # compare numeric strings as numbers when appropriate.
        return str(value)
    return str(value)


def execute_readonly_query(sql: str) -> dict[str, Any]:
    """Execute one parsed SELECT in a read-only transaction with hard limits."""
    validate_readonly_sql(sql)
    conn = _database_connection()
    cursor = None
    start = time.perf_counter()
    columns: list[str] = []
    rows: list[list[Any]] = []
    truncated = False
    bytes_used = 0
    try:
        with conn.cursor() as setup_cursor:
            setup_cursor.execute(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT_MS}ms'")
            setup_cursor.execute(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT_MS}ms'")
            setup_cursor.execute("SET LOCAL idle_in_transaction_session_timeout = '15000ms'")

        # A named cursor fetches in batches instead of buffering an unbounded
        # result set in the application process.
        cursor = conn.cursor(name=f"gayanara_{uuid.uuid4().hex}")
        cursor.itersize = 100
        cursor.execute(sql)
        columns = [description[0] for description in (cursor.description or [])]
        if not columns:
            raise QueryRejected("The query did not return a result table. Submit a SELECT query.")

        while len(rows) < MAX_ROWS:
            batch = cursor.fetchmany(min(100, MAX_ROWS - len(rows)))
            if not batch:
                break
            for raw_row in batch:
                safe_row = [_json_value(value) for value in raw_row]
                row_bytes = len(json.dumps(safe_row, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
                if bytes_used + row_bytes > MAX_RESULT_BYTES:
                    truncated = True
                    break
                rows.append(safe_row)
                bytes_used += row_bytes
            if truncated:
                break

        if not truncated and len(rows) >= MAX_ROWS:
            if cursor.fetchone() is not None:
                truncated = True
        elapsed_ms = round((time.perf_counter() - start) * 1000)
        conn.rollback()
        return {
            "columns": columns,
            "rows": rows,
            "rowCount": len(rows),
            "truncated": truncated,
            "elapsed_ms": elapsed_ms,
        }
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        try:
            conn.rollback()
        except Exception:
            pass
        conn.close()


def _acquire_query_slot() -> bool:
    return QUERY_SEMAPHORE.acquire(blocking=False)


def _release_query_slot() -> None:
    QUERY_SEMAPHORE.release()


def _json_error(message: str, status: int, detail: str | None = None):
    payload: dict[str, Any] = {"error": message}
    if detail:
        payload["detail"] = detail[:300]
    return jsonify(payload), status


def _run_user_query(sql: str):
    try:
        return execute_readonly_query(sql), None
    except QueryRejected as exc:
        return None, _json_error("Query rejected", 422, str(exc))
    except psycopg2.errors.QueryCanceled:
        return None, _json_error("Query exceeded the execution timeout", 408)
    except psycopg2.errors.LockNotAvailable:
        return None, _json_error("Query could not acquire a required database lock", 408)
    except psycopg2.ProgrammingError as exc:
        return None, _json_error("PostgreSQL rejected the query", 422, str(exc).strip())
    except psycopg2.OperationalError:
        app.logger.exception("Database connection failure")
        return None, _json_error("Database connection failed. Please retry shortly.", 503)
    except RuntimeError as exc:
        # Includes the production guard against superuser database roles.
        return None, _json_error("Database role configuration error", 503, str(exc))
    except Exception:
        app.logger.exception("Unexpected query execution failure")
        return None, _json_error("Query execution failed. Check the SQL and try again.", 500)


@app.after_request
def apply_cors(response):
    origin = request.headers.get("Origin")
    normalized = origin.rstrip("/") if origin and origin != "null" else origin
    allowed = normalized in CORS_ALLOWED_ORIGINS or (origin == "null" and ALLOW_NULL_ORIGIN)
    if origin and allowed:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Max-Age"] = "600"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(413)
def request_too_large(_error):
    return _json_error("Request body is too large.", 413)


@app.errorhandler(429)
def rate_limit_exceeded(_error):
    return _json_error("Too many requests. Please wait a minute and try again.", 429)


@app.get("/")
def api_root():
    return jsonify({
        "service": "Gayanara SQL Practice Lab API",
        "status": "online",
        "health_endpoint": "/health",
        "query_endpoint": "/api/query",
        "validation_endpoint": "/api/validate",
    })


@app.get("/health")
def health():
    try:
        conn = _database_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), 1")
                database_name, _one = cur.fetchone()
        finally:
            conn.rollback()
            conn.close()
        return jsonify({"status": "ok", "database": database_name})
    except Exception:
        app.logger.exception("Health check database connection failed")
        return jsonify({"status": "error", "database": "unavailable"}), 503


@app.get("/api/exercises/<string:sub_id>/reference")
def get_reference(sub_id: str):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", sub_id):
        return _json_error("Invalid exercise ID.", 400)
    sql = REFERENCE_QUERIES.get(sub_id)
    if not sql:
        return _json_error("Reference query not found for this exercise.", 404)
    return jsonify({"sub_id": sub_id, "reference_sql": sql})


@app.get("/reference/<string:sub_id>")
def get_reference_legacy(sub_id: str):
    return get_reference(sub_id)


@app.post("/api/query")
@app.post("/query")
@limiter.limit("20 per minute")
def query_endpoint():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _json_error("Request body must be JSON.", 400)
    sql = data.get("sql", "")
    if not isinstance(sql, str) or not sql.strip():
        return _json_error("Enter a SQL query before submitting.", 400)
    if not _acquire_query_slot():
        return _json_error("The query service is busy. Please retry shortly.", 429)
    try:
        result, error = _run_user_query(sql.strip())
        if error:
            return error
        return jsonify(result)
    finally:
        _release_query_slot()


@app.post("/api/validate")
@app.post("/validate")
@limiter.limit("20 per minute")
def validate_endpoint():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _json_error("Request body must be JSON.", 400)

    user_sql = data.get("user_sql", "")
    sub_id = data.get("sub_id", "")
    if not isinstance(user_sql, str) or not user_sql.strip():
        return _json_error("Enter a SQL query before submitting.", 400)
    if not isinstance(sub_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", sub_id):
        return _json_error("A valid exercise ID is required.", 400)

    # Crucially, reference SQL is selected from this trusted server-side file.
    # Any ref_sql supplied by a browser is ignored.
    reference_sql = REFERENCE_QUERIES.get(sub_id)
    if not reference_sql:
        return _json_error("No trusted reference query exists for this exercise.", 404)
    if not _acquire_query_slot():
        return _json_error("The query service is busy. Please retry shortly.", 429)

    try:
        reference_result, ref_error = _run_user_query(reference_sql)
        if ref_error:
            response, status = ref_error
            error_json = response.get_json(silent=True) or {}
            return _json_error(
                "The trusted reference query could not be executed. Validation is temporarily unavailable.",
                status if status in (408, 422, 503) else 500,
                error_json.get("detail"),
            )

        user_result, user_error = _run_user_query(user_sql.strip())
        if user_error:
            # For SQL/execution errors the frontend displays the existing banner.
            return user_error

        elapsed_ms = int(reference_result.get("elapsed_ms", 0)) + int(user_result.get("elapsed_ms", 0))
        user_result["elapsed_ms"] = None
        reference_result["elapsed_ms"] = None
        return jsonify({
            "user": user_result,
            "reference": reference_result,
            "elapsed_ms": elapsed_ms,
        })
    finally:
        _release_query_slot()


if __name__ == "__main__":
    # Local developer server only. Render uses Gunicorn and PORT.
    app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True)
