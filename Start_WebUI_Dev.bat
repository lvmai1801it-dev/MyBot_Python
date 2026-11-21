@echo off
rem ============================================================
rem  Web UI DEV workflow: Vite dev server + pywebview shell
rem  (hot reload cho React; khong can gan bien moi lan)
rem ============================================================
setlocal
cd /d "%~dp0"

echo [1/2] Dang khoi dong Vite dev server...
start "vite-dev" cmd /k "cd /d COCbot\webui\frontend && npm run dev"

timeout /t 4 /nobreak >nul

echo [2/2] Dang mo pywebview (WEBUI_DEV_URL tu dong)...
set WEBUI_DEV_URL=http://localhost:5173
".venv\Scripts\python.exe" run_web.py

endlocal
