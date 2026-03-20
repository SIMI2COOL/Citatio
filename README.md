# Citatio

Citatio finds and ranks the most-cited papers on any topic using Google Scholar, and exports the results as a clean CSV or XLSX file.

## Install & run (all systems)

Citatio runs on Windows, macOS, and Linux (as a normal Python program).
If Google Scholar blocks requests, the app will show a friendly message—try fewer queries / wait a bit.

Prerequisites:
- Python 3.10+
- Git
- Internet access

## Install Python (easy, if you don't have it)

First, check if Python is already installed:

```bash
python --version
```

On Windows, also check:

```powershell
py -V
```

If you see a Python version number, you are done.

If you see an error like "python is not recognized" or "py is not recognized", install Python using the steps below.

## Windows (PowerShell)

Install Python with:

```powershell
winget install --id Python.Python.3.12 -e
```

If `winget` is not found, download and install from:
https://www.python.org/downloads/windows/

Important during install:
- Enable **Add python.exe to PATH**
- Enable **Install launcher for all users (recommended)** (this installs the `py` command)

After install, close and reopen PowerShell, then run:

```powershell
python --version
py -V
```

## macOS (Terminal)

Install Python with:

```bash
brew install python
```

If Homebrew is not installed yet, install it first from:
https://brew.sh/

Then verify:

```bash
python3 --version
```

## Linux (Terminal)

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y python3 python3-pip
```

Fedora:

```bash
sudo dnf install -y python3 python3-pip
```

Arch:

```bash
sudo pacman -S --noconfirm python python-pip
```

Then verify:

```bash
python3 --version
```

## Troubleshooting (Windows)

### Error: `'py' is not recognized as an internal or external command`

This means the Python launcher is missing (or not available in your PATH).

Fix:
1. Re-run Python installer from https://www.python.org/downloads/windows/
2. Make sure this option is checked:
   - **Install launcher for all users (recommended)**
3. Also check:
   - **Add python.exe to PATH**
4. Close and reopen PowerShell, then test:

```powershell
py -V
python --version
```

If `py` still fails but `python --version` works, you can still run Citatio by replacing `py` with `python` in commands.

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
cd Citatio
py -m pip install -r .\desktop\requirements.txt
.\run.bat
```


## macOS (Terminal)

```bash
git --version
git clone https://github.com/SIMI2COOL/Citatio.git
cd Citatio
python3 -m pip install -r ./desktop/requirements.txt
chmod +x ./run.sh
./run.sh
```

## Linux (Terminal)

```bash
git --version
git clone https://github.com/SIMI2COOL/Citatio.git
cd Citatio
python3 -m pip install -r ./desktop/requirements.txt
chmod +x ./run.sh
./run.sh
```

## Reopen the app later

After the app is built, it is saved in `Citatio/desktop/dist/`.
You can add it to your Desktop with the icon, so you can just double click it to open.

From the repo root, you can also run:
- Windows: `.\run.bat`
- macOS/Linux: `./run.sh`

## Publish as downloadable app (Windows installer, no repo required)

You can publish Citatio so people download it from a web page, without cloning this repository.

### One-time setup

This repository includes a GitHub Actions workflow at:
`.github/workflows/release-windows.yml`

It automatically:
- Builds `Citatio.exe` on Windows
- Creates a real installer: `Citatio-Setup-<version>.exe`
- Attaches that installer to your GitHub Release

### How to publish each app version

1. Open your GitHub repository in the browser.
2. Go to **Releases** -> **Draft a new release**.
3. Create a tag like `v1.0.0` and publish.
4. Wait for the workflow to finish (Actions tab).
5. The release will contain `Citatio-Setup-<version>.exe` as a downloadable installer.

Then share this link:
`https://github.com/<your-username>/Citatio/releases/latest`

### Nice download page (free, on GitHub)

The repo includes a simple landing page at `docs/index.html` with a big **Download for Windows** button. It automatically points to the latest `Citatio-Setup-*.exe` from GitHub Releases.

**Turn it on once:**

1. On GitHub, open your repository -> **Settings** -> **Pages** (in the left sidebar).
2. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
3. **Branch**: choose `dev` (or your default branch) and folder **`/docs`**, then **Save**.
4. After a minute, your page will be live at:
   - `https://SIMI2COOL.github.io/Citatio/`  
   (If your username or repo name changes, GitHub shows the exact URL on the Pages settings screen.)

You only publish new app versions the same way as before (new release tag). The landing page keeps working without editing the HTML each time.

## Search tips ✨

Inside the app you can use:
- General searches
- Exact title match: put your keyword in quotes (example: `"UE-Mercosur"`)
- Excluding terms
- Author / publication filters
- Boolean queries

