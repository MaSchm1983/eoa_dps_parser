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
    FRAME_PADDING, DROPDOWN_HEIGHT, DROPDOWN_OFFSET, HIST_COM_DD_HEIGHT,
    MODE_AREA_HEIGHT, MODE_BTN_HEIGHT, MODE_BTN_WIDTH,
    BAR_HEIGHT, BAR_PADDING, BAR_TOP_OFFSET, 
    STAT_FRAME_HEIGHT, STARTSTOP_BTN_WIDTH, STARTSTOP_BTN_HEIGHT, 
    FONT_TITLE, FONT_SUBTITLE, FONT_BTN_TEXT,
    FONT_TEXT, FONT_TEXT_CLS_BTN, COLORS, AA_SKILLS
)
from combatAnalyseOverlay import CombatAnalyseOverlay


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

def get_latest_combat_log(folder=COMBAT_LOG_FOLDER):
    pattern = os.path.join(folder, "Combat_*.txt")
    files = glob.glob(pattern)
    return max(files, key=os.path.getmtime) if files else None


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
        
        self._update_layout()             # 5) update layout on interact function


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
        
        # --- animate feedback bar ---
        self.hit_pulse = 0.0               # 0..1 Energiewert für den Pulse-Strip
        self.hit_pulse_decay = 1.5         # bigger ==> faster decay
        self.recent_hits = []              # für p95-Berechnung (nur Werte, capped)
        self.recent_hits_cap = 200
        

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
        self.start_stop_btn.clicked.connect(self._toggle_startstop)

        # ── select targets for manual parsed combat ──
        self.manual_combo = QComboBox(self)
        self.manual_combo.setFont(FONT_TEXT)
        self.manual_combo.setFixedHeight(DROPDOWN_HEIGHT)
        #self.manual_combo.setFixedWidth(150)
        self.manual_combo.setStyleSheet("QComboBox{background:rgba(100,100,100,125);color:white;}")
        self.manual_combo.addItem("Total")
        self.manual_combo.currentIndexChanged.connect(self._on_manual_selection)

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
        self.analyse_btn.clicked.connect(self.open_analysis_overlay)
        
        
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
        
        # ------- kompakte Stats-Zeile -------
        bar_x, bar_y = x0 + BAR_PADDING, y0 + BAR_TOP_OFFSET
        bar_w = w0 - 2 * BAR_PADDING

        p.setFont(FONT_TEXT)
        fm = p.fontMetrics()
        p.setPen(COLORS['subtext'])

        left_txt  = f"Total damage: {self.total_damage}"
        right_txt = f"Duration: {self.combat_time:.2f}s"
        p.drawText(bar_x, bar_y, left_txt)
        right_w = fm.boundingRect(right_txt).width()
        p.drawText(bar_x + bar_w - right_w, bar_y, right_txt)

        # kleiner Abstand
        y_cursor = bar_y + fm.height() - 6

        # ------- Hit-Pulse-Strip (10px hoch) -------
        strip_h = 15
        # Hintergrund
        p.setBrush(COLORS['bar_bg']); p.setPen(Qt.NoPen)
        p.drawRect(bar_x, y_cursor, bar_w, strip_h)

        # Füllung
        pulse_col = {
            'dps': QColor(200, 65, 65, int(0.78*255)),
            'hps': QColor(65, 200, 65, int(0.78*255)),
            'dts': QColor(65, 65, 200, int(0.78*255)),
        }.get(self.stat_mode, COLORS['bar_fill'])

        pulse_w = int(bar_w * max(0.0, min(1.0, self.hit_pulse)))
        if pulse_w > 0:
            p.fillRect(bar_x, y_cursor, pulse_w, strip_h, pulse_col)
            # Glanzkante oben (wirkt „lebendiger“)
            p.fillRect(bar_x, y_cursor, pulse_w, 3, pulse_col.lighter(145))

        y_cursor += strip_h + 8

        # ------- Biggest-Hit-Zeile -------
        p.setPen(COLORS['subtext'])
        big_txt = f"Biggest hit: {self.max_hit} with {self.max_hit_skill}"
        p.drawText(bar_x, y_cursor + fm.ascent(), big_txt)
        y_cursor += fm.height() + 15

        # ------- saubere Trenner (unterhalb des Textes) -------
        p.fillRect(bar_x, y_cursor, bar_w, 1, COLORS['line_col'])

        # ------- saubere Trenner (unterhalb von select target dropdown) -------
        y_cursor += fm.height() + DROPDOWN_HEIGHT + 10
        p.fillRect(bar_x, y_cursor, bar_w, 1, COLORS['line_col'])
        # du kannst hier y_cursor weitergeben/verwenden, wenn unten noch Elemente kommen

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
                with open(pth, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(0, os.SEEK_END)
                    while self._tail_should_run:
                        line = f.readline()
                        if not line:
                            time.sleep(0.05)
                            continue
                        parsed = self._parse_line(line)
                        if not parsed:
                            continue
                        et, dmg, enemy, skill = parsed
                        if et == 'hit':
                            self._on_hit(dmg, enemy, skill)
                        if DEBUG_PARSE:
                            print(f"[PARSED] {line.rstrip()}  ->  dmg={dmg}, enemy='{enemy}', skill='{skill}'")
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
        """
        Zählt:
        - "You hit Goblin for 123 points with Swift Strike."
        - "The Lynx hits the Dourhand Scout with Surprise Attack for 282 points of Common damage to Morale."
        Rückgabe: ("hit", dmg:int, enemy:str, skill:str) oder None
        """
        text = line.strip()
        if not text:
            return None

        # an " hit " / " hits " trennen
        hit_kw = " hit " if " hit " in text else (" hits " if " hits " in text else None)
        if not hit_kw:
            return None
        try:
            actor, rest = text.split(hit_kw, 1)
        except ValueError:
            return None

        actor_lc = actor.strip().lower()
        if actor_lc.startswith("the "):
            actor_lc = actor_lc[4:].lstrip()

        # nur eigene Hits oder Pet-Hits
        is_you = actor_lc.startswith("you")
        is_pet = actor_lc in PET_NAMES
        if not (is_you or is_pet):
            return None

        # ggf. "the " vor Gegner entfernen
        if rest.lower().startswith("the "):
            rest = rest[4:].lstrip()

        # Schaden extrahieren
        if " for " not in rest or " points" not in rest:
            return None
        try:
            before_for, after_for = rest.rsplit(" for ", 1)
            dmg_token = after_for.split(" points", 1)[0]
            dmg = int(re.sub(r"[^\d]", "", dmg_token))  # erlaubt 1,234
        except Exception:
            return None

        # Enemy & Skill
        if " with " in before_for:
            enemy_part, skill_part = before_for.split(" with ", 1)
            skill = skill_part.strip().rstrip(".")
            if skill in AA_SKILLS:
            #if "Weapon Attack" in skill:
                skill = "Autoattack"
        else:
            enemy_part = before_for
            skill = "DoT damage"
        enemy = enemy_part.strip().rstrip(".")

        return ("hit", dmg, enemy, skill)

    # --- Manual-Hit Verarbeitung ---
    def _on_hit(self, dmg: int, enemy: str, skill: str):
        if not self.manual_running:
            return
        now = time.time()
        # Startzeit beim allerersten Treffer setzen
        if self.manual_waiting:
            self.manual_waiting = False
            self.manual_start_time = now            

        rel_t = (now - self.manual_start_time) if self.manual_start_time else 0.0

        evt = {"time": rel_t, "dmg": dmg, "enemy": enemy, "skill": skill}
        self.manual_events.append(evt)
        self.manual_matrix.append([rel_t, dmg, enemy, skill])

        # Anzeige aggregieren
        self.total_damage += dmg
        if dmg > self.max_hit:
            self.max_hit = dmg
            self.max_hit_skill = skill
        self.combat_time = rel_t
        self.current_enemy = "Total"
        
        # --- Pulse aufladen & Recent-Hits pflegen ---
        self.recent_hits.append(dmg)
        if len(self.recent_hits) > self.recent_hits_cap:
            self.recent_hits.pop(0)

        ref = self._dynamic_ref_value()
        # Anteil des Treffers relativ zur Referenz addieren; leichtes „Overcharge“ erlaubt
        self.hit_pulse = min(1.5, self.hit_pulse + min(1.0, dmg / ref))
        
        self.update()    
        
    
    def _toggle_startstop(self):
        if not self.manual_running:
            # --- START ---
            self.manual_running = True
            self.manual_waiting = True
            self.manual_start_time = None
            self.total_damage = 0
            self.combat_time = 0.0
            self.max_hit = 0
            self.max_hit_skill = '--'
            self.current_enemy = '--'
            self.manual_events.clear()
            self.manual_matrix.clear()
            self.start_stop_btn.setText("Stop")
            apply_style(self.start_stop_btn, bg=COLORS['button_active'], text_color="white", bold=True)

            # Tailer aktivieren
            self._ensure_log_thread()

            # Ziel-Dropdown leeren/aufbauen
            self.manual_combo.blockSignals(True)
            self.manual_combo.clear()
            self.manual_combo.addItem("Total")
            self.manual_combo.blockSignals(False)
            
            # select combat auf 'current' zurücksetzen
            self.PST_FGHT_DD.blockSignals(True)
            self.PST_FGHT_DD.clear()
            self.PST_FGHT_DD.addItem("current", userData=None)
            # ggf. frühere Kämpfe wieder anhängen:
            for it in self.fight_history[-10:][::-1]:  # letzte 10, neuestes oben
                self.PST_FGHT_DD.addItem(it['label'], userData=it['id'])
            self.PST_FGHT_DD.blockSignals(False)
            self.PST_FGHT_DD.currentIndexChanged.connect(self._on_select_combat_changed)
        else:
            # --- STOP ---
            self.manual_running = False
            self.manual_waiting = False
            self.start_stop_btn.setText("Start")
            apply_style(self.start_stop_btn, bg=COLORS['button_noactive'], text_color=rgba(COLORS['line_col']))

            # Tailer im Manual-Mode beenden (spart IO). Du kannst ihn anlassen, wenn du willst.
            self._stop_log_thread()

            # Dropdown mit Zielen füllen
            names = sorted({e['enemy'] for e in self.manual_events})
            self.manual_combo.blockSignals(True)
            self.manual_combo.clear()
            self.manual_combo.addItem("Total")
            for n in names:
                self.manual_combo.addItem(n)
            self.manual_combo.setCurrentIndex(0)
            self.manual_combo.blockSignals(False)

            # Combat-Time finalisieren (falls keine Hits: 0.0)
            if self.manual_events:
                self.combat_time = self.manual_events[-1]['time']
            else:
                self.combat_time = 0.0
                    # Snapshot bauen
            if self.manual_events:
                start_ts = time.localtime(time.time())
                ts_label = time.strftime("%Y-%m-%d %H:%M", start_ts)
                enemies = sorted({e['enemy'] for e in self.manual_events})
                enemy_label = enemies[0] if len(enemies) == 1 else "Multi"
                # total = sum(e['dmg'] for e in self.manual_events)
                # dps = int(total / (dur or 1))
                # label = f"{ts_label} | {enemy_label} | {total} / {dur:.1f}s (DPS {dps})"
                label = f"{ts_label} | {enemy_label}"

                snap = {
                    'id': self.fight_seq,
                    'label': label,
                    'events': list(self.manual_events),     # tiefe Kopie genügt hier
                    'max_hit': self.max_hit,
                    'max_hit_skill': self.max_hit_skill,
                    'duration': self.manual_events[-1]['time']
                }
                self.fight_seq += 1
                self.fight_history.append(snap)

                # Dropdown: "current" bleibt Index 0; neuen Eintrag darunter einfügen.
                self.PST_FGHT_DD.blockSignals(True)
                self.PST_FGHT_DD.insertItem(1, label, userData=snap['id'])
                self.PST_FGHT_DD.blockSignals(False)
                
            self.update()
       
    
    def _on_manual_selection(self):
        if self.manual_running or not self.manual_events:
            return
        sel = self.manual_combo.currentText()
        if sel == "Total":
            self.total_damage = sum(e['dmg'] for e in self.manual_events)
            self.combat_time = self.manual_events[-1]['time'] if self.manual_events else 0.0
            self.current_enemy = "Total"
            # Max-Hit global
            mx = max(self.manual_events, key=lambda e: e['dmg']) if self.manual_events else None
        else:
            evts = [e for e in self.manual_events if e['enemy'] == sel]
            self.total_damage = sum(e['dmg'] for e in evts)
            self.combat_time = (evts[-1]['time'] - evts[0]['time']) if len(evts) > 1 else 0.0
            self.current_enemy = sel
            mx = max(evts, key=lambda e: e['dmg']) if evts else None
        if mx:
            self.max_hit = mx['dmg']
            self.max_hit_skill = mx['skill']
        else:
            self.max_hit = 0
            self.max_hit_skill = '--'
        self.update()
    
       
    def _on_select_combat_changed(self, idx: int):
        txt = self.PST_FGHT_DD.currentText()
        if txt == "current":
            # zurück in den Live-Zustand – nichts weiter tun
            self.update()
            return

        # ID aus dem ausgewählten Dropdown-Eintrag lesen
        sel_id = self.PST_FGHT_DD.currentData()
        # passenden Snapshot finden
        item = next((it for it in self.fight_history if it['id'] == sel_id), None)
        if not item:
            return

        # View aus Snapshot rekonstruieren
        evts = item['events']
        self.manual_running = False
        self.manual_waiting = False
        self.manual_events = list(evts)
        self.manual_matrix = [[e['time'], e['dmg'], e['enemy'], e['skill']] for e in evts]
        self.total_damage = sum(e['dmg'] for e in evts)
        self.combat_time = item['duration']
        self.max_hit = item['max_hit']
        self.max_hit_skill = item['max_hit_skill']
        self.current_enemy = "Total"

        # Ziel-Dropdown füllen
        names = sorted({e['enemy'] for e in evts})
        self.manual_combo.blockSignals(True)
        self.manual_combo.clear()
        self.manual_combo.addItem("Total")
        for n in names:
            self.manual_combo.addItem(n)
        self.manual_combo.setCurrentIndex(0)
        self.manual_combo.blockSignals(False)

        # Pulse-Zustand für die Anzeige neutral setzen
        # (kein Spark/EMA mehr nötig)
        if hasattr(self, 'pulse_alpha'):
            self.pulse_alpha = 0.0
        if hasattr(self, 'hit_pulse'):
            self.hit_pulse = 0.0
        self.recent_hits = [e['dmg'] for e in evts][-getattr(self, 'recent_hits_cap', 200):]

        self.update()
    
    
    
    # --- runtime ticker ---
    def _tick(self):
        # Laufzeit während Kampf
        if self.manual_running and not self.manual_waiting and self.manual_start_time:
            now = time.time()
            self.combat_time = now - self.manual_start_time
            # animation bar tick decay
            dt = 0.1
            self.hit_pulse = max(0.0, self.hit_pulse * (1.0 - self.hit_pulse_decay * dt))

            self.update()
                
    # --- dynamic values for bar animation ---
    def _dynamic_ref_value(self):
        if self.recent_hits:
            s = sorted(self.recent_hits)
            p95 = s[int(0.95 * (len(s)-1))]
        else:
            p95 = 0
        return max(1, p95, 0.5 * (self.max_hit or 0))
            
            
    def _copy_to_clipboard(self):
        # Ausgabe je nach Auswahl
        sel = self.manual_combo.currentText()
        if sel == "Total":
            total = sum(e['dmg'] for e in self.manual_events)
            duration = self.manual_events[-1]['time'] if self.manual_events else 0.0
            target = "all targets"
        else:
            evts = [e for e in self.manual_events if e['enemy'] == sel]
            total = sum(e['dmg'] for e in evts)
            duration = (evts[-1]['time'] - evts[0]['time']) if len(evts) > 1 else 0.0
            target = sel
        dps = int(total / (duration or 1))
        QApplication.clipboard().setText(f"You dealt {total} damage over {duration:.1f}s to {target} (DPS: {dps})")        
            
    def get_manual_matrix(self):
        return ["rel_time_s", "damage", "enemy", "skill"], list(self.manual_matrix) 
        
    # --- mouse action ---
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_start = e.globalPos() - self.frameGeometry().topLeft(); e.accept()
    def mouseMoveEvent(self, e):
        if self._drag_start:
            self.move(e.globalPos() - self._drag_start); e.accept()
    def mouseReleaseEvent(self, e):
        self._drag_start = None; super().mouseReleaseEvent(e)

    # --- open analysis overlay ---
    def open_analysis_overlay(self):
        # Gather data you want to send (example structure, adapt as needed)
        enemy = self.current_enemy
        stat_mode = self.stat_mode
        total_time = self.combat_time
        skill_stats = [
            # Example: list of dicts, each for a skill (you’ll fill this out from your parsing later)
            # {'skill': 'Devastating Blow', 'total': 1234, 'dps': 432, ...},
        ]
        # Instantiate the analysis overlay, pass the stats
        self.analysis_window = CombatAnalyseOverlay(
            parent=self,   # makes it a child window, optional
            enemy=enemy,
            stat_mode=stat_mode,
            total_time=total_time,
            skill_stats=skill_stats
        )
        # Position it below the current overlay
        geo = self.geometry()
        self.analysis_window.move(geo.left(), geo.bottom() + 4)
        self.analysis_window.show()

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
