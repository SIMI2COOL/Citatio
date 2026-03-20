from __future__ import annotations

import csv
import datetime
import os
import plistlib
import re
import subprocess
import tempfile
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
import shutil
import stat
from typing import Any, List, Optional, Tuple

from PySide6.QtCore import QAbstractTableModel, QEvent, QModelIndex, QObject, QPoint, QRect, Qt, QThread, QTimer, Signal, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QKeySequence, QPainter, QPen, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QAbstractSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStyleFactory,
    QTableView,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QProgressBar,
)

from theme import LIGHT, palette_for_mode, qss


APP_NAME = "Citatio"


def _windows_native_clear_maximized(window: QWidget) -> None:
    """
    Quita WS_MAXIMIZE a nivel de Windows. Sin esto, ventanas sin marco pueden
    quedar 'pegadas' a pantalla completa y Qt no puede cambiar setGeometry
    (ver QWindowsWindow::setGeometry ... Resulting geometry no cambia).
    """
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        hwnd = int(window.winId())
        if not hwnd:
            return
        user32 = ctypes.windll.user32
        SW_RESTORE = 9
        user32.ShowWindow(hwnd, SW_RESTORE)

        GWL_STYLE = -16
        WS_MAXIMIZE = 0x01000000
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_FRAMECHANGED = 0x0020

        try:
            get_long = user32.GetWindowLongPtrW
            set_long = user32.SetWindowLongPtrW
        except AttributeError:
            get_long = user32.GetWindowLongW
            set_long = user32.SetWindowLongW

        style = int(get_long(hwnd, GWL_STYLE))
        if style & WS_MAXIMIZE:
            set_long(hwnd, GWL_STYLE, style & ~WS_MAXIMIZE)
        user32.SetWindowPos(
            hwnd,
            0,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
        )
    except Exception:
        pass


class SortByComboBox(QComboBox):
    """Force list popup to open directly below the control (always drops down)."""

    def showPopup(self) -> None:  # noqa: N802
        super().showPopup()
        container = self.view().window()
        if container is None or not container.isVisible():
            return
        pos = self.mapToGlobal(QPoint(0, self.height()))
        w = max(self.width(), container.width())
        h = container.height()
        container.setGeometry(pos.x(), pos.y(), w, h)


def _make_combo_popup_opaque(combo: QComboBox, field_bg: str | None = None) -> None:
    """Windows native popups can ignore QSS; force an opaque list background."""
    view = combo.view()
    view.setAttribute(Qt.WA_TranslucentBackground, False)
    view.setAutoFillBackground(True)
    vp = view.viewport()
    vp.setAttribute(Qt.WA_TranslucentBackground, False)
    vp.setAutoFillBackground(True)
    if field_bg:
        c = QColor(field_bg)
        pal = view.palette()
        pal.setColor(QPalette.ColorRole.Base, c)
        pal.setColor(QPalette.ColorRole.Window, c)
        pal.setColor(QPalette.ColorRole.AlternateBase, c)
        view.setPalette(pal)
        vp.setPalette(pal)


def _resolve_dist_icon() -> Path | None:
    """
    Return the icon file shipped in `dist/` (if present).
    Used for the Desktop shortcut icon on platforms that support it.
    """
    base_dir = Path(__file__).resolve().parent
    # Keep aligned with the existing window icon lookup.
    ico = base_dir / "dist" / "svgviewer-output (3) (1).ico"
    if ico.exists():
        return ico
    asset_ico = base_dir / "assets" / "icon.ico"
    return asset_ico if asset_ico.exists() else None


def _desktop_dir() -> Path:
    # On Windows, Desktop is often redirected (e.g., OneDrive).
    if sys.platform.startswith("win"):
        try:
            import ctypes
            from ctypes import wintypes

            path_ptr = ctypes.c_wchar_p()

            # SHGetKnownFolderPath(REFKNOWNFOLDERID, DWORD, HANDLE, PWSTR*)
            shell32 = ctypes.windll.shell32
            ole32 = ctypes.windll.ole32

            # Use GUID struct to avoid extra dependencies.
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

        # Fallbacks for redirected desktops.
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


def _ps_quote(s: str) -> str:
    # Single-quoted PowerShell string literal.
    return "'" + s.replace("'", "''") + "'"


def _try_make_macos_icns_from_ico(ico_path: Path, out_icns_path: Path) -> bool:
    """
    Best-effort conversion from `.ico` to `.icns` using built-in macOS tools.
    Returns True if the `.icns` is created.
    """
    if sys.platform != "darwin":
        return False

    if not shutil.which("sips") or not shutil.which("iconutil"):
        return False

    try:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            base_png = td_path / "icon.png"

            # sips can often read .ico; if it can't, conversion will fail.
            subprocess.run(
                ["sips", "-s", "format", "png", str(ico_path), "--out", str(base_png)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if not base_png.exists():
                return False

            iconset = td_path / "Icon.iconset"
            iconset.mkdir(parents=True, exist_ok=True)

            sizes = [
                ("icon_16x16.png", 16, 16),
                ("icon_16x16@2x.png", 32, 32),
                ("icon_32x32.png", 32, 32),
                ("icon_32x32@2x.png", 64, 64),
                ("icon_128x128.png", 128, 128),
                ("icon_128x128@2x.png", 256, 256),
                ("icon_256x256.png", 256, 256),
                ("icon_256x256@2x.png", 512, 512),
                ("icon_512x512.png", 512, 512),
                ("icon_512x512@2x.png", 1024, 1024),
            ]
            for name, w, h in sizes:
                out_png = iconset / name
                subprocess.run(
                    ["sips", "-z", str(h), str(w), str(base_png), "--out", str(out_png)],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            subprocess.run(
                ["iconutil", "-c", "icns", str(iconset), "-o", str(out_icns_path)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return out_icns_path.exists()
    except Exception:
        return False


def _maybe_create_desktop_shortcut() -> None:
    """
    Create an OS-appropriate Desktop shortcut launcher if one doesn't already exist.
    - Windows: `Citatio.lnk`
    - macOS: `Citatio.app` (minimal launcher)
    - Linux: `Citatio.desktop`
    """
    try:
        desktop_dir = _desktop_dir()
        icon_path = _resolve_dist_icon()
        script_path = Path(__file__).resolve()
        work_dir = script_path.parent

        if sys.platform.startswith("win"):
            desktop_dir.mkdir(parents=True, exist_ok=True)
            link_path = desktop_dir / f"{APP_NAME}.lnk"

            exe_path = work_dir / "dist" / f"{APP_NAME}.exe"
            if exe_path.exists():
                target_path = str(exe_path)
                arguments = ""
                working_directory = str(exe_path.parent)
            else:
                # Fallback: run the Python app directly.
                target_path = sys.executable
                arguments = str(script_path)
                working_directory = str(work_dir)

            # Create/overwrite the Windows LNK safely.
            ps_cmd = (
                "$WshShell = New-Object -ComObject WScript.Shell; "
                f"$Shortcut = $WshShell.CreateShortcut({_ps_quote(str(link_path))}); "
                f"$Shortcut.TargetPath = {_ps_quote(target_path)}; "
                f"$Shortcut.Arguments = {_ps_quote(arguments)}; "
                f"$Shortcut.WorkingDirectory = {_ps_quote(working_directory)}; "
            )
            if icon_path is not None:
                ps_cmd += f"$Shortcut.IconLocation = {_ps_quote(f'{str(icon_path)},0')}; "
            ps_cmd += "$Shortcut.Save();"

            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return

        if sys.platform == "darwin":
            desktop_dir.mkdir(parents=True, exist_ok=True)
            app_path = desktop_dir / f"{APP_NAME}.app"
            root_dir = Path(__file__).resolve().parent.parent
            # macOS icon file (repo: desktop/icon.icns)
            root_icon = Path(__file__).resolve().parent / "icon.icns"

            # If the launcher app already exists, make a best-effort to add the icon
            # without overwriting the whole bundle.
            if app_path.exists():
                try:
                    # Copy icon file into the existing bundle.
                    icns_path_existing = app_path / "Contents" / "Resources" / "Icon.icns"
                    if root_icon.exists():
                        icns_path_existing.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(str(root_icon), str(icns_path_existing))

                    # Ensure Info.plist tells macOS to use the icon we just placed.
                    info_plist_path = app_path / "Contents" / "Info.plist"
                    if info_plist_path.exists() and root_icon.exists():
                        with info_plist_path.open("rb") as f:
                            plist = plistlib.load(f)
                        plist["CFBundleIconFile"] = "Icon"
                        with info_plist_path.open("wb") as f:
                            plistlib.dump(plist, f)

                    # Finder often needs a refresh to show updated icons.
                    subprocess.run(["touch", str(app_path)], check=False)
                except Exception:
                    pass
                return

            dist_app_path = work_dir / "dist" / f"{APP_NAME}.app"
            built_exec = dist_app_path / "Contents" / "MacOS" / APP_NAME

            contents = app_path / "Contents"
            macos_dir = contents / "MacOS"
            resources_dir = contents / "Resources"
            macos_dir.mkdir(parents=True, exist_ok=True)
            resources_dir.mkdir(parents=True, exist_ok=True)

            # Launcher executable (a shell script) so we don't need bundling Python.
            launcher_path = macos_dir / APP_NAME
            if built_exec.exists():
                exec_target_line = f'exec "{str(built_exec)}" "$@"'
            else:
                exec_target_line = f'exec "{sys.executable}" "{str(script_path)}" "$@"'
            launcher_path.write_text(
                "\n".join(
                    [
                        "#!/bin/bash",
                        "set -e",
                        exec_target_line,
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            launcher_path.chmod(
                launcher_path.stat().st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH
            )

            icns_path = resources_dir / "Icon.icns"
            icon_ok = False
            if root_icon.exists():
                try:
                    shutil.copy2(str(root_icon), str(icns_path))
                    icon_ok = True
                except Exception:
                    icon_ok = False
            elif icon_path is not None:
                icon_ok = _try_make_macos_icns_from_ico(icon_path, icns_path)

            icon_file_line = (
                "<key>CFBundleIconFile</key>\n\t\t<string>Icon</string>\n\t"
                if icon_ok
                else ""
            )
            info_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
\t<key>CFBundleDevelopmentRegion</key>
\t<string>en</string>
\t<key>CFBundleExecutable</key>
\t<string>{APP_NAME}</string>
\t<key>CFBundleIdentifier</key>
\t<string>com.citatio.app</string>
\t<key>CFBundleName</key>
\t<string>{APP_NAME}</string>
\t<key>CFBundlePackageType</key>
\t<string>APPL</string>
\t<key>CFBundleSignature</key>
\t<string>????</string>
\t<key>NSHighResolutionCapable</key>
\t<true/>
{icon_file_line}</dict>
</plist>
"""
            info_plist_path = contents / "Info.plist"
            info_plist_path.write_text(info_plist, encoding="utf-8")

            # Force CFBundleIconFile to be correct (and use plistlib to avoid formatting issues).
            try:
                if info_plist_path.exists():
                    with info_plist_path.open("rb") as f:
                        plist = plistlib.load(f)
                    plist["CFBundleIconFile"] = "Icon"
                    with info_plist_path.open("wb") as f:
                        plistlib.dump(plist, f)
            except Exception:
                pass

            # Finder icon cache refresh (best-effort).
            subprocess.run(["touch", str(app_path)], check=False)
            return

        # Linux / other Unix-like.
        desktop_dir.mkdir(parents=True, exist_ok=True)
        desktop_file = desktop_dir / f"{APP_NAME}.desktop"
        if desktop_file.exists():
            return

        dist_bin = work_dir / "dist" / APP_NAME
        if dist_bin.exists():
            exec_cmd = f'"{str(dist_bin)}"'
        else:
            exec_cmd = f'"{sys.executable}" "{str(script_path)}"'

        icon_field = f"Icon={icon_path}\n" if icon_path is not None else ""

        content = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={APP_NAME}\n"
            f"{icon_field}"
            f"Exec={exec_cmd}\n"
            "Terminal=false\n"
            "Categories=Education;Science;\n"
        )
        desktop_file.write_text(content, encoding="utf-8")
        try:
            desktop_file.chmod(
                desktop_file.stat().st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH
            )
        except Exception:
            pass
    except Exception:
        # Never block app startup on shortcut creation issues.
        return


def _sanitize_filename(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("\xa0", " ")
    s = re.sub(r"[\\/:*?\"<>|]+", "_", s)  # Windows-illegal chars
    s = re.sub(r"\s+", " ", s).strip()
    s = s[:120].strip(" ._")
    return s or "scholar_results"


def _load_runner():
    from core.scholar_runner import run_search_semantic_scholar

    return run_search_semantic_scholar


@dataclass(frozen=True)
class SearchParams:
    keyword: str
    sortby: str
    nresults: int
    start_year: Optional[int]
    end_year: Optional[int]
    langfilter: str
    extra_delay: bool
    out_format: str  # csv|xlsx
    out_path: Path


class ResultsModel(QAbstractTableModel):
    def __init__(self) -> None:
        super().__init__()
        self.headers: List[str] = []
        self.rows: List[List[Any]] = []
        self._link_color = LIGHT.link
        self._row_a = LIGHT.surface
        self._row_b = LIGHT.alt_row

    def apply_palette(self, pal) -> None:
        self._link_color = pal.link
        self._row_a = pal.surface
        self._row_b = pal.alt_row
        if self.rowCount() > 0 and self.columnCount() > 0:
            top_left = self.index(0, 0)
            bottom_right = self.index(self.rowCount() - 1, self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right)

    def set_results(self, headers: List[str], rows: List[List[Any]]) -> None:
        self.beginResetModel()
        self.headers = headers
        self.rows = rows
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:  # noqa: N802
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        if r >= len(self.rows) or c >= len(self.headers):
            return None

        if role == Qt.DisplayRole:
            v = self.rows[r][c]
            return "" if v is None else str(v)

        if role in (Qt.ForegroundRole, Qt.FontRole):
            try:
                v = self.rows[r][c]
                s = "" if v is None else str(v)
                if s.startswith("http://") or s.startswith("https://"):
                    if role == Qt.ForegroundRole:
                        return QColor(self._link_color)
                    f = QFont()
                    f.setUnderline(True)
                    return f
            except Exception:
                return None

        if role == Qt.BackgroundRole:
            return QColor(self._row_a if (r % 2 == 0) else self._row_b)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:  # noqa: N802
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal and 0 <= section < len(self.headers):
            return self.headers[section]
        return str(section + 1)


class SearchWorker(QObject):
    finished = Signal(list, list)  # headers, rows
    failed = Signal(str)  # message
    progress = Signal(int)  # 0..100 (coarse)

    def __init__(self, params: SearchParams) -> None:
        super().__init__()
        self.params = params

    def run(self) -> None:
        try:
            self.progress.emit(5)
            run_search = _load_runner()

            keyword = self.params.keyword.strip()
            # If the user wraps the keyword in quotes, treat it as an exact title match.
            # Examples: `"UE-Mercosur"` or `'UE-Mercosur'`
            phrase: str | None = None
            if len(keyword) >= 2:
                if (keyword[0] == '"' and keyword[-1] == '"') or (keyword[0] == "'" and keyword[-1] == "'"):
                    inner = keyword[1:-1].strip()
                    phrase = inner if inner else None

            # Allow larger pulls, but cap to reduce bans.
            nresults = max(10, min(100, int(self.params.nresults)))

            self.progress.emit(15)
            headers, rows = run_search(
                keyword=keyword,
                nresults=nresults,
                sortby=self.params.sortby,
                start_year=self.params.start_year,
                end_year=self.params.end_year,
                langfilter="All" if self.params.langfilter == "All" else [self.params.langfilter],
                debug=False,
                delay_seconds=2.5 if self.params.extra_delay else 1.0,
                request_timeout=10,
            )

            if phrase:
                lowered = phrase.lower()
                rows = [row for row in rows if lowered in str(row[2]).lower()]

            if not rows:
                raise RuntimeError("No results found. Try a different keyword.")

            self.progress.emit(85)
            _export_results(headers, rows, self.params.out_format, self.params.out_path)
            self.progress.emit(100)
            self.finished.emit(headers, rows)
        except Exception as e:
            msg = str(e).strip() or f"{type(e).__name__}"
            self.failed.emit(msg)


def _export_results(headers: List[str], rows: List[List[Any]], fmt: str, out_path: Path) -> None:
    fmt = fmt.lower()
    if fmt == "xlsx":
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "Results"
        ws.append(headers)
        for row in rows:
            ws.append(list(row))
        wb.save(out_path)
        return

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


class RainbowHeader(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(52)
        self._tick = 0
        self._timer = QTimer(self)
        self._timer.setInterval(120)  # 8-bit-ish pacing
        self._timer.timeout.connect(self._advance)
        self._timer.start()

    def _advance(self) -> None:
        self._tick = (self._tick + 1) % 10_000
        self.update()

    def paintEvent(self, event):  # noqa: N802
        colors = [LIGHT.green, LIGHT.yellow, LIGHT.orange, LIGHT.red, LIGHT.purple, LIGHT.blue]
        stripe_h = max(1, self.height() // len(colors))
        p = QPainter(self)

        # Pixel shimmer: animated 4px "blocks" drifting across.
        block = 4
        drift = (self._tick * 2) % (block * len(colors))
        y = 0
        for i, c in enumerate(colors):
            p.fillRect(0, y, self.width(), stripe_h, QColor(c))
            # Add 8-bit dither highlights (subtle, never as base surface)
            accent = QColor(colors[(i + (self._tick // 2)) % len(colors)])
            accent.setAlpha(60)
            for x in range(-drift, self.width() + block, block):
                if ((x // block) + i + (self._tick // 2)) % 7 == 0:
                    p.fillRect(x, y, block, stripe_h, accent)
            y += stripe_h

        if y < self.height():
            p.fillRect(0, y, self.width(), self.height() - y, QColor(colors[-1]))


class BevelFrame(QWidget):
    """
    Transparent outer frame that draws the window bevel on top.
    Drawing here (instead of MainWindow paintEvent) avoids the central widgets
    repainting over the border.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAutoFillBackground(False)
        # Override the global QWidget background from theme.qss().
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        r = self.rect()
        thickness = 20

        # We draw a multi-offset bevel border by repeatedly drawing 4 border lines
        # (top/bottom/left/right) for each pixel offset from the outer edge.
        # - Top/left: bright highlight, then inner gray
        # - Bottom/right: dark shadow, then inner gray
        # Scale the highlight/inner bands with total thickness.
        highlight_px = max(2, thickness // 3)
        inner_px = max(2, thickness // 3)  # inner gray thickness

        for i in range(thickness):
            pal = getattr(self.window(), "_pal", LIGHT)
            top_left_pen = (
                pal.bevel_highlight if i < highlight_px else pal.bevel_inner
            )

            # Bottom/right stay dark on the outside, then become inner gray, then dark again.
            bottom_right_pen = (
                pal.bevel_shadow if i < highlight_px or i >= highlight_px + inner_px else pal.bevel_inner
            )

            # Top and left
            p.setPen(QColor(top_left_pen))
            p.drawLine(r.left() + i, r.top() + i, r.right() - i, r.top() + i)
            p.drawLine(r.left() + i, r.top() + i, r.left() + i, r.bottom() - i)

            # Bottom and right
            p.setPen(QColor(bottom_right_pen))
            p.drawLine(r.left() + i, r.bottom() - i, r.right() - i, r.bottom() - i)
            p.drawLine(r.right() - i, r.top() + i, r.right() - i, r.bottom() - i)


class PlatinumTitleBar(QWidget):
    close_clicked = Signal()
    minimize_clicked = Signal()
    restore_clicked = Signal()  # green: shrink / center window
    maximize_toggle_clicked = Signal()  # double-click title: maximize toggle

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedHeight(26)
        self._drag_pos = None
        self._pal = palette_for_mode("light")

    def set_palette(self, pal) -> None:
        self._pal = pal
        self.update()

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            px, py = event.position().x(), event.position().y()
            on_btn = False
            for (x, y, w, h) in self._button_rects():
                if x <= px <= x + w and y <= py <= y + h:
                    on_btn = True
                    break
            if not on_btn:
                self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._drag_pos is None:
            return
        delta = event.globalPosition().toPoint() - self._drag_pos
        self.window().move(self.window().pos() + delta)
        self._drag_pos = event.globalPosition().toPoint()
        event.accept()

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        self.maximize_toggle_clicked.emit()

    def _button_rects(self):
        # Right side cluster, ordered: yellow(min), green(max), red(close)
        size = 16
        gap = 6
        y = 5
        x_right = self.width() - 10
        red = (x_right - size, y, size, size)
        green = (x_right - size - gap - size, y, size, size)
        yellow = (x_right - size - gap - size - gap - size, y, size, size)
        return yellow, green, red

    def mouseReleaseEvent(self, event):  # type: ignore[override]  # noqa: N802
        if event.button() == Qt.LeftButton:
            px, py = event.position().x(), event.position().y()
            yellow, green, red = self._button_rects()
            for which, (x, y, w, h) in (
                ("min", yellow),
                ("restore", green),
                ("close", red),
            ):
                if x <= px <= x + w and y <= py <= y + h:
                    if which == "close":
                        self.close_clicked.emit()
                    elif which == "min":
                        self.minimize_clicked.emit()
                    elif which == "restore":
                        self.restore_clicked.emit()
                    break
        self._drag_pos = None
        event.accept()

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        # Grey platinum title bar (pinstripe)
        p.fillRect(self.rect(), QColor(self._pal.chrome))
        pen = QPen(QColor(self._pal.edge))
        p.setPen(pen)
        for yy in range(0, self.height(), 2):
            p.drawLine(0, yy, self.width(), yy)

        # Window buttons: yellow(min), green(max), red(close) on the right
        yellow, green, red = self._button_rects()
        for (x, y, w, h), fill in (
            (yellow, "#F5BC00"),
            (green, "#6ABD45"),
            (red, "#E2231A"),
        ):
            p.setPen(QColor("#000000"))
            p.setBrush(QColor(fill))
            p.drawRect(x, y, w, h)
            # Small in-button symbols for clarity.
            p.setPen(QColor("#111111"))
            if fill == "#F5BC00":  # minimize
                p.drawLine(x + 4, y + h - 5, x + w - 4, y + h - 5)
            elif fill == "#6ABD45":  # restore / shrink toward center
                p.drawRect(x + 4, y + 6, w - 9, h - 10)
                p.drawRect(x + 6, y + 4, w - 9, h - 10)
            else:  # close
                p.drawLine(x + 4, y + 4, x + w - 4, y + h - 4)
                p.drawLine(x + w - 4, y + 4, x + 4, y + h - 4)

        # Title text (avoid button cluster)
        p.setPen(QColor("#000000"))
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_font.setFamilies(["Chicago", "Geneva", "Helvetica Neue", "Tahoma", "MS Sans Serif", "sans-serif"])
        p.setFont(title_font)
        left_pad = 10
        right_limit = yellow[0] - 10
        p.drawText(left_pad, 0, max(0, right_limit - left_pad), self.height(), Qt.AlignVCenter | Qt.AlignLeft, APP_NAME)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._theme_mode = "light"
        self._pal = palette_for_mode(self._theme_mode)
        self._save_dir = Path.home() / "Downloads"
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(980, 640)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        # Prefer the explicitly provided icon from your dist folder.
        icon_path = Path(__file__).resolve().parent / "dist" / "svgviewer-output (3) (1).ico"
        if not icon_path.exists():
            icon_path = Path(__file__).resolve().parent / "assets" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Frameless window frame — thick outer bevel (matches BevelFrame thickness).
        self._frame_margin = 20
        # Outer rim hit band (2px is too small on Windows / HiDPI; 8px is still “edge only”).
        self._resize_edge = 8
        self._manual_resize_edges: Qt.Edge | None = None
        self._resize_last_global: QPoint | None = None

        outer = BevelFrame(self)
        self.outer_layout = QVBoxLayout(outer)
        self.outer_layout.setContentsMargins(
            self._frame_margin,
            self._frame_margin,
            self._frame_margin,
            self._frame_margin,
        )
        self.outer_layout.setSpacing(0)

        self.titlebar = PlatinumTitleBar(outer)
        self.titlebar.close_clicked.connect(self.close)
        self.titlebar.minimize_clicked.connect(self.showMinimized)
        self.titlebar.restore_clicked.connect(self._restore_centered_window)
        self.titlebar.maximize_toggle_clicked.connect(self._toggle_maximize)
        self.titlebar.set_palette(self._pal)
        self.outer_layout.addWidget(self.titlebar)
        self.outer_layout.addWidget(RainbowHeader())

        content = QWidget()
        self.outer_layout.addWidget(content, 1)

        self.setCentralWidget(outer)
        # Needed so we can update the cursor when hovering edges.
        self.setMouseTracking(True)

        root = QVBoxLayout(content)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        self.keyword = QLineEdit()
        self.keyword.setObjectName("keywordField")
        self.keyword.setPlaceholderText('e.g. UE-Mercosur OR "UE-Mercosur"')
        self.keyword.textChanged.connect(self._refresh_save_path)
        self.keyword.setFixedHeight(22)
        self.keyword.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.sortby = SortByComboBox()
        self.sortby.addItems(["Citations", "cit/year"])
        self.sortby.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.nresults = QSpinBox()
        self.nresults.setRange(10, 100)
        self.nresults.setSingleStep(5)
        self.nresults.setValue(25)
        self.nresults.setButtonSymbols(QAbstractSpinBox.UpDownArrows)
        self.nresults.setMinimumWidth(88)
        self.nresults.setMaximumWidth(120)
        self.nresults.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        this_year = datetime.datetime.now().year
        self.start_year = QSpinBox()
        self.start_year.setRange(0, this_year)
        self.start_year.setSpecialValueText("Any")
        self.start_year.setValue(0)
        self.start_year.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.start_year.setButtonSymbols(QAbstractSpinBox.UpDownArrows)
        self.start_year.setMinimumWidth(88)
        self.start_year.setMaximumWidth(120)

        self.end_year = QSpinBox()
        self.end_year.setRange(0, this_year)
        self.end_year.setSpecialValueText("Any")
        self.end_year.setValue(0)
        self.end_year.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.end_year.setButtonSymbols(QAbstractSpinBox.UpDownArrows)
        self.end_year.setMinimumWidth(88)
        self.end_year.setMaximumWidth(120)

        self.lang = QComboBox()
        self._lang_map = {
            "All languages": "All",
            "English": "en",
            "Español": "es",
            "Polski": "pl",
            "Français": "fr",
            "Deutsch": "de",
            "Português": "pt",
            "Italiano": "it",
            "Nederlands": "nl",
            "Svenska": "sv",
            "Norsk": "no",
            "Dansk": "da",
            "Suomi": "fi",
            "Čeština": "cs",
            "Slovenčina": "sk",
            "Magyar": "hu",
            "Română": "ro",
            "Türkçe": "tr",
            "Ελληνικά": "el",
            "Русский": "ru",
            "Українська": "uk",
            "العربية": "ar",
            "हिन्दी": "hi",
            "ไทย": "th",
            "Tiếng Việt": "vi",
            "Bahasa Indonesia": "id",
            "日本語": "ja",
            "한국어": "ko",
            "中文（简体）": "zh-CN",
            "中文（繁體）": "zh-TW",
        }
        # Order matters; place Polish directly below Español as requested.
        ordered = [
            "All languages",
            "English",
            "Español",
            "Polski",
            "Français",
            "Deutsch",
            "Português",
            "Italiano",
            "Nederlands",
            "Svenska",
            "Norsk",
            "Dansk",
            "Suomi",
            "Čeština",
            "Slovenčina",
            "Magyar",
            "Română",
            "Türkçe",
            "Ελληνικά",
            "Русский",
            "Українська",
            "العربية",
            "हिन्दी",
            "ไทย",
            "Tiếng Việt",
            "Bahasa Indonesia",
            "日本語",
            "한국어",
            "中文（简体）",
            "中文（繁體）",
        ]
        self.lang.addItems(ordered)
        self.lang.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.format = QComboBox()
        self.format.addItems(["csv", "xlsx"])
        self.format.currentTextChanged.connect(self._refresh_save_path)
        self.format.setMinimumWidth(72)
        self.format.setMaximumWidth(100)
        self.format.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        for combo in (self.sortby, self.lang, self.format):
            _make_combo_popup_opaque(combo, self._pal.field_bg)

        self.save_to = QLineEdit()
        self.save_to.setReadOnly(True)
        self.save_to.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.save_hint = QLabel("(Auto-saved to your Downloads folder)")
        self.save_hint.setObjectName("saveHint")
        self.choose_folder_btn = QPushButton("Change folder")
        self.choose_folder_btn.clicked.connect(self._choose_save_folder)
        self.theme_btn = QPushButton("Switch to dark mode")
        self.theme_btn.clicked.connect(self._toggle_theme)

        self.instructions = QLabel(
            "Examples:\n"
            "- UE-Mercosur → General search\n"
            '- "UE-Mercosur" → Exact title match\n'
            "- UE-Mercosur -transformer → Exclude specific term\n"
            '- UE-Mercosur author:"Geoffrey Hinton" → Search by author\n'
            "- UE-Mercosur source:Nature → Search within a specific publication\n"
            '- ("UE-Mercosur" OR "Transformer Models") AND (GPT OR BERT) → Boolean search'
        )
        self.instructions.setObjectName("helperText")
        self.instructions.setWordWrap(True)

        form = QWidget()
        form_layout = QFormLayout(form)
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(8)
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        kw_lbl = QLabel("Keyword:")
        kw_lbl.setBuddy(self.keyword)
        form_layout.addRow(kw_lbl, self.keyword)
        form_layout.addRow(QLabel(""), self.instructions)

        quad = QWidget()
        qg = QGridLayout(quad)
        qg.setContentsMargins(0, 0, 0, 0)
        qg.setHorizontalSpacing(12)
        qg.setVerticalSpacing(8)
        qg.setColumnStretch(1, 1)
        qg.setColumnStretch(3, 1)

        lbl_sort = QLabel("Sort by:")
        lbl_lang = QLabel("Language:")
        lbl_res = QLabel("Results:")
        lbl_ft = QLabel("File type:")
        for lb in (lbl_sort, lbl_lang, lbl_res, lbl_ft):
            lb.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_sort.setBuddy(self.sortby)
        lbl_lang.setBuddy(self.lang)
        lbl_res.setBuddy(self.nresults)
        lbl_ft.setBuddy(self.format)

        qg.addWidget(lbl_sort, 0, 0)
        qg.addWidget(self.sortby, 0, 1)
        qg.addWidget(lbl_lang, 0, 2)
        qg.addWidget(self.lang, 0, 3)
        qg.addWidget(lbl_res, 1, 0)
        qg.addWidget(self.nresults, 1, 1)
        qg.addWidget(lbl_ft, 1, 2)
        qg.addWidget(self.format, 1, 3)
        form_layout.addRow(QLabel(""), quad)

        year_row = QWidget()
        yh = QHBoxLayout(year_row)
        yh.setContentsMargins(0, 0, 0, 0)
        yh.setSpacing(10)
        ly_from = QLabel("Year from:")
        ly_to = QLabel("Year to:")
        ly_from.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        ly_to.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        ly_from.setBuddy(self.start_year)
        ly_to.setBuddy(self.end_year)
        yh.addWidget(ly_from)
        yh.addWidget(self.start_year)
        yh.addSpacing(16)
        yh.addWidget(ly_to)
        yh.addWidget(self.end_year)
        yh.addStretch(1)
        form_layout.addRow(QLabel(""), year_row)

        save_row = QWidget()
        sh = QHBoxLayout(save_row)
        sh.setContentsMargins(0, 0, 0, 0)
        sh.setSpacing(8)
        sh.addWidget(self.save_to, 1)
        sh.addWidget(self.choose_folder_btn)
        form_layout.addRow(QLabel("Save as:"), save_row)
        form_layout.addRow(QLabel(""), self.save_hint)

        appearance_wrap = QWidget()
        appearance_layout = QHBoxLayout(appearance_wrap)
        appearance_layout.setContentsMargins(0, 0, 0, 0)
        appearance_layout.setSpacing(6)
        appearance_layout.addWidget(self.theme_btn)
        appearance_layout.addStretch(1)
        form_layout.addRow(QLabel("Appearance:"), appearance_wrap)

        root.addWidget(form)

        buttons = QHBoxLayout()
        self.run_btn = QPushButton("Search")
        self.run_btn.clicked.connect(self._run_search)
        self.open_btn = QPushButton("Open folder")
        self.open_btn.clicked.connect(self._open_folder)
        self.open_btn.setEnabled(False)

        buttons.addWidget(self.run_btn)
        buttons.addWidget(self.open_btn)
        buttons.addStretch(1)

        self.status = QLabel("")  # remove the initial "Ready." text
        buttons.addWidget(self.status)
        root.addLayout(buttons)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        root.addWidget(self.progress)

        self.model = ResultsModel()
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSortingEnabled(False)
        self.table.clicked.connect(self._on_table_clicked)
        root.addWidget(self.table, 1)

        self._last_saved: Optional[Path] = None
        self._install_shortcuts()
        # Create a Desktop shortcut so users can quickly launch the app later.
        # This is safe: we check existence first and never overwrite anything.
        _maybe_create_desktop_shortcut()
        self._refresh_save_path()
        self._apply_theme()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)

    def _edge_bits_from_pos(self, pos) -> int:
        x = pos.x()
        y = pos.y()
        e = self._resize_edge

        left = x <= e
        right = x >= self.width() - e - 1
        top = y <= e
        bottom = y >= self.height() - e - 1

        bits = 0
        if left:
            bits |= 1
        if right:
            bits |= 2
        if top:
            bits |= 4
        if bottom:
            bits |= 8
        return bits

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._manual_resize_edges is not None and self._resize_last_global is not None:
            if event.buttons() & Qt.LeftButton:
                self._manual_resize_step(event.globalPosition().toPoint())
            event.accept()
            return

        if self.isMaximized() or self.isFullScreen():
            return super().mouseMoveEvent(event)

        pos = event.position().toPoint()
        edges = self._edge_bits_from_pos(pos)

        if edges == 0:
            self.unsetCursor()
        else:
            if (edges & 1 and edges & 4) or (edges & 2 and edges & 8):
                self.setCursor(Qt.SizeFDiagCursor)
            elif (edges & 2 and edges & 4) or (edges & 1 and edges & 8):
                self.setCursor(Qt.SizeBDiagCursor)
            elif edges & (1 | 2):
                self.setCursor(Qt.SizeHorCursor)
            elif edges & (4 | 8):
                self.setCursor(Qt.SizeVerCursor)

        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton and self._manual_resize_edges is not None:
            self.releaseMouse()
            self._manual_resize_edges = None
            self._resize_last_global = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        if self.isMaximized() or self.isFullScreen():
            return super().mousePressEvent(event)

        pos = event.position().toPoint()
        edges = self._edge_bits_from_pos(pos)
        if edges == 0:
            return super().mousePressEvent(event)

        # If the user clicked inside a real control, don't resize.
        clicked = self.childAt(pos)
        if clicked is not None and clicked != self and isinstance(
            clicked,
            (QCheckBox, QComboBox, QLineEdit, QSpinBox, QPushButton, QTableView, PlatinumTitleBar),
        ):
            return super().mousePressEvent(event)

        qt_edges = Qt.Edge(0)
        if edges & 1:
            qt_edges |= Qt.Edge.LeftEdge
        if edges & 2:
            qt_edges |= Qt.Edge.RightEdge
        if edges & 4:
            qt_edges |= Qt.Edge.TopEdge
        if edges & 8:
            qt_edges |= Qt.Edge.BottomEdge

        # En Windows, ventana sin marco: startSystemResize suele fallar o comportarse mal; usamos arrastre manual.
        handle = self.windowHandle()
        if (
            not sys.platform.startswith("win")
            and handle is not None
            and qt_edges
            and handle.startSystemResize(qt_edges)
        ):
            event.accept()
            return True

        self._manual_resize_edges = qt_edges
        self._resize_last_global = event.globalPosition().toPoint()
        self.grabMouse()
        event.accept()
        return True

    def _manual_resize_step(self, global_pos: QPoint) -> None:
        if self._manual_resize_edges is None or self._resize_last_global is None:
            return
        delta = global_pos - self._resize_last_global
        self._resize_last_global = global_pos
        g = self.geometry()
        min_w, min_h = self.minimumWidth(), self.minimumHeight()
        e = self._manual_resize_edges

        if e & Qt.Edge.LeftEdge:
            new_w = g.width() - delta.x()
            if new_w >= min_w:
                g.setLeft(g.left() + delta.x())
                g.setWidth(new_w)
        if e & Qt.Edge.RightEdge:
            new_w = g.width() + delta.x()
            g.setWidth(max(min_w, new_w))
        if e & Qt.Edge.TopEdge:
            new_h = g.height() - delta.y()
            if new_h >= min_h:
                g.setTop(g.top() + delta.y())
                g.setHeight(new_h)
        if e & Qt.Edge.BottomEdge:
            new_h = g.height() + delta.y()
            g.setHeight(max(min_h, new_h))

        self.setGeometry(g)

    def _install_shortcuts(self) -> None:
        act = QAction(self)
        act.setShortcut(QKeySequence(Qt.Key_F11))
        act.triggered.connect(self._toggle_fullscreen)
        self.addAction(act)

    def paintEvent(self, event):  # noqa: N802
        # Bevel border is drawn by the central `BevelFrame` widget.
        super().paintEvent(event)

    def _refresh_save_path(self) -> None:
        keyword = (self.keyword.text() or "").strip()
        ext = self.format.currentText()
        base = _sanitize_filename(keyword) if keyword else "scholar_results"
        out = self._save_dir / f"{base}.{ext}"
        self.save_to.setText(str(out))
        default_dir = Path.home() / "Downloads"
        if self._save_dir == default_dir:
            self.save_hint.setText("(Auto-saved to your Downloads folder)")
        else:
            self.save_hint.setText(f"(Auto-saved to: {self._save_dir})")

    def _apply_theme(self) -> None:
        self._pal = palette_for_mode(self._theme_mode)
        QApplication.instance().setStyleSheet(qss(self._theme_mode))
        for combo in (self.sortby, self.lang, self.format):
            _make_combo_popup_opaque(combo, self._pal.field_bg)
        self.titlebar.set_palette(self._pal)
        self.model.apply_palette(self._pal)
        if self._theme_mode == "dark":
            self.theme_btn.setText("Switch to light mode")
        else:
            self.theme_btn.setText("Switch to dark mode")

    def _toggle_theme(self) -> None:
        self._theme_mode = "dark" if self._theme_mode == "light" else "light"
        self._apply_theme()

    def _choose_save_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self,
            "Choose export folder",
            str(self._save_dir),
        )
        if chosen:
            self._save_dir = Path(chosen)
            self._refresh_save_path()

    def _toggle_maximize(self) -> None:
        new_state = self.windowState() ^ Qt.WindowState.WindowMaximized
        self.setWindowState(new_state)
        if not (new_state & Qt.WindowState.WindowMaximized):
            _windows_native_clear_maximized(self)
            QApplication.processEvents()

    def _restore_centered_window(self) -> None:
        """Green control: salir de maximizado real de Windows y centrar la ventana."""
        self.setWindowState(Qt.WindowState.WindowNoState)
        self.showNormal()
        _windows_native_clear_maximized(self)
        QApplication.processEvents()
        QTimer.singleShot(0, self._apply_restore_size)

    def _apply_restore_size(self) -> None:
        _windows_native_clear_maximized(self)
        self.setWindowState(Qt.WindowState.WindowNoState)
        self.showNormal()
        QApplication.processEvents()

        screen = QApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        mw, mh = self.minimumWidth(), self.minimumHeight()
        w = max(mw, min(1040, avail.width() - 48))
        h = max(mh, min(720, avail.height() - 48))
        x = avail.x() + max(0, (avail.width() - w) // 2)
        y = avail.y() + max(0, (avail.height() - h) // 2)
        self.setGeometry(QRect(x, y, w, h))
        # Si el SO aún ignora el tamaño, un segundo intento tras un frame.
        if self.width() != w or self.height() != h:
            QTimer.singleShot(50, lambda: self._retry_restore_if_stuck(w, h, x, y))
        self.raise_()
        self.activateWindow()

    def _retry_restore_if_stuck(self, w: int, h: int, x: int, y: int) -> None:
        _windows_native_clear_maximized(self)
        QApplication.processEvents()
        self.setGeometry(QRect(x, y, w, h))

    def _toggle_fullscreen(self) -> None:
        # Keep taskbar visible: use maximize toggle instead of true fullscreen.
        if self.isMaximized():
            self.showNormal()
            _windows_native_clear_maximized(self)
            QApplication.processEvents()
        else:
            self.showMaximized()

    def _on_table_clicked(self, index: QModelIndex) -> None:
        try:
            v = self.model.data(index, Qt.DisplayRole)
            s = "" if v is None else str(v)
            if s.startswith("http://") or s.startswith("https://"):
                QDesktopServices.openUrl(QUrl(s))
        except Exception:
            return

    def _open_folder(self) -> None:
        if not self._last_saved:
            return
        folder = self._last_saved.parent
        try:
            if sys.platform.startswith("win"):
                import os

                os.startfile(str(folder))  # noqa: S606
            elif sys.platform == "darwin":
                # macOS
                subprocess.run(["open", str(folder)], check=False)
            else:
                # Linux and other Unix-like
                subprocess.run(["xdg-open", str(folder)], check=False)
        except Exception:
            QMessageBox.information(self, APP_NAME, f"Saved in:\n{folder}")

    def _params(self) -> SearchParams:
        keyword = self.keyword.text().strip()
        start = self.start_year.value()
        end = self.end_year.value()
        start_year = None if start == 0 else int(start)
        end_year = None if end == 0 else int(end)

        out_path = Path(self.save_to.text().strip() or "").expanduser()
        if not out_path.suffix:
            out_path = out_path.with_suffix("." + self.format.currentText())

        return SearchParams(
            keyword=keyword,
            sortby=self.sortby.currentText(),
            nresults=int(self.nresults.value()),
            start_year=start_year,
            end_year=end_year,
            langfilter=self._lang_map.get(self.lang.currentText(), "All"),
            # Removed the UI "tick option", keep the safer default delay behavior.
            extra_delay=True,
            out_format=self.format.currentText(),
            out_path=out_path,
        )

    def _run_search(self) -> None:
        params = self._params()
        if not params.keyword:
            QMessageBox.warning(self, APP_NAME, "Please enter a keyword.")
            return
        if not params.out_path.parent.exists():
            QMessageBox.warning(self, APP_NAME, "The chosen folder does not exist.")
            return

        self.run_btn.setEnabled(False)
        self.open_btn.setEnabled(False)
        self.status.setText("Searching…")
        self.progress.setValue(0)

        self._thread = QThread(self)
        self._worker = SearchWorker(params)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.progress.setValue)
        self._worker.finished.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_done(self, headers: list, rows: list) -> None:
        self.model.set_results(list(headers), list(rows))
        self.table.resizeColumnsToContents()
        self.status.setText(f"Saved {len(rows)} rows.")
        self.progress.setValue(100)
        self.run_btn.setEnabled(True)
        self.open_btn.setEnabled(True)
        self._last_saved = Path(self.save_to.text().strip())

    def _on_failed(self, message: str) -> None:
        self.status.setText("Failed.")
        self.progress.setValue(0)
        self.run_btn.setEnabled(True)
        QMessageBox.critical(
            self,
            APP_NAME,
            "Google Scholar blocked the request or the network timed out.\n\n"
            f"Details:\n{message}\n\n"
            "Tip: try fewer searches, wait a few minutes, then try again.",
        )


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    # Fusion makes combo popups follow QSS instead of semi-transparent native menus (esp. Windows).
    fusion = QStyleFactory.create("Fusion")
    if fusion is not None:
        app.setStyle(fusion)
    app.setStyleSheet(qss("light"))
    w = MainWindow()
    # No usar showMaximized() con ventana sin marco en Windows: deja WS_MAXIMIZE y
    # setGeometry deja de funcionar (pantalla completa “pegada”). Misma apariencia:
    sc = QApplication.primaryScreen()
    if sc is not None:
        w.setGeometry(sc.availableGeometry())
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

