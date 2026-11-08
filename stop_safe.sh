#!/usr/bin/env bash
# Safe stop for run_cmd.sh (macOS / Linux): creates the STOP file that every user checks at the start of
# its iteration. A user in the middle of an iteration finishes it, then stops.
#   ./stop_safe.sh          -> run "run"
#   ./stop_safe.sh run2     -> run "run2"
set -eu

BASE="$(cd "$(dirname "$0")" && pwd)"
RUN="${1:-run}"
REPORT_DIR="$BASE/report/$RUN"

if [ ! -d "$REPORT_DIR" ]; then
  echo "No such run folder: $REPORT_DIR" >&2
  exit 1
fi
echo "stop requested $(date)" > "$REPORT_DIR/STOP"
echo "STOP file created in $REPORT_DIR"
echo "Each user stops after its current iteration; JMeter ends by itself."
