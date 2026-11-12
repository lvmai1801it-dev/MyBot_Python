@echo off
setlocal
title GLM-OCR server (MyBot)
set "LLAMA_DIR=%LOCALAPPDATA%\llama.cpp"
set "LLAMA_EXE=%LLAMA_DIR%\llama-server.exe"
set "PORT=%~1"
if "%PORT%"=="" set "PORT=8080"

if not exist "%LLAMA_EXE%" (
    echo [ERROR] llama-server.exe not found:
    echo         %LLAMA_EXE%
    echo.
    echo Download a Windows build from:
    echo   https://github.com/ggml-org/llama.cpp/releases
    echo Extract it to: %LLAMA_DIR%
    echo or edit LLAMA_DIR in this file.
    echo.
    pause
    exit /b 1
)

echo ============================================
echo  GLM-OCR local server for MyBot
echo  Address : http://127.0.0.1:%PORT%
echo  Model   : ggml-org/GLM-OCR-GGUF
echo  First run downloads the model (~1 GB).
echo  Close this window to stop the server.
echo ============================================
echo.

"%LLAMA_EXE%" -hf ggml-org/GLM-OCR-GGUF -c 256 -np 2 -ngl 0 -lm none --host 127.0.0.1 --port %PORT%

echo.
echo [INFO] Server stopped.
pause