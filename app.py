from flask import Flask, render_template, request, jsonify
from datetime import datetime, timezone
from collections import defaultdict, deque
from functools import wraps
import json, os, time

app = Flask(__name__)
ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(ROOT, "lab-events.jsonl")
# In-memory IP block list: deliberately local-lab scope, resets when app restarts.
attempts = defaultdict(deque)
blocked_until = {}
LIMIT = 10
WINDOW_SECONDS = 60
BLOCK_SECONDS = 300

def log_event(category, action, detail="", severity="info"):
    row = {
        "time": datetime.now(timezone.utc).isoformat(),
        "category": category, "action": action, "detail": str(detail)[:240],
        "severity": severity, "client": request.remote_addr,
        "path": request.path, "method": request.method,
        "status": None
    }
    # status is completed after response in after_request
    request.environ["lab_log_row"] = row

@app.before_request
def local_only_and_block():
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return "Lord Security Lab is restricted to localhost.", 403
    ip = request.remote_addr or "unknown"
    until = blocked_until.get(ip, 0)
    if until > time.time() and request.path not in ("/health", "/api/lab/events"):
        log_event("defense", "blocked_request", f"blocked_until={int(until)}; remaining_seconds={int(until-time.time())}", "danger")
        return jsonify(ok=False, error="LAB_IP_BLOCKED", message="Too many failed sign-in attempts. This local IP is temporarily blocked."), 429
    return None

@app.after_request
def write_event(response):
    if request.path == "/api/lab/events":
        return response
    row = request.environ.get("lab_log_row")
    if row is None:
        row = {
            "time": datetime.now(timezone.utc).isoformat(),
            "category": "http", "action": "request",
            "detail": "", "severity": "info",
            "client": request.remote_addr, "path": request.path,
            "method": request.method
        }
    row["status"] = response.status_code
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except OSError:
        pass
    return response

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/health")
def health():
    return jsonify(status="ok", app="Lord Security Lab", mode="local-only")

@app.get("/api/lab/events")
def lab_events():
    """Read events from the server's log, ensuring the dashboard watches the right file."""
    try:
        since = max(0, int(request.args.get("since", "0")))
    except ValueError:
        since = 0
    rows = []
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass
    return jsonify(total=len(rows), events=rows[since:])

@app.get("/api/accounts")
def accounts():
    log_event("api", "accounts_viewed", "fictional account summaries")
    return jsonify([
        {"account":"•••• 1048","type":"Everyday Checking","balance":"$2,480.50"},
        {"account":"•••• 8821","type":"Savings","balance":"$8,120.00"}
    ])

@app.post("/api/admin/login")
def admin_login():
    data = request.get_json(silent=True) or request.form
    username = str(data.get("username", ""))[:80]
    password = str(data.get("password", ""))[:120]
    ip = request.remote_addr or "unknown"
    now = time.time()
    queue = attempts[ip]
    while queue and now - queue[0] > WINDOW_SECONDS:
        queue.popleft()
    if len(queue) >= LIMIT:
        blocked_until[ip] = now + BLOCK_SECONDS
        log_event("defense", "ip_blocked", f"failed_attempts={len(queue)}; block_seconds={BLOCK_SECONDS}; reason=threshold_reached", "danger")
        return jsonify(ok=False, error="LAB_IP_BLOCKED", message="Lab defence blocked this local IP for 5 minutes after 10 failed sign-in attempts."), 429

    # Fictional demo account; this is a lab sign-in, not a real bank account.
    if username == "labadmin" and password == "LabAdmin!2026":
        queue.clear()
        log_event("auth", "demo_admin_login_success", "fictional lab account", "success")
        return jsonify(ok=True, message="Demo administrator sign-in successful.")

    queue.append(now)
    log_event("auth", "admin_login_failed", f"username_length={len(username)}; failed_in_window={len(queue)}", "warning")
    if len(queue) >= LIMIT:
        blocked_until[ip] = now + BLOCK_SECONDS
        log_event("defense", "ip_blocked", f"failed_attempts={len(queue)}; block_seconds={BLOCK_SECONDS}; reason=threshold_reached", "danger")
        return jsonify(ok=False, error="LAB_IP_BLOCKED", message="Lab defence blocked this local IP for 5 minutes after 10 failed sign-in attempts."), 429
    return jsonify(ok=False, message=f"Demo credentials not accepted. Failed attempts: {len(queue)}/{LIMIT}."), 401

@app.get("/api/search")
def search():
    q = str(request.args.get("q", ""))[:160]
    catalog = [
        {"id":"A01","name":"Everyday Checking","kind":"Account"},
        {"id":"A02","name":"High Yield Savings","kind":"Account"},
        {"id":"C01","name":"Debit Card","kind":"Card"},
        {"id":"S01","name":"Security Center","kind":"Support"}
    ]
    qlow = q.casefold()
    results = [x for x in catalog if qlow in (x["name"] + " " + x["kind"]).casefold()] if qlow else catalog
    log_event("search", "query", f"query_length={len(q)}")
    return jsonify({"query": q, "count": len(results), "results": results})

@app.post("/api/support")
def support():
    data = request.get_json(silent=True) or request.form
    name = str(data.get("name", ""))[:100]
    message = str(data.get("message", ""))[:800]
    log_event("support", "message_submitted", f"name_length={len(name)}, message_length={len(message)}")
    return jsonify(ok=True, message="Your demo support request has been recorded.")

@app.get("/api/profile/<account_id>")
def profile(account_id):
    log_event("profile", "demo_profile_requested", f"id_length={len(account_id)}")
    if account_id not in ("demo", "1048", "8821"):
        return jsonify(error="Demo account not found."), 404
    return jsonify(account_id=account_id, owner="Alex Morgan (fictional)", account_type="Demo account", sensitive_data=False)

if __name__ == "__main__":
    print("Lord Security Lab: http://127.0.0.1:5000")
    print(f"Application file: {os.path.abspath(__file__)}")
    print(f"Event log: {LOG_PATH}")
    print("Registered routes:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        print(f"  {','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'})):12} {rule.rule}")
    if not any(rule.rule == "/api/lab/events" for rule in app.url_map.iter_rules()):
        raise RuntimeError("Required route /api/lab/events is not registered; refusing to start.")
    print("Local-only demo. Failed login threshold: 10 attempts / 60 seconds.")
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
