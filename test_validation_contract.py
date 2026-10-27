"""
Regression tests for the Submit Query contract.

Run from the project root:

    python test_validation_contract.py

These tests do not need a database. They exercise the pure comparison logic in
index.html (extracted from the real source, never copied) and the reference
sync guard.

Covers:
  * identical result is accepted
  * a wrong column alias is rejected (the P1 bug from the audit)
  * column order is enforced
  * NULL vs 0 handling
  * row-count mismatch detection
  * truncation warnings render for correct answers and use the server limit
"""

import json
import os
import re
import subprocess
import sys
import tempfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(BASE_DIR, "index.html")

FUNCTION_NAMES = [
    "formatRowLimit",
    "compareResults",
    "requiresOrder",
    "rowKey",
    "rowDisplay",
    "rowDiff",
    "valuesEqual",
    "fmtVal",
]


def extract_function(source, name):
    start = source.find("function " + name + "(")
    if start < 0:
        return None
    brace = source.find("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise SystemExit(f"Unbalanced braces while extracting {name}")


def main():
    with open(INDEX_FILE, encoding="utf-8") as handle:
        source = handle.read()

    harness = [
        "const SUB_MAP = {};  // ordering rules are not exercised by these cases",
        "const results = [];",
        "function check(label, cond, detail) { results.push({label, ok: !!cond, detail: detail || ''}); }",
    ]

    for name in FUNCTION_NAMES:
        snippet = extract_function(source, name)
        if snippet:
            harness.append(snippet)

    harness.append(
        """
function payload(columns, rows, extra) {
  return Object.assign({ columns: columns, rows: rows, truncated: false }, extra || {});
}
const SUB = { rows: [["a", [1]]] };

var r = compareResults(payload(["a"], [[1]]), payload(["a"], [[1]]));
check("identical result accepted", r.status === "correct", r.summary);

r = compareResults(payload(["revenue_idr"], [[5]]), payload(["total_revenue_idr"], [[5]]));
check("wrong column alias rejected", r.status === "incorrect", r.summary);
check("alias diagnostics name the column", /Column names\\/order differ/.test(r.summary), r.summary);

r = compareResults(payload(["total_revenue_idr"], [[5]]), payload(["total_revenue_idr"], [[5]]));
check("matching alias accepted", r.status === "correct", r.summary);

r = compareResults(payload(["b", "a"], [[2, 1]]), payload(["a", "b"], [[1, 2]]));
check("swapped column order rejected", r.status === "incorrect", r.summary);

r = compareResults(payload(["a"], [[null]]), payload(["a"], [[null]]));
check("NULL equals NULL", r.status === "correct", r.summary);

r = compareResults(payload(["a"], [[0]]), payload(["a"], [[null]]));
check("0 differs from NULL", r.status === "incorrect", r.summary);

r = compareResults(payload(["a"], [[5]]), payload(["a"], [[5.0]]));
check("5 equals 5.00", r.status === "correct", r.summary);

r = compareResults(payload(["a"], [[1], [2]]), payload(["a"], [[1]]));
check("row-count mismatch detected", r.status === "incorrect" && /Row count differs/.test(r.summary), r.summary);

r = compareResults(payload(["a"], [[1]], { truncated: true, maxRows: 5000 }),
                   payload(["a"], [[1]], { truncated: true, maxRows: 5000 }));
check("truncation warning kept for correct answer", r.status === "correct" && r.details.some(d => /5,000 rows/.test(d)), r.summary);
check("truncation never hardcodes 10,000", !/10,000/.test(JSON.stringify(r)), JSON.stringify(r.details));

r = compareResults(payload(["a"], [[1]], { truncated: true, maxRows: 10000 }),
                   payload(["a"], [[1]], { truncated: true, maxRows: 10000 }));
check("truncation follows a 10,000 server limit", r.details.some(d => /10,000 rows/.test(d)), JSON.stringify(r.details));

r = compareResults(payload(["a"], [[1]], { truncated: true }), payload(["a"], [[1]], { truncated: true }));
check("truncation falls back when limit is absent", r.details.some(d => /server row limit/.test(d)), JSON.stringify(r.details));

console.log(JSON.stringify(results));
"""
    )

    script = "\n".join(harness)

    workdir = tempfile.mkdtemp()
    script_path = os.path.join(workdir, "contract_check.js")
    with open(script_path, "w", encoding="utf-8") as handle:
        handle.write(script)

    try:
        completed = subprocess.run(
            ["node", script_path],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("SKIP: node is not installed, cannot run the Submit Query contract tests.")
        return 0

    if completed.returncode != 0:
        print("FAILED to run harness:\n" + completed.stderr)
        return 1

    results = json.loads(completed.stdout.strip().splitlines()[-1])
    failures = [item for item in results if not item["ok"]]

    for item in results:
        print(("PASS " if item["ok"] else "FAIL ") + item["label"])
        if not item["ok"] and item["detail"]:
            print("      " + item["detail"])

    print(f"\n{len(results) - len(failures)}/{len(results)} checks passed.")

    sync = subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, "check_reference_sync.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    print("\n--- reference sync ---")
    print(sync.stdout.strip())
    if sync.returncode != 0:
        print(sync.stderr.strip())

    return 0 if not failures and sync.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
