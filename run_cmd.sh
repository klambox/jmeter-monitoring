#!/usr/bin/env bash
# Real run of a JMeter test plan in non-GUI mode, exactly as the JMX is saved (macOS / Linux).
#   ./run_cmd.sh          -> reports in report/run
#   ./run_cmd.sh run2     -> reports in report/run2
# Settings (environment variables, all optional):
#   JMX          path of the test plan  (default: test_plan.jmx next to this file)
#   JMETER_HOME  JMeter install folder  (default: jmeter on PATH)
# The JMX gets the properties base_dir and report_dir. STOP SAFELY with ./stop_safe.sh from another
# terminal; the JMX must end its threads when ${report_dir}/STOP exists. Do NOT use Ctrl+C.
set -eu

BASE="$(cd "$(dirname "$0")" && pwd)"
JMX="${JMX:-$BASE/test_plan.jmx}"
RUN="${1:-run}"
REPORT_DIR="$BASE/report/$RUN"
if [ -n "${JMETER_HOME:-}" ]; then JMETER="$JMETER_HOME/bin/jmeter"; else JMETER="jmeter"; fi

if [ ! -f "$JMX" ]; then
  echo "Test plan not found: $JMX" >&2
  echo "Put your plan at that path or set the JMX environment variable." >&2
  exit 1
fi
mkdir -p "$REPORT_DIR/responses"
# a STOP file left from an earlier run would stop the new run at once
rm -f "$REPORT_DIR/STOP"

echo "Running. To stop safely: ./stop_safe.sh $RUN"
"$JMETER" -n -t "$JMX" -j "$REPORT_DIR/jmeter_cmd.log" -Jsummariser.interval=10 \
  "-Jbase_dir=$BASE" "-Jreport_dir=$REPORT_DIR"

echo
echo "JMeter finished or stopped. Reports: $REPORT_DIR"
