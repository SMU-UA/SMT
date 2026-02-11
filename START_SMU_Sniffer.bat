@echo off
title SMU Modbus Sniffer
color 0B

echo.
echo  ============================================
echo    SMU Modbus Bus Sniffer + Scenario Logger
echo  ============================================
echo.

:: Find Typhoon HIL Python
set "PYTHON="
for /d %%D in ("C:\Program Files\Typhoon HIL Control Center*") do (
    if exist "%%D\python3_portable\python.exe" (
        set "PYTHON=%%D\python3_portable\python.exe"
    )
)

if not defined PYTHON (
    echo  ERROR: Typhoon HIL Control Center not found!
    echo  Please install Typhoon HIL Control Center first.
    echo.
    pause
    exit /b 1
)

echo  Found Python: %PYTHON%
echo.
echo  Starting server...
echo  Browser will open automatically.
echo.
echo  -----------------------------------------------
echo   DO NOT CLOSE THIS WINDOW while using sniffer
echo  -----------------------------------------------
echo.

:: Open browser after 2 second delay
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8765"

:: Run the server (blocks until Ctrl+C)
"%PYTHON%" "%~dp0scenario_server.py"

echo.
echo  Server stopped.
pause
