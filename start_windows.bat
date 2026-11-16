@echo off
rem Starts Prose Clinic. Double-click this file.
rem The first run sets things up automatically (needs internet for a minute or two).
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto nopython
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if errorlevel 1 goto nopython

if exist ".venv\Scripts\python.exe" goto install
echo First run: creating a private Python environment in the .venv folder...
%PY% -m venv .venv
if errorlevel 1 goto failed

:install
fc /b requirements.txt .venv\requirements.installed >nul 2>nul
if not errorlevel 1 goto run
echo Installing the packages Prose Clinic needs (one time only)...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
copy /y requirements.txt .venv\requirements.installed >nul

:run
echo.
echo Starting Prose Clinic. Your browser should open automatically.
echo If it does not, open http://localhost:8501
echo To stop the app, close this window.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
pause
exit /b 0

:nopython
echo Prose Clinic needs Python 3.11 or newer, and it was not found.
echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
echo See README.md for step-by-step help.
pause
exit /b 1

:failed
echo Setup failed. Check your internet connection and double-click this file again.
pause
exit /b 1
