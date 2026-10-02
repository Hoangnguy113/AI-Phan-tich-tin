@echo off
REM Khoi dong Agnet chay nen (daemon). Dung cho Task Scheduler hoac bam chay tay.
setlocal
cd /d "%~dp0.."
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
echo [%date% %time%] Khoi dong Agnet daemon bang %PY%
"%PY%" -m agnet serve
set RC=%ERRORLEVEL%
echo [%date% %time%] Agnet daemon ket thuc, ma thoat %RC%
if "%AGNET_PAUSE%"=="1" pause
exit /b %RC%
