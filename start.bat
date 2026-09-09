@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 exit /b 1
set "BLUEFOX_PYTHON=%~dp0.venv\Scripts\python.exe"
if exist "%BLUEFOX_PYTHON%" goto launch
set "BLUEFOX_PYTHON=%~dp0venv\Scripts\python.exe"
if exist "%BLUEFOX_PYTHON%" goto launch
echo BlueFox: environnement absent. Executez setup.bat. 1>&2
exit /b 1
:launch
"%BLUEFOX_PYTHON%" -c "import sys; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 14) else 1)"
if errorlevel 1 goto unsupported
"%BLUEFOX_PYTHON%" "%~dp0BlueFox.py" %*
exit /b %errorlevel%
:unsupported
echo BlueFox: recreez le venv avec Python 3.10 a 3.14. 1>&2
exit /b 1
