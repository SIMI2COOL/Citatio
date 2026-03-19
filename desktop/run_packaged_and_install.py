from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Optional


APP_NAME = "Citatio"


def _desktop_dir() -> Path:
    # On Windows, Desktop is often redirected (e.g., OneDrive).
    if sys.platform.startswith("win"):
        try:
            import ctypes
            from ctypes import wintypes

            path_ptr = ctypes.c_wchar_p()
            shell32 = ctypes.windll.shell32
            ole32 = ctypes.windll.ole32

            class GUID(ctypes.Structure):
                _fields_ = [
                    ("Data1", wintypes.DWORD),
                    ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD),
                    ("Data4", ctypes.c_ubyte * 8),
                ]

            desktop_guid = GUID(
                0xB4BFCC3A,
                0xDB2C,
                0x424C,
                (ctypes.c_ubyte * 8)(0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41),
            )

            result = shell32.SHGetKnownFolderPath(
                ctypes.byref(desktop_guid), 0, None, ctypes.byref(path_ptr)
            )
            if result == 0 and path_ptr.value:
                desktop = Path(path_ptr.value)
                ole32.CoTaskMemFree(path_ptr)
                return desktop
        except Exception:
            pass

        env_candidates = [
            os.environ.get("OneDrive"),
            os.environ.get("OneDriveConsumer"),
            os.environ.get("OneDriveCommercial"),
            os.environ.get("USERPROFILE"),
        ]
        for base in env_candidates:
            if not base:
                continue
            candidate = Path(base) / "Desktop"
            if candidate.exists():
                return candidate

    return Path.home() / "Desktop"


def _base_dir() -> Path:
    return Path(__file__).resolve().parent


def _resolve_icon() -> Optional[Path]:
    # Best match: the .ico copied into dist by your Windows build.
    dist_ico = _base_dir() / "dist" / "svgviewer-output (3) (1).ico"
    if dist_ico.exists():
        return dist_ico
    asset_ico = _base_dir() / "assets" / "icon.ico"
    return asset_ico if asset_ico.exists() else None


def _resolve_target() -> tuple[str, Optional[Path]]:
    """
    Returns (platform_tag, target_path).
    platform_tag is one of: "win", "mac", "linux".
    """
    if sys.platform.startswith("win"):
        exe = _base_dir() / "dist" / f"{APP_NAME}.exe"
        return ("win", exe if exe.exists() else None)
    if sys.platform == "darwin":
        app = _base_dir() / "dist" / f"{APP_NAME}.app"
        return ("mac", app if app.exists() else None)
    # Linux / Unix-like
    bin_path = _base_dir() / "dist" / APP_NAME
    return ("linux", bin_path if bin_path.exists() else None)


def _ps_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def _install_windows_shortcut(icon_path: Optional[Path], target_exe: Path) -> None:
    desktop = _desktop_dir()
    desktop.mkdir(parents=True, exist_ok=True)

    link_path = desktop / f"{APP_NAME}.lnk"
    if link_path.exists():
        return

    work_dir = str(target_exe.parent)
    target_path = str(target_exe)

    ps_cmd = (
        "$WshShell = New-Object -ComObject WScript.Shell; "
        f"$Shortcut = $WshShell.CreateShortcut({_ps_quote(str(link_path))}); "
        f"$Shortcut.TargetPath = {_ps_quote(target_path)}; "
        f"$Shortcut.Arguments = ''; "
        f"$Shortcut.WorkingDirectory = {_ps_quote(work_dir)}; "
    )
    if icon_path is not None:
        ps_cmd += f"$Shortcut.IconLocation = {_ps_quote(str(icon_path))}; "
    ps_cmd += "$Shortcut.Save();"

    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _install_linux_desktop_file(icon_path: Optional[Path], target_bin: Path) -> None:
    desktop = _desktop_dir()
    desktop.mkdir(parents=True, exist_ok=True)
    desktop_file = desktop / f"{APP_NAME}.desktop"
    if desktop_file.exists():
        return

    icon_field = f"Icon={icon_path}\n" if icon_path is not None else ""
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        f"{icon_field}"
        f'Exec="{str(target_bin)}"\n'
        "Terminal=false\n"
        "Categories=Education;Science;\n"
    )
    desktop_file.write_text(content, encoding="utf-8")

    # Make launcher executable when required by some desktop environments.
    try:
        desktop_file.chmod(
            desktop_file.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )
    except Exception:
        pass


def _install_macos_desktop_app_symlink(target_app: Path) -> None:
    """
    macOS: prefer a symlink from Desktop/Citatio.app -> dist/Citatio.app.
    Create-only: if Desktop/Citatio.app already exists, do nothing.
    """
    desktop = _desktop_dir()
    desktop.mkdir(parents=True, exist_ok=True)
    desktop_app = desktop / f"{APP_NAME}.app"

    if desktop_app.exists():
        return

    # Best-effort: symlink is simplest and uses your real built app bundle.
    try:
        os.symlink(str(target_app), str(desktop_app))
        return
    except Exception:
        # If symlink fails, fall back to doing nothing (safe create-only).
        # The user can still launch from the built folder.
        return


def main() -> int:
    icon_path = _resolve_icon()
    platform_tag, target = _resolve_target()

    if target is None:
        print(
            f"Could not find the built app in `desktop/dist` for this system.\n"
            f"Expected a {APP_NAME} executable/app under `desktop/dist/`.\n"
            f"Please run the build first."
        )
        return 1

    # 1) Add a Desktop shortcut (create-only).
    if platform_tag == "win":
        _install_windows_shortcut(icon_path, target)
    elif platform_tag == "mac":
        _install_macos_desktop_app_symlink(target)
    else:
        _install_linux_desktop_file(icon_path, target)

    # 2) Open the built app/exe.
    try:
        if platform_tag == "win":
            subprocess.Popen(
                [str(target)],
                cwd=str(target.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif platform_tag == "mac":
            subprocess.Popen(["open", str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen([str(target)], cwd=str(target.parent))
    except Exception as e:
        print(f"Built app was found, but couldn't launch it: {e}")
        return 2

    print("Launched app and added Desktop shortcut (if needed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

