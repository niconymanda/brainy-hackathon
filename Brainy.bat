@echo off
rem Double-click on Windows to launch Brainy (first run installs everything).
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Premiere installation de Brainy...
  py -3 -m venv .venv 2>nul || python -m venv .venv
  if not exist .venv\Scripts\python.exe (
    echo Python 3.10+ requis : https://www.python.org/downloads/ ^(cocher "Add to PATH"^)
    pause
    exit /b 1
  )
  .venv\Scripts\python -m pip install -q --disable-pip-version-check -r requirements.txt
)
if not exist frontend\dist\index.html (
  echo frontend\dist manquant : lancer "npm install && npm run build" dans frontend\
  pause
  exit /b 1
)
.venv\Scripts\python -m brainy.app %*
if errorlevel 1 pause
