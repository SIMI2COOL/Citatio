#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python3 -m pip install -r ./requirements.txt
python3 -m pip install pyinstaller

ICON_ARG=()
if [ -f "../icon.icns" ]; then
  ICON_ARG=(--icon "../icon.icns")
elif [ -f "./dist/svgviewer-output (3) (1).ico" ]; then
  ICON_ARG=(--icon "./dist/svgviewer-output (3) (1).ico")
elif [ -f "./assets/icon.ico" ]; then
  ICON_ARG=(--icon "./assets/icon.ico")
fi

# On macOS we build an .app bundle (no --onefile) so Desktop can launch it naturally.
python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --name "Citatio" \
  --windowed \
  "${ICON_ARG[@]}" \
  ./Citatio.py

echo "Built (macOS): $SCRIPT_DIR/dist/Citatio.app"

