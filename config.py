from PyQt5.QtGui import QColor, QFont

# Window & frame sizes
WINDOW_WIDTH = 400
MIN_HEIGHT = 500  # Increased height by 50
MAX_HEIGHT = 500
TITLE_BAR_HEIGHT = 35
BUTTON_SIZE = 25
FRAME_PADDING = 5
DROPDOWN_HEIGHT = 25
MODE_AREA_HEIGHT = 40
MODE_BTN_HEIGHT = 30
MODE_BTN_WIDTH = 120
BAR_HEIGHT = 20
BAR_PADDING = 10
STARTSTOP_BTN_WIDTH = 80
STARTSTOP_BTN_HEIGHT = 25
AUTO_STOP_SECONDS = 30


# Fonts
FONT_TITLE        = QFont('Arial', 12, QFont.Bold)
FONT_SUBTITLE     = QFont('Arial', 12, QFont.Bold)
FONT_BTN_TEXT     = QFont('Arial', 12, QFont.Bold)
FONT_TEXT         = QFont('Arial', 11)
FONT_TEXT_CLS_BTN = QFont('Arial', 14, QFont.Bold)

# Colors
COLORS = {
    'background':          QColor(0, 0, 0, int(0.5*255)),
    'MODE_BTN_BG_DPS':     QColor(255, 100, 100, int(0.3*255)),
    'MODE_BTN_BG_HPS':     QColor(100, 255, 100, int(0.3*255)),
    'MODE_BTN_BG_DTS':     QColor(100, 100, 255, int(0.3*255)),
    'title_bar':       QColor(70, 50,  30, int(0.8*255)),
    'title_bar_dps':       QColor(160, 80,  80, int(0.6*255)),
    'title_bar_hps':       QColor(80,  160,  80, int(0.6*255)),
    'title_bar_dts':       QColor(80,  80,  160, int(0.6*255)),
    'line_col':      QColor( 50,  50,  50, int(0.8*255)),
    'button_active':   QColor(80,  200,  80, int(0.5*255)),
    'button_noactive': QColor(200,  80,  80, int(0.5*255)),
    'text':            QColor( 25,  25,  25),
    'subtext':         QColor(  0,   0,   0),
    'white':           QColor(255, 255, 255, int(1.0*255)),
}

AA_SKILLS = {
    "Dual-wield Attack",
    "Bow Attack",
    "Weapon Attack",
    "1H Weapon/Shield Attack",
    "2H Weapon Attack",
    "Bogenangriff",
    "1H-Waffen-/Schild-Angriff",
    "Doppelangriff",
    "2H-Waffen-Angriff",
    "Waffen-Angriff",
}

DEBUG_PARSE = True

# Default-Pfad – nur Fallback, wenn User noch nichts gesetzt hat
CMBT_LOG_DIR = r"C:/Users/<username>/Documents/The Lord of the Rings Online"
LOG_CHECK_INTERVAL = 10.0      # searching for new combat log file every 10s

# Default-Pet-Namen (englisch + deutsch etc.)
DEFAULT_PET_NAMES = [
    "Raven",
    "Lesser Giant Eagle",
    "Bear",
    "Lynx",
    "Commoner Herald",
    "Noble Spirit",
    "Greater Noble Spirit",
    "Rabe",
    "Adler",
    "Luchs",
    "Bär",
]
DEFAULT_PET_NAMES_LOWER = [n.lower() for n in DEFAULT_PET_NAMES]
# Aktive Pet-Liste (wird zur Laufzeit überschrieben)
PET_NAMES = [n.lower() for n in DEFAULT_PET_NAMES]