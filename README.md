# Que-Dice Google Scholar — Desktop App

Desktop-only app to search Google Scholar and export results.

## Install & run from GitHub (Windows PowerShell) 🪟

1. Clone the repo:
```powershell
git clone https://github.com/SIMI2COOL/Citatio.git
```
2. Go to the desktop app folder:
```powershell
cd Citatio/desktop
```
3. Install Python dependencies:
```powershell
py -m pip install -r requirements.txt
```
4. Start the app:
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
- Exact phrase (title filtering)
- Excluding terms
- Author / publication filters
- Boolean queries

