$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

py -m pip install -r .\requirements.txt
py -m pip install pyinstaller

$iconArg = @()
if (Test-Path ".\\dist\\svgviewer-output (3) (1).ico") {
  $iconArg = @("--icon", ".\\dist\\svgviewer-output (3) (1).ico")
}
elseif (Test-Path ".\\assets\\icon.ico") {
  $iconArg = @("--icon", ".\\assets\\icon.ico")
}

py -m PyInstaller `
  --noconfirm `
  --clean `
  --name "Citatio" `
  --onefile `
  --windowed `
  $iconArg `
  .\main.py

Write-Host ""
Write-Host "Built: $PSScriptRoot\dist\Citatio.exe"

