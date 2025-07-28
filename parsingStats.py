###############################################################################
#######       Echoes of Angmar DPS parsing overlay (beta 0.9.2)         #######
####### ________________________________________________________________#######
####### Echoes of Angmar (https://www.echoesofangmar.com/) is a vanilla #######
####### version of Lord of the Rings online - Shadows of Angmar as it   #######
####### was back in the days. Vanilla LotRo did not have as man options #######
####### for logging combat events and stats, thus its tricky to parse   #######
####### DPS, but except for some just impossible things it works quite  #######
####### solid.                                                          #######
####### --------------------------------------------------------------- #######
####### The code so far is in beta state and for development and bug    #######
####### fix only. It is legal to use it (I asked "Chillzor") but for    #######
####### now it is not allowed to distribute it or do advertisment.      #######
####### That being sad, only few people should use it at the moment     #######
####### for testing purposes and giving feedback, anyone else does it   #######
####### on his own intention.                                           #######
####### --------------------------------------------------------------- #######
####### Send feedback in Github or ingame to Deladora / Namaleth        #######
####### Code is free but owner remains the Author:                      #######
####### https://github.com/MaSchm1983                                   #######
###############################################################################



import sys, configparser
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QComboBox, QCheckBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from config import (
    WINDOW_WIDTH, MIN_HEIGHT, MAX_HEIGHT,
    TITLE_BAR_HEIGHT, BUTTON_SIZE,
    FRAME_PADDING, DROPDOWN_HEIGHT, DROPDOWN_OFFSET, HIST_COM_DD_HEIGHT,
    MODE_AREA_HEIGHT, MODE_BTN_HEIGHT, MODE_BTN_WIDTH,
    BAR_HEIGHT, BAR_PADDING, BAR_TOP_OFFSET, 
    STAT_FRAME_HEIGHT, STARTSTOP_BTN_WIDTH, STARTSTOP_BTN_HEIGHT, 
    FONT_TITLE, FONT_SUBTITLE, FONT_BTN_TEXT,
    FONT_TEXT, FONT_TEXT_CLS_BTN, COLORS
)

###############################################################################
#######           Helper for colors and button styles                   #######    
###############################################################################

def rgba(c: QColor) -> str:
    r, g, b, a = c.getRgb()
    return f"rgba({r},{g},{b},{a})"

def apply_style(btn: QPushButton,
                bg: QColor,
                text_color: str = "white",
                border_color: QColor = None,
                hover: QColor = None,
                #hover: str = "rgba(170,170,170,80)",
                radius: int = 8,
                border_w: int = 1,
                bold: bool = False):
    border = (border_color or COLORS['line_col']).name()
    hover_rgba = rgba(hover) if hover else "rgba(220,220,220,90)"
    weight = "bold" if bold else "normal"
    btn.setStyleSheet(f"""
        QPushButton {{
            color: {text_color};
            background: {rgba(bg)};
            border: {border_w}px solid {border};
            border-radius: {radius}px;
            font-weight: {weight};
        }}
        QPushButton:hover {{ background: {hover_rgba}; }}
    """)

###############################################################################
####### Parse for config.ini where the path to combat log is located    #######
###############################################################################

def load_config(fn: str = "config.ini") -> configparser.ConfigParser:
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    cfg = configparser.ConfigParser()
    if not cfg.read(base / fn):
        raise FileNotFoundError(f"Missing {fn!r} in {base}")
    return cfg

###############################################################################
####### Main routine: building Overlay with widgets and add functions   #######
####### to all widgets. Will be cleaned up for first 1.0.0 release      #######
###############################################################################

class OverlayWindow(QWidget):
    
    ###--- Start: initializing functions and update of the overlay ---###
    # ── init overlay on startup ──
    def __init__(self):
        super().__init__()
        self.stat_mode = 'dps'            # default mode
        self._create_stat_mode_buttons()  # 1) add a chose mode snippet for damage, heal or damage taken
        self._init_window()               # 2) init window size and attributes on startup
        self._init_data()                 # 3) init any kind of needed data for parsing
        self._create_widgets()            # 4) create all widgets on the overlay
        
        self._update_layout()    # 5) update layout on interact function

    # ── 2) init window size and attributes on startup ──
    def _init_window(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(WINDOW_WIDTH)
        self.setMinimumHeight(MIN_HEIGHT)
        self.setMaximumHeight(MAX_HEIGHT)
        self.resize(WINDOW_WIDTH, MIN_HEIGHT)
        self.setMouseTracking(True)

    # ── 3) init any kind of needed data for parsing ──
    def _init_data(self):
        self._drag_start = None
        self.track_mode = 'manual'
        self.current_enemy = '--'
        self.total_damage = 0
        self.combat_time = 0.0
        self.max_hit = 0
        self.max_hit_skill = '--'

    # ── 1) add a chose mode snippet for damage, heal or damage taken ──
    def _create_stat_mode_buttons(self):
        self.stat_mode_btns = {
            'dps': QPushButton("Damage", self),
            'hps': QPushButton("Heal", self),
            'dts': QPushButton("Taken", self)
        }
        # Use your mode colors for buttons
        MODE_BTN_COLORS = {
            'dps': COLORS['MODE_BTN_BG_DPS'],
            'hps': COLORS['MODE_BTN_BG_HPS'],
            'dts': COLORS['MODE_BTN_BG_DTS']
        }
        MODE_BTN_INACTIVE_COLORS = {
            'dps': COLORS['title_bar_dps'],
            'hps': COLORS['title_bar_hps'],
            'dts': COLORS['title_bar_dts']
        }
        for key, btn in self.stat_mode_btns.items():
            btn.setFont(FONT_BTN_TEXT)
            btn.setFixedSize(MODE_BTN_WIDTH, MODE_BTN_HEIGHT)
            btn.setCheckable(True)
            # Default: only 'dps' is active on start
            active = (key == self.stat_mode)
            apply_style(
                btn,
                bg=MODE_BTN_COLORS[key] if active else MODE_BTN_INACTIVE_COLORS[key],
                text_color="white" if active else "#d4d4d4",
                hover=MODE_BTN_COLORS[key].lighter(120),
                radius=8,
                border_w=1,
                bold=active
            )
            btn.setChecked(active)
        # Connect each button
        self.stat_mode_btns['dps'].clicked.connect(lambda: self._switch_stat_mode('dps'))
        self.stat_mode_btns['hps'].clicked.connect(lambda: self._switch_stat_mode('hps'))
        self.stat_mode_btns['dts'].clicked.connect(lambda: self._switch_stat_mode('dts'))



    # ── 4) create all widgets on the overlay ──
    def _create_widgets(self):

        # ── Close button in upper right corner ──
        self.close_btn = QPushButton("✕", self)
        self.close_btn.setFont(FONT_TEXT_CLS_BTN)
        self.close_btn.setFixedSize(BUTTON_SIZE, BUTTON_SIZE)
        self.close_btn.clicked.connect(self.close)
        apply_style(self.close_btn, bg=QColor(0,0,0,0), text_color=rgba(COLORS['line_col']))


        # ── past fights selection dropdown ──
        self.label = QLabel("Select combat:", self)
        self.label.setFont(FONT_SUBTITLE)
        lbl_width = self.label.fontMetrics().boundingRect(self.label.text()).width()
        self.label.setFixedWidth(lbl_width)
        self.PST_FGHT_DD = QComboBox(self)
        self.PST_FGHT_DD.setFont(FONT_TEXT)
        self.PST_FGHT_DD.setFixedHeight(DROPDOWN_HEIGHT)
        self.PST_FGHT_DD.setStyleSheet("QComboBox{background:rgba(100,100,100,125);color:white;}")
        self.PST_FGHT_DD.addItem("current")

        # ── start/stop button for manual parsing mode ──
        self.start_stop_btn = QPushButton("Start", self)
        self.start_stop_btn.setFont(FONT_BTN_TEXT)
        self.start_stop_btn.setFixedSize(STARTSTOP_BTN_WIDTH, STARTSTOP_BTN_HEIGHT)
        apply_style(self.start_stop_btn, bg=COLORS['button_noactive'], text_color=rgba(COLORS['line_col']))

        # ── select targets for manual parsed combat ──
        self.manual_combo = QComboBox(self)
        self.manual_combo.setFont(FONT_TEXT)
        self.manual_combo.setFixedHeight(DROPDOWN_HEIGHT)
        #self.manual_combo.setFixedWidth(150)
        self.manual_combo.setStyleSheet("QComboBox{background:rgba(100,100,100,125);color:white;}")
        self.manual_combo.addItem("Total")

        self.manual_label = QLabel("Select target:", self)
        self.manual_label.setFont(FONT_SUBTITLE)
        ml_w = self.manual_label.fontMetrics().boundingRect(self.manual_label.text()).width()
        self.manual_label.setFixedWidth(ml_w)

        self.manual_combo.hide()
        self.manual_label.hide()
        
        
        self.analyse_btn = QPushButton("Analyse combat", self)
        self.analyse_btn.setFont(FONT_BTN_TEXT)
        # Height same as start/stop
        self.analyse_btn.setFixedHeight(STARTSTOP_BTN_HEIGHT)
        # Will set width in layout
        # Use DPS color as default, and lighter as hover (update as needed for other modes)
        btn_color = COLORS['MODE_BTN_BG_DPS']
        apply_style(
            self.analyse_btn,
            bg=btn_color,
            text_color="white",
            hover=btn_color.lighter(120),
            radius=8,
            border_w=1,
            bold=True
        )
        
        
        self.auto_stop_cb = QCheckBox("stop combat after 30s", self)
        self.auto_stop_cb.setFont(FONT_TEXT)
        self.auto_stop_cb.setStyleSheet("""
            QCheckBox {
                color: white;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        self.auto_stop_cb.setChecked(True)
        

        # ── copy button to copy selected parse to clipboard ──
        self.copy_btn = QPushButton("Copy", self)
        self.copy_btn.setFont(FONT_BTN_TEXT)
        self.copy_btn.setFixedSize(60, 25)
        apply_style(self.copy_btn, bg=QColor(0,0,0,0), text_color=rgba(COLORS['line_col']))


    # ── 5) styling updated for layout and update on interaction/events ──
    def _update_layout(self):
        # ── Add window height for manual mode extension (start/stop button and dropdown) ──
        new_h = MIN_HEIGHT
        self.resize(self.width(), new_h)
        
        # ── close button ──
        self.close_btn.move(self.width() - BUTTON_SIZE - FRAME_PADDING, FRAME_PADDING)
        
        # ── stat mode buttons to switch between damage, heal or damage taken parsing ──
        mode_btns = list(self.stat_mode_btns.values())
        gap = 8
        MODE_BTN_W = mode_btns[0].width()
        total_w = len(mode_btns) * MODE_BTN_W + (len(mode_btns) - 1) * gap
        start_x = (self.width() - total_w) // 2
        y_mode = TITLE_BAR_HEIGHT + 18  # More space below title bar
        for i, btn in enumerate(mode_btns):
            btn.move(start_x + i * (MODE_BTN_W + gap), y_mode)
            btn.show()

        # ── past fights dropdown ──
        ext_y = y_mode + MODE_AREA_HEIGHT + FRAME_PADDING
        self.label.move(FRAME_PADDING, ext_y + 5)
        dd_x = FRAME_PADDING + self.label.width() + DROPDOWN_OFFSET
        dd_w = self.width() - dd_x - FRAME_PADDING
        self.PST_FGHT_DD.setGeometry(dd_x, ext_y, dd_w, DROPDOWN_HEIGHT)

        # ── calculate DPS frame origin and height ──
        self._frame_y = ext_y + DROPDOWN_HEIGHT + DROPDOWN_OFFSET
        
        # ── target selection dropdown aligned right with same padding as start/stop's left ──
        self.manual_combo.show()
        self.manual_label.show()
        mc_x = FRAME_PADDING + BAR_PADDING + self.manual_label.width() + DROPDOWN_OFFSET
        mc_y = self._frame_y + 120
        mc_w = self.width() - mc_x - FRAME_PADDING - BAR_PADDING
        self.manual_combo.move(mc_x, mc_y)
        self.manual_combo.setGeometry(mc_x, mc_y, mc_w, DROPDOWN_HEIGHT)        
        # ── label left of the dropdown ──
        ml_x = mc_x - self.manual_label.width() - DROPDOWN_OFFSET
        self.manual_label.move(ml_x, mc_y+5)
        
        
        # ── analyze button ──
        bar_x = FRAME_PADDING + BAR_PADDING
        bar_w = self.width() - 2 * (FRAME_PADDING + BAR_PADDING)
        # Position analyse button below manual_combo
        analyse_y = mc_y + DROPDOWN_HEIGHT + 25  # 18px gap under target dropdown
        self.analyse_btn.setFixedWidth(bar_w)
        self.analyse_btn.move(bar_x, analyse_y)
        self.analyse_btn.show()
                
        

        # ── start/stop button and auto stop checkbox ──
        self.start_stop_btn.show()
        ss_x = FRAME_PADDING + BAR_PADDING
        ss_y = self._frame_y + STAT_FRAME_HEIGHT - FRAME_PADDING - BAR_PADDING
        self.start_stop_btn.move(ss_x, ss_y)
        
        cb_x = ss_x + self.start_stop_btn.width() + 18  # some gap to right
        cb_y = ss_y + (self.start_stop_btn.height() - self.auto_stop_cb.sizeHint().height()) // 2  # vertical align
        self.auto_stop_cb.move(cb_x, cb_y)
        self.auto_stop_cb.show()
        
        



        # ── position copy button: left padding, centered vertically in leftover space ──
        copy_x = self.width() - self.copy_btn.width() - FRAME_PADDING
        copy_y = MAX_HEIGHT - STARTSTOP_BTN_HEIGHT - 2*FRAME_PADDING
        self.copy_btn.move(copy_x, copy_y)
        self.update()

    # ── paint all colors, texts, bars etc ──
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # ── paint background w.r.t. the chosen mode ──
        bg_map = {
            'dps': COLORS['background_dps'],
            'hps': COLORS['background_hps'],
            'dts': COLORS['background_dts']
        }
        title_map = {
            'dps': COLORS['title_bar_dps'],
            'hps': COLORS['title_bar_hps'],
            'dts': COLORS['title_bar_dts']
        }
        p.fillRect(self.rect(), bg_map.get(self.stat_mode, COLORS['background']))
        # ── recolor title bar w.r.t. the chosen mode and draw left-aligned, vertically centered title ──
        p.fillRect(0, 0, self.width(), TITLE_BAR_HEIGHT, title_map.get(self.stat_mode, COLORS['title_bar']))
        p.setPen(COLORS['line_col'])
        p.setFont(FONT_TITLE)
        fm = p.fontMetrics()
        ty = (TITLE_BAR_HEIGHT + fm.ascent() - fm.descent())  // 2
        p.drawText(FRAME_PADDING, ty, "ParsingStats in EoA v1.0.0")
        # ── paint line beneath titelbar
        sep_y = TITLE_BAR_HEIGHT + MODE_AREA_HEIGHT + 2*FRAME_PADDING
        p.fillRect(0, sep_y - 2, self.width(), 2, COLORS['line_col'])
        sep_y = TITLE_BAR_HEIGHT + 18 + MODE_AREA_HEIGHT + HIST_COM_DD_HEIGHT + DROPDOWN_OFFSET+ FRAME_PADDING
        p.fillRect(0, sep_y - 2, self.width(), 2, COLORS['line_col'])
        # ── draw DPS frame and content ──
        # frame
        x0, y0 = FRAME_PADDING, self._frame_y + 20
        w0 = self.width() - 2 * FRAME_PADDING
        h0 = STAT_FRAME_HEIGHT
        p.setBrush(COLORS['frame_bg']); p.setPen(Qt.NoPen)
        p.drawRoundedRect(x0, y0, w0, h0, 5, 5)
        p.setPen(QPen(COLORS['line_col'], 2)); p.drawRect(x0, y0, w0, h0)
        # bar and stats
        bar_x, bar_y = x0 + BAR_PADDING, y0 + BAR_TOP_OFFSET
        bar_w = w0 - 2 * BAR_PADDING
        p.setBrush(COLORS['bar_bg']); p.setPen(Qt.NoPen)
        p.drawRect(bar_x, bar_y + 10, bar_w, BAR_HEIGHT)
        bar_fill_map = {
            'dps': QColor(200, 65, 65, int(0.6*255)),
            'hps': QColor(65, 200, 65, int(0.6*255)),
            'dts': QColor(65, 65, 200, int(0.6*255))
        }
        p.fillRect(bar_x, bar_y + 10, bar_w, BAR_HEIGHT, bar_fill_map.get(self.stat_mode, COLORS['bar_fill']))
        
        p.setFont(FONT_TEXT); p.setPen(COLORS['subtext'])
        p.drawText(bar_x, bar_y + 4, f"Total damage: {self.total_damage}")
        p.drawText(bar_x, bar_y + BAR_HEIGHT + 28, f"Duration: {self.combat_time:.2f}s")
        max_str = f"Max hit: {self.max_hit}"; mw = fm.boundingRect(max_str).width()
        p.drawText(bar_x + bar_w - mw - 10, bar_y + 4, max_str)
        skill_str = f"max hitting skill: {self.max_hit_skill}"; sw = fm.boundingRect(skill_str).width()
        p.drawText(bar_x + bar_w - sw - 10, bar_y + BAR_HEIGHT + 28, skill_str)
        p.end()

    ###--- End: initializing functions and update of the overlay ---###

    ###--- Start: functionality functions and parsing routines ---###

    # ── define parsing mode damage/heal/damage taken by button click ──
    def _switch_stat_mode(self, mode):
        if self.stat_mode == mode:
            return
        self.stat_mode = mode
        MODE_BTN_COLORS = {
            'dps': COLORS['MODE_BTN_BG_DPS'],
            'hps': COLORS['MODE_BTN_BG_HPS'],
            'dts': COLORS['MODE_BTN_BG_DTS']
        }
        MODE_BTN_INACTIVE_COLORS = {
            'dps': COLORS['title_bar_dps'],
            'hps': COLORS['title_bar_hps'],
            'dts': COLORS['title_bar_dts']
        }
        ANALYSE_BTN_COLORS = {
            'dps': COLORS['MODE_BTN_BG_DPS'],
            'hps': COLORS['MODE_BTN_BG_HPS'],
            'dts': COLORS['MODE_BTN_BG_DTS']
        }
        for key, btn in self.stat_mode_btns.items():
            active = (key == mode)
            apply_style(
                btn,
                bg=MODE_BTN_COLORS[key] if active else MODE_BTN_INACTIVE_COLORS[key],
                text_color="white" if active else "#d4d4d4",
                hover=MODE_BTN_COLORS[key].lighter(120),
                radius=8,
                border_w=1,
                bold=active
            )
            btn.setChecked(key == mode)
            # Style the Analyse button in the selected color
        analyse_color = ANALYSE_BTN_COLORS[mode]
        apply_style(
            self.analyse_btn,
            bg=analyse_color,
            text_color="white",
            hover=analyse_color.lighter(120),
            radius=8,
            border_w=1,
            bold=True
        )
        self._update_layout()
        self.update()  # force repaint to use new colors

    ###--- End: functionality functions and parsing routines ---###
    
    

    ###--- Start: helper functions for interaction with overlay ---###
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_start = e.globalPos() - self.frameGeometry().topLeft(); e.accept()
    def mouseMoveEvent(self, e):
        if self._drag_start:
            self.move(e.globalPos() - self._drag_start); e.accept()
    def mouseReleaseEvent(self, e):
        self._drag_start = None; super().mouseReleaseEvent(e)

    ###--- End: helper functions for interaction with overlay ---###

###############################################################################
####### End of: Main routine                                            #######
###############################################################################    

###############################################################################
####### Execute code                                                    #######
###############################################################################    

if __name__ == "__main__":
    cfg = load_config()
    print("Pets names:", cfg.get("Pets","names"))
    app = QApplication(sys.argv)
    ov = OverlayWindow()
    ov.show(); sys.exit(app.exec_())
