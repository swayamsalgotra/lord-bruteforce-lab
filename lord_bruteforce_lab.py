#!/usr/bin/env python3
"""Lord BruteForce Lab — localhost-only defensive monitor and bounded test helper."""
import argparse, json, os, sys, time, urllib.parse, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

LOG = Path(__file__).with_name("lab-events.jsonl")
RESET="\033[0m"; CYAN="\033[96m"; BLUE="\033[94m"; GREEN="\033[92m"; YELLOW="\033[93m"; RED="\033[91m"; DIM="\033[2m"; BOLD="\033[1m"
BANNER = f"""{CYAN}{BOLD}
╭──────────────────────────────────────────────────────────────╮
│  L O R D   S E C U R I T Y   L A B                           │
│  Defensive monitoring  •  Local training environment         │
╰──────────────────────────────────────────────────────────────╯{RESET}"""

def request_json(url, payload=None, timeout=3):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body=r.read().decode(errors="replace")
            try: parsed=json.loads(body)
            except json.JSONDecodeError: parsed={"body":body[:200]}
            return r.status, parsed
    except urllib.error.HTTPError as e:
        body=e.read().decode(errors="replace")
        try: parsed=json.loads(body)
        except json.JSONDecodeError: parsed={"body":body[:200]}
        return e.code, parsed
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, {"error": str(e)}

def validate_url(url):
    p=urllib.parse.urlparse(url)
    if p.scheme not in ("http","https") or not p.hostname:
        raise ValueError("Enter a full URL such as http://127.0.0.1:5000")
    if p.hostname not in ("127.0.0.1","localhost","::1"):
        raise ValueError("Safety guard: this tool only accepts localhost / 127.0.0.1 / ::1 URLs.")
    return url.rstrip("/")

def prompt_url():
    while True:
        url=input(f"{CYAN}Local lab URL [http://127.0.0.1:5000]: {RESET}").strip() or "http://127.0.0.1:5000"
        try:
            url=validate_url(url); status,data=request_json(url+"/health")
            if status==200 and data.get("status")=="ok":
                print(f"{GREEN}● Local lab connected{RESET}"); return url
            print(f"{RED}Health check failed: HTTP {status} {data}{RESET}")
        except ValueError as e: print(f"{RED}{e}{RESET}")

def read_events():
    if not LOG.exists(): return []
    rows=[]
    try:
        with LOG.open(encoding="utf-8") as f:
            for line in f:
                try: rows.append(json.loads(line))
                except json.JSONDecodeError: continue
    except OSError: pass
    return rows

def dashboard(url):
    url=validate_url(url)
    status,data=request_json(url+"/health")
    if status!=200:
        print(f"{RED}Lab not reachable at {url} (HTTP {status}). Start app.py first.{RESET}"); return 2
    print(BANNER)
    print(f"  {GREEN}● ONLINE{RESET}  {DIM}{url}{RESET}")
    print(f"  {BOLD}LIVE DEFENCE MONITOR{RESET}  {DIM}threshold 10 / 60 sec  •  temporary block 5 min{RESET}")
    print(f"  {DIM}Ctrl+C to exit • Event source: server API (same log as app.py){RESET}\n")
    totals={"events":0,"failed":0,"blocked":0,"success":0}
    cursor=0
    def show(ev):
        action=ev.get("action","request"); sev=ev.get("severity","info")
        color=RED if sev=="danger" or action in ("ip_blocked","blocked_request") else YELLOW if sev=="warning" or action=="admin_login_failed" else GREEN if sev=="success" or action=="demo_admin_login_success" else CYAN
        stamp=ev.get("time","")
        try: stamp=datetime.fromisoformat(stamp.replace("Z","+00:00")).astimezone().strftime("%H:%M:%S")
        except Exception: stamp=stamp[11:19] or "--:--:--"
        detail=str(ev.get("detail", "")).replace("\n", " ")[:42]
        print(f"{color}{stamp:10} {sev.upper():10} {action[:25]:25} {str(ev.get('status',''))[:6]:6} {str(ev.get('client',''))[:15]:15} {detail}{RESET}")
    print(f"{BOLD}{'TIME':10} {'SEVERITY':10} {'EVENT':25} {'HTTP':6} {'CLIENT':15} DETAILS{RESET}")
    print("─"*112)
    try:
        while True:
            code,payload=request_json(f"{url}/api/lab/events?since={cursor}")
            if code==200 and isinstance(payload,dict) and isinstance(payload.get("events"),list):
                events=payload.get("events", [])
                total=payload.get("total", cursor)
                if total < cursor:
                    cursor=0
                    continue
                source_note = "server API"
            else:
                # Compatibility fallback for an older app.py that has no event-feed route.
                # Read the JSONL file next to this tool so the dashboard can still update live.
                local_rows=read_events()
                total=len(local_rows)
                if total < cursor:
                    cursor=0
                events=local_rows[cursor:]
                source_note = "local JSONL fallback" if code == 404 else "local JSONL fallback (API unavailable)"
                if code not in (0, 404):
                    print(f"{YELLOW}Server event API returned HTTP {code}; using local log fallback.{RESET}")
            for ev in events:
                cursor += 1
                action=ev.get("action", "")
                totals["events"]+=1
                if action=="admin_login_failed": totals["failed"]+=1
                if action in ("ip_blocked","blocked_request"): totals["blocked"]+=1
                if action=="demo_admin_login_success": totals["success"]+=1
                show(ev)
                print(f"{DIM}Totals: {totals['events']} events | {totals['failed']} failed | {totals['blocked']} blocked | {totals['success']} successful{RESET}")
            if not events and cursor==0:
                print(f"{DIM}Waiting for events… (source: {source_note}){RESET}")
            elif code == 404 and not events:
                # Explain why no events can be displayed instead of endlessly spamming HTTP 404.
                print(f"{YELLOW}API route missing; checking {LOG} for new lines…{RESET}")
            time.sleep(.5)
    except KeyboardInterrupt:
        print(f"\n{CYAN}Dashboard stopped.{RESET}")
    return 0

def controlled_test(url, count=12, delay=.15):
    url=validate_url(url)
    if count<1 or count>12:
        print(f"{YELLOW}Count must be between 1 and 12 for this controlled local lab test.{RESET}"); return 2
    status,health=request_json(url+"/health")
    if status!=200 or health.get("status")!="ok":
        print(f"{RED}Local lab not reachable at {url}. Start app.py first.{RESET}"); return 2
    print(f"{BOLD}Controlled defence test{RESET}  {DIM}→ {url}/api/admin/login{RESET}")
    print("Sending a small fixed set of invalid demo credentials to localhost only. No wordlists.\n")
    for i in range(1,count+1):
        status,data=request_json(url+"/api/admin/login",{"username":"lab-test-invalid","password":"intentionally-wrong"})
        msg=data.get("message",data.get("error",data.get("body","")))
        color=RED if status==429 else YELLOW if status==401 else GREEN if status==200 else RED
        print(f"  {CYAN}{i:02d}/{count:02d}{RESET}  {color}HTTP {status}{RESET}  {msg}")
        if status==429 or data.get("error")=="LAB_IP_BLOCKED":
            print(f"\n  {RED}{BOLD}✓ DEFENCE TRIGGERED — local client temporarily blocked{RESET}")
            print(f"  {GREEN}Open the dashboard: the ip_blocked event and blocked requests are recorded in {LOG.name}.{RESET}")
            break
        time.sleep(max(.05,min(delay,1.0)))
    print(f"\n{DIM}Review the dashboard terminal or run: python3 lord_bruteforce_lab.py dashboard --url {url}{RESET}")
    return 0

def main():
    parser=argparse.ArgumentParser(description="Local-only defensive monitor for Lord Security Lab")
    sub=parser.add_subparsers(dest="cmd")
    d=sub.add_parser("dashboard",help="Watch live defensive events"); d.add_argument("--url")
    t=sub.add_parser("test",help="Run a bounded local lockout test (max 12 requests)"); t.add_argument("--url"); t.add_argument("--count",type=int,default=12)
    args=parser.parse_args()
    # Intentionally no branded banner for the test/attack command; keep output focused on results.
    if args.cmd is None:
        print(BANNER); url=prompt_url()
        print("\n[1] Live dashboard  [2] Controlled lockout test")
        return controlled_test(url) if input("Select: ").strip()=="2" else dashboard(url)
    try: url=validate_url(args.url or prompt_url())
    except ValueError as e: print(f"{RED}{e}{RESET}"); return 2
    if args.cmd=="dashboard": return dashboard(url)
    if args.cmd=="test": return controlled_test(url,args.count)
    return 0

if __name__=="__main__": raise SystemExit(main())
