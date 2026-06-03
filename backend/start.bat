@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\uvicorn.exe" (
  echo ERROR: Missing .venv — run: python -m venv .venv ^& .venv\Scripts\pip install -e ".[dev]"
  exit /b 1
)
echo Using project venv — NOT conda uvicorn
.venv\Scripts\uvicorn.exe app.main:app --reload
