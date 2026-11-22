@echo off
rem ============================================================
rem  Web UI: mo pywebview (trang webui/index.html trong repo)
rem ============================================================
setlocal
cd /d "%~dp0"

echo Dang mo pywebview web UI...
".venv\Scripts\python.exe" run_web.py

endlocal
