from PyQt5.QtGui import QColor, QFont

# Window & frame sizes
WINDOW_WIDTH = 400
MIN_HEIGHT = 280  # Increased height by 50
MAX_HEIGHT = 330
TITLE_BAR_HEIGHT = 35
BUTTON_SIZE = 25
FRAME_PADDING = 5
FRAME_HEIGHT = 100
DROPDOWN_HEIGHT = 30
DROPDOWN_OFFSET = 15
SWITCH_AREA_HEIGHT = 50
SWITCH_BTN_WIDTH = 160
SWITCH_BTN_HEIGHT = 30
BAR_HEIGHT = 20
BAR_PADDING = 10
BAR_TOP_OFFSET = 20
MANUAL_EXTRA_HEIGHT = 50
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
    'background':      QColor(180, 180, 180, int(0.35*255)),
    'title_bar':       QColor(160,  80,  80, int(0.7*255)),
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