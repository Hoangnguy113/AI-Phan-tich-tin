@echo off
REM Chay NGAY mot luong (ton chi phi API). Vi du: run_flow.bat suckhoe-yt-sang
setlocal
cd /d "%~dp0.."
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if "%~1"=="" (
  "%PY%" -m agnet flows
  echo.
  echo Cach dung: run_flow.bat ^<flow_id^>
  exit /b 1
)
"%PY%" -m agnet run %1
exit /b %ERRORLEVEL%
