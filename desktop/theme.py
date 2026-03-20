from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    # Rainbow strip colors (header widget in app — unchanged)
    green: str = "#6ABD45"
    yellow: str = "#F5BC00"
    orange: str = "#F6821F"
    red: str = "#E2231A"
    purple: str = "#8A2BE2"
    blue: str = "#009CDE"

    # Classic platinum / high-contrast greys (original app look)
    surface: str = "#F0F0F0"
    chrome: str = "#C0C0C0"
    edge: str = "#909090"
    shadow: str = "#606060"

    field_bg: str = "#FFFFFF"
    alt_row: str = "#FFFFFF"

    # 3D helpers (raised / inset)
    highlight: str = "#FFFFFF"
    light_edge: str = "#DFDFDF"
    dark_shadow: str = "#404040"

    text: str = "#1A1A1A"
    text_muted: str = "#606060"
    link: str = "#8A2BE2"

    selection_bg: str = "#009CDE"
    selection_text: str = "#000000"

    # Outer window bevel (BevelFrame paint)
    bevel_highlight: str = "#FFFFFF"
    bevel_inner: str = "#808080"
    bevel_shadow: str = "#404040"

    # Unused by title bar paint (grey bar) — kept for compatibility
    caption_bg: str = "#C0C0C0"
    caption_text: str = "#000000"


LIGHT = Palette()

DARK = Palette(
    surface="#181818",
    chrome="#383838",
    edge="#7A7A7A",
    shadow="#D0D0D0",
    field_bg="#242424",
    alt_row="#202020",
    highlight="#9A9A9A",
    light_edge="#7A7A7A",
    dark_shadow="#101010",
    text="#F2F2F2",
    text_muted="#B0B0B0",
    link="#7FCBFF",
    selection_bg="#F5BC00",
    selection_text="#111111",
    bevel_highlight="#9A9A9A",
    bevel_inner="#4D4D4D",
    bevel_shadow="#101010",
    caption_bg="#383838",
    caption_text="#F2F2F2",
)

PAL = LIGHT


def palette_for_mode(mode: str) -> Palette:
    return DARK if mode == "dark" else LIGHT


def qss(mode: str = "light") -> str:
    p = palette_for_mode(mode)
    return f"""
    * {{
      border-radius: 0px;
    }}

    QWidget {{
      background: {p.surface};
      color: {p.text};
      font-family: Chicago, Geneva, "Helvetica Neue", Tahoma, "MS Sans Serif", sans-serif;
      font-size: 12px;
      font-weight: normal;
    }}

    QLabel {{
      font-weight: normal;
    }}

    /* Sunken inputs (dark top-left, light bottom-right) */
    QLineEdit {{
      background: {p.field_bg};
      color: {p.text};
      border: 2px solid {p.edge};
      border-top-color: {p.shadow};
      border-left-color: {p.shadow};
      border-right-color: {p.highlight};
      border-bottom-color: {p.light_edge};
      padding: 2px 4px;
      min-height: 18px;
    }}
    QLineEdit#keywordField {{
      max-height: 22px;
    }}

    QSpinBox, QComboBox {{
      background: {p.field_bg};
      color: {p.text};
      border: 2px solid {p.edge};
      border-top-color: {p.shadow};
      border-left-color: {p.shadow};
      border-right-color: {p.highlight};
      border-bottom-color: {p.light_edge};
      padding: 2px 4px;
      min-height: 20px;
    }}

    QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{
      color: {p.edge};
      background: {p.surface};
    }}

    QSpinBox::up-button, QSpinBox::down-button {{
      width: 16px;
      background: {p.chrome};
      border: 2px solid {p.shadow};
      border-top-color: {p.highlight};
      border-left-color: {p.highlight};
      border-right-color: {p.dark_shadow};
      border-bottom-color: {p.dark_shadow};
    }}
    QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{
      border-top-color: {p.dark_shadow};
      border-left-color: {p.dark_shadow};
      border-right-color: {p.highlight};
      border-bottom-color: {p.highlight};
    }}

    QComboBox::drop-down {{
      subcontrol-origin: padding;
      subcontrol-position: top right;
      width: 18px;
      background: {p.chrome};
      border-left: 1px solid {p.edge};
      border-top: 2px solid {p.highlight};
      border-right: 2px solid {p.dark_shadow};
      border-bottom: 2px solid {p.dark_shadow};
    }}

    QComboBox QAbstractItemView {{
      background: {p.field_bg};
      color: {p.text};
      border: 2px solid {p.edge};
      border-top-color: {p.shadow};
      border-left-color: {p.shadow};
      border-right-color: {p.highlight};
      border-bottom-color: {p.light_edge};
      selection-background-color: {p.selection_bg};
      selection-color: {p.selection_text};
      outline: 0;
      font-size: 12px;
    }}

    QAbstractItemView {{
      background: {p.field_bg};
    }}

    /* Raised buttons */
    QPushButton {{
      background: {p.chrome};
      color: {p.text};
      border: 2px solid {p.shadow};
      border-top-color: {p.highlight};
      border-left-color: {p.highlight};
      border-right-color: {p.dark_shadow};
      border-bottom-color: {p.dark_shadow};
      padding: 4px 10px;
      min-height: 22px;
      font-weight: normal;
    }}
    QPushButton:pressed {{
      border: 2px solid {p.shadow};
      border-top-color: {p.dark_shadow};
      border-left-color: {p.dark_shadow};
      border-right-color: {p.highlight};
      border-bottom-color: {p.highlight};
      padding-top: 5px;
      padding-left: 11px;
      padding-bottom: 3px;
      padding-right: 9px;
    }}
    QPushButton:disabled {{
      color: {p.edge};
      background: {p.chrome};
    }}

    QCheckBox {{
      spacing: 6px;
    }}

    QTableView {{
      background: {p.field_bg};
      gridline-color: {p.edge};
      border: 2px solid {p.edge};
      border-top-color: {p.shadow};
      border-left-color: {p.shadow};
      border-right-color: {p.highlight};
      border-bottom-color: {p.light_edge};
      selection-background-color: {p.selection_bg};
      selection-color: {p.selection_text};
      alternate-background-color: {p.surface};
      font-size: 12px;
    }}
    QTableView::item:selected {{
      color: {p.selection_text};
    }}

    QHeaderView::section {{
      background: {p.chrome};
      border: 1px solid {p.shadow};
      border-top-color: {p.highlight};
      border-left-color: {p.highlight};
      padding: 4px 6px;
      font-weight: 700;
      color: {p.shadow};
      font-size: 12px;
    }}

    QProgressBar {{
      border: 2px solid {p.edge};
      border-top-color: {p.shadow};
      border-left-color: {p.shadow};
      border-right-color: {p.highlight};
      border-bottom-color: {p.light_edge};
      background: {p.field_bg};
      text-align: center;
      height: 18px;
      font-size: 12px;
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

    QScrollBar:horizontal {{
      background: {p.chrome};
      border: 1px solid {p.edge};
      height: 16px;
      margin: 0px;
    }}
    QScrollBar::handle:horizontal {{
      background: {p.chrome};
      border: 2px solid {p.shadow};
      border-top-color: {p.highlight};
      border-left-color: {p.highlight};
      border-right-color: {p.dark_shadow};
      border-bottom-color: {p.dark_shadow};
      min-width: 24px;
    }}
    QScrollBar:vertical {{
      background: {p.chrome};
      border: 1px solid {p.edge};
      width: 16px;
      margin: 0px;
    }}
    QScrollBar::handle:vertical {{
      background: {p.chrome};
      border: 2px solid {p.shadow};
      border-top-color: {p.highlight};
      border-left-color: {p.highlight};
      border-right-color: {p.dark_shadow};
      border-bottom-color: {p.dark_shadow};
      min-height: 24px;
    }}

    QLabel#helperText {{
      color: {p.text_muted};
      font-size: 12px;
    }}
    QLabel#saveHint {{
      color: {p.text_muted};
      font-size: 12px;
    }}
    """
