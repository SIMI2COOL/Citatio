# Citatio

Desktop app to search Google Scholar and export results.

## Install & run (all systems)

This app runs on Windows, macOS, and Linux (as a normal Python program).
If Google Scholar blocks requests, the app will show a friendly message—try fewer queries / wait a bit.

Prerequisites:
Python 3.10+, Git, and internet access.

## Windows (PowerShell)

```powershell
git --version
git clone https://github.com/SIMI2COOL/Citatio.git
cd Citatio/desktop
py -m pip install -r requirements.txt
py Citatio.py
```

## macOS (Terminal)

```bash
git --version
git clone https://github.com/SIMI2COOL/Citatio.git
cd Citatio/desktop
python3 -m pip install -r requirements.txt
python3 Citatio.py
```

## Linux (Terminal)

```bash
git --version
git clone https://github.com/SIMI2COOL/Citatio.git
cd Citatio/desktop
python3 -m pip install -r requirements.txt
python3 Citatio.py
```

## Build a Windows EXE (optional)

Windows-only right now (uses the PowerShell build script).

From `desktop/`:
```powershell
.\build_windows.ps1
```

The EXE will be created at `desktop/dist/Citatio.exe`.

## Search tips ✨

Inside the app you can use:
- General searches
- Exact title match: put your keyword in quotes (example: `"UE-Mercosur"`)
- Excluding terms
- Author / publication filters
- Boolean queries

