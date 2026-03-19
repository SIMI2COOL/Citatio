# Citatio

Desktop-only app to search Google Scholar and export results.

## Install & run from GitHub (Windows PowerShell) 🪟

Before you start, please install Git (this app needs it to download the files). ✅

1. Open Windows PowerShell.
2. Check if Git is already installed:
```powershell
git --version
```
If you see a version number (like `git version 2.xx.x`), Git is ready.
3. If PowerShell says `git` is not recognized (Git missing), install Git:
- Option A (easy, if `winget` exists): run
```powershell
winget install --id Git.Git -e
```
- Option B (if Option A doesn't work): download and install Git for Windows: https://git-scm.com/download/win
  (During install, just click Next / Install using the defaults.)

4. Clone the repo:
```powershell
git clone https://github.com/SIMI2COOL/Citatio.git
```
5. Go to the desktop app folder:
```powershell
cd Citatio/desktop
```
6. Install Python dependencies:
```powershell
py -m pip install -r requirements.txt
```
7. Start the app:
```powershell
py main.py
```

If Google Scholar blocks requests, just try fewer queries / wait a bit (the app shows a friendly error).

## Build a Windows EXE (optional) 🧰

From `desktop/`:
```powershell
.\build_windows.ps1
```
The EXE will be created at `desktop/dist/Citatio.exe`.

## Search tips ✨

Inside the app you can use:
- General searches
- Exact title match: put your keyword in quotes
- Excluding terms
- Author / publication filters
- Boolean queries

