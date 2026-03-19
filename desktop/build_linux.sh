#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python3 -m pip install -r ./requirements.txt
python3 -m pip install pyinstaller

ICON_ARG=()
if [ -f "./dist/svgviewer-output (3) (1).ico" ]; then
  ICON_ARG=(--icon "./dist/svgviewer-output (3) (1).ico")
elif [ -f "./assets/icon.ico" ]; then
  ICON_ARG=(--icon "./assets/icon.ico")
fi

# On Linux we build a single executable (no .exe extension) so it can run directly.
python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --name "Citatio" \
  --onefile \
  --windowed \
  "${ICON_ARG[@]}" \
  ./Citatio.py

echo "Built (Linux): $SCRIPT_DIR/dist/Citatio"

