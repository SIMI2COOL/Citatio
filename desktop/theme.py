from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    # Apple rainbow accents (exact palette per user spec)
    green: str = "#6ABD45"
    yellow: str = "#F5BC00"
    orange: str = "#F6821F"
    red: str = "#E2231A"
    purple: str = "#8A2BE2"
    blue: str = "#009CDE"

    # Mac OS 9 Platinum grays
    surface: str = "#F0F0F0"
    chrome: str = "#C0C0C0"
    edge: str = "#909090"
    shadow: str = "#606060"

    text: str = "#1A1A1A"


PAL = Palette()


def qss() -> str:
    p = PAL
    return f"""
    /* Global */
    QWidget {{
      background: {p.surface};
      color: {p.text};
      font-family: Chicago, Geneva, "Helvetica Neue", sans-serif;
      font-size: 12px;
    }}

    /* Inset wells */
    QLineEdit, QSpinBox, QComboBox {{
      background: #FFFFFF;
      border: 2px solid {p.edge};
      border-top-color: {p.shadow};
      border-left-color: {p.shadow};
      padding: 4px 6px;
    }}
    QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{
      color: {p.edge};
      background: {p.surface};
    }}

    /* Raised buttons */
    QPushButton {{
      background: {p.chrome};
      border: 2px solid {p.shadow};
      border-top-color: #FFFFFF;
      border-left-color: #FFFFFF;
      padding: 6px 10px;
      min-height: 24px;
    }}
    QPushButton:pressed {{
      border: 2px solid {p.shadow};
      border-bottom-color: #FFFFFF;
      border-right-color: #FFFFFF;
      padding-top: 7px;
      padding-left: 11px;
    }}
    QPushButton:disabled {{
      color: {p.edge};
      background: {p.chrome};
    }}

    /* Checkboxes */
    QCheckBox {{
      spacing: 6px;
    }}

    /* Table */
    QTableView {{
      background: #FFFFFF;
      gridline-color: {p.edge};
      border: 2px solid {p.edge};
      border-top-color: {p.shadow};
      border-left-color: {p.shadow};
      selection-background-color: {p.blue};
      selection-color: #000000;
      alternate-background-color: {p.surface};
    }}
    QHeaderView::section {{
      background: {p.chrome};
      border: 1px solid {p.shadow};
      border-top-color: #FFFFFF;
      border-left-color: #FFFFFF;
      padding: 4px 6px;
      font-weight: 700;
      color: {p.shadow};
    }}

    /* Progress bar */
    QProgressBar {{
      border: 2px solid {p.edge};
      border-top-color: {p.shadow};
      border-left-color: {p.shadow};
      background: #FFFFFF;
      text-align: center;
      height: 18px;
    }}
    QProgressBar::chunk {{
      background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {p.green},
        stop:0.2 {p.yellow},
        stop:0.4 {p.orange},
        stop:0.6 {p.red},
        stop:0.8 {p.purple},
        stop:1 {p.blue}
      );
    }}
    """

