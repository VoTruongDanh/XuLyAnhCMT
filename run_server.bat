@echo off
title Irrelevant Image Checker Server
echo ==================================================
echo      Irrelevant Image Checker (Level 0 + 1)
echo ==================================================
echo.

echo [1/2] Checking dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error installing dependencies!
    pause
    exit /b %errorlevel%
)
echo Dependencies OK.
echo.

echo [2/3] Opening UI in default browser...
start "" "http://127.0.0.1:8000/ui/"

echo [3/3] Starting Server...
echo.
echo Local UI: http://127.0.0.1:8000/ui/
echo API Docs: http://127.0.0.1:8000/docs
echo.
echo Press Ctrl+C to stop the server.
echo.

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause
