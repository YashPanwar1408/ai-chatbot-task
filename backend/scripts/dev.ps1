# Run API with project venv (avoids conda missing asyncpg/psycopg2).
$Root = Split-Path -Parent $PSScriptRoot
$Uvicorn = Join-Path $Root ".venv\Scripts\uvicorn.exe"

if (-not (Test-Path $Uvicorn)) {
    Write-Error "Missing $Uvicorn — run: python -m venv .venv; .venv\Scripts\pip install -e `".[dev]`""
    exit 1
}

Set-Location $Root
& $Uvicorn app.main:app --reload
