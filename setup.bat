@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 exit /b 1
if exist ".venv\Scripts\python.exe" goto install
where py >nul 2>&1
if errorlevel 1 goto python_fallback
py -3 -m venv .venv
if errorlevel 1 goto failed
goto install
:python_fallback
python -m venv .venv
if errorlevel 1 goto failed
:install
".venv\Scripts\python.exe" -m pip install -e ".[full]"
if errorlevel 1 goto failed
echo BlueFox installe dans .venv. Diagnostic local : start.bat doctor
exit /b 0
:failed
echo Echec de l'installation. Python 3.10 a 3.14 et le module venv sont requis. 1>&2
exit /b 1
