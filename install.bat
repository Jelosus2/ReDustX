@echo off
setlocal EnableExtensions

rem Change to the directory of this script
cd /d "%~dp0"

set "PY_EMB_DIR=python"
set "PY_EXE=%PY_EMB_DIR%\python.exe"
set "REQ_FILE=requirements.txt"
set "ENTRY_FILE=ReDustX.py"

echo === ReDustX embedded setup ===

rem Ensure embedded Python exists
if not exist "%PY_EXE%" (
    echo.
    echo Embedded Python not found at "%PY_EXE%".
    echo Please ensure the "python" folder is present in this directory.
    echo.
    pause
    exit /b 1
)

rem Install requirements into the embedded environment
if exist "%REQ_FILE%" (
    if exist "%PY_EMB_DIR%\Scripts\pip.exe" (
        "%PY_EXE%" -m pip install --upgrade --no-warn-script-location --disable-pip-version-check -r "%REQ_FILE%"
        if errorlevel 1 (
            echo.
            echo Failed to install dependencies from %REQ_FILE%.
            echo.
            pause
            exit /b 1
        )
    ) else (
        echo.
        echo pip was not found in "%PY_EMB_DIR%\Scripts". Attempting to bootstrap with get-pip.py...
        "%PY_EXE%" "%PY_EMB_DIR%\get-pip.py"
        if errorlevel 1 (
            echo.
            echo Failed to bootstrap pip.
            echo.
            pause
            exit /b 1
        )
            
        "%PY_EXE%" -m pip install --upgrade --no-warn-script-location --disable-pip-version-check -r "%REQ_FILE%"
        if errorlevel 1 (
            echo.
            echo Failed to install dependencies from %REQ_FILE%.
            echo.
            pause
            exit /b 1
        )
    )
) else (
    echo Warning: %REQ_FILE% not found. Skipping dependency install.
)

echo.
echo Setup complete. Launching ReDustX...
call "%~dp0run.bat"
exit /b %errorlevel%
