# CiteRank Desktop

This is the **Windows desktop app** version of the project (no website required).

## Run locally (developer)

1. Open PowerShell in this folder.
2. Install dependencies:

```powershell
py -m pip install -r requirements.txt
```

3. Run the app:

```powershell
py main.py
```

## Build a double-clickable EXE (Windows)

1. Install build tool:

```powershell
py -m pip install pyinstaller
```

2. Build:

```powershell
.\build_windows.ps1
```

Your EXE will be in `dist\CiteRank.exe`.

