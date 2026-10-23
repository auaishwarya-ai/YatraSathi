@echo off
REM One-click setup and run for Windows
cd /d "%~dp0"
if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
echo Installing requirements (first run takes a few minutes)...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
python app.py
pause
