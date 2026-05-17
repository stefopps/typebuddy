# One-time / launch deps for TypeBuddy
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Installing TypeBuddy dependencies..."
python -m pip install -r requirements.txt -q
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "Preparing SymSpell dictionary..."
python -c "import dictionary; dictionary.ensure_data_files(); dictionary._load_engine(); print('Dictionary ready:', dictionary.word_count(), 'words')"
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "Starting TypeBuddy..."
Start-Process python -ArgumentList "main.py" -WorkingDirectory $PSScriptRoot
