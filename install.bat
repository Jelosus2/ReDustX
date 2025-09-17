@echo off
setlocal EnableExtensions

rem Change to the directory of this script
cd /d "%~dp0"

set "VENV_DIR=venv"
set "REQ_FILE=requirements.txt"
set "ENTRY_FILE=ReDustX.py"

echo === ReDustX setup ===

rem Detect a usable Python 3
set "PY_CMD="
where py >nul 2>nul
if %errorlevel%==0 (
    set "PY_CMD=py -3"
) else (
    rem Fall back to python if available and not the WindowsApps stub
    for /f "usebackq delims=" %%P in (`where python 2^>nul`) do (
        echo %%P | findstr /I /C:"\WindowsApps\python.exe" >nul
        if errorlevel 1 (
            set "PY_CMD=\"%%P\""
            goto :got_python
        )
    )
)

:got_python
if not defined PY_CMD (
    echo.
    echo Python 3 is not installed or not on PATH.
    echo Please install Python 3 and ensure you check:
    echo   "Add python.exe to PATH" during setup.
    echo Download: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

rem Create virtual environment if it doesn't exist
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating virtual environment in "%VENV_DIR%"...
    %PY_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

rem Install the requirements
if exist "%REQ_FILE%" (
    "%VENV_DIR%\Scripts\python.exe" -m pip install -r "%REQ_FILE%"
    if errorlevel 1 (
        echo Failed to install dependencies from %REQ_FILE%.
        pause
        exit /b 1
    )
) else (
    echo Warning: %REQ_FILE% not found. Skipping dependency install.
)

echo.
echo Setup complete. Launching ReDustX...
call "%~dp0run.bat"
exit /b %errorlevel%
