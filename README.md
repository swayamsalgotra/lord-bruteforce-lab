# Lord Security Lab — rebuilt local defensive training tool

A localhost-only training lab for login-failure monitoring, temporary blocking, and event viewing. All accounts and balances are fictional.

## Install / update on Kali Linux

1. Stop the old Flask server in its terminal with **Ctrl+C**. This matters: editing `app.py` does not change the code already loaded in a running Python process.
2. Extract this ZIP into `~/Downloads/` and allow it to merge into `lord-bruteforce-lab`. If prompted, replace the project files. Keep your existing `lab-events.jsonl` if you want to preserve its history.
3. In a terminal:

```bash
cd ~/Downloads/lord-bruteforce-lab
source .venv/bin/activate  # if you already made this environment
python3 verify_lab.py
```

The verification should show four `PASS` lines. It uses a temporary test log and does not overwrite your event history.

## Terminal 1 — start the website

```bash
cd ~/Downloads/lord-bruteforce-lab
source .venv/bin/activate
bash start_lab.sh
```

Startup prints the exact `app.py` path, event-log path, and registered routes. Confirm `/api/lab/events` appears in the route list. The server binds only to `127.0.0.1:5000`.

## Terminal 2 — live dashboard

```bash
cd ~/Downloads/lord-bruteforce-lab
source .venv/bin/activate
python3 lord_bruteforce_lab.py dashboard --url http://127.0.0.1:5000
```

## Terminal 3 — verify the live event API

```bash
curl -i 'http://127.0.0.1:5000/api/lab/events?since=0'
curl -s http://127.0.0.1:5000/api/accounts
curl -s 'http://127.0.0.1:5000/api/lab/events?since=0'
tail -n 5 ~/Downloads/lord-bruteforce-lab/lab-events.jsonl
```

The event API should return HTTP 200 and JSON containing `events` and `total`. Calling `/api/accounts` creates an event in the same directory's `lab-events.jsonl`.

## Optional bounded defence test

```bash
python3 lord_bruteforce_lab.py test --url http://127.0.0.1:5000 --count 12
```

This sends no more than 12 invalid demo sign-ins to localhost, stopping when the temporary block triggers.

## Defence behaviour

- 10 failed demo sign-ins in 60 seconds trigger a 5-minute in-memory block.
- The dashboard reads the event feed from the same Flask app and log.
- Blocks reset when Flask restarts; the JSONL event history is kept on disk.
- Demo credentials are fictional and only intended for this local training app.

Use only with this project's own localhost demo. No external targets or wordlists are supported.
