$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

py -m pip install -r .\requirements.txt
py -m pip install pyinstaller

py -m PyInstaller `
  --noconfirm `
  --clean `
  --name "Citatio" `
  --onefile `
  --windowed `
  .\main.py

Write-Host ""
Write-Host "Built: $PSScriptRoot\dist\Citatio.exe"

