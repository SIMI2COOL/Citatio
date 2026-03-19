# Que-Dice Google Scholar — Desktop App

This project is now **desktop-only** (the web app has been removed).

## Easiest way (for your girlfriend)

1. Download/copy the file:
   - `desktop\dist\CiteRank.exe`
2. Double-click it to open.

If Windows shows a warning:
- Click **More info** → **Run anyway**

## Run the desktop app (developer)

Open PowerShell in the `desktop` folder and run:

```powershell
py -m pip install -r requirements.txt
py main.py
```

## Build a Windows EXE

From the `desktop` folder:

```powershell
.\build_windows.ps1
```

The EXE will be created at `desktop\dist\CiteRank.exe`.

## How saving works

- Results are automatically saved into your **Downloads** folder
- The filename is the **keyword you searched**, like:
  - `deep learning for radiology.csv`
  - `diffusion models xlsx.xlsx`

## Search tips (inside the app)

Click **Search tips** in the app to see examples like:
- Quotes for exact phrases
- OR / minus-exclude / parentheses grouping

