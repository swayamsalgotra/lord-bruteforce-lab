#!/usr/bin/env python3
"""Offline smoke test for the local Flask app; no network or real accounts used."""
import json
import os
import tempfile
import app as lab

# Isolate test log so verification never changes the real lab's event history.
fd, path = tempfile.mkstemp(prefix="lord-lab-test-", suffix=".jsonl")
os.close(fd)
old_path = lab.LOG_PATH
lab.LOG_PATH = path
try:
    client = lab.app.test_client()
    checks = []
    checks.append(("health", client.get("/health").status_code == 200))
    event_response = client.get("/api/lab/events?since=0")
    checks.append(("event API route", event_response.status_code == 200 and isinstance(event_response.get_json().get("events"), list)))
    accounts_response = client.get("/api/accounts")
    checks.append(("event logging", accounts_response.status_code == 200 and os.path.exists(path) and os.path.getsize(path) > 0))
    events = client.get("/api/lab/events?since=0").get_json()["events"]
    checks.append(("event retrieval", any(e.get("action") == "accounts_viewed" for e in events)))
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
    raise SystemExit(0 if all(p for _, p in checks) else 1)
finally:
    lab.LOG_PATH = old_path
    try: os.unlink(path)
    except OSError: pass
