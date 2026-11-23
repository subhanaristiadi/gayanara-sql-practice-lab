"""Regression checks for the connection banner; no network or database required."""

import subprocess
from pathlib import Path

from test_validation_contract import extract_function


def main():
    source = Path(__file__).with_name("index.html").read_text(encoding="utf-8")
    harness = """
const assert = require('node:assert/strict');
const elements = {health: {}, retryConnectionBtn: {hidden: true}};
const document = {getElementById: id => elements[id]};
const getBackendBase = () => 'https://example.invalid';
let backendHealthVersion = 0;
let fetch;
"""
    for name in ("markBackendConnected", "checkBackendHealth"):
        prefix = "async " if "async function " + name + "(" in source else ""
        harness += prefix + extract_function(source, name) + "\n"
    harness += """
(async () => {
  fetch = async () => { throw new Error('Network unavailable'); };
  await checkBackendHealth();
  assert.equal(elements.retryConnectionBtn.hidden, false);
  assert.match(elements.health.textContent, /Connection not confirmed/);
  console.log('PASS failed health request offers a retry');

  fetch = async () => ({ok: false, json: async () => ({status: 'error'})});
  await checkBackendHealth();
  assert.equal(elements.retryConnectionBtn.hidden, false);
  assert.equal(elements.health.className, 'health unavailable');
  console.log('PASS HTTP error does not claim the database is connected');

  fetch = async () => ({ok: true, json: async () => ({status: 'error'})});
  await checkBackendHealth();
  assert.equal(elements.retryConnectionBtn.hidden, false);
  console.log('PASS unhealthy response does not claim a successful connection');

  fetch = async () => ({ok: true, json: async () => ({status: 'ok'})});
  await checkBackendHealth();
  assert.equal(elements.health.className, 'health connected');
  assert.equal(elements.retryConnectionBtn.hidden, true);
  console.log('PASS successful retry restores the connected banner');

  let rejectOldCheck;
  fetch = () => new Promise((resolve, reject) => { rejectOldCheck = reject; });
  const pending = checkBackendHealth();
  markBackendConnected();
  rejectOldCheck(new Error('Old request timed out'));
  await pending;
  assert.equal(elements.health.className, 'health connected');
  assert.equal(elements.retryConnectionBtn.hidden, true);
  console.log('PASS late health failure cannot overwrite a successful query');

  let resolveOldCheck;
  fetch = () => new Promise(resolve => { resolveOldCheck = resolve; });
  const older = checkBackendHealth();
  fetch = async () => { throw new Error('Latest connection failed'); };
  await checkBackendHealth();
  resolveOldCheck({ok: true, json: async () => ({status: 'ok'})});
  await older;
  assert.equal(elements.health.className, 'health unavailable');
  assert.equal(elements.retryConnectionBtn.hidden, false);
  console.log('PASS latest check wins when health requests complete out of order');
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
    subprocess.run(["node", "-"], input=harness, encoding="utf-8", check=True)


if __name__ == "__main__":
    main()
