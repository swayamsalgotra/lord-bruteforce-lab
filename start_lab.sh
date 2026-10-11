#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
echo "Starting Lord Security Lab from: $PWD"
echo "If port 5000 is already in use, stop the existing server with Ctrl+C in its terminal first."
exec python3 app.py
