from __future__ import annotations

import csv
import datetime
import re
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
    QSizeGrip,
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
    exact_phrase: bool
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
            phrase = keyword.strip().strip("'\"") if self.params.exact_phrase else None

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

        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.titlebar = PlatinumTitleBar(outer)
        self.titlebar.close_clicked.connect(self.close)
        self.titlebar.minimize_clicked.connect(self.showMinimized)
        self.titlebar.zoom_clicked.connect(self._toggle_maximize)
        outer_layout.addWidget(self.titlebar)
        outer_layout.addWidget(RainbowHeader())

        content = QWidget()
        outer_layout.addWidget(content, 1)

        self.setCentralWidget(outer)

        # Manual resize handle for a frameless window.
        self._size_grip = QSizeGrip(self)
        self._size_grip.setFixedSize(self._size_grip.sizeHint())
        self._size_grip.raise_()

        self._resizing = False
        self._resize_edges = 0
        self._resize_start_pos = None
        self._resize_start_geom = None

        # Edge-resize for frameless windows: native resizing doesn't work reliably.
        QApplication.instance().installEventFilter(self)

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
        self.keyword.setPlaceholderText("e.g. \"UE-Mercosur\" OR \"Transformer Models\"")

        self.exact_label = QLabel("Exact phrase (filters by title)")
        self.exact_label.setStyleSheet("font-weight: 600;")

        self.exact = QCheckBox("")  # box is rendered to the right of the label
        self.exact.setToolTip("Filters results by whether the phrase appears in the title.")
        self.exact.setFixedSize(22, 22)
        self.exact.setStyleSheet(
            """
            QCheckBox::indicator {
              width: 16px;
              height: 16px;
              border: 2px solid #000000;
              background-color: transparent;
              border-radius: 2px;
            }
            QCheckBox::indicator:unchecked {
              border: 2px solid #000000;
              background-color: transparent;
            }
            QCheckBox::indicator:checked {
              border: 2px solid #000000;
              background-color: transparent;
            }
            """
        )

        exact_row = QWidget()
        exact_layout = QHBoxLayout(exact_row)
        exact_layout.setContentsMargins(0, 0, 0, 0)
        exact_layout.setSpacing(6)
        exact_layout.addWidget(self.exact_label, 0, Qt.AlignLeft | Qt.AlignVCenter)
        # Keep the square immediately next to the label (not pushed to the far right).
        exact_layout.addWidget(self.exact, 0, Qt.AlignLeft | Qt.AlignVCenter)
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

        # Exact phrase option must sit between the keyword bar and the examples.
        grid.addWidget(exact_row, row, 1, 1, 3)
        row += 1

        self.instructions = QLabel(
            "Examples:\n"
            "- UE-Mercosur → General search\n"
            '- "UE-Mercosur" → Exact phrase search\n'
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
        if hasattr(self, "_size_grip") and self._size_grip:
            # Anchor to the bottom-right corner in the main window frame.
            self._size_grip.move(
                self.width() - self._size_grip.width(),
                self.height() - self._size_grip.height(),
            )
            self._size_grip.raise_()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # type: ignore[override]
        # Frameless resizing: detect clicks near window edges and resize accordingly.
        # (We ignore title bar events so dragging the window still works normally.)
        if event is None:
            return False
        if self.isMaximized():
            return False

        # Only handle events relevant to resizing.
        if event.type() not in (QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            return False

        # Avoid interfering with the custom title bar drag.
        if event.type() == QEvent.MouseButtonPress and obj == self.titlebar:
            return False

        # local position of cursor within the window
        try:
            gp = event.globalPosition().toPoint()  # type: ignore[attr-defined]
        except Exception:
            return False

        lp = self.mapFromGlobal(gp)

        # Ignore if cursor is outside the window rect.
        if not self.rect().contains(lp):
            if not self._resizing:
                self.unsetCursor()
            return False

        EDGE = 8
        left = lp.x() <= EDGE
        right = lp.x() >= self.width() - EDGE
        top = lp.y() <= EDGE
        bottom = lp.y() >= self.height() - EDGE

        edges = 0
        if left:
            edges |= 1
        if right:
            edges |= 2
        if top:
            edges |= 4
        if bottom:
            edges |= 8

        if event.type() == QEvent.MouseMove:
            if self._resizing:
                if self._resize_start_pos is None or self._resize_start_geom is None:
                    return True
                dx = gp.x() - self._resize_start_pos.x()
                dy = gp.y() - self._resize_start_pos.y()
                g = self._resize_start_geom
                active_edges = self._resize_edges
                min_w = max(self.minimumWidth(), 200)
                min_h = max(self.minimumHeight(), 200)

                new_x = g.x()
                new_y = g.y()
                new_w = g.width()
                new_h = g.height()

                if active_edges & 1:  # left
                    new_x = g.x() + dx
                    new_w = g.width() - dx
                if active_edges & 2:  # right
                    new_w = g.width() + dx
                if active_edges & 4:  # top
                    new_y = g.y() + dy
                    new_h = g.height() - dy
                if active_edges & 8:  # bottom
                    new_h = g.height() + dy

                # Enforce minimum size (and keep the "pinned" edge stable).
                if new_w < min_w:
                    if active_edges & 1:
                        new_x = g.right() - (min_w - 1)
                    new_w = min_w
                if new_h < min_h:
                    if active_edges & 4:
                        new_y = g.bottom() - (min_h - 1)
                    new_h = min_h

                self.setGeometry(new_x, new_y, new_w, new_h)
                return True

            # Not resizing: update cursor if hovering over an edge.
            if edges == 0:
                self.unsetCursor()
                return False

            if (edges & 1 and edges & 4) or (edges & 2 and edges & 8):
                self.setCursor(Qt.SizeFDiagCursor)
            elif (edges & 2 and edges & 4) or (edges & 1 and edges & 8):
                self.setCursor(Qt.SizeBDiagCursor)
            elif edges & (1 | 2):
                self.setCursor(Qt.SizeHorCursor)
            elif edges & (4 | 8):
                self.setCursor(Qt.SizeVerCursor)
            return False

        if event.type() == QEvent.MouseButtonPress:
            # Start resizing only when the click is near an edge.
            if edges == 0:
                return False
            try:
                btn = event.button()  # type: ignore[attr-defined]
            except Exception:
                return False
            if btn != Qt.LeftButton:
                return False

            # Anchor to the initial edges where the press happened.
            self._resizing = True
            self._resize_edges = edges
            self._resize_start_pos = gp
            self._resize_start_geom = self.geometry()
            return True

        if event.type() == QEvent.MouseButtonRelease:
            if self._resizing:
                self._resizing = False
                self._resize_edges = 0
                self._resize_start_pos = None
                self._resize_start_geom = None
                return True

        return False

    def _install_shortcuts(self) -> None:
        act = QAction(self)
        act.setShortcut(QKeySequence(Qt.Key_F11))
        act.triggered.connect(self._toggle_fullscreen)
        self.addAction(act)

    def paintEvent(self, event):  # noqa: N802
        # Chunky 3px beveled border: light top-left, dark bottom-right.
        p = QPainter(self)
        r = self.rect()
        for i in range(3):
            p.setPen(QColor(PAL.surface))
            p.drawLine(r.left() + i, r.top() + i, r.right() - i, r.top() + i)
            p.drawLine(r.left() + i, r.top() + i, r.left() + i, r.bottom() - i)
            p.setPen(QColor(PAL.shadow))
            p.drawLine(r.left() + i, r.bottom() - i, r.right() - i, r.bottom() - i)
            p.drawLine(r.right() - i, r.top() + i, r.right() - i, r.bottom() - i)
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
            else:
                QMessageBox.information(self, APP_NAME, f"Saved in:\n{folder}")
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
            exact_phrase=self.exact.isChecked(),
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

