@echo off
rem Real run of a JMeter test plan in non-GUI mode, exactly as the JMX is saved.
rem   run_cmd.bat          -> reports in report\run
rem   run_cmd.bat run2     -> reports in report\run2
rem Settings (environment variables, all optional):
rem   JMX          path of the test plan   (default: test_plan.jmx next to this file)
rem   JMETER_HOME  JMeter install folder   (required unless jmeter.bat is on PATH)
rem The JMX gets the properties base_dir and report_dir (-Jbase_dir / -Jreport_dir), so it can write its listener CSVs,
rem the log and failed responses under the report folder.
rem
rem STOP SAFELY: run stop_safe.bat (same run name) from another window. The JMX must check for the file
rem   ${report_dir}/STOP at the start of each iteration and end its thread when it exists.
rem Do NOT use Ctrl+C or close this window: that kills requests half way and the server may answer with errors.

set "BASE=%~dp0"
set "BASE=%BASE:~0,-1%"
if not defined JMX set "JMX=%BASE%\test_plan.jmx"
set "RUN=%~1"
if "%RUN%"=="" set "RUN=run"
set "REPORT_DIR=%BASE%\report\%RUN%"
if defined JMETER_HOME (set "JMETER=%JMETER_HOME%\bin\jmeter.bat") else (set "JMETER=jmeter.bat")

if not exist "%JMX%" (
  echo Test plan not found: %JMX%
  echo Put your plan at that path or set the JMX environment variable.
  if not defined NOPAUSE pause
  exit /b 1
)
if not exist "%REPORT_DIR%\responses" mkdir "%REPORT_DIR%\responses"
rem a STOP file left from an earlier run would stop the new run at once
if exist "%REPORT_DIR%\STOP" del "%REPORT_DIR%\STOP"

echo Running. To stop safely: stop_safe.bat %RUN%
rem summary line every 10 s with the Err count
call "%JMETER%" -n -t "%JMX%" -j "%REPORT_DIR%\jmeter_cmd.log" -Jsummariser.interval=10 "-Jbase_dir=%BASE:\=/%" "-Jreport_dir=%REPORT_DIR:\=/%"

echo.
echo JMeter finished or stopped. Reports: %REPORT_DIR%
if not defined NOPAUSE pause
