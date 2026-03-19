# Que-Dice Google Scholar — Desktop App

Desktop-only app to search Google Scholar and export results. If Scholar blocks requests, just try fewer queries / wait a bit (the app shows friendly errors).

## Quick start (Windows) 🪟

If you already have a built EXE:
1. Go to `desktop/dist/`
2. Double-click `Citatio.exe`

If Windows shows a warning:
- Click **More info** → **Run anyway** ✅

## Run from source (Windows/macOS/Linux) 🐍

1. Install Python 3+
2. Open a terminal in the `desktop/` folder
3. Run:

```powershell
py -m pip install -r requirements.txt
py main.py
```

## Build a Windows EXE (developer) 🧰

From the `desktop/` folder:

```powershell
.\build_windows.ps1
```

The EXE is created at `desktop/dist/Citatio.exe`.

## Saving 💾

- Results are automatically saved into your **Downloads** folder
- The filename is based on your keyword, e.g.:
  - `deep learning for radiology.csv`
  - `ue-mercosur xlsx.xlsx`

## Search tips ✨

Inside the app, you can use the examples to do:
- General searches
- Exact phrase searches (title filtering)
- Excluding terms
- Author / publication filters
- Boolean queries

