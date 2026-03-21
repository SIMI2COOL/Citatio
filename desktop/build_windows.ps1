$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

# GitHub Actions has `python` on PATH; some PCs only have the `py` launcher.
$PyCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $PyCmd = "python" }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $PyCmd = "py" }
else { throw "Neither 'python' nor 'py' found on PATH." }

& $PyCmd -m pip install -r .\requirements.txt
& $PyCmd -m pip install pyinstaller

$iconArg = @()
if (Test-Path ".\\dist\\svgviewer-output (3) (1).ico") {
  $iconArg = @("--icon", ".\\dist\\svgviewer-output (3) (1).ico")
}
elseif (Test-Path ".\\assets\\icon.ico") {
  $iconArg = @("--icon", ".\\assets\\icon.ico")
}

& $PyCmd -m PyInstaller `
  --noconfirm `
  --clean `
  --name "Citatio" `
  --onefile `
  --windowed `
  $iconArg `
  .\Citatio.py

Write-Host ""
Write-Host "Built: $PSScriptRoot\dist\Citatio.exe"

