from PyQt5.QtGui import QColor, QFont

# Window & frame sizes
WINDOW_WIDTH = 400
MIN_HEIGHT = 480  # Increased height by 50
MAX_HEIGHT = 480
TITLE_BAR_HEIGHT = 35
BUTTON_SIZE = 25
FRAME_PADDING = 5
DROPDOWN_HEIGHT = 30
DROPDOWN_OFFSET = 15
HIST_COM_DD_HEIGHT = 30
STAT_FRAME_HEIGHT = 250 
MODE_AREA_HEIGHT = 60
MODE_BTN_HEIGHT = 30
MODE_BTN_WIDTH = 120
BAR_HEIGHT = 20
BAR_PADDING = 10
BAR_TOP_OFFSET = 20
STARTSTOP_BTN_WIDTH = 80
STARTSTOP_BTN_HEIGHT = 25


# Fonts
FONT_TITLE        = QFont('Arial', 12, QFont.Bold)
FONT_SUBTITLE     = QFont('Arial', 12, QFont.Bold)
FONT_BTN_TEXT     = QFont('Arial', 12, QFont.Bold)
FONT_TEXT         = QFont('Arial', 11)
FONT_TEXT_CLS_BTN = QFont('Arial', 14, QFont.Bold)

# Colors
COLORS = {
    'background':      QColor(210, 180, 180, int(0.35*255)),
    'background_dps':      QColor(210, 180, 180, int(0.35*255)),
    'background_hps':      QColor(180, 210, 180, int(0.35*255)),
    'background_dts':      QColor(180, 180, 210, int(0.35*255)),
    'MODE_BTN_BG_DPS':     QColor(255, 100, 100, int(0.6*255)),
    'MODE_BTN_BG_HPS':     QColor(100, 255, 100, int(0.6*255)),
    'MODE_BTN_BG_DTS':     QColor(100, 100, 255, int(0.6*255)),
    'title_bar':       QColor(160,  80,  80, int(0.6*255)),
    'title_bar_dps':       QColor(160,  80,  80, int(0.6*255)),
    'title_bar_hps':       QColor(80,  160,  80, int(0.6*255)),
    'title_bar_dts':       QColor(80,  80,  160, int(0.6*255)),
    'line_col':      QColor( 50,  50,  50, int(0.8*255)),
    'frame_bg':        QColor(100, 100, 100, int(0.55*255)),
    #'frame_bg':        QColor(255, 220, 220, int(0.5*255)),
    'bar_bg':          QColor(170, 170, 170, int(0.55*255)),
    'bar_fill':        QColor(200,  65,  65, int(0.6*255)),
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
    "1H Weapon/Shield Attack"
}