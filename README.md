# jmeter-monitoring

Live, browser-based monitoring for Apache JMeter runs started in non-GUI (terminal) mode.
A small Python server tails the listener CSV while JMeter is still writing it and shows a
Response Time Graph style page: per-request series, slow/error alerts, per-request statistics
(min, avg, median, P90/P95/P99, max) and a time-range slider. Python 3.7+ standard library only;
the page loads Chart.js from cdnjs. Works on Windows, macOS and Linux.

## Requirements

- Apache JMeter 5.x (runs the test; not bundled)
- Python 3.7+ (runs the monitor; standard library only)
- A browser

## Quick start

1. **Get the tool**
   ```
   git clone https://github.com/klambox/jmeter-monitoring.git
   cd jmeter-monitoring
   ```
2. **Add your test plan** as `test_plan.jmx` in this folder (or set the `JMX` environment variable to its path).
   The plan must follow the contract in [Test plan requirements](#test-plan-requirements).
3. **Tell the scripts where JMeter is**, unless `jmeter` is already on your PATH:
   - macOS / Linux: `export JMETER_HOME=/path/to/apache-jmeter`
   - Windows: `set JMETER_HOME=C:\path\to\apache-jmeter`
4. **Optional dry run** (1 user, 1 loop; your plan file is not changed). Note that it is a real run against the target:
   - macOS / Linux: `./run_dry.sh`
   - Windows: `run_dry.bat`
5. **Start the test** (reports go to `report/run`; pass a name to use another folder, e.g. `./run_cmd.sh run2`):
   - macOS / Linux: `./run_cmd.sh`
   - Windows: `run_cmd.bat`
6. **Start the monitor** in a second terminal, pointing at the report folder:
   ```
   python3 tool/live_monitor.py report/run        # Windows: python tool\live_monitor.py report\run
   ```
   It opens http://localhost:8765 and updates while JMeter is running.
7. **Stop the test safely** from a third terminal (same run name as step 5). Every virtual user finishes its
   current iteration, then stops, and JMeter exits by itself:
   - macOS / Linux: `./stop_safe.sh`
   - Windows: `stop_safe.bat`

   Do not use Ctrl+C or close the JMeter window: requests are cut in the middle and the server may answer with errors.

## Files

```
run_cmd.sh / run_cmd.bat       run a test plan in non-GUI mode
run_dry.sh / run_dry.bat       dry run: 1 user, 1 loop per enabled thread group (on a copy of the plan)
stop_safe.sh / stop_safe.bat   graceful stop (creates report/<run>/STOP)
tool/live_monitor.py           the monitor server
tool/live_monitor.html         the page
tool/make_dry_jmx.py           makes the dry-run copy of a JMX
```

## Monitor

```
python tool/live_monitor.py [PATH]          # PATH = a CSV file or a folder (preferred/newest CSV is used)
python tool/live_monitor.py --dir report/run --file results.csv
python tool/live_monitor.py --thr login=3000 --thr search=8000 --default-thr 10000
```

Open http://localhost:8765 (opened automatically; `--no-browser` to skip, `--port` to change).
Without PATH the page starts idle: type a path and press "Start tracking".
The server listens on 127.0.0.1 only.

Options: `--thr TEXT=MS` sets the slow threshold (ms) for labels containing TEXT (repeatable);
`--default-thr` applies to all other labels (default 10000).

The CSV must have a header row with the standard JMeter columns `timeStamp`, `elapsed`, `label`,
`responseCode`, `success` and optionally `failureMessage` / `responseMessage`.

## Test plan requirements

The run scripts pass two properties to JMeter: `base_dir` (folder of the scripts) and `report_dir`
(`report/<run>`). Your plan should:

- write its listener CSV (Simple Data Writer or any listener with a file name) to `${__P(report_dir)}`, with a
  header row containing the standard columns (see [Monitor](#monitor));
- for the safe stop, check at the start of each iteration (e.g. an `If Controller` or a JSR223 sampler) whether
  `${__P(report_dir)}/STOP` exists and end the thread if it does.

## Notes

- The "Browse..." button needs tkinter and a desktop session. If it is missing, paste the path instead.
  Install: `brew install python-tk` (Homebrew Python), `sudo apt install python3-tk` (Debian/Ubuntu).
- On a headless Linux box the browser is not opened automatically; open http://localhost:8765 yourself
  (use an SSH tunnel to view it from another machine, the server only listens on 127.0.0.1).

## Privacy

`.gitignore` excludes `*.jmx`, `*.csv`, `*.jtl`, logs, `report/` and saved responses, since test
plans and results usually contain hostnames, credentials and real responses. Check before committing.

## License

MIT
