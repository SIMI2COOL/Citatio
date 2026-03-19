from __future__ import annotations

import csv
import sys
import traceback
import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, Qt, QThread, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableView,
    QVBoxLayout,
    QWidget,
    QProgressBar,
)

from theme import PAL, qss


APP_NAME = "CiteRank (Desktop)"


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

            # Keep conservative by default to reduce Scholar blocks.
            nresults = max(10, min(15, int(self.params.nresults)))

            self.progress.emit(15)
            headers, rows = run_search(
                keyword=keyword,
                nresults=nresults,
                sortby=self.params.sortby,
                start_year=self.params.start_year,
                end_year=self.params.end_year,
                langfilter="All" if self.params.langfilter == "All" else [self.params.langfilter],
                debug=False,
                delay_seconds=1.0,
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
        self.setFixedHeight(18)

    def paintEvent(self, event):  # noqa: N802
        colors = [PAL.green, PAL.yellow, PAL.orange, PAL.red, PAL.purple, PAL.blue]
        stripe_h = max(1, self.height() // len(colors))
        p = QPainter(self)
        y = 0
        for c in colors:
            p.fillRect(0, y, self.width(), stripe_h, QColor(c))
            y += stripe_h
        if y < self.height():
            p.fillRect(0, y, self.width(), self.height() - y, QColor(colors[-1]))


class PlatinumTitleBar(QWidget):
    close_clicked = Signal()

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
        w = self.window()
        w.setWindowState(w.windowState() ^ Qt.WindowMaximized)

    def _close_rect(self):
        return (10, 7, 12, 12)

    def mouseReleaseEvent(self, event):  # type: ignore[override]  # noqa: N802
        if event.button() == Qt.LeftButton:
            x, y, w, h = self._close_rect()
            if x <= event.position().x() <= x + w and y <= event.position().y() <= y + h:
                self.close_clicked.emit()
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

        # Title text
        p.setPen(QColor(PAL.shadow))
        p.drawText(34, 0, self.width() - 34, self.height(), Qt.AlignVCenter | Qt.AlignLeft, APP_NAME)

        # Close box: small square with 1px black outline
        x, y, w, h = self._close_rect()
        p.setPen(QColor("#000000"))
        p.setBrush(QColor(PAL.chrome))
        p.drawRect(x, y, w, h)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(980, 640)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.titlebar = PlatinumTitleBar(outer)
        self.titlebar.close_clicked.connect(self.close)
        outer_layout.addWidget(self.titlebar)
        outer_layout.addWidget(RainbowHeader())

        content = QWidget()
        outer_layout.addWidget(content, 1)

        self.setCentralWidget(outer)

        root = QVBoxLayout(content)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        form = QWidget()
        grid = QGridLayout(form)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.keyword = QLineEdit()
        self.keyword.setPlaceholderText("e.g. diffusion models medical imaging")
        self.exact = QCheckBox("Exact phrase (filters by title)")

        self.sortby = QComboBox()
        self.sortby.addItems(["Citations", "cit/year"])

        self.nresults = QSpinBox()
        self.nresults.setRange(10, 15)
        self.nresults.setValue(15)

        this_year = datetime.datetime.now().year
        self.start_year = QSpinBox()
        self.start_year.setRange(0, this_year)
        self.start_year.setSpecialValueText("Any")
        self.start_year.setValue(0)

        self.end_year = QSpinBox()
        self.end_year.setRange(0, this_year)
        self.end_year.setSpecialValueText("Any")
        self.end_year.setValue(0)

        self.lang = QComboBox()
        self.lang.addItems(["All", "en", "es", "fr", "de", "pt", "it"])

        self.format = QComboBox()
        self.format.addItems(["csv", "xlsx"])

        self.save_to = QLineEdit()
        self.save_to.setReadOnly(True)
        self.browse = QPushButton("Choose file…")
        self.browse.clicked.connect(self._choose_file)

        row = 0
        grid.addWidget(QLabel("Keyword"), row, 0)
        grid.addWidget(self.keyword, row, 1, 1, 3)
        row += 1

        grid.addWidget(self.exact, row, 1, 1, 3)
        row += 1

        grid.addWidget(QLabel("Sort by"), row, 0)
        grid.addWidget(self.sortby, row, 1)
        grid.addWidget(QLabel("Results (max 15)"), row, 2)
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
        grid.addWidget(self.browse, row, 3)

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

        self.status = QLabel("Ready.")
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
        root.addWidget(self.table, 1)

        self._last_saved: Optional[Path] = None
        self._choose_default_file()

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

    def _choose_default_file(self) -> None:
        base = "scholar_results"
        ext = self.format.currentText()
        out = Path.home() / "Downloads" / f"{base}.{ext}"
        self.save_to.setText(str(out))

    def _choose_file(self) -> None:
        ext = self.format.currentText()
        suggested = self.save_to.text().strip() or str(Path.home() / "Downloads" / f"scholar_results.{ext}")
        filt = "CSV (*.csv)" if ext == "csv" else "Excel (*.xlsx)"
        path, _ = QFileDialog.getSaveFileName(self, "Save results as…", suggested, filt)
        if path:
            self.save_to.setText(path)

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
            langfilter=self.lang.currentText(),
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

