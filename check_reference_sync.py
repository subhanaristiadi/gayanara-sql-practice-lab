"""
Reference sync guard for the Gayanara SQL Practice Lab.

Three copies of the reference SQL exist by design:

  1. reference_queries.json          - served to the backend / used by generate_reference.py
  2. const REF_SQL in index.html     - embedded so the file:// app still validates
  3. expectedOutput.columns in index.html - the documented output contract

They must not drift. Run this before committing:

    python check_reference_sync.py

Exit code 0 = in sync, 1 = drift found.
"""

import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(BASE_DIR, "index.html")
REFERENCE_FILE = os.path.join(BASE_DIR, "reference_queries.json")

ENTRY_RE = re.compile(r'^"((?:ex|q)-\d\d-s\d)"\s*:\s*"(.*)"$')


def load_json_reference():
    with open(REFERENCE_FILE, encoding="utf-8") as handle:
        return json.load(handle)


def load_embedded_reference():
    with open(INDEX_FILE, encoding="utf-8") as handle:
        text = handle.read()
    match = re.search(r"const REF_SQL = \{(.*?)\n\};", text, re.S)
    if not match:
        raise SystemExit("Could not locate the const REF_SQL block in index.html.")
    embedded = {}
    for line in match.group(1).split("\n"):
        stripped = line.strip().rstrip(",")
        if not stripped:
            continue
        entry = ENTRY_RE.match(stripped)
        if not entry:
            raise SystemExit(f"Unparseable REF_SQL line: {stripped[:80]}")
        embedded[entry.group(1)] = json.loads('"' + entry.group(2) + '"')
    return embedded


def load_expected_columns():
    with open(INDEX_FILE, encoding="utf-8") as handle:
        text = handle.read()
    parents = re.search(r"const PARENTS = \[(.*?)\n\];", text, re.S)
    if not parents:
        raise SystemExit("Could not locate the const PARENTS block in index.html.")
    chunks = re.split(r'\n\s*\{\s*\n\s*id: "(ex-\d\d-s\d)"', parents.group(1))
    expected = {}
    for i in range(1, len(chunks), 2):
        columns = re.search(
            r"expectedOutput:\s*\{\s*columns:\s*\[([^\]]*)\]", chunks[i + 1]
        )
        if columns:
            expected[chunks[i]] = re.findall(r'"([^"]*)"', columns.group(1))
    return expected


def main():
    json_ref = load_json_reference()
    embedded = load_embedded_reference()
    expected = load_expected_columns()

    problems = []

    only_json = sorted(set(json_ref) - set(embedded))
    only_embedded = sorted(set(embedded) - set(json_ref))
    if only_json:
        problems.append(f"In reference_queries.json but missing from REF_SQL: {only_json}")
    if only_embedded:
        problems.append(f"In REF_SQL but missing from reference_queries.json: {only_embedded}")

    drift = sorted(k for k in json_ref if k in embedded and json_ref[k] != embedded[k])
    if drift:
        problems.append(f"SQL text differs between JSON and REF_SQL: {drift}")

    no_ref = sorted(k for k in expected if k not in json_ref)
    if no_ref:
        problems.append(f"Exercise defined without a reference query: {no_ref}")

    no_columns = sorted(k for k in json_ref if k not in expected)
    if no_columns:
        problems.append(f"Reference query without a documented output contract: {no_columns}")

    print(f"reference_queries.json : {len(json_ref)} queries")
    print(f"embedded REF_SQL       : {len(embedded)} queries")
    print(f"documented outputs     : {len(expected)} exercises")

    if problems:
        print("\nFAIL - reference drift detected:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\nOK - JSON, embedded REF_SQL, and exercise definitions are in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
