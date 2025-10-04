@echo off
setlocal EnableExtensions

rem Change to the directory of this script
cd /d "%~dp0"

set "PY_EMB_DIR=python"
set "PY_EXE=%PY_EMB_DIR%\python.exe"
set "ENTRY_FILE=ReDustX.py"

rem Launch using the embedded Python
if not exist "%PY_EXE%" (
    echo.
    echo Embedded Python not found at "%PY_EXE%".
    echo Please restore the python folder.
    echo.
    pause
    exit /b 1
)

"%PY_EXE%" "%ENTRY_FILE%"
set "RET=%errorlevel%"
echo.
pause
exit /b %RET%
