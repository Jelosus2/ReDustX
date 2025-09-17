@echo off
setlocal EnableExtensions

rem Change to the directory of this script
cd /d "%~dp0"

set "VENV_DIR=venv"
set "ENTRY_FILE=ReDustX.py"

rem Launch using existing virtual environment
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo.
    echo Virtual environment not found at "%VENV_DIR%".
    echo Please run install.bat first to set up dependencies.
    echo.
    pause
    exit /b 1
)

rem Launch the entry file
"%VENV_DIR%\Scripts\python.exe" "%ENTRY_FILE%"
set "RET=%errorlevel%"
echo.
pause
exit /b %RET%
