@echo off
rem Dry run: every enabled thread group of the JMX with 1 user and 1 loop. The JMX itself is not changed;
rem a copy with those settings is made in the report folder and run.
rem   run_dry.bat          -> reports in report\dry
rem   run_dry.bat dry2     -> reports in report\dry2
rem Settings: see run_cmd.bat (JMX, JMETER_HOME).
rem NOTE: this is a real run against the target server.

set "BASE=%~dp0"
set "BASE=%BASE:~0,-1%"
if not defined JMX set "JMX=%BASE%\test_plan.jmx"
set "RUN=%~1"
if "%RUN%"=="" set "RUN=dry"
set "REPORT_DIR=%BASE%\report\%RUN%"
set "DRY_JMX=%REPORT_DIR%\dry_run.jmx"
if defined JMETER_HOME (set "JMETER=%JMETER_HOME%\bin\jmeter.bat") else (set "JMETER=jmeter.bat")

if not exist "%JMX%" (
  echo Test plan not found: %JMX%
  echo Put your plan at that path or set the JMX environment variable.
  if not defined NOPAUSE pause
  exit /b 1
)
if not exist "%REPORT_DIR%\responses" mkdir "%REPORT_DIR%\responses"
python -B "%BASE%\tool\make_dry_jmx.py" "%JMX%" "%DRY_JMX%"
if errorlevel 1 (
  echo Could not make the dry run copy.
  if not defined NOPAUSE pause
  exit /b 1
)

call "%JMETER%" -n -t "%DRY_JMX%" -j "%REPORT_DIR%\jmeter_cmd.log" "-Jbase_dir=%BASE:\=/%" "-Jreport_dir=%REPORT_DIR:\=/%"

echo.
echo Dry run finished. Reports: %REPORT_DIR%
if not defined NOPAUSE pause
