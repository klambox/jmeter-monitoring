@echo off
rem Safe stop for run_cmd.bat: creates the STOP file that every user checks at the start of its iteration.
rem A user in the middle of an iteration finishes it, then stops. Allow up to the length of one iteration
rem before JMeter ends.
rem   stop_safe.bat          -> run "run"
rem   stop_safe.bat run2     -> run "run2"

set "BASE=%~dp0"
set "BASE=%BASE:~0,-1%"
set "RUN=%~1"
if "%RUN%"=="" set "RUN=run"
set "REPORT_DIR=%BASE%\report\%RUN%"

if not exist "%REPORT_DIR%" (
  echo No such run folder: %REPORT_DIR%
  if not defined NOPAUSE pause
  exit /b 1
)
echo stop requested %DATE% %TIME%> "%REPORT_DIR%\STOP"
echo STOP file created in %REPORT_DIR%
echo Each user stops after its current iteration; JMeter ends by itself. Watch the run window.
if not defined NOPAUSE pause
