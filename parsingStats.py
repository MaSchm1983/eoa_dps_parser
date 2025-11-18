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


import sys, configparser, os, glob, re
import time
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QComboBox, QCheckBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from config import (
    WINDOW_WIDTH, MIN_HEIGHT, MAX_HEIGHT,
    TITLE_BAR_HEIGHT, BUTTON_SIZE,
    FRAME_PADDING, DROPDOWN_HEIGHT,
    MODE_AREA_HEIGHT, MODE_BTN_HEIGHT, MODE_BTN_WIDTH,
    BAR_PADDING, STARTSTOP_BTN_WIDTH, STARTSTOP_BTN_HEIGHT, 
    FONT_TITLE, FONT_SUBTITLE, FONT_BTN_TEXT,
    FONT_TEXT, FONT_TEXT_CLS_BTN, COLORS, AA_SKILLS
)

###############################################################################
##################### Parse for config.ini for infos ##########################
###############################################################################

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

# ── Helper to read current combat log (will be updated every 5s later) ── 

def _clean_dir(p: str) -> str:
    # Quotes + Leerraum weg, Variablen expandieren, normalisieren
    p = (p or "").strip().strip('"').strip("'")
    p = os.path.expandvars(os.path.expanduser(p))
    return os.path.normpath(p)

def get_latest_combat_log(folder=COMBAT_LOG_FOLDER):
    base = _clean_dir(folder)
    if not base or not os.path.isdir(base):
        if DEBUG_PARSE:
            print(f"[LOG] Invalid log dir: {repr(folder)} -> {repr(base)} (exists={os.path.isdir(base)})")
        return None

    # mehrere übliche Muster erlauben
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
#######           Helper for tracking all three types                   #######    
###############################################################################



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
        
        self._update_layout()             # 5) update layout on interact function
        self.show()   # optional, das show im Main-Window funktioniert aber auch
        self.raise_()
        self.activateWindow()


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
        self.modes = {
            'dps': {'events': [], 'total': 0, 'max': 0, 'max_skill': '--'},
            'hps': {'events': [], 'total': 0, 'max': 0, 'max_skill': '--'},
            'dts': {'events': [], 'total': 0, 'max': 0, 'max_skill': '--'},
        }
        
        self.sel_target = None  # aktuelle Auswahl im Target-Dropdown (None = Total)        
        self.total_damage = 0
        self.combat_time = 0.0
        self.max_hit = 0
        self.max_hit_skill = '--'
        self.fight_history = []  # list of dicts
        self.fight_seq = 0        # laufende ID für Snapshots
        
         # --- Manual-Run State ---
        self.manual_running = False
        self.manual_waiting = False
        self.manual_start_time = None
        self.manual_events = []          # [{time, dmg, enemy, skill}]
        self.manual_matrix = []          # [[time, dmg, enemy, skill]]

        # --- Tail-Thread State ---
        self._current_log_path = None
        self._tail_thread = None
        self._tail_should_run = False

        # --- UI/Timer ---
        from PyQt5.QtCore import QTimer
        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._tick)
        self._ui_timer.start(100)  # smooth time label while running
        
        # Position des Target-Headers (All targets / DPS / 19.0s)
        self._info_bar_y = TITLE_BAR_HEIGHT + MODE_BTN_HEIGHT + 8
        self._table_top_y = TITLE_BAR_HEIGHT + 80
        # Scroll-Offset für Skill-Tabelle
        self._table_scroll = 0.0
              

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
        apply_style(self.close_btn, bg=QColor(0,0,0,70), text_color=rgba(COLORS['background']))


        # ── past fights selection dropdown ──
        self.label = QLabel("Select combat:", self)
        self.label.setFont(FONT_SUBTITLE)
        lbl_width = self.label.fontMetrics().boundingRect(self.label.text()).width()
        self.label.setFixedWidth(lbl_width)
        self.PST_FGHT_DD = QComboBox(self)
        self.PST_FGHT_DD.setFont(FONT_TEXT)
        self.PST_FGHT_DD.setFixedHeight(DROPDOWN_HEIGHT)
        self.PST_FGHT_DD.addItem("Select combat")

        # ── start/stop button for manual parsing mode ──
        self.start_stop_btn = QPushButton("Start", self)
        self.start_stop_btn.setFont(FONT_BTN_TEXT)
        self.start_stop_btn.setFixedSize(STARTSTOP_BTN_WIDTH, STARTSTOP_BTN_HEIGHT)
        apply_style(self.start_stop_btn, bg=COLORS['button_noactive'], text_color=rgba(COLORS['line_col']))
        self.start_stop_btn.clicked.connect(self._toggle_startstop)

        # ── select targets for manual parsed combat ──
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
        
        
        # ── gemeinsamer LotRO-Style für beide Dropdowns ──
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
        
        
        
        self.auto_stop_cb = QCheckBox("stop combat after 15s", self)
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
        self.copy_btn.clicked.connect(self._copy_to_clipboard)


    # ── 5) styling updated for layout and update on interaction/events ──
    def _update_layout(self):
        # Höhe im Rahmen halten
        new_h = max(MIN_HEIGHT, min(self.height(), MAX_HEIGHT))
        self.resize(WINDOW_WIDTH, new_h)

        # ── Close-Button ──
        self.close_btn.move(self.width() - BUTTON_SIZE - FRAME_PADDING,
                            FRAME_PADDING)

        # ── Mode-Buttons (Damage / Heal / Taken) direkt unter Titel ──
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

        # ── Info-Bar ("All targets  |  DPS | 19.0s") direkt unter den Buttons ──
        info_h = 24
        self._info_bar_y = y          # wird in paintEvent verwendet
        y += info_h + 10               # etwas Abstand zu den Combos

        # Gemeinsame Breite / X-Position für beide Dropdowns
        dd_x = FRAME_PADDING + BAR_PADDING
        dd_w = self.width() - 2 * (FRAME_PADDING + BAR_PADDING)

        # ── Select combat (Label verstecken, Combo über volle Breite) ──
        self.label.hide()
        self.PST_FGHT_DD.setGeometry(dd_x, y, dd_w, DROPDOWN_HEIGHT)

        y += DROPDOWN_HEIGHT + 6

        # ── Select target / ally / source (Label verstecken, volle Breite) ──
        self.manual_label.hide()
        self.manual_combo.show()
        self.manual_combo.setGeometry(dd_x, y, dd_w, DROPDOWN_HEIGHT)

        # Startpunkt der Skill-Tabelle
        self._table_top_y = y + DROPDOWN_HEIGHT + 8

        # ── Untere Button-Leiste (Start/Stop, Auto-Stop, Copy) ──
        bottom_y = self.height() - STARTSTOP_BTN_HEIGHT - FRAME_PADDING

        self.start_stop_btn.move(FRAME_PADDING, bottom_y)

        cb_x = self.start_stop_btn.x() + self.start_stop_btn.width() + 12
        cb_y = bottom_y + (STARTSTOP_BTN_HEIGHT - self.auto_stop_cb.sizeHint().height()) // 2
        self.auto_stop_cb.move(cb_x, cb_y)

        copy_x = self.width() - self.copy_btn.width() - FRAME_PADDING
        copy_y = bottom_y + (STARTSTOP_BTN_HEIGHT - self.copy_btn.height()) // 2
        self.copy_btn.move(copy_x, copy_y)

        self.update()

    # ── paint all colors, texts, bars etc ──
    def paintEvent(self, e):
        from PyQt5.QtGui import QFont, QColor, QPainter
        from PyQt5.QtCore import Qt, QRect

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # ---------- halbtransparenter Hintergrund ----------
        p.fillRect(self.rect(), QColor(0, 0, 0, int(0.5 * 255)))

        # ---------- gemeinsame Header-Farben (LotRO-Stil) ----------
        header_bg     = QColor(60, 40, 20, int(0.95 * 255))   # dunkles Braun
        header_border = QColor(180, 140, 60, 255)             # Gold/Kante
        header_text   = QColor(235, 220, 190, 255)            # helles Beige

        # ---------- Titelbar ----------
        p.fillRect(0, 0, self.width(), TITLE_BAR_HEIGHT, header_bg)
        p.setPen(header_border)
        p.drawLine(0, TITLE_BAR_HEIGHT - 1, self.width(), TITLE_BAR_HEIGHT - 1)

        p.setPen(header_text)
        p.setFont(FONT_TITLE)
        fm = p.fontMetrics()
        ty = (TITLE_BAR_HEIGHT + fm.ascent() - fm.descent()) // 2
        p.drawText(FRAME_PADDING, ty, "ParsingStats in EoA v1.0.0")

        # ---------- Info-Bar ("All targets   DPS | 19.0s") ----------
        header_h = 24
        margin_l = 16
        margin_r = 16  # Platz für Close-Button

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

        mode_txt = self.stat_mode.upper()
        info_txt = f"{mode_txt} | {self.combat_time:.1f}s"
        p.setFont(QFont("Arial", 9))
        p.drawText(
            info_rect.adjusted(8, 0, -8, 0),
            Qt.AlignVCenter | Qt.AlignRight,
            info_txt
        )

        # ---------- Skill-Tabelle + Summary ----------

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

        # Bereich für Tabelle / Summary nach unten begrenzen
        bottom_y = self.height() - STARTSTOP_BTN_HEIGHT - FRAME_PADDING
        summary_block_h = row_h + 8           # Platz für Linie + Summary-Zeile
        body_top = table_top + 2 * row_h - 5     # nach Headerzeile
        body_bottom = bottom_y - summary_block_h - 4

        # --- Header über der Tabelle ---
        header_y2 = table_top + row_h
        p.setFont(QFont("Arial", 10, QFont.Bold))
        p.setPen(QColor(200, 200, 200, 210))

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

        stats = self._build_skill_stats()
        if not stats:
            p.setFont(QFont("Arial", 9))
            p.setPen(QColor(220, 220, 220))
            p.drawText(bar_left, body_top + 8,
                    "No data for this combat / mode yet.")
            p.end()
            return

        max_val = max(s['total'] for s in stats) or 1

        # Farben für Bars je nach Modus
        if self.stat_mode == 'dps':
            bar_base_col = QColor(150, 40, 40, 230)
            bar_highlight_col = QColor(210, 80, 80, 255)
        elif self.stat_mode == 'hps':
            bar_base_col = QColor(40, 130, 40, 230)
            bar_highlight_col = QColor(90, 200, 90, 255)
        else:
            bar_base_col = QColor(40, 40, 130, 230)
            bar_highlight_col = QColor(90, 90, 200, 255)

        # --- Gesamt-Summary über alle Skills vorberechnen ---
        total_hits_sum = sum(s['hits'] for s in stats)
        total_val_sum = sum(s['total'] for s in stats)
        overall_avg = (total_val_sum / total_hits_sum) if total_hits_sum else 0.0

        # --- Scroll-Grenzen berechnen ---
        visible_h = max(1, body_bottom - body_top)
        content_h = len(stats) * row_h
        max_scroll = max(0, content_h - visible_h)
        self._table_scroll = max(0.0, min(self._table_scroll, float(max_scroll)))

        # Startindex der ersten sichtbaren Zeile
        start_index = int(self._table_scroll // row_h) if max_scroll > 0 else 0
        offset_y = -(self._table_scroll % row_h) if max_scroll > 0 else 0.0

        # --- Zeilen zeichnen ---
        p.setFont(QFont("Arial", 9))
        y = body_top + offset_y

        for i in range(start_index, len(stats)):
            s = stats[i]
            if y >= body_bottom:
                break

            skill = s['skill']
            hits = s['hits']
            total_val = s['total']
            avg = s['avg']

            frac = total_val / max_val
            bar_w = int(bar_max_w * frac)

            bar_rect = QRect(bar_left, int(y) + 4, bar_w, row_h - 6)
            corner_radius = 3

            # Bar
            p.setPen(Qt.NoPen)
            p.setBrush(bar_base_col)
            p.drawRoundedRect(bar_rect, corner_radius, corner_radius)

            hi_rect = QRect(bar_rect.left(), bar_rect.top(),
                            bar_rect.width(), 4)
            p.setBrush(bar_highlight_col)
            p.drawRoundedRect(hi_rect, corner_radius, corner_radius)

            # Skill-Name
            p.setPen(Qt.white)
            skill_rect = QRect(bar_left + 4, int(y) + 2,
                            bar_max_w - 8, row_h)
            p.drawText(skill_rect,
                    Qt.AlignVCenter | Qt.AlignLeft, skill)

            # Zahlen-Spalten zentriert
            p.setPen(QColor(230, 230, 230))
            hits_rect = QRect(col_hits_x, int(y) + 2, col_hits_w, row_h)
            total_rect = QRect(col_total_x, int(y) + 2, col_total_w, row_h)
            avg_rect = QRect(col_avg_x, int(y) + 2, col_avg_w, row_h)

            p.drawText(hits_rect, Qt.AlignCenter, f"{hits}")
            p.drawText(total_rect, Qt.AlignCenter, f"{total_val:,}")
            p.drawText(avg_rect, Qt.AlignCenter, f"{int(avg):,}")

            y += row_h

        # --- primitive Scrollbar rechts (optional, optisch dezent) ---
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

        # --- Summary-Zeile (immer fest unten) ---
        sum_top = bottom_y - summary_block_h + 4

        p.setPen(header_border)
        p.drawLine(bar_left, sum_top, right, sum_top)
        sum_top += 4

        p.setFont(QFont("Arial", 9, QFont.Bold))
        p.setPen(header_text)

        sum_label_rect = QRect(bar_left, sum_top, bar_max_w, row_h)
        p.drawText(sum_label_rect,
                Qt.AlignVCenter | Qt.AlignLeft, "Summary")

        hits_sum_rect = QRect(col_hits_x, sum_top, col_hits_w, row_h)
        total_sum_rect = QRect(col_total_x, sum_top, col_total_w, row_h)
        avg_sum_rect = QRect(col_avg_x, sum_top, col_avg_w, row_h)

        p.drawText(hits_sum_rect, Qt.AlignCenter, f"{total_hits_sum}")
        p.drawText(total_sum_rect, Qt.AlignCenter, f"{total_val_sum:,}")
        p.drawText(avg_sum_rect, Qt.AlignCenter, f"{int(overall_avg):,}")

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
        
        self._rebuild_target_dropdown()
        self._refresh_view_from_mode()
        self._update_layout()
        self.update()  # force repaint to use new colors

    ###--- End: functionality functions and parsing routines ---###
    

    ###--- Start: helper functions for interaction with overlay ---###
    
    # --- Tail Lifecycle ---
    def _ensure_log_thread(self):
        # wenn Thread läuft: gut; Retry-Timer kann weiterlaufen oder gestoppt werden
        if self._tail_thread and self._tail_thread.is_alive():
            return
        path = get_latest_combat_log()
        if not path:
            # noch keine Datei gefunden – wir probieren es beim nächsten Retry wieder
            return
        self._current_log_path = path
        self._tail_should_run = True
        def _tail_loop(pth):
            try:
                enc = _detect_encoding(path)
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

                        try:
                            et = parsed[0]
                            if et == 'hit':
                                _, val, target, skill = parsed
                                self._on_hit(val, target, skill)
                                if DEBUG_PARSE:
                                    print(f"[DMG ] {line.strip()} -> {val} on {target} with {skill}")
                            elif et == 'heal':
                                if len(parsed) == 5:
                                    _, val, target, skill, rtype = parsed
                                else:
                                    _, val, target, skill = parsed
                                    rtype = None
                                self._on_heal(val, target, skill, rtype)
                                if DEBUG_PARSE:
                                    print(f"[HEAL] {line.strip()} -> {val} to {target} (skill={skill}, type={rtype})")
                            elif et == 'taken':
                                # 5-Tuple ('taken', amount, attacker, skill, dtype) – dtype optional
                                if len(parsed) == 5:
                                    _, val, attacker, skill, dtype = parsed
                                else:
                                    _, val, attacker, skill = parsed
                                    dtype = None
                                self._on_taken(val, attacker, skill, dtype)
                                if DEBUG_PARSE:
                                    print(f"[TAKE] {line.strip()} -> {val} from {attacker} with {skill} type={dtype}")
                        except Exception as e:
                            # damit eine einzelne fehlerhafte Zeile den Thread NICHT stoppt
                            if DEBUG_PARSE:
                                print(f"[ERR ] tail-loop: {e!r}")
                            continue
            except Exception:
                # still retry later if something goes wrong
                pass
        import threading
        self._tail_thread = threading.Thread(target=_tail_loop, args=(path,), daemon=True)
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
            if skill in AA_SKILLS: skill = "Autoattack"
        else:
            enemy_part = before_for; skill = "DoT damage"
        enemy = enemy_part.strip().rstrip(".")
        return ("hit", dmg, enemy, skill)

    def _parse_heal_line(self, line: str):
        """
        Liefert:
        ('heal', amount:int, target:str, skill:str, rtype:str|None)
        rtype ∈ {'Morale','Power'} wenn vorhanden.
        """
        text = line.strip()
        if not text:
            return None

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

    def _on_hit(self, dmg, enemy, skill):
        if not self.manual_running: return
        now = time.time()
        if self.manual_waiting:
            self.manual_waiting = False; self.manual_start_time = now
        rel_t = (now - self.manual_start_time) if self.manual_start_time else 0.0
        evt = {"time": rel_t, "dmg": dmg, "enemy": enemy, "skill": skill}
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
        if rtype:
            evt["rtype"] = rtype  # 'Morale' oder 'Power'
            self._append_evt('hps', evt)
            self._refresh_view_from_mode()
            return

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
        
        if hasattr(self, "analysis_window") and self.analysis_window.isVisible():
            self.analysis_window.close()
        
        if not self.manual_running:
            # --- START ---
            self.manual_running = True
            self.manual_waiting = True
            self.manual_start_time = None

            # Alle Aggregates & Anzeige zurücksetzen
            if hasattr(self, "_reset_all_modes"):
                self._reset_all_modes()
            else:
                # Fallback-Reset (falls Helper noch nicht eingefügt)
                self.total_damage = 0
                self.combat_time = 0.0
                self.max_hit = 0
                self.max_hit_skill = '--'
                self.current_enemy = '--'
                self.manual_events.clear()
                self.manual_matrix.clear()
                if hasattr(self, "modes"):
                    for k in ('dps', 'hps', 'dts'):
                        self.modes[k]['events'].clear()
                        self.modes[k]['total'] = 0
                        self.modes[k]['max'] = 0
                        self.modes[k]['max_skill'] = '--'
                if hasattr(self, "sel_target"):
                    self.sel_target = None

            # UI: Start-Button aktiv stylen
            self.start_stop_btn.setText("Stop")
            apply_style(self.start_stop_btn, bg=COLORS['button_active'], text_color="white", bold=True)

            # Tailer aktivieren
            self._ensure_log_thread()

            # Target-Dropdown neu (nur "Total" oder aus aktuellem Mode)
            if hasattr(self, "_rebuild_target_dropdown"):
                self._rebuild_target_dropdown()
            else:
                self.manual_combo.blockSignals(True)
                self.manual_combo.clear()
                self.manual_combo.addItem("Total")
                self.manual_combo.blockSignals(False)

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
            if hasattr(self, "_refresh_view_from_mode"):
                self._refresh_view_from_mode()
            else:
                self.update()

            return
        else:
            # --- STOP ---
            self.manual_running = False
            self.manual_waiting = False
            self.start_stop_btn.setText("Start")
            apply_style(self.start_stop_btn, bg=COLORS['button_noactive'], text_color=rgba(COLORS['line_col']))

            # Tailer im Manual-Mode beenden (spart IO). Du kannst ihn anlassen, wenn du willst.
            self._stop_log_thread()

            # Dropdown mit Zielen füllen
            self._rebuild_target_dropdown()

            # Combat-Time finalisieren (unverändert okay)
            if hasattr(self, 'modes'):
                any_events = any(self.modes[m]['events'] for m in ('dps','hps','dts'))
            else:
                any_events = bool(self.manual_events)

            # --- Snapshot bauen, nur wenn es wirklich Events gab ---
            if any_events:
                start_ts = time.localtime(time.time())
                ts_label = time.strftime("%Y-%m-%d %H:%M", start_ts)

                if hasattr(self, 'modes'):
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
                else:
                    # Fallback für alten Codepfad (nur ein Event-Stream)
                    enemies = sorted({e['enemy'] for e in self.manual_events})
                    enemy_label = enemies[0] if len(enemies) == 1 else ("Multi" if enemies else "--")
                    label = f"{ts_label} | {enemy_label}"
                    snap = {
                        'id': self.fight_seq,
                        'label': label,
                        'events': list(self.manual_events),
                        'max_hit': self.max_hit,
                        'max_hit_skill': self.max_hit_skill,
                        'duration': self.manual_events[-1]['time'] if self.manual_events else 0.0,
                    }

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
        # Laufzeit während Kampf
        if self.manual_running and not self.manual_waiting and self.manual_start_time:
            now = time.time()
            self.combat_time = now - self.manual_start_time
            self.update()
            
    # --- overwrite mouse wheel function for table scrolling
    
    def wheelEvent(self, event):
        """scrolling skill table with mouse wheel"""
        if not hasattr(self, "_table_top_y"):
            return super().wheelEvent(event)

        pos = event.pos()
        # Bereich der Tabelle: zwischen Header-Zeile und Summary-Block
        table_top = self._table_top_y
        row_h = 22

        bottom_y = self.height() - STARTSTOP_BTN_HEIGHT - FRAME_PADDING
        summary_block_h = row_h + 8
        body_top = table_top + 2 * row_h        # nach Header-Zeile
        body_bottom = bottom_y - summary_block_h - 4

        if not (body_top <= pos.y() <= body_bottom):
            # Mausrad außerhalb der Tabelle -> normal verarbeiten
            return super().wheelEvent(event)

        stats = self._build_skill_stats()
        if not stats:
            return

        visible_h = max(1, body_bottom - body_top)
        content_h = len(stats) * row_h
        max_scroll = max(0, content_h - visible_h)
        if max_scroll <= 0:
            return

        # Delta: 120 Einheiten pro "Raster" – wir scrollen 1 Zeile pro Raster
        steps = event.angleDelta().y() / 120.0
        self._table_scroll -= steps * row_h
        self._table_scroll = max(0.0, min(self._table_scroll, max_scroll))

        self.update()
        event.accept()
    
           
    def _copy_to_clipboard(self):
        # ---- Events je nach Code-Stand holen ----
        if hasattr(self, "modes"):  # neuer Multi-Mode-Stand
            evts = list(self._agg()['events'])
            sel = getattr(self, "sel_target", None)
            if sel:
                evts = [e for e in evts if e['enemy'] == sel]
            target_total_label = ("all allies" if self.stat_mode == 'hps'
                                else "all sources" if self.stat_mode == 'dts'
                                else "all targets")
            selected_label = sel or target_total_label
            # Dauer
            if not evts:
                duration = 0.0
            else:
                duration = (evts[-1]['time'] - evts[0]['time']) if sel and len(evts) > 1 else evts[-1]['time']
        else:  # älterer Stand (single stream + ComboBox)
            sel_txt = self.manual_combo.currentText()
            evts = list(self.manual_events) if sel_txt == "Total" else [e for e in self.manual_events if e['enemy'] == sel_txt]
            selected_label = ("all allies" if self.stat_mode == 'hps'
                            else "all sources" if self.stat_mode == 'dts'
                            else "all targets") if sel_txt == "Total" else sel_txt
            if not evts:
                duration = 0.0
            else:
                duration = (evts[-1]['time'] - evts[0]['time']) if sel_txt != "Total" and len(evts) > 1 else evts[-1]['time']

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
            
    def get_manual_matrix(self):
        return ["rel_time_s", "damage", "enemy", "skill"], list(self.manual_matrix) 
    
    
    
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
        Aggregiert Events des aktuellen Modes (+ evtl. Target-Filter)
        zu einer Liste von:
        { 'skill', 'hits', 'total', 'avg', 'rate' }
        """
        agg = self._agg()
        evts = list(agg['events'])

        # ggf. nach ausgewähltem Target filtern
        if self.sel_target:
            evts = [e for e in evts if e['enemy'] == self.sel_target]

        if not evts:
            return []

        stats = {}
        for e in evts:
            key = e['skill']
            s = stats.setdefault(key, {'skill': key, 'hits': 0, 'total': 0})
            s['hits'] += 1
            s['total'] += e['dmg']

        dur = self.combat_time or 1.0
        for s in stats.values():
            s['avg'] = s['total'] / s['hits'] if s['hits'] else 0.0
            s['rate'] = s['total'] / dur if dur > 0 else 0.0

        return sorted(stats.values(), key=lambda x: x['total'], reverse=True)

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

        # --- All targets ---
        if evts:
            # Dauer für "All" = bis letztes Event dieses Modes
            dur_all = evts[-1]['time']
            rate_all = int(agg['total'] / (dur_all or 1)) if dur_all else 0
            all_label = f"All targets   ({rate_all} {metric_short})"
        else:
            all_label = "All targets"

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
        self.total_damage = total
        self.combat_time = dur
        if mx_e:
            self.max_hit = mx_e['dmg']; self.max_hit_skill = mx_e.get('max_skill_override', mx_e['skill'])
        else:
            self.max_hit = agg['max'];  self.max_hit_skill = agg['max_skill']
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

    def _combat_dd_label_for_mode(self, snap):
        """Erzeugt den Text für das 'Select combat'-Dropdown je nach aktuellem Modus."""
        metric_short = {'dps': 'DPS', 'hps': 'HPS', 'dts': 'DTPS'}.get(self.stat_mode, 'DPS')
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
        self.total_damage = 0
        self.max_hit = 0
        self.max_hit_skill = '--'
        self.combat_time = 0.0
        self.current_enemy = '--'
        self.sel_target = None if hasattr(self, "sel_target") else None
        # Höhe wieder eher minimal halten
        self._auto_adjust_height()
        
    # --- mouse action ---
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_start = e.globalPos() - self.frameGeometry().topLeft(); e.accept()
    def mouseMoveEvent(self, e):
        if self._drag_start:
            self.move(e.globalPos() - self._drag_start); e.accept()
    def mouseReleaseEvent(self, e):
        self._drag_start = None; super().mouseReleaseEvent(e)

    def _compute_skill_stats(self):
        """
        Aggregiert nach Skill für den aktuellen Mode.
        Liefert Liste von Dicts mit:
        { 'skill': str, 'total': int, 'hits': int, 'avg': float }
        """
        evts = list(self._agg()['events'])
        if not evts:
            return []

        from collections import defaultdict
        sums = defaultdict(int)
        counts = defaultdict(int)

        for e in evts:
            s = e['skill']
            dmg = e['dmg']
            sums[s] += dmg
            counts[s] += 1

        stats = []
        for skill, total in sums.items():
            hits = counts[skill]
            avg = total / hits if hits else 0.0
            stats.append({
                'skill': skill,
                'total': total,
                'hits': hits,
                'avg': avg,
            })

        # nach total desc sortieren
        stats.sort(key=lambda s: s['total'], reverse=True)
        return stats

        
    def closeEvent(self, event):
        # Analysefenster schließen, falls noch offen
        if hasattr(self, "analysis_window") and self.analysis_window.isVisible():
            self.analysis_window.close()

        # Log-Tailer korrekt stoppen, damit kein Thread überlebt
        if hasattr(self, "_stop_log_thread"):
            self._stop_log_thread()

        super().closeEvent(event)

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
