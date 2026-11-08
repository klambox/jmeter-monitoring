#!/usr/bin/env bash
# Dry run (macOS / Linux): every enabled thread group of the JMX with 1 user and 1 loop, on a copy of the plan.
#   ./run_dry.sh          -> reports in report/dry
#   ./run_dry.sh dry2     -> reports in report/dry2
# Settings: see run_cmd.sh (JMX, JMETER_HOME). NOTE: this is a real run against the target server.
set -eu

BASE="$(cd "$(dirname "$0")" && pwd)"
JMX="${JMX:-$BASE/test_plan.jmx}"
RUN="${1:-dry}"
REPORT_DIR="$BASE/report/$RUN"
DRY_JMX="$REPORT_DIR/dry_run.jmx"
if [ -n "${JMETER_HOME:-}" ]; then JMETER="$JMETER_HOME/bin/jmeter"; else JMETER="jmeter"; fi
if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi

if [ ! -f "$JMX" ]; then
  echo "Test plan not found: $JMX" >&2
  echo "Put your plan at that path or set the JMX environment variable." >&2
  exit 1
fi
mkdir -p "$REPORT_DIR/responses"
"$PY" -B "$BASE/tool/make_dry_jmx.py" "$JMX" "$DRY_JMX"

"$JMETER" -n -t "$DRY_JMX" -j "$REPORT_DIR/jmeter_cmd.log" "-Jbase_dir=$BASE" "-Jreport_dir=$REPORT_DIR"

echo
echo "Dry run finished. Reports: $REPORT_DIR"
