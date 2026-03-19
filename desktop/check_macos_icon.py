from __future__ import annotations

import plistlib
import sys
from pathlib import Path


APP_NAME = "Citatio.app"


def _check_bundle(app_path: Path) -> tuple[bool, list[str]]:
    lines: list[str] = []
    ok = True

    if not app_path.exists():
        return False, [f"[FAIL] Missing app bundle: {app_path}"]

    info_plist = app_path / "Contents" / "Info.plist"
    icon_file = app_path / "Contents" / "Resources" / "Icon.icns"

    if info_plist.exists():
        lines.append(f"[OK] Info.plist exists: {info_plist}")
    else:
        lines.append(f"[FAIL] Missing Info.plist: {info_plist}")
        ok = False

    if icon_file.exists():
        lines.append(f"[OK] Icon file exists: {icon_file}")
    else:
        lines.append(f"[FAIL] Missing Icon.icns: {icon_file}")
        ok = False

    if info_plist.exists():
        try:
            with info_plist.open("rb") as f:
                plist = plistlib.load(f)
            icon_key = plist.get("CFBundleIconFile")
            if icon_key == "Icon":
                lines.append("[OK] CFBundleIconFile is set to 'Icon'")
            else:
                lines.append(
                    f"[FAIL] CFBundleIconFile is '{icon_key}' (expected 'Icon')"
                )
                ok = False
        except Exception as e:
            lines.append(f"[FAIL] Could not parse Info.plist: {e}")
            ok = False

    return ok, lines


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    dist_app = script_dir / "dist" / APP_NAME
    desktop_app = Path.home() / "Desktop" / APP_NAME

    print("Checking macOS icon wiring...\n")

    dist_ok, dist_lines = _check_bundle(dist_app)
    print("dist bundle:")
    for line in dist_lines:
        print("  " + line)
    print()

    desktop_ok, desktop_lines = _check_bundle(desktop_app)
    print("desktop bundle:")
    for line in desktop_lines:
        print("  " + line)
    print()

    if dist_ok and desktop_ok:
        print("[PASS] Icon setup looks correct for both bundles.")
        return 0

    print("[FAIL] One or more icon checks failed.")
    print("Tip: rebuild, then recreate Desktop app and run this check again.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

