#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python3 -m pip install -r ./requirements.txt
python3 -m pip install pyinstaller

ICON_ARG=()
if [ -f "./icon.icns" ]; then
  ICON_ARG=(--icon "./icon.icns")
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

# Ensure the built .app bundle has the correct icon file.
# Some PyInstaller builds set the icon but Finder may not refresh unless the app
# bundle contains `Contents/Resources/Icon.icns` referenced by Info.plist.
APP_BUNDLE="$SCRIPT_DIR/dist/Citatio.app"
if [ -d "$APP_BUNDLE" ] && [ -f "./icon.icns" ]; then
  mkdir -p "$APP_BUNDLE/Contents/Resources"
  cp "./icon.icns" "$APP_BUNDLE/Contents/Resources/Icon.icns"

  python3 - <<PY
import pathlib, plistlib

app_bundle = pathlib.Path(r"$APP_BUNDLE")
info_plist = app_bundle / "Contents" / "Info.plist"

if info_plist.exists():
    with info_plist.open("rb") as f:
        plist = plistlib.load(f)
    plist["CFBundleIconFile"] = "Icon"
    with info_plist.open("wb") as f:
        plistlib.dump(plist, f)
PY
fi

echo "Built (macOS): $SCRIPT_DIR/dist/Citatio.app"

