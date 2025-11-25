###############################################################################
#######       Echoes of Angmar DPS parsing overlay (beta 0.9.9)         #######
####### ________________________________________________________________#######
####### Echoes of Angmar (https://www.echoesofangmar.com/) is a vanilla #######
####### version of Lord of the Rings online - Shadows of Angmar as it   #######
####### was back in the days. Vanilla LotRo did not have as many        #######
####### options for logging combat events and stats, thus its tricky    #######
####### to parse stats. However, this parser is capabel to track most   #######
####### important DAMAGE, HEAL and DAMAGE TAKEN stats. More or less     #######
####### impossible is calculating e.g. crit chances since this events   #######
####### are not markes in the combat log. Attempts to calculate them    #######
####### from raw numbers worked well for e.g. Hunters, but not for      #######
####### dual-wield classes or classes swapping weapons for skills etc.  #######
####### --------------------------------------------------------------- #######
####### The code is in final beta state right before release. For now   #######
####### code and parser are for development and bug fix only.           #######
####### It is legal to use it (I asked "Chillzor") but for              #######
####### now it is not allowed to distribute it or do advertisment.      #######
####### That being sad, only few people should use it at the moment     #######
####### for testing purposes and giving feedback, anyone else does it   #######
####### on his own intention.                                           #######
####### --------------------------------------------------------------- #######
####### Send feedback in Github or ingame to Deladora / Namaleth        #######
####### Code is free but owner remains the Author:                      #######
####### https://github.com/MaSchm1983                                   #######
###############################################################################


import sys, configparser, os, glob, re
import time, queue
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QComboBox, QCheckBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from config import (
    WINDOW_WIDTH, MIN_HEIGHT, MAX_HEIGHT,
    TITLE_BAR_HEIGHT, BUTTON_SIZE,
    FRAME_PADDING, DROPDOWN_HEIGHT,
    MODE_BTN_HEIGHT, MODE_BTN_WIDTH,
    BAR_PADDING, STARTSTOP_BTN_WIDTH, STARTSTOP_BTN_HEIGHT, AUTO_STOP_SECONDS,
    FONT_TITLE, FONT_SUBTITLE, FONT_BTN_TEXT,
    FONT_TEXT, FONT_TEXT_CLS_BTN, COLORS, AA_SKILLS
)
TARGET_TEXT_HEX = "#f2e3a0"


###############################################################################
####################### Parse config.ini for infos ############################
###############################################################################


LOG_CHECK_INTERVAL = 10.0      # searching for new combat log file every 10s

# ── searching and loading for config.ini ── 
if getattr(sys, 'frozen', False):
    # we’re in a PyInstaller bundle → exe lives in dist\ folder
    base_dir = os.path.dirname(sys.executable)
else:
    # normal script
    base_dir = os.path.dirname(__file__)

config_path = os.path.join(base_dir, 'config.ini')
config = configparser.ConfigParser()
read = config.read(config_path)
if not read:
    raise FileNotFoundError(f"Couldn’t find config.ini at {config_path}")
COMBAT_LOG_FOLDER = config.get('Settings','CMBT_LOG_DIR')

# ── get pet names from config.ini ──
pets_raw = (
    config.get('Pets', 'name', fallback='') or
    config.get('Pets', 'names', fallback='')
)
PET_NAMES = {
    n.strip().lower()
    for n in re.split(r'[,\n;]+', pets_raw)
    if n.strip()
}

DEBUG_PARSE = config.getboolean('Settings', 'DEBUG_PARSE', fallback=False)

# ── Helper to read current combat log (will be updated every 10s later) ── 

def _clean_dir(p: str) -> str:
    # remove quotes + white space, expand variables, normalize
    p = (p or "").strip().strip('"').strip("'")
    p = os.path.expandvars(os.path.expanduser(p))
    return os.path.normpath(p)

def get_latest_combat_log(folder=COMBAT_LOG_FOLDER):
    base = _clean_dir(folder)
    if not base or not os.path.isdir(base):
        if DEBUG_PARSE:
            print(f"[LOG] Invalid log dir: {repr(folder)} -> {repr(base)} (exists={os.path.isdir(base)})")
        return None

    # allow multiple patterns, but usually they are called the same for any clients
    patterns = [
        os.path.join(base, "Combat_*.txt"),
        os.path.join(base, "CombatLog_*.txt"),
        os.path.join(base, "combat_*.txt"),
    ]
    files = []
    for pat in patterns:
        hit = glob.glob(pat)
        if DEBUG_PARSE:
            print(f"[LOG] glob {pat} -> {len(hit)}")
        files.extend(hit)

    return max(files, key=os.path.getmtime) if files else None

# ── Helper to avoid decoding issues ── 
def _detect_encoding(path: str) -> str:
    with open(path, 'rb') as fb:
        head = fb.read(4)
    if head.startswith(b'\xff\xfe'): return 'utf-16-le'
    if head.startswith(b'\xfe\xff'): return 'utf-16-be'
    if head.startswith(b'\xef\xbb\xbf'): return 'utf-8-sig'
    return 'utf-8'


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
        
        self._update_layout()             # 5) update layout on interact function
        self.raise_()
        self.activateWindow()
        self._toggle_startstop()          # 6) start and stop parsing


    # ── 1) add a chose mode snippet for damage, heal or damage taken ──
    def _create_stat_mode_buttons(self):
        self.stat_mode_btns = {
            'dps': QPushButton("Damage", self),
            'hps': QPushButton("Heal", self),
            'dts': QPushButton("Taken", self)
        }
        # Use mode colors for buttons
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
        self.modes = {
            'dps': {'events': [], 'total': 0, 'max': 0, 'max_skill': '--'},
            'hps': {'events': [], 'total': 0, 'max': 0, 'max_skill': '--'},
            'dts': {'events': [], 'total': 0, 'max': 0, 'max_skill': '--'},
        }
        
        # --- current selection on target dropdown menu (None = Total) ---
        self.sel_target = None 
        
        # --- combat summary ---
        self.combat_time = 0.0
        self.max_hit = 0
        self.max_hit_skill = '--'
        self.fight_history = []   # list of dicts
        self.fight_seq = 0        # running IDs for snapshots
        
        # --- Manual-Run State ---
        self.manual_running = False
        self.manual_waiting = False
        self.manual_start_time = None

        # --- Tail-Thread State ---
        self._current_log_path = None
        self._tail_thread = None
        self._tail_should_run = False
        
        # --- results from tail-thread ---
        self._event_queue = queue.Queue()
        self._last_event_time = None
        self._last_log_check = 0.0
 
        # --- UI/Timer ---
        from PyQt5.QtCore import QTimer
        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._tick)
        self._ui_timer.start(100)  # smooth time label while running
        
        # --- positioning of target headers (All targets / DPS / 19.0s) ---
        self._info_bar_y = TITLE_BAR_HEIGHT + MODE_BTN_HEIGHT + 8
        self._table_top_y = TITLE_BAR_HEIGHT + 80
        
        # --- scroll-offset for skill table ---
        self._table_scroll = 0.0
        
        # --- skill analysis / selection ---
        self.selected_skill = None        # currently chosen skill name by mouse click
        self._skill_row_bounds = []       # will be filled in paintEvent    
        
        # --- Hover-State für Tabelle & Summary ---
        self._hover_skill = None          # Skill-Name, über dem die Maus steht
        self._hover_summary = False       # True, wenn Maus über Summary-Zeile    
              

    # ── 4) create all widgets on the overlay ──
    def _create_widgets(self):

        # --- Close button in upper right corner ---
        self.close_btn = QPushButton("✕", self)
        self.close_btn.setFont(FONT_TEXT_CLS_BTN)
        self.close_btn.setFixedSize(BUTTON_SIZE, BUTTON_SIZE)
        self.close_btn.clicked.connect(self.close)
        apply_style(self.close_btn, bg=QColor(0,0,0,70), text_color=TARGET_TEXT_HEX)


        # --- past fights selection dropdown ---
        self.label = QLabel("Select combat:", self)
        self.label.setFont(FONT_SUBTITLE)
        lbl_width = self.label.fontMetrics().boundingRect(self.label.text()).width()
        self.label.setFixedWidth(lbl_width)
        self.PST_FGHT_DD = QComboBox(self)
        self.PST_FGHT_DD.setFont(FONT_TEXT)
        self.PST_FGHT_DD.setFixedHeight(DROPDOWN_HEIGHT)
        self.PST_FGHT_DD.addItem("Select combat")

        # --- start/stop button ---
        self.start_stop_btn = QPushButton("Start", self)
        self.start_stop_btn.setFont(FONT_BTN_TEXT)
        self.start_stop_btn.setFixedSize(STARTSTOP_BTN_WIDTH, STARTSTOP_BTN_HEIGHT)
        apply_style(self.start_stop_btn, bg=COLORS['button_noactive'], text_color=TARGET_TEXT_HEX)
        self.start_stop_btn.clicked.connect(self._toggle_startstop)

        # --- select targets ---
        self.manual_combo = QComboBox(self)
        self.manual_combo.setFont(FONT_TEXT)
        self.manual_combo.setFixedHeight(DROPDOWN_HEIGHT)
        self.manual_combo.addItem("All targets")
        self.manual_combo.currentIndexChanged.connect(self._on_manual_selection)

        self.manual_label = QLabel("Select target:", self)
        self.manual_label.setFont(FONT_SUBTITLE)
        ml_w = self.manual_label.fontMetrics().boundingRect(self.manual_label.text()).width()
        self.manual_label.setFixedWidth(ml_w)

        self.manual_combo.hide()
        self.manual_label.hide()
        
        
        # --- style for both dropdown menues ---
        common_dd_style = """
        QComboBox {
            background-color: rgba(0, 0, 0, 190);
            color: #f2e3a0;
            border: 1px solid #6b5b35;
            padding: 2px 24px 2px 6px;
            font-family: "Arial";
            font-size: 10pt;
        }
        QComboBox::drop-down {
            border: none;
            width: 18px;
        }
        QComboBox::down-arrow {
            width: 0;
            height: 0;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 7px solid #f2e3a0;   /* gleiche Farbe wie Text */
            margin-right: 4px;
        }
        QComboBox QAbstractItemView {
            background-color: rgba(0, 0, 0, 230);
            color: #f2e3a0;
            selection-background-color: rgba(255, 255, 255, 40);
            selection-color: #ffffff;
        }
        """
        self.PST_FGHT_DD.setStyleSheet(common_dd_style)
        self.manual_combo.setStyleSheet(common_dd_style)
        
        # --- checkbox for auto combat stop ---
        
        self.auto_stop_cb = QCheckBox("stop combat after 30s", self)
        self.auto_stop_cb.setFont(FONT_TEXT)
        self.auto_stop_cb.setStyleSheet(
            "QCheckBox {"
            f"  color: {TARGET_TEXT_HEX};"
            "  spacing: 8px;"
            "}"
            "QCheckBox::indicator {"
            "  width: 20px;"
            "  height: 20px;"
            "}"
        )
        self.auto_stop_cb.setChecked(True)
        
        # --- copy button for copy selected parse to clipboard ---
        self.copy_btn = QPushButton("Copy", self)
        self.copy_btn.setFont(FONT_BTN_TEXT)
        self.copy_btn.setFixedSize(60, 25)
        apply_style(self.copy_btn, bg=QColor(0,0,0,0), text_color=TARGET_TEXT_HEX)
        self.copy_btn.clicked.connect(self._copy_to_clipboard)


    # ── 5) styling updated for layout and update on interaction/events ──
    def _update_layout(self):
        # --- window height and width ---
        new_h = max(MIN_HEIGHT, min(self.height(), MAX_HEIGHT))
        self.resize(WINDOW_WIDTH, new_h)

        # --- close button ---
        self.close_btn.move(self.width() - BUTTON_SIZE - FRAME_PADDING,
                            FRAME_PADDING)

        # --- mode buttons (Damage / Heal / Taken) right under titel bar ---
        mode_btns = list(self.stat_mode_btns.values())
        gap = 6
        btn_w = mode_btns[0].width()
        total_w = len(mode_btns) * btn_w + (len(mode_btns) - 1) * gap
        start_x = (self.width() - total_w) // 2
        y = TITLE_BAR_HEIGHT + 10

        for i, btn in enumerate(mode_btns):
            btn.move(start_x + i * (btn_w + gap), y)
            btn.show()

        y += MODE_BTN_HEIGHT + 14


        # --- info bar ("All targets  |  DPS | 19.0s") next to mode buttons ---
        info_h = 24
        self._info_bar_y = y           # used in paintEvent
        y += info_h + 10               

        # --- width and positions for both dropdowns ---
        dd_x = FRAME_PADDING + BAR_PADDING
        dd_w = self.width() - 2 * (FRAME_PADDING + BAR_PADDING)

        # --- select combat dropdown ---
        self.label.hide()
        self.PST_FGHT_DD.setGeometry(dd_x, y, dd_w, DROPDOWN_HEIGHT)

        y += DROPDOWN_HEIGHT + 6

        # --- select target / ally / source dropdown ---
        self.manual_label.hide()
        self.manual_combo.show()
        self.manual_combo.setGeometry(dd_x, y, dd_w, DROPDOWN_HEIGHT)

        # --- start skill table ---
        self._table_top_y = y + DROPDOWN_HEIGHT + 8

        # --- lower button bar (Start/Stop button, auto stop cb, copy button) ---
        # start/stop button
        bottom_y = self.height() - STARTSTOP_BTN_HEIGHT - FRAME_PADDING
        gutter = FRAME_PADDING + BAR_PADDING   
        self.start_stop_btn.move(gutter, bottom_y)
        # checkbox
        cb_x = self.start_stop_btn.x() + self.start_stop_btn.width() + 12
        cb_y = bottom_y + (STARTSTOP_BTN_HEIGHT - self.auto_stop_cb.sizeHint().height()) // 2
        self.auto_stop_cb.move(cb_x, cb_y)
        # copy-Button
        copy_x = self.width() - self.copy_btn.width() - gutter
        copy_y = bottom_y + (STARTSTOP_BTN_HEIGHT - self.copy_btn.height()) // 2
        self.copy_btn.move(copy_x, copy_y)

        self.update()

    # ── paint all colors, texts, bars etc ──
    def paintEvent(self, e):
        from PyQt5.QtGui import QFont, QColor, QPainter
        from PyQt5.QtCore import Qt, QRect

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # --- background transparent ---
        p.fillRect(self.rect(), QColor(0, 0, 0, int(0.5 * 255)))

        # --- header style ---
        header_bg     = QColor(60, 40, 20, int(0.95 * 255))   # dark brown
        header_border = QColor(180, 140, 60, 255)             # golden
        header_text   = QColor(235, 220, 190, 255)            
        table_text = QColor(0xF2, 0xE3, 0xA0)

        # --- titel bar ---
        p.fillRect(0, 0, self.width(), TITLE_BAR_HEIGHT, header_bg)
        p.setPen(header_border)
        p.drawLine(0, TITLE_BAR_HEIGHT - 1, self.width(), TITLE_BAR_HEIGHT - 1)
        p.setPen(header_text)
        p.setFont(FONT_TITLE)
        fm = p.fontMetrics()
        ty = (TITLE_BAR_HEIGHT + fm.ascent() - fm.descent()) // 2
        p.drawText(FRAME_PADDING, ty, "ParsingStats in EoA v1.0.0")

        # --- info bar ("All targets   DPS | 19.0s") ---
        header_h = 24
        margin_l = 16
        margin_r = 16  # space for close button

        header_y = getattr(
            self,
            "_info_bar_y",
            TITLE_BAR_HEIGHT + MODE_BTN_HEIGHT + 8
        )
        info_rect = QRect(
            margin_l,
            header_y,
            self.width() - margin_l - margin_r,
            header_h
        )
        p.setBrush(header_bg)
        p.setPen(header_border)
        p.drawRect(info_rect)
        title = self._current_target_label()
        p.setFont(QFont("Arial", 10, QFont.Bold))
        p.setPen(header_text)
        p.drawText(
            info_rect.adjusted(8, 0, -8, 0),
            Qt.AlignVCenter | Qt.AlignLeft,
            title
        )
        mode_txt = self._metric_short()
        info_txt = f"{mode_txt} mode - Duration | {self.combat_time:.1f}s"
        p.setFont(QFont("Arial", 9))
        p.drawText(
            info_rect.adjusted(8, 0, -8, 0),
            Qt.AlignVCenter | Qt.AlignRight,
            info_txt
        )

        # --- skill table + summary ---
        self._skill_row_bounds = []

        table_top = self._table_top_y
        left = 14
        right = self.width() - 14
        row_h = 22

        col_hits_w = 40
        col_total_w = 70
        col_avg_w = 70
        spacing = 10

        col_avg_x = right - col_avg_w
        col_total_x = col_avg_x - spacing - col_total_w
        col_hits_x = col_total_x - spacing - col_hits_w
        bar_left = left
        bar_right = col_hits_x - spacing
        bar_max_w = max(40, bar_right - bar_left)

        # --- table header ---
        header_y2 = table_top + row_h
        p.setFont(QFont("Arial", 11, QFont.Bold))
        p.setPen(table_text)
        #p.setPen(QColor(200, 200, 200, 210))

        skills_header_rect = QRect(bar_left, header_y2 - row_h + 4,
                                bar_max_w, row_h)
        p.drawText(skills_header_rect,
                Qt.AlignVCenter | Qt.AlignLeft,
                "Skills")

        hits_header_rect = QRect(col_hits_x, header_y2 - row_h + 4,
                                col_hits_w, row_h)
        total_header_rect = QRect(col_total_x, header_y2 - row_h + 4,
                                col_total_w, row_h)
        avg_header_rect = QRect(col_avg_x, header_y2 - row_h + 4,
                                col_avg_w, row_h)

        p.drawText(hits_header_rect, Qt.AlignCenter, "Hits")
        p.drawText(total_header_rect, Qt.AlignCenter, "Total")
        p.drawText(avg_header_rect, Qt.AlignCenter, "Avg")

        p.setPen(header_border)
        p.drawLine(bar_left, header_y2 + 2, right, header_y2 + 2)

        # --- get data ---
        stats = self._build_skill_stats()
        has_stats = bool(stats)

        if has_stats:
            max_val = max(s['total'] for s in stats) or 1
        else:
            # dummy value
            max_val = 1

        # --- color for bars related to parsing mode
        if self.stat_mode == 'dps':
            bar_base_col = QColor(150, 40, 40, 230)
            bar_highlight_col = QColor(210, 80, 80, 255)
        elif self.stat_mode == 'hps':
            bar_base_col = QColor(40, 130, 40, 230)
            bar_highlight_col = QColor(90, 200, 90, 255)
        else:
            bar_base_col = QColor(40, 40, 130, 230)
            bar_highlight_col = QColor(90, 90, 200, 255)

    # --- global summary values for all skills ---
        # DoT hits will not count into summary hitcounter ...
        total_hits_sum = sum(
            s['hits'] for s in stats
            if s['skill'] != "DoT damage"
        )
        total_val_sum = sum(s['total'] for s in stats)  # ... whereas total damage includes dot damage

        all_min = None
        all_max = None
       
        for s in stats:
            s_min = s.get('min')
            s_max = s.get('max')
            if s_min is not None:
                all_min = s_min if all_min is None else min(all_min, s_min)
            if s_max is not None:
                all_max = s_max if all_max is None else max(all_max, s_max)


        overall_avg = (total_val_sum / total_hits_sum) if total_hits_sum else 0.0

        # --- define are for table and summary ---
        bottom_y = self.height() - STARTSTOP_BTN_HEIGHT - FRAME_PADDING
        summary_block_h = row_h * 3 + 10           # line + summary + detail

        extra_bottom_gap = 10                      # space between detail lines and buttons

        body_top = header_y2 + 6
        body_bottom = bottom_y - summary_block_h - extra_bottom_gap

        # --- bind visible bars to fix column sizes ---
        raw_h = max(0, body_bottom - body_top)
        visible_rows = max(1, raw_h // row_h)
        visible_h = visible_rows * row_h
        body_bottom = body_top + visible_h

        # --- calculate scrolling borders ---
        content_h = len(stats) * row_h
        max_scroll = max(0, content_h - visible_h)
        self._max_scroll = max_scroll
        self._table_scroll = max(0.0, min(self._table_scroll, float(max_scroll)))

        # --- staring index for first visbile row
        start_index = int(self._table_scroll // row_h)
        offset_y = 0  # only scroll for full line ticks

        # --- paint lines ---
        p.setFont(QFont("Arial", 9))
        y = body_top + offset_y

        for i in range(start_index, len(stats)):
            if y >= body_bottom:
                break
            s = stats[i]
            skill = s['skill']
            hits = s['hits']
            total_val = s['total']
            avg = s['avg']

            row_top = y
            row_bottom = y + row_h

            # row bounds for click
            self._skill_row_bounds.append((row_top, row_bottom, skill))

            # highlight background while selected or hover
            is_selected = (skill == self.selected_skill)
            is_hover = (skill == getattr(self, "_hover_skill", None))

            if is_selected or is_hover:
                alpha = 60 if is_selected else 30   # highlight selected lines more than just hover
                p.setBrush(QColor(255, 255, 255, alpha))
                p.setPen(Qt.NoPen)
                p.drawRect(bar_left - 2, row_top + 2,
                           right - bar_left, row_h - 2)

            frac = total_val / max_val
            bar_w = int(bar_max_w * frac)

            bar_rect = QRect(bar_left, row_top + 4, bar_w, row_h - 6)
            corner_radius = 3

            # --- draw bar ---
            p.setPen(Qt.NoPen)
            if self.stat_mode == 'hps':
                total_val = s['total'] or 1
                frac = total_val / max_val
                bar_w = int(bar_max_w * frac)
                bar_rect = QRect(bar_left, row_top + 4, bar_w, row_h - 6)

                rtype = s.get('rtype', 'morale')
                if rtype == 'power':
                    bar_col = QColor(90, 140, 220, 230)   
                else:
                    bar_col = QColor(70, 150, 70, 230)    

                p.setBrush(bar_col)
                p.drawRoundedRect(bar_rect, corner_radius, corner_radius)

                # slight hightlight line upper edge of the bar
                hi_rect = QRect(bar_rect.left(), bar_rect.top(),
                                bar_rect.width(), 4)
                p.setBrush(QColor(255, 255, 255, 40))
                p.drawRoundedRect(hi_rect, corner_radius, corner_radius)
                
            elif self.stat_mode == 'dts':
                by_dtype = s.get('by_dtype', {})
                total_val = s['total'] or 1

                frac = total_val / max_val
                bar_w = int(bar_max_w * frac)
                bar_rect = QRect(bar_left, row_top + 4, bar_w, row_h - 6)
                # colors for different damage types
                dtype_colors = {
                    'common': QColor(140, 140, 140, 230),   # grey
                    'shadow': QColor(110, 70, 160, 230),    # violett
                    'fire':   QColor(190, 110, 40, 230),    # dark orange
                    'other':  QColor(90, 90, 120, 230),
                }

                x = bar_left
                h = row_h - 6

                # --- fixed order ---
                for key in ('common', 'shadow', 'fire', 'other'):
                    part = by_dtype.get(key, 0)
                    if part <= 0:
                        continue
                    w = int(bar_w * part / total_val)
                    if w <= 0:
                        continue
                    color = dtype_colors.get(key, dtype_colors['other'])
                    p.setBrush(color)
                    p.drawRect(x, row_top + 4, w, h)
                    x += w

                # slight hightlight line upper edge of the bar
                hi_rect = QRect(bar_left, row_top + 4, bar_w, 4)
                p.setBrush(QColor(255, 255, 255, 40))
                p.drawRect(hi_rect)    

            else:
                # common DPS/DTPS unicolor bar
                frac = total_val / max_val
                bar_w = int(bar_max_w * frac)
                bar_rect = QRect(bar_left, row_top + 4, bar_w, row_h - 6)
                corner_radius = 3

                p.setBrush(bar_base_col)
                p.drawRoundedRect(bar_rect, corner_radius, corner_radius)

                hi_rect = QRect(bar_rect.left(), bar_rect.top(),
                                bar_rect.width(), 4)
                p.setBrush(bar_highlight_col)
                p.drawRoundedRect(hi_rect, corner_radius, corner_radius)

            # --- skill name ---
            p.setPen(table_text)
            skill_rect = QRect(bar_left + 4, row_top + 2,
                            bar_max_w - 8, row_h)
            p.drawText(skill_rect,
                    Qt.AlignVCenter | Qt.AlignLeft, skill)

            # --- center columns with numbers ---
            p.setPen(QColor(230, 230, 230))
            hits_rect = QRect(col_hits_x, row_top + 2, col_hits_w, row_h)
            total_rect = QRect(col_total_x, row_top + 2, col_total_w, row_h)
            avg_rect = QRect(col_avg_x, row_top + 2, col_avg_w, row_h)

            # --- show DoT hits in brackets ---
            if skill == "DoT damage":
                hits_txt = f"({hits})"
            else:
                hits_txt = f"{hits}"

            p.drawText(hits_rect, Qt.AlignCenter, hits_txt)
            p.drawText(total_rect, Qt.AlignCenter, f"{total_val:,}")
            p.drawText(avg_rect, Qt.AlignCenter, f"{int(avg):,}")
            y += row_h

        # --- if no stats are available, info in table are and note for start ingame chat logging ---
        if not has_stats:
            p.setFont(QFont("Arial", 9))
            #p.setPen(QColor(220, 220, 220))
            p.setPen(table_text)
            p.drawText(
                bar_left,
                body_top + int(row_h),
                "No data yet. Make sure, you're logging your ingame combat chat!"
            )
            
        # --- scrollbar on the right side ---
        if max_scroll > 0:
            sb_x = right + 2
            sb_w = 4
            sb_rect = QRect(sb_x, body_top, sb_w, visible_h)
            p.setPen(QColor(80, 80, 80, 200))
            p.setBrush(QColor(40, 40, 40, 150))
            p.drawRect(sb_rect)

            ratio = visible_h / float(content_h)
            bar_h = max(20, int(visible_h * ratio))
            pos_ratio = self._table_scroll / float(max_scroll) if max_scroll else 0.0
            bar_y = body_top + int((visible_h - bar_h) * pos_ratio)

            thumb_rect = QRect(sb_x, bar_y, sb_w, bar_h)
            p.setBrush(QColor(180, 140, 60, 220))
            p.setPen(Qt.NoPen)
            p.drawRect(thumb_rect)

        # --- summary line fixed below skill table ---
        sum_top = bottom_y - summary_block_h - extra_bottom_gap + 4

        p.setPen(header_border)
        p.drawLine(bar_left, sum_top, right, sum_top)
        sum_top += 4
        
        # --- remember summary area ---
        self.summary_rect = QRect(bar_left, sum_top, right - bar_left, row_h)

        # --- hover highlight for summary ---
        if getattr(self, "_hover_summary", False):
            p.setBrush(QColor(255, 255, 255, 25))  
            p.setPen(Qt.NoPen)
            hl_rect = self.summary_rect.adjusted(0, 1, 0, -1)
            p.drawRect(hl_rect)

        p.setFont(QFont("Arial", 10, QFont.Bold))
        p.setPen(header_text)

        sum_label_rect = QRect(bar_left, sum_top, bar_max_w, row_h)
        p.drawText(sum_label_rect,
                Qt.AlignVCenter | Qt.AlignLeft, "Summary")
        
        # --- remember for clicking lines ---
        self.summary_rect = QRect(bar_left, sum_top, right - bar_left, row_h)

        hits_sum_rect = QRect(col_hits_x, sum_top, col_hits_w, row_h)
        total_sum_rect = QRect(col_total_x, sum_top, col_total_w, row_h)
        avg_sum_rect = QRect(col_avg_x, sum_top, col_avg_w, row_h)

        p.drawText(hits_sum_rect, Qt.AlignCenter, f"{total_hits_sum}")
        p.drawText(total_sum_rect, Qt.AlignCenter, f"{total_val_sum:,}")
        p.drawText(avg_sum_rect, Qt.AlignCenter, f"{int(overall_avg):,}")

        # --- detail area below summary (two lines) ---
        detail_y = sum_top + row_h + 4
        line_h = row_h

        p.setFont(QFont("Arial", 9))
        p.setPen(QColor(180, 140, 60))
        fm = p.fontMetrics()

        total_w = right - bar_left
        
        ## --- static area for min and max
        col_w = int(total_w * 0.22)  
        baseline1 = detail_y + int(0.7 * line_h)
        baseline2 = detail_y + line_h + int(0.7 * line_h)

        if self.selected_skill:
            details = self._compute_skill_details(self.selected_skill)
            if not details:
                msg = "No data for selected skill."
                p.drawText(bar_left, baseline1, msg)
            else:
                skill_name = self.selected_skill
                hits = details['hits']
                min_val = details['min']
                max_val = details['max']
                total = hits * details['avg']

                # line 1: skill name (left, dynamic lenght), min & max (right, static)
                p.drawText(bar_left, baseline1, skill_name)
                # shared column for "min:" / "Total:" 
                label_col_right = right - 2 * col_w   
                label_col_width = col_w               

                # line 1: min: <value>
                label1 = "min:"
                val1   = f"{min_val}"
                label1_rect = QRect(
                    label_col_right - label_col_width,
                    detail_y,
                    label_col_width,
                    line_h,
                )
                p.drawText(label1_rect, Qt.AlignVCenter | Qt.AlignRight, label1)
                val1_x = label_col_right + 5
                p.drawText(val1_x, baseline1, val1)

                # line 2: total: <value>
                label2 = "Total:"
                val2   = f"{int(total):,}"
                label2_rect = QRect(
                    label_col_right - label_col_width,
                    detail_y + line_h,
                    label_col_width,
                    line_h,
                )
                p.drawText(label2_rect, Qt.AlignVCenter | Qt.AlignRight, label2)
                val2_x = label_col_right + 5
                p.drawText(val2_x, baseline2, val2)

                # line 1: max <value>
                max_txt = f"max: {max_val}"
                max_rect = QRect(
                    right - col_w - 10,
                    detail_y,
                    col_w,
                    line_h,
                )
                p.drawText(max_rect, Qt.AlignVCenter | Qt.AlignRight, max_txt)

                # line 2: hits, total damage
                x = bar_left
                part = f"Hits: {hits}"
                p.drawText(x, baseline2, part)
        else:
            # all skills
            skill_name = "All skills"
            hits = total_hits_sum
            min_val = all_min if all_min is not None else 0
            max_val = all_max if all_max is not None else 0
            total = total_val_sum if total_val_sum is not None else 0
            
            # line 1: skill name (left, dynamic lenght), min & max (right, static)
            p.drawText(bar_left, baseline1, skill_name)
            # shared column for "min:" / "Total:"
            label_col_right = right - 2 * col_w  
            label_col_width = col_w              

            # line 1: min: <value>
            label1 = "min:"
            val1   = f"{min_val}"
            label1_rect = QRect(
                label_col_right - label_col_width,
                detail_y,
                label_col_width,
                line_h,
            )
            p.drawText(label1_rect, Qt.AlignVCenter | Qt.AlignRight, label1)
            val1_x = label_col_right + 5
            p.drawText(val1_x, baseline1, val1)

            # line 2: total: <value>
            label2 = "Total:"
            val2   = f"{int(total):,}"
            label2_rect = QRect(
                label_col_right - label_col_width,
                detail_y + line_h,
                label_col_width,
                line_h,
            )
            p.drawText(label2_rect, Qt.AlignVCenter | Qt.AlignRight, label2)            
            val2_x = label_col_right + 5
            p.drawText(val2_x, baseline2, val2)
            
            # line 1: max <value>
            max_txt = f"max: {max_val}"
            max_rect = QRect(
                right - col_w - 10,
                detail_y,
                col_w,
                line_h,
            )
            p.drawText(max_rect, Qt.AlignVCenter | Qt.AlignRight, max_txt)

            # line 2: hits, total damage          
            x = bar_left
            part = f"Hits: {hits}"
            p.drawText(x, baseline2, part)

        # line below detail area
        p.setPen(header_border)
        p.drawLine(
            bar_left,
            detail_y + 2 * line_h + 2,
            right,
            detail_y + 2 * line_h + 2
        )

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
        if self.stat_mode == 'hps':
            self.manual_label.setText("Select ally:")
        elif self.stat_mode == 'dts':
            self.manual_label.setText("Select source:")
        else:
            self.manual_label.setText("Select target:")
        
        self.selected_skill = None
        self._rebuild_target_dropdown()
        self._refresh_view_from_mode()
        self._update_layout()
        self.update()  # force repaint to use new colors

    ###--- End: functionality functions and parsing routines ---###
    

    ###--- Start: helper functions for interaction with overlay ---###
    
    # --- Tail Lifecycle ---
    def _ensure_log_thread(self):
        # Wenn der Thread noch lebt: nichts zu tun
        if self._tail_thread and self._tail_thread.is_alive():
            return

        path = get_latest_combat_log()
        if not path:
            if DEBUG_PARSE:
                print("[LOG] no combat log yet – will retry")
            return

        self._current_log_path = path
        self._tail_should_run = True

        def _tail_loop(pth: str):
            try:
                enc = _detect_encoding(pth)
                with open(pth, 'r', encoding=enc, errors='ignore') as f:
                    f.seek(0, os.SEEK_END)
                    while self._tail_should_run:
                        line = f.readline()
                        if not line:
                            time.sleep(0.05)
                            continue

                        parsed = self._parse_line(line)
                        if not parsed:
                            continue

                        # WICHTIG: keine UI-Aufrufe hier, nur Queue!
                        try:
                            if hasattr(self, "_event_queue"):
                                self._event_queue.put(parsed)
                        except Exception as e:
                            if DEBUG_PARSE:
                                print(f"[ERR] enqueue failed: {e!r}")
                            continue
            except Exception as e:
                if DEBUG_PARSE:
                    print(f"[ERR] tail-loop outer: {e!r}")
            finally:
                # markieren, dass der Thread beendet ist
                self._tail_thread = None

        import threading
        self._tail_thread = threading.Thread(
            target=_tail_loop,
            args=(path,),
            daemon=True,
        )
        self._tail_thread.start()

    def _stop_log_thread(self):
        self._tail_should_run = False
        # daemon thread – kein join nötig
        
    # --- Logzeile -> Event ---
    def _parse_line(self, line):
        # 1) Eigener Schaden?
        hit = self._parse_damage_line(line)   # <- das ist dein bisheriger DPS-Parser-Inhalt aus _parse_line
        if hit:  # ('hit', dmg, enemy, skill)
            return hit
        # 2) Eigenes Heal?
        heal = self._parse_heal_line(line)
        if heal:  # ('heal', amount, target, skill)
            return heal
        # 3) Eingehender Schaden?
        taken = self._parse_taken_line(line)
        if taken:  # ('taken', amount, attacker, skill, dtype)
            return taken
        return None
    
    def _parse_damage_line(self, line):
        text = line.strip()
        if not text: return None
        
        
        # --- Deutscher Client: "Ihr trefft ..." ---
        low = text.lower()
        if "ihr trefft" in low:
            # Variante mit Skill:
            # [PREFIX:] Ihr trefft <Ziel> mit der Fertigkeit '<Skill>' und (ihre|seine) Moral nimmt N Punkte Schaden (<dtype>).
            m = re.match(
                r"^(?:(?P<prefix>[^:]+):\s*)?Ihr trefft\s+(?P<target>.+?)\s+mit der Fertigkeit\s+'(?P<skill>[^']+)'\s+und\s+(?:ihre|seine)\s+Moral nimmt\s+(?P<amt>[\d\.]+)\s+Punkte Schaden\s+\((?P<dtype>[^)]+)\)\.",
                text,
                re.IGNORECASE,
            )
            if m:
                enemy = m.group("target").strip()
                skill = m.group("skill").strip()
                dmg = int(re.sub(r"[^\d]", "", m.group("amt")))

                # Autoattacks erkennst du weiterhin über AA_SKILLS
                # (hier kannst du die deutschen Skillnamen ergänzen)
                if skill in AA_SKILLS:
                    s_low = skill.lower()
                    if "bow" in s_low or "bogen" in s_low:
                        skill = "Autoattack (ranged)"
                    else:
                        skill = "Autoattack (melee)"

                return ("hit", dmg, enemy, skill)

            # Variante ohne Skill (DoT):
            # Ihr trefft <Ziel> und (ihre|seine) Moral nimmt N Punkte Schaden (<dtype>).
            m = re.match(
                r"^(?:(?P<prefix>[^:]+):\s*)?Ihr trefft\s+(?P<target>.+?)\s+und\s+(?:ihre|seine)\s+Moral nimmt\s+(?P<amt>[\d\.]+)\s+Punkte Schaden\s+\((?P<dtype>[^)]+)\)\.",
                text,
                re.IGNORECASE,
            )
            if m:
                enemy = m.group("target").strip()
                dmg = int(re.sub(r"[^\d]", "", m.group("amt")))
                skill = "DoT damage"
                return ("hit", dmg, enemy, skill)

            # Falls die deutsche Variante doch nicht gepasst hat, weiter mit EN-Parser
            # (z.B. wenn die Zeile doch was anderes war)
        
        
        hit_kw = " hit " if " hit " in text else (" hits " if " hits " in text else None)
        if not hit_kw: return None
        try:
            actor, rest = text.split(hit_kw, 1)
        except ValueError:
            return None
        actor_lc = actor.strip().lower()
        if actor_lc.startswith("the "): actor_lc = actor_lc[4:].lstrip()
        is_you = actor_lc.startswith("you")
        is_pet = actor_lc in PET_NAMES
        if not (is_you or is_pet): return None
        if rest.lower().startswith("the "): rest = rest[4:].lstrip()
        if " for " not in rest or " points" not in rest: return None
        try:
            before_for, after_for = rest.rsplit(" for ", 1)
            dmg_token = after_for.split(" points", 1)[0]
            dmg = int(re.sub(r"[^\d]", "", dmg_token))
        except Exception:
            return None
        if " with " in before_for:
            enemy_part, skill_part = before_for.split(" with ", 1)
            skill = skill_part.strip().rstrip(".")
            if skill in AA_SKILLS:
                # Unterscheide nach Name – z.B. "Bow Attack" → Autoattack (ranged)
                if "bow" in skill.lower():
                    skill = "Autoattack (ranged)"
                else:
                    skill = "Autoattack (melee)"
        else:
            enemy_part = before_for; skill = "DoT damage"
        enemy = enemy_part.strip().rstrip(".")
        return ("hit", dmg, enemy, skill, is_pet)

    def _parse_heal_line(self, line: str):
        """
        Liefert:
        ('heal', amount:int, target:str, skill:str, rtype:str|None)
        rtype ∈ {'Morale','Power'} wenn vorhanden.
        """
        text = line.strip()
        if not text:
            return None
        
         # --- Deutscher Client: "Ihr heilt N Punkte des Schadens (Moral) ..." ---
        low = text.lower()
        if low.startswith("ihr heilt"):
            m = re.match(
                r"^Ihr heilt\s+(?P<amt>[\d\.]+)\s+Punkte des Schadens\s+\((?P<res>[^)]+)\),\s+den\s+(?P<target>.+?)\s+genommen hat\.",
                text,
                re.IGNORECASE,
            )
            if m:
                amt = int(re.sub(r"[^\d]", "", m.group("amt")))
                res_raw = m.group("res").strip().lower()
                if "moral" in res_raw:
                    rtype = "Morale"
                elif "kraft" in res_raw:
                    rtype = "Power"
                else:
                    rtype = None

                target = m.group("target").strip()
                # Selbstheilung auf "You" mappen
                if target.lower() in ("ihr", "euch", "euer", "euch selbst"):
                    target = "You"

                skill = "Heal"
                return ("heal", amt, target, skill, rtype)
        

        def strip_the(s: str) -> str:
            s = s.strip()
            return s[4:].lstrip() if s.lower().startswith("the ") else s

        def to_int(num: str) -> int:
            return int(re.sub(r"[^\d]", "", num))

        t = text.rstrip()

        # Hilfs-Teil für Ressource:
        # … (Morale points) | (Power points) | (points of Morale/Power) | points
        res_part = r"(?:(?P<res1>Morale|Power)\s+points?|points?\s+of\s+(?P<res2>Morale|Power)|points?)"

        # A) "<actor> heal(s|ed) <target> for N <res_part>"
        m = re.search(
            rf"^(?P<actor>.+?)\s+heal(?:s|ed)?\s+(?P<target>.+?)\s+for\s+(?P<amt>[\d,]+)\s+{res_part}(?:\.\s*)?$",
            t, re.IGNORECASE)
        if m:
            actor = strip_the(m.group("actor"))
            actor_lc = actor.lower()
            is_you = actor_lc.startswith("you")
            is_pet = actor_lc in PET_NAMES
            if not (is_you or is_pet):
                return None  # nur eigene Heals zählen

            target = strip_the(m.group("target"))
            if target.lower() in ("yourself", "you"):
                target = "You"

            amt = to_int(m.group("amt"))
            rtype = (m.group("res1") or m.group("res2"))  # None wenn nur "points"
            skill = "Heal"
            return ("heal", amt, target, skill, rtype)

        # B) "<skill> heals <target> for N <res_part>"  (nur "Your <skill>" zählt)
        m = re.search(
            rf"^(?P<skill>.+?)\s+heal(?:s|ed)?\s+(?P<target>.+?)\s+for\s+(?P<amt>[\d,]+)\s+{res_part}(?:\.\s*)?$",
            t, re.IGNORECASE)
        if m:
            skill = m.group("skill").strip()
            if not skill.lower().startswith("your "):
                return None
            skill = skill[5:].lstrip()

            target = strip_the(m.group("target"))
            if target.lower() in ("yourself", "you"):
                target = "You"

            amt = to_int(m.group("amt"))
            rtype = (m.group("res1") or m.group("res2"))
            return ("heal", amt, target, skill, rtype)

        return None

    def _parse_taken_line(self, line: str):
        """
        Erkenne eingehenden Schaden.
        Beispiele:
        "The Downs Wildcat hits you with Melee Common Low for 45 points of Common damage to Morale"
        "Goblin hits you for 12 points of Fire damage to Morale."
        Rückgabe: ("taken", amount:int, attacker:str, skill:str, dtype:str|None) oder None
        """
        text = line.strip()
        if not text:
            return None
        
        
        low = text.lower()

        # --- Deutscher Client: "<Mob> trifft Euch mit der Fertigkeit '...'" ---
        if "trifft euch" in low:
            # Beispiel:
            # "Wütender Keiler trifft Euch mit der Fertigkeit 'Niedriger allgemeiner Schaden (Nahkampf)'"
            m = re.match(
                r"^(?P<attacker>.+?)\s+trifft\s+Euch\s+mit der Fertigkeit\s+'(?P<skill>[^']+)'",
                text,
                re.IGNORECASE,
            )
            if not m:
                return None

            attacker = m.group("attacker").strip()
            raw_skill = m.group("skill").strip()

            # Damage-Type grob aus dem Skillnamen ableiten
            skill_lower = raw_skill.lower()
            dtype = "common"
            if "schatten" in skill_lower:
                dtype = "shadow"
            elif "feuer" in skill_lower:
                dtype = "fire"

            # Skill selbst etwas normalisieren – optional:
            # "Niedriger allgemeiner Schaden (Nahkampf)" -> "Standard attack"
            skill = raw_skill
            if "schaden" in skill_lower:
                skill = "Hit"  # oder "Standard attack", je nach Geschmack

            # WICHTIG:
            # Diese Zeile enthält noch KEINE Schadenszahl -> wir können hier
            # noch keinen DTPS-Eintrag erzeugen.
            #
            # D.h. entweder:
            #   - wir ignorieren sie komplett (return None), oder
            #   - wir bauen später ein System, das Angriffszeile + Schadenzeile
            #     matcht. Dafür bräuchten wir aber ein Beispiel der eigentlichen
            #     "Eure Moral nimmt ... Schaden"-Zeile im DE-Client.
            #
            # Bis wir diese Zeile kennen, ist es am sichersten:
            return None
        
        

        def strip_the(s: str) -> str:
            s = s.strip()
            return s[4:].lstrip() if s.lower().startswith("the ") else s

        # Grundmuster: <actor> hits you [with <skill>] for N points [of <dtype>] damage to Morale
        m = re.search(
            r"^(?P<actor>.+?)\s+hits?\s+you(?:rself)?(?:\s+with\s+(?P<skill>.+?))?\s+for\s+(?P<amt>[\d,]+)\s+points?(?:\s+of\s+(?P<dtype>[A-Za-z]+))?\s+damage\s+to\s+Morale\.?$",
            text, re.IGNORECASE)
        if not m:
            return None

        actor = strip_the(m.group("actor"))
        amt = int(re.sub(r"[^\d]", "", m.group("amt")))
        skill = (m.group("skill") or "Hit").strip()
        dtype = (m.group("dtype") or "").strip() or None

        # Nur eingehenden Schaden, also Ziel = du; passt durch Regex (… hits you …)
        return ("taken", amt, actor, skill, dtype)

    def _handle_parsed_event(self, parsed):
        """
        Wird im UI-Thread aufgerufen, um ein geparstes Event
        in die Aggregates einzubauen.
        """
        if not parsed:
            return

        now = time.time()
        self._last_event_time = now

        # Wenn der Parser „aus“ ist, ignorieren wir neue Events
        if not self.manual_running:
            return

        et = parsed[0]

        if et == 'hit':
            # neue Variante mit is_pet
            if len(parsed) == 5:
                _, val, target, skill, is_pet = parsed
            else:
                # Fallback für alte Tuples
                _, val, target, skill = parsed
                is_pet = False

            self._on_hit(val, target, skill, is_pet)

        elif et == 'heal':
            if len(parsed) == 5:
                _, val, target, skill, rtype = parsed
            else:
                _, val, target, skill = parsed
                rtype = None
            self._on_heal(val, target, skill, rtype)

        elif et == 'taken':
            if len(parsed) == 5:
                _, val, attacker, skill, dtype = parsed
            else:
                _, val, attacker, skill = parsed
                dtype = None
            self._on_taken(val, attacker, skill, dtype)


    def _on_hit(self, dmg, enemy, skill, is_pet: bool = False):
        if not self.manual_running: return
        now = time.time()
        if self.manual_waiting:
            self.manual_waiting = False; self.manual_start_time = now
        rel_t = (now - self.manual_start_time) if self.manual_start_time else 0.0
        evt = {"time": rel_t, "dmg": dmg, "enemy": enemy, "skill": skill, "is_pet": bool(is_pet)}
        self._append_evt('dps', evt)
        # Anzeige auf **aktuellen** Modus mappen
        self._refresh_view_from_mode()

    def _on_heal(self, amount: int, target: str, skill: str, rtype: str | None):
        if not self.manual_running:
            return
        now = time.time()
        if self.manual_waiting:
            self.manual_waiting = False
            self.manual_start_time = now

        rel_t = (now - self.manual_start_time) if self.manual_start_time else 0.0

        evt = {
            "time": rel_t,
            "dmg": amount,
            "enemy": target,
            "skill": skill,
            "rtype": rtype or "Morale"   # <-- Default setzen
        }
        self._append_evt('hps', evt)
        self._refresh_view_from_mode()

    def _on_taken(self, amount, attacker, skill, dtype):
        if not self.manual_running: return
        now = time.time()
        if self.manual_waiting:
            self.manual_waiting = False; self.manual_start_time = now
        rel_t = (now - self.manual_start_time) if self.manual_start_time else 0.0
        evt = {"time": rel_t, "dmg": amount, "enemy": attacker, "skill": skill}
        if dtype: evt["dtype"] = dtype
        if dtype: evt["max_skill_override"] = f"{skill} ({dtype})"
        self._append_evt('dts', evt)
        self._refresh_view_from_mode()

    
    def _toggle_startstop(self):
        
        if not self.manual_running:
            # --- START ---
            self.manual_running = True
            self.manual_waiting = True
            self.manual_start_time = None

            # Alle Aggregates & Anzeige zurücksetzen
            self._reset_all_modes()

            # UI: Start-Button aktiv stylen
            self.start_stop_btn.setText("Stop")
            apply_style(self.start_stop_btn, bg=COLORS['button_active'], text_color=TARGET_TEXT_HEX, bold=True)

            # Tailer aktivieren
            self._ensure_log_thread()

            # Target-Dropdown neu (nur "Total" oder aus aktuellem Mode)

            self._rebuild_target_dropdown()

            # Select-combat zurücksetzen und History einhängen
            self.PST_FGHT_DD.blockSignals(True)
            self.PST_FGHT_DD.clear()
            self.PST_FGHT_DD.addItem("Select combat", userData=None)
            for it in self.fight_history[-10:][::-1]:
                label = self._combat_dd_label_for_mode(it)
                self.PST_FGHT_DD.addItem(label, userData=it['id'])
            self.PST_FGHT_DD.blockSignals(False)

            # History-Handler nur EINMAL verbinden
            if not getattr(self, "_history_signal_bound", False):
                self.PST_FGHT_DD.currentIndexChanged.connect(self._on_select_combat_changed)
                self._history_signal_bound = True

            # UI sofort aktualisieren (alles 0)
            self._refresh_view_from_mode()
            return
        else:
            # --- STOP ---
            self.manual_running = False
            self.manual_waiting = False
            self.start_stop_btn.setText("Start")
            apply_style(self.start_stop_btn, bg=COLORS['button_noactive'], text_color=TARGET_TEXT_HEX)

            # Tailer im Manual-Mode beenden (spart IO). Du kannst ihn anlassen, wenn du willst.
            self._stop_log_thread()

            # Dropdown mit Zielen füllen
            self._rebuild_target_dropdown()

            # Combat-Time finalisieren (unverändert okay)
            any_events = any(self.modes[m]['events'] for m in ('dps','hps','dts'))

            # --- Snapshot bauen, nur wenn es wirklich Events gab ---
            if any_events:
                start_ts = time.localtime(time.time())
                ts_label = time.strftime("%Y-%m-%d %H:%M", start_ts)

             
                # Label: bevorzugt Gegner aus DPS, sonst Quellen aus DTS, sonst Targets aus HPS
                def names_from(mode):
                    ev = self.modes[mode]['events']
                    return sorted({e['enemy'] for e in ev}) if ev else []

                names = names_from('dps') or names_from('dts') or names_from('hps')
                enemy_label = names[0] if len(names) == 1 else ("Multi" if names else "--")

                # Dauer = max letztes Event über alle Modi
                last_times = [mm['events'][-1]['time'] for mm in self.modes.values() if mm['events']]
                duration_all = max(last_times) if last_times else 0.0

                #label = f"{ts_label} | {enemy_label}"
                base_label = enemy_label
                time_label = time.strftime("%H:%M", start_ts)

                def _mode_view(v):
                    return {
                        'events': list(v['events']),
                        'total':  v['total'],
                        'max':    v['max'],
                        'max_skill': v['max_skill'],
                    }

                snap = {
                    'id': self.fight_seq,
                    'enemy_label': base_label,
                    'time_label': time_label,
                    'modes': { k: _mode_view(v) for k, v in self.modes.items() },
                    'duration': duration_all,
                }
                snap['label'] =  f"{base_label} | {time_label}"

                self.fight_seq += 1
                self.fight_history.append(snap)

                # Dropdown: "current" bleibt Index 0; neuen Eintrag darunter einfügen.
                self.PST_FGHT_DD.blockSignals(True)
                label_for_mode = self._combat_dd_label_for_mode(snap)
                self.PST_FGHT_DD.insertItem(1, label_for_mode, userData=snap['id'])
                self.PST_FGHT_DD.blockSignals(False)

            self.update()
       
    
    def _on_manual_selection(self):
        # wenn im Kampf und noch keine Events → nichts tun
        if self.manual_running is True and not self._agg()['events']:
            return
        data = self.manual_combo.currentData()
        # None = All targets
        self.sel_target = data
        self._refresh_view_from_mode()
    
       
    def _on_select_combat_changed(self, idx: int):
        # Index 0 = "current" → Live-Ansicht
        if self.PST_FGHT_DD.currentIndex() == 0:
            self._reset_all_modes()
            self._rebuild_target_dropdown()
            self._refresh_view_from_mode()
            return

        # Snapshot holen (per ID aus userData)
        sel_id = self.PST_FGHT_DD.currentData()
        item = next((it for it in self.fight_history if it['id'] == sel_id), None)
        if not item:
            return

        # --- HIER: Snapshot -> per-Mode-States laden ---
        if 'modes' in item:
            m = item['modes']
            for k in ('dps','hps','dts'):
                self.modes[k]['events'] = list(m[k]['events'])
                self.modes[k]['total'] = m[k]['total']
                self.modes[k]['max'] = m[k]['max']
                self.modes[k]['max_skill'] = m[k]['max_skill']
            # Dauer: letztes Event über alle Modi
            last_times = [mm['events'][-1]['time'] for mm in self.modes.values() if mm['events']]
            self.combat_time = max(last_times) if last_times else 0.0
        else:
            # Fallback für alte Snaps
            evts = item['events']
            agg = self.modes[self.stat_mode]
            agg['events'] = list(evts)
            agg['total']  = sum(e['dmg'] for e in evts)
            mx = max(evts, key=lambda e: e['dmg']) if evts else None
            agg['max'] = mx['dmg'] if mx else 0
            agg['max_skill'] = mx['skill'] if mx else '--'
            self.combat_time = evts[-1]['time'] if evts else 0.0

        self.sel_target = None
        self._rebuild_target_dropdown()
        self._refresh_view_from_mode()
   
    # --- runtime ticker ---
    def _tick(self):
        # 1) Events aus dem Log-Thread holen (thread-safe über Queue)
        if hasattr(self, "_event_queue"):
            import queue as _qmod
            while True:
                try:
                    parsed = self._event_queue.get_nowait()
                except _qmod.Empty:
                    break
                self._handle_parsed_event(parsed)

        now = time.time()

        # 2) Combat-Log-Überwachung (neue Datei / File entsteht erst später)
        if self.manual_running:
            last_check = getattr(self, "_last_log_check", 0.0)
            if now - last_check >= LOG_CHECK_INTERVAL:
                self._last_log_check = now

                # Wenn ein Thread läuft, prüfen wir auf Log-Rotation
                if self._tail_thread and self._tail_thread.is_alive():
                    latest = get_latest_combat_log()
                    if (
                        latest
                        and self._current_log_path
                        and os.path.normcase(latest) != os.path.normcase(self._current_log_path)
                    ):
                        if DEBUG_PARSE:
                            print(f"[LOG] switching to new combat log: {latest}")
                        self._stop_log_thread()
                        self._tail_thread = None
                        self._current_log_path = None

                # Sicherstellen, dass ein Tail-Thread läuft
                if (self._tail_thread is None) or (not self._tail_thread.is_alive()):
                    self._ensure_log_thread()

            # 2b) Start/Stop-Button leicht grün pulsieren lassen, solange tracing läuft
            import math
            base_col = COLORS['button_active']
            phase = (now * 1.5) % (2 * math.pi)  # Puls-Frequenz
            factor = 110 + int(40 * math.sin(phase))  # 110% ± 20%

            # .lighter erwartet Prozentangabe (100 = normal)
            factor = max(40, min(200, factor))
            pulse_bg = base_col.lighter(factor)
            hover_col = pulse_bg.lighter(120)

            apply_style(
                self.start_stop_btn,
                bg=pulse_bg,
                text_color=TARGET_TEXT_HEX,
                hover=hover_col,
                bold=True,
            )

        # 3) Laufzeit im aktuellen Kampf NICHT mehr per now-Startzeit setzen.
        #    combat_time wird ausschließlich in _refresh_view_from_mode
        #    aus den Event-Zeitstempeln berechnet.
        
        # 4) Auto-Stop nach X Sekunden Inaktivität
        if (
            self.manual_running
            and not self.manual_waiting
            and self.auto_stop_cb.isChecked()
            and getattr(self, "_last_event_time", None)
            and now - self._last_event_time >= AUTO_STOP_SECONDS
        ):
            if DEBUG_PARSE:
                print(f"[AUTO] segment combat after {AUTO_STOP_SECONDS}s of inactivity")

            # 1) aktuellen Kampf beenden (Snapshot anlegen etc.)
            self._toggle_startstop()

            # 2) sofort neue Session starten (leerer Kampf, aber Parser bleibt „armed“)
            self._toggle_startstop()

        # 5) Repaint
        self.update()
            
    # --- overwrite mouse wheel function for table scrolling
    
    def wheelEvent(self, event):
        # Nur scrollen, wenn wir überhaupt eine Tabelle + Scrollbereich haben
        if not hasattr(self, "_max_scroll") or self._max_scroll <= 0:
            return super().wheelEvent(event)

        delta = event.angleDelta().y()
        if delta == 0:
            return

        row_h = 22  # muss zu paintEvent passen
        steps = int(delta / 120)   # ein "Klick" = 1 Zeile
        if steps == 0:
            return

        new_scroll = self._table_scroll - steps * row_h
        new_scroll = max(0.0, min(float(self._max_scroll), float(new_scroll)))
        if new_scroll != self._table_scroll:
            self._table_scroll = new_scroll
            self.update()
            event.accept()
    
           
    def _copy_to_clipboard(self):
        # ---- Events je nach Code-Stand holen ----

        evts = list(self._agg()['events'])
        sel = getattr(self, "sel_target", None)
        if sel:
            evts = [e for e in evts if e['enemy'] == sel]
        target_total_label = (
            "all allies" if self.stat_mode == 'hps'
            else "all sources" if self.stat_mode == 'dts'
            else "all targets"
        )
        selected_label = sel or target_total_label
        
        # Dauer
        if not evts:
            duration = 0.0
        else:
            duration = (evts[-1]['time'] - evts[0]['time']) if sel and len(evts) > 1 else evts[-1]['time']

        total = sum(e['dmg'] for e in evts)
        rate  = int(total / (duration or 1))

        # ---- Nachricht pro Modus ----
        if self.stat_mode == 'hps':
            # Basistext
            base_target = selected_label if 'selected_label' in locals() else (
                ("all allies" if self.manual_combo.currentText() == "Total" else self.manual_combo.currentText())
            )
            # Breakdown nach Ressource
            type_totals = {}
            for e in evts:
                rt = e.get('rtype') or "Morale"  # default Morale, falls nicht geloggt
                type_totals[rt] = type_totals.get(rt, 0) + e['dmg']

            parts = []
            for rt, amt in sorted(type_totals.items(), key=lambda kv: kv[1], reverse=True):
                pct = (100.0 * amt / total) if total else 0.0
                parts.append(f"{rt} {amt} ({pct:.0f}%)")
            breakdown = f" | by resource: {', '.join(parts)}" if parts else ""

            # Self-Heal phrasing
            if isinstance(base_target, str) and base_target in ("You", "yourself"):
                msg = f"You healed yourself for {total} over {duration:.1f}s (HPS: {rate}){breakdown}"
            else:
                msg = f"You healed {base_target} for {total} over {duration:.1f}s (HPS: {rate}){breakdown}"

        elif self.stat_mode == 'dts':
            # Breakdown nach dtype
            type_totals = {}
            for e in evts:
                dt = e.get('dtype') or "Unknown"
                type_totals[dt] = type_totals.get(dt, 0) + e['dmg']

            # sortiert nach Menge absteigend
            parts = []
            for dt, amt in sorted(type_totals.items(), key=lambda kv: kv[1], reverse=True):
                pct = (100.0 * amt / total) if total else 0.0
                parts.append(f"{dt} {amt} ({pct:.0f}%)")

            breakdown = f" | by type: {', '.join(parts)}" if parts else ""
            msg = f"You took {total} damage over {duration:.1f}s from {selected_label} (DTPS: {rate}){breakdown}"

        else:  # 'dps'
            msg = f"You dealt {total} damage over {duration:.1f}s to {selected_label} (DPS: {rate})"

        QApplication.clipboard().setText(msg)
            
    def _agg(self, mode=None):
        return self.modes[mode or self.stat_mode]
    
    def _current_target_label(self):
        """Text für die linke Titelzeile."""
        if self.sel_target:
            return self.sel_target
        if self.stat_mode == 'hps':
            return "All allies"
        elif self.stat_mode == 'dts':
            return "All sources"
        else:
            return "All targets"

    
    def _build_skill_stats(self):
        """
        Aggregiert Events des aktuellen Modus in tabellenfähige Zeilen.

        DPS / DTPS:
            - Gruppierung nach Skill
            - Felder: skill, hits, total, avg, min, max
            - DTPS zusätzlich: by_dtype = {'common': ..., 'shadow': ..., 'fire': ..., 'other': ...}

        HPS:
            - Gruppierung nach (ally, rtype)  (ally = Ziel, rtype = 'morale' / 'power')
            - Felder: skill (Label), ally, rtype, hits, total, avg, min, max
        """
        evts = self._agg()['events']
        
        if self.sel_target:
            evts = [e for e in evts if e['enemy'] == self.sel_target]
        
        
        if not evts:
            return []

        mode = self.stat_mode

        # --- HPS: nach Ally + Ressourcentyp gruppieren ---
        if mode == 'hps':
            by_row = {}  # key: (ally, rtype)
            for e in evts:
                ally = e.get('enemy') or "Unknown"
                r_raw = (e.get('rtype') or "").lower()
                rtype = 'power' if 'power' in r_raw else 'morale'

                key = (ally, rtype)
                d = by_row.setdefault(key, {
                    'ally': ally,
                    'rtype': rtype,
                    'hits': 0,
                    'total': 0,
                    'vals': [],
                })

                dmg = e['dmg']
                d['hits'] += 1
                d['total'] += dmg
                d['vals'].append(dmg)

            stats = []
            for (ally, rtype), d in by_row.items():
                vals = d['vals']
                hits = d['hits']
                total = d['total']
                avg = total / hits if hits else 0.0
                s_min = min(vals) if vals else None
                s_max = max(vals) if vals else None

                label = f"{ally} ({'Power' if rtype == 'power' else 'Heal'})"

                stats.append({
                    'skill': label,
                    'ally': ally,
                    'rtype': rtype,
                    'hits': hits,
                    'total': total,
                    'avg': avg,
                    'min': s_min,
                    'max': s_max,
                })

            stats.sort(key=lambda s: s['total'], reverse=True)
            return stats

        # --- DPS / DTPS: nach Skill gruppieren ---
        by_skill = {}
        for e in evts:
            sname = e['skill']

            key = sname
            dtype_key = None

            if mode == 'dts':
                dtype_raw = (e.get('dtype') or "").lower()
                dtype_key = 'other'
                if 'common' in dtype_raw:
                    dtype_key = 'common'
                elif 'shadow' in dtype_raw:
                    dtype_key = 'shadow'
                elif 'fire' in dtype_raw:
                    dtype_key = 'fire'

                # Speziell: "Hit" nach Schadenstyp splitten
                if sname == "Hit":
                    key = (sname, dtype_key)

            d = by_skill.setdefault(key, {
                'hits': 0,
                'total': 0,
                'vals': [],
                'by_dtype': {},
            })

            dmg = e['dmg']
            d['hits'] += 1
            d['total'] += dmg
            d['vals'].append(dmg)

            if mode == 'dts' and dtype_key is not None:
                bymap = d.setdefault('by_dtype', {})
                bymap[dtype_key] = bymap.get(dtype_key, 0) + dmg

        stats = []
        for key, d in by_skill.items():
            vals = d['vals']
            hits = d['hits']
            total = d['total']
            avg = total / hits if hits else 0.0
            s_min = min(vals) if vals else None
            s_max = max(vals) if vals else None

            sname = key
            dtype_for_label = None
            if mode == 'dts' and isinstance(key, tuple):
                sname, dtype_for_label = key

            # Anzeigename
            display_name = sname
            if mode == 'dts' and sname == "Hit":
                base = "Standard attack"
                if dtype_for_label:
                    type_label = {
                        'common': "Common",
                        'shadow': "Shadow",
                        'fire':   "Fire",
                        'other':  "Other",
                    }.get(dtype_for_label, dtype_for_label.title())
                    display_name = f"{base} ({type_label})"
                else:
                    display_name = base

            entry = {
                'skill': display_name,
                'hits': hits,
                'total': total,
                'avg': avg,
                'min': s_min,
                'max': s_max,
            }

            if mode == 'dts':
                entry['by_dtype'] = d.get('by_dtype', {})

            stats.append(entry)

        stats.sort(key=lambda s: s['total'], reverse=True)
        return stats

    def _compute_skill_details(self, skill_name: str):
        """
        Liefert Detaildaten für eine Zeile aus _build_skill_stats()
        Rückgabe: dict oder None
            {
                'skill': ...,
                'hits': ...,
                'min': ...,
                'max': ...,
                'avg': ...,
                'total': ...,
            }
        """
        stats = self._build_skill_stats()
        if not stats:
            return None

        row = None
        for s in stats:
            if s['skill'] == skill_name:
                row = s
                break

        if not row:
            return None

        hits = row['hits']
        avg = row['avg']
        total = row['total']

        return {
            'skill': row['skill'],
            'hits': hits,
            'min': row['min'],
            'max': row['max'],
            'avg': avg,
            'total': total,
        }


    def _auto_adjust_height(self):
        """Passt die Fensterhöhe dynamisch an Anzahl der Skill-Zeilen an."""
        stats = self._build_skill_stats()
        row_h = 22
        header_rows = 2      # Spaltenkopf + Summary
        visible_rows = max(1, len(stats)) + header_rows

        needed = self._table_top_y + visible_rows * row_h \
                 + STARTSTOP_BTN_HEIGHT + 2 * FRAME_PADDING

        new_h = int(max(MIN_HEIGHT, min(needed, MAX_HEIGHT)))
        if self.height() != new_h:
            self.resize(self.width(), new_h)

    def _rebuild_target_dropdown(self):
        agg = self._agg()
        evts = agg['events']

        metric_short = {'dps': 'DPS', 'hps': 'HPS', 'dts': 'DTPS'}.get(self.stat_mode, 'DPS')

        if self.stat_mode == 'hps':
            base = "All allies"
        elif self.stat_mode == 'dts':
            base = "All sources"
        else:
            base = "All targets"

        # --- All targets ---
        if evts:
            # Dauer für "All" = bis letztes Event dieses Modes
            dur_all = evts[-1]['time']
            rate_all = int(agg['total'] / (dur_all or 1)) if dur_all else 0
            all_label = f"{base}   ({rate_all} {metric_short})"
        else:
            all_label = base

        # --- pro Target gruppieren ---
        by_enemy = {}
        for e in evts:
            by_enemy.setdefault(e['enemy'], []).append(e)

        self.manual_combo.blockSignals(True)
        self.manual_combo.clear()
        # Eintrag 0 = All
        self.manual_combo.addItem(all_label, userData=None)

        for enemy in sorted(by_enemy.keys()):
            lst = by_enemy[enemy]
            total = sum(x['dmg'] for x in lst)
            if len(lst) > 1:
                dur = lst[-1]['time'] - lst[0]['time']
            else:
                dur = lst[-1]['time']
            rate = int(total / (dur or 1)) if dur else 0
            txt = f"{enemy}   ({rate} {metric_short})"
            self.manual_combo.addItem(txt, userData=enemy)

        self.manual_combo.setCurrentIndex(0)
        self.manual_combo.blockSignals(False)
        self.sel_target = None

    def _refresh_view_from_mode(self):
        agg = self._agg()
        evts = agg['events']
        if self.sel_target:  # „per Target“ Ansicht
            flt = [e for e in evts if e['enemy'] == self.sel_target]
            total = sum(e['dmg'] for e in flt)
            dur = (flt[-1]['time'] - flt[0]['time']) if len(flt) > 1 else (flt[-1]['time'] if flt else 0.0)
            mx_e = max(flt, key=lambda e: e['dmg']) if flt else None
        else:                # „Total“
            total = agg['total']
            # Dauer = bis letztes Event in diesem Mode (nicht global)
            dur = evts[-1]['time'] if evts else 0.0
            mx_e = None
            
        self.combat_time = dur
        if mx_e:
            self.max_hit = mx_e['dmg']; 
            self.max_hit_skill = mx_e.get('max_skill_override', mx_e['skill'])
        else:
            self.max_hit = agg['max']; 
            self.max_hit_skill = agg['max_skill']
        # Pulse-Referenz aus Mode-Recent spiegeln
        self._auto_adjust_height()
        self.update()

    def _append_evt(self, mode, evt):
        agg = self.modes[mode]
        agg['events'].append(evt)
        agg['total'] += evt['dmg']
        if evt['dmg'] > agg['max']:
            agg['max'] = evt['dmg']
            agg['max_skill'] = evt.get('max_skill_override', evt['skill'])

    def _metric_short(self, mode=None):
        """
        Kurzes Kürzel für den aktuellen Modus, z.B. 'DPS' / 'HPS' / 'DTPS'.
        """
        mode = mode or self.stat_mode
        return {'dps': 'DPS', 'hps': 'HPS', 'dts': 'DTPS'}.get(mode, 'DPS')


    def _combat_dd_label_for_mode(self, snap):
        """Erzeugt den Text für das 'Select combat'-Dropdown je nach aktuellem Modus."""
        metric_short = self._metric_short()
        enemy = snap.get('enemy_label', '--')
        time_s = snap.get('time_label', '')
        dur = snap.get('duration', 0.0)
        mode_view = snap.get('modes', {}).get(self.stat_mode, {})
        total = mode_view.get('total', 0)

        rate = int(total / (dur or 1)) if dur else 0

        # z.B. "Common Forest-boar (09:30)   245 DPS"
        left = f"{enemy}"
        middle = f"({time_s})" if time_s else ""
        right = f"{rate} {metric_short}" if total else ""

        # wir machen es einfach in einer Zeile, leicht „LotRO-Style“
        parts = [p for p in (left, middle, right) if p]
        return "  ".join(parts)
    
    def _reset_all_modes(self):
        if hasattr(self, "modes"):
            for k in ('dps', 'hps', 'dts'):
                self.modes[k]['events'].clear()
                self.modes[k]['total'] = 0
                self.modes[k]['max'] = 0
                self.modes[k]['max_skill'] = '--'
        # Anzeige-/Laufzeit-Reset
        self.max_hit = 0
        self.max_hit_skill = '--'
        self.combat_time = 0.0
        self.sel_target = None if hasattr(self, "sel_target") else None

        self.selected_skill = None
        self._skill_row_bounds = []        
        self._auto_adjust_height()
        
    # --- mouse action ---
    def mousePressEvent(self, e):
        from PyQt5.QtCore import Qt

        if e.button() != Qt.LeftButton:
            return super().mousePressEvent(e)

        y = e.pos().y()
        pos = e.pos()  # <-- QPoint, nicht nur y

        # 1) Klick in der Titelbar -> Fenster ziehen
        if y <= TITLE_BAR_HEIGHT:
            self._drag_start = e.globalPos() - self.frameGeometry().topLeft()
            e.accept()
            return

        # 2) Klick in einer Skill-Zeile?
        for top, bottom, skill in getattr(self, "_skill_row_bounds", []):
            if top <= y <= bottom:
                self.selected_skill = skill
                self.update()
                return
            
         # 3) Klick auf Summary-Zeile -> zurück auf "All skills"
        if getattr(self, "summary_rect", None) and self.summary_rect.contains(pos):
            self.selected_skill = None
            self.update()
            return

        # 4) Sonst: normales Drag-Verhalten
        self._drag_start = e.globalPos() - self.frameGeometry().topLeft()
        e.accept()    
            
    def mouseMoveEvent(self, e):
        from PyQt5.QtCore import Qt

        # Drag der Titelbar
        if self._drag_start:
            self.move(e.globalPos() - self._drag_start)
            e.accept()
            return

        pos = e.pos()
        y = pos.y()

        # Hover in Skill-Tabelle?
        hover_skill = None
        for top, bottom, skill in getattr(self, "_skill_row_bounds", []):
            if top <= y <= bottom:
                hover_skill = skill
                break

        # Hover in Summary-Zeile?
        hover_summary = False
        if getattr(self, "summary_rect", None) and self.summary_rect.contains(pos):
            hover_summary = True

        # Nur neu zeichnen, wenn sich was geändert hat
        if hover_skill != getattr(self, "_hover_skill", None) \
        or hover_summary != getattr(self, "_hover_summary", False):
            self._hover_skill = hover_skill
            self._hover_summary = hover_summary
            self.update()

        super().mouseMoveEvent(e)
            
            
            
    def mouseReleaseEvent(self, e):
        self._drag_start = None; super().mouseReleaseEvent(e)

    def closeEvent(self, event):
        # Log-Tailer korrekt stoppen, damit kein Thread überlebt
        if hasattr(self, "_stop_log_thread"):
            self._stop_log_thread()

        super().closeEvent(event)
        
    def leaveEvent(self, e):
        self._hover_skill = None
        self._hover_summary = False
        self.update()
        super().leaveEvent(e)

    ###--- End: helper functions for interaction with overlay ---###

###############################################################################
####### End of: Main routine                                            #######
###############################################################################    

###############################################################################
####### Execute code                                                    #######
###############################################################################    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ov = OverlayWindow()
    ov.show(); sys.exit(app.exec_())
