@echo off
REM Run the estimate server on this PC for local testing (cwd = repo root).
REM   data   : estimate_server\data_local\estimate.db
REM   allowed: 127.0.0.1 (local test only) + office LAN ranges
setlocal
cd /d "%~dp0.."
set "ESTIMATE_DATA_DIR=%~dp0data_local"
set "ESTIMATE_ALLOWED_CIDRS=127.0.0.1/32,192.168.0.0/24,192.168.10.0/24"
set "ESTIMATE_BACKUP_ENABLED=0"
python -m uvicorn estimate_server.app:app --host 0.0.0.0 --port 8100
endlocal
