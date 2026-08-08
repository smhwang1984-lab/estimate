@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo Install Python from https://www.python.org and run this again.
    pause
    exit /b 1
)

python -c "import openpyxl" >nul 2>nul
if errorlevel 1 (
    echo [INFO] Installing required package: openpyxl
    python -m pip install --quiet openpyxl
)

where pythonw >nul 2>nul
if errorlevel 1 (
    python machine_estimate_app.py
) else (
    start "" pythonw machine_estimate_app.py
)

endlocal
