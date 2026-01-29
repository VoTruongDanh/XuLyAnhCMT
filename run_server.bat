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

echo [3/3] Starting Server...
echo.
echo Launching Application...
echo.

python -m app.main
pause
