$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$requirementsPath = Join-Path $projectRoot "requirements.txt"
$appPath = Join-Path $projectRoot "streamlit_app.py"

Set-Location $projectRoot

if (-not (Test-Path -LiteralPath $pythonPath)) {
    Write-Host "Creating the project environment..."
    py -3.11 -m venv (Join-Path $projectRoot ".venv")
}

& $pythonPath -c "import streamlit, groq, docx, pypdf, PIL, dotenv" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing project dependencies..."
    & $pythonPath -m pip install -r $requirementsPath
}

Write-Host "Starting ConsultingCraft AI at http://localhost:8501"
& $pythonPath -m streamlit run $appPath
