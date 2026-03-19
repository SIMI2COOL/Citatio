# Citatio

Citatio finds and ranks the most-cited papers on any topic using Google Scholar, and exports the results as a clean CSV or XLSX file.

## Install & run (all systems)

Citatio runs on Windows, macOS, and Linux (as a normal Python program).
If Google Scholar blocks requests, the app will show a friendly message—try fewer queries / wait a bit.

Prerequisites:
Python 3.10+, Git, and internet access.

## Install Git (easy, if you don't have it)

First, check if Git is already installed:

```bash
git --version
```

If you see a version number, you are done.

If you see an error like "git is not recognized" or "command not found", follow the steps below for your computer:

## Windows (PowerShell)

1. Open PowerShell.
2. Run this command:

```powershell
winget install --id Git.Git -e
```

If `winget` is not found, install Git using the normal installer:
https://git-scm.com/download/win

After installing, close and reopen PowerShell, then run:

```powershell
git --version
```

## macOS (Terminal)

1. Open Terminal.
2. Run this command:

```bash
git --version
```

If Git is missing, run this:

```bash
xcode-select --install
```

Follow the on-screen instructions to install the Command Line Tools.
After it finishes, close and reopen Terminal, then run:

```bash
git --version
```

## Linux (Terminal)

If you are on Ubuntu or Debian (common examples: Ubuntu, Pop!_OS, Mint), run:

```bash
sudo apt update
sudo apt install -y git
```

If you are on Fedora, run:

```bash
sudo dnf install -y git
```

If you are on Arch (Manjaro/EndeavourOS are common examples), run:

```bash
sudo pacman -S --noconfirm git
```

After installing, run:

```bash
git --version
```

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

## Reopen the app later (no re-install needed)

After you do the steps above once, you do not need to install the requirements again.

Later, just:

### Windows (PowerShell)

```powershell
cd Citatio/desktop
py Citatio.py
```

### macOS (Terminal)

```bash
cd Citatio/desktop
python3 Citatio.py
```

### Linux (Terminal)

```bash
cd Citatio/desktop
python3 Citatio.py
```

## Search tips ✨

Inside the app you can use:
- General searches
- Exact title match: put your keyword in quotes (example: `"UE-Mercosur"`)
- Excluding terms
- Author / publication filters
- Boolean queries

