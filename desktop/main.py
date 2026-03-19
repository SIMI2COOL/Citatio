from __future__ import annotations

import csv
import datetime
import re
import subprocess
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple

from PySide6.QtCore import QAbstractTableModel, QEvent, QModelIndex, QObject, Qt, QThread, QTimer, Signal, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QKeySequence, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QAbstractSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableView,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QProgressBar,
)

from theme import PAL, qss


APP_NAME = "Citatio"


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
                        return QColor(PAL.purple)
                    f = QFont()
                    f.setUnderline(True)
                    return f
            except Exception:
                return None

        if role == Qt.BackgroundRole:
            # Zebra rows: #F0F0F0 / #FFFFFF
            return QColor(PAL.surface if (r % 2 == 0) else "#FFFFFF")

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
        colors = [PAL.green, PAL.yellow, PAL.orange, PAL.red, PAL.purple, PAL.blue]
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
            top_left_pen = (
                PAL.bevel_highlight if i < highlight_px else PAL.bevel_inner
            )

            # Bottom/right stay dark on the outside, then become inner gray, then dark again.
            bottom_right_pen = (
                PAL.bevel_shadow if i < highlight_px or i >= highlight_px + inner_px else PAL.bevel_inner
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
    zoom_clicked = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedHeight(26)
        self._drag_pos = None

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
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
        # "Zoom" behavior on title bar double click (simple maximize toggle)
        self.zoom_clicked.emit()

    def _button_rects(self):
        # Right side cluster, ordered: yellow(min), green(max), red(close)
        size = 12
        gap = 6
        y = 7
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
                ("zoom", green),
                ("close", red),
            ):
                if x <= px <= x + w and y <= py <= y + h:
                    if which == "close":
                        self.close_clicked.emit()
                    elif which == "min":
                        self.minimize_clicked.emit()
                    else:
                        self.zoom_clicked.emit()
                    break
        self._drag_pos = None
        event.accept()

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        # Pinstripe title bar in chrome/edge
        p.fillRect(self.rect(), QColor(PAL.chrome))
        pen = QPen(QColor(PAL.edge))
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

        # Title text (avoid button cluster)
        p.setPen(QColor(PAL.shadow))
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        p.setFont(title_font)
        left_pad = 10
        right_limit = yellow[0] - 10
        p.drawText(left_pad, 0, max(0, right_limit - left_pad), self.height(), Qt.AlignVCenter | Qt.AlignLeft, APP_NAME)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(980, 640)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        # Prefer the explicitly provided icon from your dist folder.
        icon_path = Path(__file__).resolve().parent / "dist" / "svgviewer-output (3) (1).ico"
        if not icon_path.exists():
            icon_path = Path(__file__).resolve().parent / "assets" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Frameless window frame (Mac OS-style bevel).
        # Keep this in sync with the bevel thickness drawn in paintEvent().
        self._frame_margin = 20
        # Wider hit area so resizing feels dynamic even while dragging quickly.
        self._resize_edge = 7

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
        self.titlebar.zoom_clicked.connect(self._toggle_maximize)
        self.outer_layout.addWidget(self.titlebar)
        self.outer_layout.addWidget(RainbowHeader())

        content = QWidget()
        self.outer_layout.addWidget(content, 1)

        self.setCentralWidget(outer)
        # Needed so we can update the cursor when hovering edges.
        self.setMouseTracking(True)

        root = QVBoxLayout(content)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        form = QWidget()
        grid = QGridLayout(form)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(8)
        grid.setColumnMinimumWidth(0, 90)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 1)

        self.keyword = QLineEdit()
        self.keyword.setPlaceholderText('e.g. UE-Mercosur OR "UE-Mercosur"')
        self.keyword.textChanged.connect(self._refresh_save_path)

        self.sortby = QComboBox()
        self.sortby.addItems(["Citations", "cit/year"])

        self.nresults = QSpinBox()
        self.nresults.setRange(10, 100)
        self.nresults.setSingleStep(5)
        self.nresults.setValue(25)
        self.nresults.setButtonSymbols(QAbstractSpinBox.UpDownArrows)
        self.nresults.setFixedWidth(90)  # ensure both arrows remain visible

        this_year = datetime.datetime.now().year
        self.start_year = QSpinBox()
        self.start_year.setRange(0, this_year)
        self.start_year.setSpecialValueText("Any")
        self.start_year.setValue(0)
        self.start_year.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.end_year = QSpinBox()
        self.end_year.setRange(0, this_year)
        self.end_year.setSpecialValueText("Any")
        self.end_year.setValue(0)
        self.end_year.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

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

        self.format = QComboBox()
        self.format.addItems(["csv", "xlsx"])
        self.format.currentTextChanged.connect(self._refresh_save_path)

        self.save_to = QLineEdit()
        self.save_to.setReadOnly(True)
        self.save_hint = QLabel("(Auto-saved to your Downloads folder)")
        self.save_hint.setStyleSheet(f"color: {PAL.edge};")

        row = 0
        grid.addWidget(QLabel("Keyword"), row, 0, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        grid.addWidget(self.keyword, row, 1, 1, 3)
        row += 1

        self.instructions = QLabel(
            "Examples:\n"
            "- UE-Mercosur → General search\n"
            '- "UE-Mercosur" → Exact title match\n'
            "- UE-Mercosur -transformer → Exclude specific term\n"
            '- UE-Mercosur author:"Geoffrey Hinton" → Search by author\n'
            "- UE-Mercosur source:Nature → Search within a specific publication\n"
            '- ("UE-Mercosur" OR "Transformer Models") AND (GPT OR BERT) → Boolean search'
        )
        self.instructions.setStyleSheet(f"color: {PAL.shadow};")
        self.instructions.setWordWrap(True)
        grid.addWidget(self.instructions, row, 1, 1, 3)
        row += 1

        grid.addWidget(QLabel("Sort by"), row, 0)
        grid.addWidget(self.sortby, row, 1)
        grid.addWidget(QLabel("Results (max 100)"), row, 2)
        grid.addWidget(self.nresults, row, 3)
        row += 1

        grid.addWidget(QLabel("Year from"), row, 0)
        grid.addWidget(self.start_year, row, 1)
        grid.addWidget(QLabel("Year to"), row, 2)
        grid.addWidget(self.end_year, row, 3)
        row += 1

        grid.addWidget(QLabel("Language"), row, 0)
        grid.addWidget(self.lang, row, 1)
        grid.addWidget(QLabel("File type"), row, 2)
        grid.addWidget(self.format, row, 3)
        row += 1

        grid.addWidget(QLabel("Save as"), row, 0)
        grid.addWidget(self.save_to, row, 1, 1, 2)
        grid.addWidget(self.save_hint, row, 3)

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
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSortingEnabled(False)
        self.table.clicked.connect(self._on_table_clicked)
        root.addWidget(self.table, 1)

        self._last_saved: Optional[Path] = None
        self._install_shortcuts()
        self._refresh_save_path()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        # No manual grip: resizing is edge-only for the frameless window.

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

        handle = self.windowHandle()
        if handle is not None:
            qt_edges = Qt.Edge(0)
            if edges & 1:
                qt_edges |= Qt.Edge.LeftEdge
            if edges & 2:
                qt_edges |= Qt.Edge.RightEdge
            if edges & 4:
                qt_edges |= Qt.Edge.TopEdge
            if edges & 8:
                qt_edges |= Qt.Edge.BottomEdge
            if qt_edges and handle.startSystemResize(qt_edges):
                event.accept()
                return True

        return super().mousePressEvent(event)

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
        out = Path.home() / "Downloads" / f"{base}.{ext}"
        self.save_to.setText(str(out))

    def _toggle_maximize(self) -> None:
        self.setWindowState(self.windowState() ^ Qt.WindowMaximized)

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

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
    app.setStyleSheet(qss())
    w = MainWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

