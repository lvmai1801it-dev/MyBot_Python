@echo off
rem ============================================================
rem  Web UI PRODUCTION: build React + mo pywebview dung ban dist
rem ============================================================
setlocal
cd /d "%~dp0"

echo [1/2] Dang build frontend (npm run build)...
pushd COCbot\webui\frontend
call npm run build || (echo Build loi - kiem tra code React & popd & exit /b 1)
popd

echo [2/2] Dang mo pywebview (ban dist)...
".venv\Scripts\python.exe" run_web.py

endlocal
