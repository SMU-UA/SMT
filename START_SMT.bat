@echo off
title SMT - System Monitoring Tool
color 0B

echo.
echo  ============================================
echo    SMT - System Monitoring Tool
echo  ============================================
echo.

:: Find Typhoon HIL Python
set "PYTHON="
:: Check C:\Program Files first
for /d %%D in ("C:\Program Files\Typhoon HIL Control Center*") do (
    if exist "%%D\python3_portable\python.exe" (
        set "PYTHON=%%D\python3_portable\python.exe"
    )
)
:: Check D:\Typhoon if not found
if not defined PYTHON (
    for /d %%D in ("D:\Typhoon\Typhoon HIL Control Center*") do (
        if exist "%%D\python3_portable\python.exe" (
            set "PYTHON=%%D\python3_portable\python.exe"
        )
    )
)
:: Check D:\Typhoon Centre if not found
if not defined PYTHON (
    for /d %%D in ("D:\Typhoon Centre\Typhoon HIL Control Center*") do (
        if exist "%%D\python3_portable\python.exe" (
            set "PYTHON=%%D\python3_portable\python.exe"
        )
    )
)

:: Fall back to system Python if Typhoon not found
if not defined PYTHON (
    python --version >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON=python"
    ) else (
        python3 --version >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON=python3"
        ) else (
            echo  ERROR: No Python found!
            echo  Install Typhoon HIL Control Center or Python 3.
            echo.
            pause
            exit /b 1
        )
    )
)

echo  Found Python: %PYTHON%
echo.
echo  Starting server...
echo  Browser will open automatically.
echo.
echo  -----------------------------------------------
echo   DO NOT CLOSE THIS WINDOW while using SMT
echo  -----------------------------------------------
echo.

:: Open browser after 2 second delay
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8780"

:: Run the server (blocks until Ctrl+C)
"%PYTHON%" "%~dp0SMT_Server.py"

echo.
echo  Server stopped.
pause
