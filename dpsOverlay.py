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

import configparser
from datetime import datetime
import sys
import os, glob, re, time, threading
from collections import deque
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QComboBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QPen
from config import (
    WINDOW_WIDTH, MIN_HEIGHT, MAX_HEIGHT, TITLE_BAR_HEIGHT, BUTTON_SIZE,
    FRAME_PADDING, FRAME_HEIGHT, DROPDOWN_HEIGHT, DROPDOWN_OFFSET,
    SWITCH_AREA_HEIGHT, SWITCH_BTN_WIDTH, SWITCH_BTN_HEIGHT,
    BAR_HEIGHT, BAR_PADDING, BAR_TOP_OFFSET,
    MANUAL_EXTRA_HEIGHT, STARTSTOP_BTN_WIDTH, STARTSTOP_BTN_HEIGHT,
    FONT_TITLE, FONT_SUBTITLE, FONT_BTN_TEXT, FONT_TEXT, FONT_TEXT_CLS_BTN, COLORS
)

###############################################################################
####### Parse for config.ini where the path to combat log is located    #######
###############################################################################
'''
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

COMBAT_LOG_FOLDER = config.get('Settings','CombatLogFolder')
'''
COMBAT_LOG_FOLDER = "C:/Users/manus/Documents/The Lord of the Rings Online"
# ── Helper to read current combat log (will be updated every 5s later) ── 

def get_latest_combat_log(folder=COMBAT_LOG_FOLDER):
    pattern = os.path.join(folder, "Combat_*.txt")
    files = glob.glob(pattern)
    return max(files, key=os.path.getmtime) if files else None

###############################################################################
####### Main routine: building Overlay with widgets and add functions   #######
####### to all widgets. Will be cleaned up for first 1.0.0 release      #######
###############################################################################

class OverlayWindow(QWidget):
    """
    Main overlay window for live DPS parsing and manual runs.
    Features:
    - Automatic 'on-hit' DPS parsing
    - Manual start/stop DPS parsing
    - History of recent fights
    - Copy summary to clipboard
    """    
    # ── Initial window setup and update ──
    def __init__(self):
        super().__init__()
        self._init_window()
        self._init_data()
        self._create_widgets()
        self._update_layout()
        # ── Start file-watching every 5 seconds and UI update timers ── 
        self._current_log_path = None
        self._watch_timer = QTimer(self)
        self._watch_timer.timeout.connect(self._check_for_new_log)
        self._watch_timer.start(5000)
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(100)
        
        self._start_log_thread()

    # ------------ Window initialization ------------------
    def _init_window(self):
        
        ## ── Configure window appearance and fixed size ──
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(WINDOW_WIDTH)
        self.setMinimumHeight(MIN_HEIGHT)
        self.setMaximumHeight(MAX_HEIGHT)
        self.resize(WINDOW_WIDTH, MIN_HEIGHT)
        self.setMouseTracking(True)

    # ------------ Data initialization ------------------
    def _init_data(self):
        
        ## ── Initialize parsing state and buffers ──
        # ── Auto-mode state ──
        self.fight_active = False
        self.start_time = None
        self.last_hit_time = None
        self.last_stop_time = None
        self.damage_events = deque()
        self.last_enemy_hits = {}
        
        # ── Manual-mode state ──
        self.manual_running    = False
        self.manual_waiting = False
        self.manual_start_time = None
        self.manual_events     = []
        self.manual_history    = deque(maxlen=10)
        
        # ── Common stats ──        
        self.current_enemy = ''
        self.total_damage = 0
        self.combat_time = 0.0
        self.peak_dps = 0.0
        self.max_hit = 0
        self.max_hit_skill = "--"
        self.fill_ratio = 0.0        
        self.fight_history = deque(maxlen=5)
        
        self.pending_timer = None
        self._drag_start = None
        self._resizing = False

    # ------------ Widget Creation ------------------
    def _create_widgets(self):
        ## ── Instantiate buttons, labels, and dropdowns ──
        # ── Mode switch buttons ──
        self.btn_hit = QPushButton("Parse on hit", self)
        self.btn_hit.setFont(FONT_BTN_TEXT)
        self.btn_hit.setFixedSize(SWITCH_BTN_WIDTH, SWITCH_BTN_HEIGHT)
        
        self.btn_manual = QPushButton("Parse on start/stop", self)
        self.btn_manual.setFont(FONT_BTN_TEXT)
        self.btn_manual.setFixedSize(SWITCH_BTN_WIDTH, SWITCH_BTN_HEIGHT)

        # make them toggleable and wire up mode switching
        self.btn_hit.setCheckable(True)
        self.btn_manual.setCheckable(True)
        self.track_mode = 'hit'
        self.btn_hit.setChecked(True)
        self.btn_hit.clicked.connect(lambda: self._switch_mode('hit'))
        self.btn_manual.clicked.connect(lambda: self._switch_mode('manual'))
        
        # apply initial styles
        self._update_switch_styles()      
 
        # ── start/stop button (manual mode) ──
        self.start_stop_btn = QPushButton("Start", self)
        self.start_stop_btn.setFont(FONT_BTN_TEXT)
        self.start_stop_btn.setFixedSize(STARTSTOP_BTN_WIDTH, STARTSTOP_BTN_HEIGHT)
        # style like the switch buttons (inactive by default)
        btn_c = COLORS['line_col'] 
        rgba_btn = f"rgba({btn_c.red()},{btn_c.green()},{btn_c.blue()},{btn_c.alpha()})"
        c = COLORS['button_noactive']
        self.start_stop_btn.setStyleSheet(
            f"QPushButton{{"
              f"color: {rgba_btn};"
              f"background: rgba({c.red()},{c.green()},{c.blue()},{c.alpha()});"
              f"border: 2px solid {COLORS['line_col'].name()};"
              f"border-radius: 5px;"
            f"}}"
            "QPushButton:hover{background:rgba(61,61,61,80)}"
        )
        self.start_stop_btn.hide()
        self.start_stop_btn.clicked.connect(self._toggle_manual)
    
        # ── manual‐target dropdown (manual mode) ──
        self.manual_combo = QComboBox(self)
        self.manual_combo.setFont(FONT_TEXT)
        self.manual_combo.setFixedHeight(DROPDOWN_HEIGHT)
        self.manual_combo.setStyleSheet("QComboBox{background:rgba(100,100,100,200);color:white;}")
        self.manual_combo.hide()  
        # repaint whenever the user picks a different target
        self.manual_combo.currentIndexChanged.connect(self._on_manual_selection)
     
        # default selection styling (you can flesh this out later)
        self.btn_hit.setCheckable(True)
        self.btn_manual.setCheckable(True)
        self.btn_hit.setChecked(True)      
        
        # ── close button ──
        self.close_btn = QPushButton('X', self)
        self.close_btn.setFont(FONT_TEXT_CLS_BTN)
        self.close_btn.setFixedSize(BUTTON_SIZE, BUTTON_SIZE)
        self.close_btn.setFlat(True)
        border = COLORS['line_col'].name()
        self.close_btn.setStyleSheet(
            f"QPushButton{{"
                f"color: {rgba_btn};"
                f"background:transparent;"
                f"border:2px solid {border};"
                f"border-radius:5px;"
                f"}}"
            "QPushButton:hover{background:rgba(170,170,170,80)}"
        )
        self.close_btn.move(self.width() - BUTTON_SIZE - FRAME_PADDING, FRAME_PADDING)
        self.close_btn.clicked.connect(self.close)

        # ── past fights dropdown ──
        self.label = QLabel("Select combat:", self)
        self.label.setFont(FONT_SUBTITLE)
        self.label.setStyleSheet(f"color:{COLORS['text'].name()}")
        self.combo = QComboBox(self)
        self.combo.setFont(FONT_TEXT)
        self.combo.setFixedHeight(DROPDOWN_HEIGHT)
        self.combo.setStyleSheet("QComboBox{background:rgba(100,100,100,125);color:white;}")
        self.combo.addItem("current")
        self.combo.currentIndexChanged.connect(self._on_history_selected)

        # ── copy button ──
        self.copy_button = QPushButton("Copy", self)
        self.copy_button.setFont(FONT_BTN_TEXT)
        self.copy_button.setFixedSize(60, 25)
        self.copy_button.setStyleSheet(
            "QPushButton {"
            "  color: white;"
            "  background: transparent;"
            f"  border: 2px solid {COLORS['text'].name()};"
            "  border-radius: 5px;"
            "}"
            "QPushButton:hover {"
            "  background-color: rgba(61,61,61,80);"
            "}"
            "QPushButton:disabled {"
            "  color: gray; border-color: gray;"
            "}"
        )
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.copy_button.setEnabled(False)
        
        # ── enemy‐select dropdown (manual mode) ──
        self.enemy_combo = QComboBox(self)
        self.enemy_combo.setFont(FONT_TEXT)
        self.enemy_combo.setFixedHeight(DROPDOWN_HEIGHT)
        self.enemy_combo.setStyleSheet("QComboBox{background:rgba(100,100,100,200);color:white;}")
        # hidden until after a manual fight ends
        self.enemy_combo.hide()
        self.enemy_combo.currentIndexChanged.connect(self.update)

    def _update_layout(self):
        
        # ── switches and main dropdown ──
        switch_y = TITLE_BAR_HEIGHT + (SWITCH_AREA_HEIGHT - SWITCH_BTN_HEIGHT)//2
        self.btn_hit.move(FRAME_PADDING, switch_y)
        self.btn_manual.move(self.width() - FRAME_PADDING - SWITCH_BTN_WIDTH, switch_y)
        # everything below switch row gets pushed down by SWITCH_AREA_HEIGHT
        y = TITLE_BAR_HEIGHT + SWITCH_AREA_HEIGHT + DROPDOWN_OFFSET        
        lblw = self.label.fontMetrics().boundingRect(self.label.text()).width()
        self.label.setGeometry(FRAME_PADDING, y, lblw, DROPDOWN_HEIGHT)
        x2 = FRAME_PADDING + lblw + DROPDOWN_OFFSET
        self.combo.setGeometry(x2, y, self.width() - x2 - FRAME_PADDING, DROPDOWN_HEIGHT)
   
        # ── compute extra once ──
        extra = (DROPDOWN_HEIGHT + 5) \
          if (self.track_mode == 'manual'
              and not self.manual_running
              and self.enemy_combo.count()) \
          else 0
          
        # ── frame origin ──
        self._frame_y = y + DROPDOWN_HEIGHT + DROPDOWN_OFFSET + extra
                
        # ── place the enemy dropdown just below the first, only in manual mode ───
        if self.track_mode == 'manual' and not self.manual_running and self.enemy_combo.count():
            ex, ey = FRAME_PADDING, y + DROPDOWN_HEIGHT + 5
            self.enemy_combo.setGeometry(ex, ey, self.width() - 2*FRAME_PADDING, DROPDOWN_HEIGHT)
            self.enemy_combo.show()
        else:
            self.enemy_combo.hide()        
            
        # ── copy button ──
        frame_h = FRAME_HEIGHT + (MANUAL_EXTRA_HEIGHT if self.track_mode=='manual' else 0)
        cb_x = FRAME_PADDING
        cb_y = self._frame_y + frame_h + FRAME_PADDING
        self.copy_button.move(cb_x, cb_y)
        
        # ── position start/stop button inside frame if in manual mode ──
        if self.track_mode == 'manual':
            # just under “Total damage” (which is at _bar_y + BAR_HEIGHT + 28)
            y0 = self._bar_y + BAR_HEIGHT + 40
            x0 = self._bar_x
            # x0 = (self.width() - STARTSTOP_BTN_WIDTH) // 2
            self.start_stop_btn.move(x0, int(y0))
            self.start_stop_btn.show()
            # now place the manual‐target dropdown below it
            mc_x = self._bar_x
            mc_y = y0 + STARTSTOP_BTN_HEIGHT + 8
            mc_w = self._bar_w
            self.manual_combo.setGeometry(mc_x, mc_y, mc_w, DROPDOWN_HEIGHT)
            self.manual_combo.show()            
        else:
            self.start_stop_btn.hide()
            self.manual_combo.hide()
                  

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setRenderHint(QPainter.HighQualityAntialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        self._draw_background(p)
        self._draw_title_bar(p)
        # draw separator below the switch-button row
        sep_y = TITLE_BAR_HEIGHT + SWITCH_AREA_HEIGHT
        p.fillRect(0, sep_y - 2, self.width(), 3, COLORS['line_col'])    
            
        self._draw_frame(p)
        self._draw_bar_and_texts(p)

    def _draw_background(self, p):
        p.fillRect(self.rect(), COLORS['background'])

    def _draw_title_bar(self, p):
        p.fillRect(0, 0, self.width(), TITLE_BAR_HEIGHT, COLORS['title_bar'])
        p.fillRect(0, TITLE_BAR_HEIGHT - 2, self.width(), 3, COLORS['line_col'])
        p.setPen(COLORS['line_col'])
        p.setFont(FONT_TITLE)
        m = p.fontMetrics()
        yy = (TITLE_BAR_HEIGHT + m.ascent() - m.descent()) // 2 + m.descent() - 3
        p.drawText(FRAME_PADDING, yy, "EoA DPS parser beta 0.9.2")

    def _draw_frame(self, p):
        x, y = FRAME_PADDING, self._frame_y
        w = self.width() - 2 * FRAME_PADDING
        h = FRAME_HEIGHT + (MANUAL_EXTRA_HEIGHT if self.track_mode=='manual' else 0)
        p.setBrush(COLORS['frame_bg'])
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(x, y, w, h, 5, 5)
        p.setPen(QPen(COLORS['line_col'], 2))
        p.setBrush(Qt.NoBrush)
        p.drawRect(x, y, w, h)
        self._bar_x = x + BAR_PADDING
        self._bar_w = w - 2 * BAR_PADDING
        self._bar_y = y + BAR_TOP_OFFSET
    
    def _draw_bar_and_texts(self, p):
              # ───── compute display values ─────
        if self.track_mode == 'manual':
            max_hit       = self.max_hit
            max_hit_skill = self.max_hit_skill
            if self.manual_running:
                # during manual run: running numbers but no bar fill
                enemy    = "Total"
                enemy     = self.current_enemy
                duration  = self.combat_time
                total     = self.total_damage
                dps       = int(total / (duration or 1))
                peak_val  = self.peak_dps
                ratio     = ratio    = dps / peak_val if peak_val > 0 else 0
            else:
                # after manual run: use manual_combo selection
                sel = self.manual_combo.currentText()
                if sel == "Total":
                    enemy         = "Total"
                    total         = self.total_damage
                    duration      = self.combat_time
                    max_hit       = self.max_hit
                    max_hit_skill = self.max_hit_skill
                else:
                    evts          = [e for e in self.manual_events if e['enemy']==sel]
                    total         = sum(e['dmg'] for e in evts)
                    duration      = (evts[-1]['time'] - evts[0]['time']) if len(evts)>1 else 0.0
                    enemy         = sel
                    # recalc max per‐enemy if you like, else reuse global max
                    max_hit       = max((e['dmg'] for e in evts), default=self.max_hit)
                    max_hit_skill = next((e['skill'] for e in evts
                         if e['dmg'] == max_hit), self.max_hit_skill)
                dps      = int(total / (duration or 1))
                peak_val = self.peak_dps                  # ← grab your max ceiling
                ratio    = dps / peak_val if peak_val>0 else 0       
            
            self.max_hit       = max_hit
            self.max_hit_skill = max_hit_skill
        
            # stash for paintEvent()
            self._current_enemy   = enemy
            self._current_total   = total
            self._current_duration= duration
            self._current_dps     = dps
            self._current_peak    = peak_val
            self.fill_ratio       = ratio
            self.update() 
        else:
            idx = self.combo.currentIndex()
            if idx == 0:
                enemy     = self.current_enemy
                total     = self.total_damage
                duration  = self.combat_time
                ratio     = self.fill_ratio
                peak_val  = self.peak_dps
                dps       = int(total / (duration or 1))
            else:
                s         = self.fight_history[idx - 1]
                enemy     = s['enemy']
                total     = s['total']
                duration  = s['duration']
                dps       = s['dps']
                peak_val  = s['peak_dps']
                ratio     = dps / peak_val if peak_val > 0 else 0
 
        # ───── draw texts ─────
        p.setFont(FONT_TEXT)
        p.setPen(COLORS['subtext'])
        p.drawText(self._bar_x, self._bar_y + 4, f"DPS parse: {enemy}")
        p.drawText(self._bar_x + self._bar_w - 110, self._bar_y + 4, f"Duration: {duration:.2f}s")
        p.drawText(self._bar_x, self._bar_y + BAR_HEIGHT + 28, f"Total damage: {total}")
        max_str = f"Max hit: {self.max_hit}"
        fm      = p.fontMetrics()
        text_w  = fm.boundingRect(max_str).width()
        p.drawText(self._bar_x + self._bar_w - text_w - 10,
                   self._bar_y + BAR_HEIGHT + 28,
                   max_str)
        # now draw skill below it:
        skill_str = f"with {self.max_hit_skill}"
        fm2       = p.fontMetrics()
        w2        = fm2.boundingRect(skill_str).width()
        # offset by another line of text (e.g. +20px)
        p.drawText(self._bar_x + self._bar_w - w2 - 10,
                self._bar_y + BAR_HEIGHT + 28 + 20,
                skill_str)


        # ───── draw bar ─────
        p.setPen(QPen(COLORS['line_col'], 2))
        p.setBrush(COLORS['bar_bg'])
        p.drawRect(self._bar_x, self._bar_y + 10, self._bar_w, BAR_HEIGHT)
        p.fillRect(self._bar_x, self._bar_y + 10,
                   int(self._bar_w * ratio), BAR_HEIGHT,
                   COLORS['bar_fill'])

        # ───── draw DPS text ─────
        p.setPen(COLORS['white'])
        p.drawText(self._bar_x + 5, self._bar_y + BAR_HEIGHT + 5, f"{dps} dps")
        
        
    def _switch_mode(self, mode):
        
        self.track_mode = mode
        self.btn_hit.setChecked(mode == 'hit')
        self.btn_manual.setChecked(mode == 'manual')
        self._update_switch_styles()
        # resize window for manual mode
        new_h = MAX_HEIGHT if mode == 'manual' else MIN_HEIGHT
        self.resize(WINDOW_WIDTH, new_h)
        self._update_layout()  # reposition widgets
        # clear out any old DPS/timer stats when switching modes
        self._reset_frame_data()
        
        # if there’s a past run selected, re-enable Copy right away
        if mode == 'manual':
            # manual_combo has “Total combat” + each enemy if a run ended
            if self.manual_combo.count() > 1 and not self.manual_running:
                self.copy_button.setEnabled(True)
        else:  # hit-mode
            # “Select combat” combo has history entries
            if self.combo.count() > 1 and self.combo.currentIndex() > 0:
                self.copy_button.setEnabled(True)

        self.update()  # trigger repaint / layout     
 
    def _toggle_manual(self):
        if not self.manual_running:
            # → STARTING
            self.manual_running    = True
            self.manual_waiting    = True
            self.manual_start_time = None
            self.total_damage      = 0
            self.combat_time       = 0.0
            self.manual_events.clear()
            self.start_stop_btn.setText("Stop")
            # reset UI…
            self._reset_frame_data()
            self.manual_combo.blockSignals(True)
            self.manual_combo.clear()
            self.manual_combo.addItem("Total")
            self.manual_combo.blockSignals(False)
            self.copy_button.setEnabled(False)
        else:
            # → STOPPING
            self.manual_running = False
            self.manual_waiting = False
            self.start_stop_btn.setText("Start")
            # use last hit’s timestamp for combat_time
            if self.manual_events:
                last_rel = self.manual_events[-1]['time']
                self.combat_time = last_rel
            else:
                self.combat_time = 0.0
                
            # build summary entry
            total = sum(e['dmg'] for e in self.manual_events)
            summary = {
                'enemy':         f"Manual {datetime.now():%I:%M:%S %p}",
                'total':         total,
                'duration':      self.combat_time,
                'dps':           int(total/(self.combat_time or 1)),
                'max_hit':       self.max_hit,
                'max_hit_skill': self.max_hit_skill,
                'events':        list(self.manual_events),
            }
            self.fight_history.appendleft(summary)

            # repopulate dropdowns & enable copy
            self.combo.blockSignals(True)
            self.combo.clear()
            self.combo.addItem('current')
            for s in self.fight_history:
                self.combo.addItem(s['enemy'])
            self.combo.setCurrentIndex(0)
            self.combo.blockSignals(False)
            self._populate_manual_combo()
            self.copy_button.setEnabled(True)

        # update UI styles and repaint
        self._update_manual_styles()
        self._update_layout()
        self.update()

    def _update_manual_styles(self):
        # style the Start/Stop button based on running state
        self.style_button(
            self.start_stop_btn,
            'button_active' if self.manual_running else 'button_noactive'
        )     

    def _update_switch_styles(self):
        for btn, name in ((self.btn_hit, 'hit'), (self.btn_manual, 'manual')):
            active = (self.track_mode == name)
            self.style_button(
                btn,
                'button_active' if active else 'button_noactive'
            )     

    def _start_log_thread(self, path=None):
        # if caller didn’t specify, pick up the latest now
        path = path or get_latest_combat_log()
        if not path:
            return
        # remember it and begin tailing
        self._current_log_path = path        
        self._running = True
        t = threading.Thread(target=self._tail_file, args=(path,), daemon=True)
        t.start()

    def _tail_file(self, path):
        with open(path) as f:
            f.seek(0, 2)
            while getattr(self, '_running', False):
                line = f.readline()
                if line:
                    et, dmg, en, skl= self._parse_line(line)
                    if et == 'hit':
                        self._on_hit(dmg, en, skl)
                else:
                    time.sleep(0.05)

    def _parse_line(self, line):
        # “You hit … with SKILL for DAMAGE”
        m_hit = re.search(
            r"You (?:critically )?hit(?: the)?\s+(.+?)\s+with\s+(.+?)\s+for\s+([\d,]+)",
            line, re.IGNORECASE
        )
        if m_hit:
            enemy  = m_hit.group(1)
            skill  = m_hit.group(2)
            dmg_str = m_hit.group(3).replace(',', '')
            try:
                dmg = int(dmg_str)
            except ValueError:
                return None, None, None, None
            return 'hit', dmg, enemy, skill

        # fallback: other lines
        return None, None, None, None

    def _on_hit(self, dmg, en, skill):
        now = time.time()

        # ── If in Manual mode, only handle hits when running; otherwise ignore entirely ──
        if self.track_mode == 'manual':
            if not self.manual_running:
                return
            # on first hit after Start, begin the timer
            if self.manual_waiting:
                self.manual_waiting    = False
                self.manual_start_time = now
                self.start_time        = now
                self.combat_time       = 0.0
                self.current_enemy     = "Total"
                # leave total_damage=0 and manual_events empty until we append below
            return self._on_manual(dmg, en, skill)

        # ── AUTO MODE: first‐hit of a new fight ──
        if not self.fight_active:
            # ignore “echo” hits within 2s of last end
            if self.last_stop_time and (now - self.last_stop_time) < 2.0:
                return

            # initialize fight state from scratch
            self.fight_active         = True
            self.start_time           = now
            self.last_hit_time        = now
            self.current_enemy        = en
            self.total_damage         = 0
            self.damage_events.clear()
            self.peak_dps             = 0.0
            self.peak_dps_displayed   = False
            self.fill_ratio           = 0.0
            self.copy_button.setEnabled(False)

        # ── common per‐hit updates ──
        self.last_enemy_hits[en] = now
        self.total_damage       += dmg
        self.last_hit_time       = now
        if dmg > self.max_hit:
            self.max_hit = dmg
            self.max_hit_skill = skill

        # now your existing sliding‐window DPS and peak logic...
        self.combat_time = now - self.start_time
        window = 3.0
        cutoff = now - window
        while self.damage_events and self.damage_events[0][0] < cutoff:
            self.damage_events.popleft()
        self.damage_events.append((now, dmg))

        if self.combat_time >= 1.0:
            win_dmg = sum(d for t, d in self.damage_events)
            current_dps = win_dmg / min(window, self.combat_time)
            if current_dps > self.peak_dps:
                self.peak_dps = current_dps
        if self.combat_time >= 3.0:
            self.peak_dps_displayed = True

        self.fill_ratio = (self.peak_dps and ( (sum(d for t,d in self.damage_events)/min(window,self.combat_time)) / self.peak_dps )) or 0
        self.update()
        
 
    def _on_manual(self, dmg, en, skill):
        """
        Handle a hit while in Manual (start/stop) mode:
        - record timestamp, damage, and enemy name
        - update total_damage and elapsed time for display
        """
        now = time.time()
        # record the event
        self.manual_events.append({
            "time":  now - self.manual_start_time,
            "dmg":   dmg,
            "enemy": en,
            "skill": skill,
        })
        # accumulate damage
        self.total_damage += dmg
        if dmg > self.max_hit:
            self.max_hit = dmg
            self.max_hit_skill = skill
        # update timer and fill ratio for the bar
        self.combat_time = now - self.manual_start_time
        # you can choose to compute a running DPS or just raw totals here
        # e.g. current_dps = self.total_damage / (self.combat_time or 1)
        self.update()
     
    def _stop_fight(self):
        self.fight_active = False
        self.combat_time = self.last_hit_time - self.start_time if self.last_hit_time else 0.0
        summary = {
            'enemy': self.current_enemy,
            'total': self.total_damage,
            'duration': self.combat_time,
            'dps': int(self.total_damage / (self.combat_time or 1)),
            'peak_dps':    int(self.peak_dps),
            'max_hit':     self.max_hit,
            'max_hit_skill': self.max_hit_skill,            
        }
        
        self.fight_history.appendleft(summary)
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItem('current')
        for s in self.fight_history:
            self.combo.addItem(s['enemy'])
        self.combo.setCurrentIndex(0)
        self.combo.blockSignals(False)
        self.last_stop_time = time.time()
        self.combat_time = self.last_hit_time - self.start_time
        self.pending_timer = None
        self.copy_button.setEnabled(True)
        self.last_enemy_hits.clear()
        # populate enemy dropdown from manual_events
        # populate the manual‐mode dropdown with Total + each enemy
        if self.track_mode == 'manual':
            # gather unique enemy names
            names = sorted({e['enemy'] for e in self.manual_events})
            self.manual_combo.blockSignals(True)
            self.manual_combo.clear()
            self.manual_combo.addItem("Total")
            for nm in names:
                self.manual_combo.addItem(nm)
            self.manual_combo.setCurrentIndex(0)
            self.manual_combo.blockSignals(False)
        self.update()

    def _tick(self):
        # in manual mode, only update timer if running; skip auto-stop
        if self.track_mode == 'manual':
            if self.manual_running:
                now = time.time()
                # only update combat_time once we’ve recorded the first hit
                if self.manual_start_time is not None:
                    self.combat_time = now - self.manual_start_time
                # otherwise still waiting for first hit; combat_time stays at 0.0
                self.update()
            return
        # normal “on hit” auto-stop logic
        if self.fight_active:
            now = time.time()
            # update elapsed time
            self.combat_time = now - self.start_time
            # if no hit on this enemy for >3.5s, end the fight
            last = self.last_enemy_hits.get(self.current_enemy, 0)
            if now - last > 3.5:
                self._stop_fight()
            else:
                # still in fight; after 3s show peak, and repaint
                if self.combat_time >= 3.0:
                    self.peak_dps_displayed = True
                self.update()

    def close(self):
        self._running = False
        super().close()
        
    def _reset_frame_data(self):
        # zero out everything displayed in the frame
        self.combat_time        = 0.0
        self.total_damage       = 0
        self.fill_ratio         = 0.0
        self.peak_dps           = 0.0
        self.max_hit            = 0
        self.max_hit_skill      = "--"
        self.current_enemy      = '--'
        # also disable copy until next stop
        self.copy_button.setEnabled(False)
        self.update() 


    def _check_for_new_log(self):
        """Periodically called: if a newer Combat_*.txt exists, switch over."""
        new_path = get_latest_combat_log()
        # if nothing yet or still the same file, do nothing
        if not new_path or new_path == self._current_log_path:
            return
        # stop the old tail thread
        self._running = False
        # small delay to ensure the thread exits cleanly
        time.sleep(0.1)
        # clear any fight state
        self._reset_frame_data()
        # start tailing the new file
        self._start_log_thread(path=new_path)
 
    def _populate_manual_combo(self):
        """Fill manual_combo with 'Total combat' + each enemy after manual run."""
        names = sorted({e['enemy'] for e in self.manual_events})
        self.manual_combo.blockSignals(True)
        self.manual_combo.clear()
        self.manual_combo.addItem("Total")
        for nm in names:
            self.manual_combo.addItem(nm)
        self.manual_combo.setCurrentIndex(0)
        self.manual_combo.blockSignals(False)    
        # ensure the frame shows the “Total combat” values immediately
        # self._on_manual_selection(0)   
    
    def _on_history_selected(self, idx):
        if idx == 0:
            self._reset_frame_data()
            return

        # grab the summary for the chosen past run
        summary = self.fight_history[idx - 1]

        # detect manual vs auto by presence of events list
        is_manual = 'events' in summary

        # switch modes (this also resets frame and adjusts layout)
        self._switch_mode('manual' if is_manual else 'hit')

        if is_manual:
            self.manual_running    = False
            self.total_damage      = summary['total']
            self.combat_time       = summary['duration']
            # restore from the saved summary
            self.max_hit           = summary.get('max_hit', 0)
            self.max_hit_skill     = summary.get('max_hit_skill', "")
            self.manual_events     = list(summary['events'])
            self._populate_manual_combo()
        else:
            # restore auto‐mode stats
            self.current_enemy   = summary['enemy']
            self.total_damage    = summary['total']
            self.combat_time     = summary['duration']
            self.peak_dps        = summary['peak_dps']
            self.max_hit         = summary.get('max_hit', 0)
            self.max_hit_skill   = summary.get('max_hit_skill', "")
            # ensure the bar‐fill and texts redraw correctly
            # (you don’t need to repopulate manual combo here)
        
        # now that we’ve got valid data, enable Copy
        self.copy_button.setEnabled(True)
        # and repaint
        self.update()   
    
    
    def _on_manual_selection(self):
         # reflow the UI
         self._update_layout()

         # only when a run has finished (not while running)
         if not self.manual_running and self.manual_events:
             sel = self.manual_combo.currentText()
             # pick the events to scan
             if sel == "Total":
                 evts = self.manual_events
             else:
                 evts = [e for e in self.manual_events if e['enemy'] == sel]
 
             if evts:
                 # find the single largest hit in that subset
                 max_evt = max(evts, key=lambda e: e['dmg'])
                 self.max_hit       = max_evt['dmg']
                 self.max_hit_skill = max_evt.get('skill', "")
             else:
                 self.max_hit       = 0
                 self.max_hit_skill = ""

         # finally, redraw everything
         self.update()     

    def copy_to_clipboard(self):
        if self.track_mode == 'manual' and not self.manual_running and self.manual_combo.count():
            sel = self.manual_combo.currentText()
            if sel == "Total":
                total   = self.total_damage
                duration= self.combat_time
                enemy   = "all targets"
            else:
                evts = [e for e in self.manual_events if e['enemy'] == sel]
                total    = sum(e['dmg'] for e in evts)
                duration = (evts[-1]['time'] - evts[0]['time']) if len(evts) > 1 else 0.0
                enemy    = sel
            dps = int(total / (duration or 1))
        else:
            # your existing on-hit/history logic
            idx = self.combo.currentIndex()
            if idx == 0:
                total   = self.total_damage
                duration= self.combat_time
                enemy   = self.current_enemy
            else:
                s = self.fight_history[idx - 1]
                total    = s['total']
                duration = s['duration']
                enemy    = s['enemy']
            dps = int(total / (duration or 1))
        text = f"You dealt {total} damage over {duration:.1f}s to {enemy} (DPS: {dps})"
        QApplication.clipboard().setText(text)

    def style_button(self, btn, bgcolor, text_color='rgba(50,50,50,255)', hover_color="rgba(170,170,170,80)"):
        """Apply a uniform border, rounding, hover, and background color."""
        if isinstance(bgcolor, str):
            c = COLORS[bgcolor]
        else:
            c = bgcolor
        btn.setStyleSheet(
            f"QPushButton{{"
            f"  color: {text_color};"
            f"  background: rgba({c.red()},{c.green()},{c.blue()},{c.alpha()});"
            f"  border: 2px solid {COLORS['line_col'].name()};"
            f"  border-radius: 5px;"
            f"}}"
            f"QPushButton:hover{{background:{hover_color}}}"
        )     
        

    def mousePressEvent(self, e):
        # begin a window-drag when left button is pressed
        if e.button() != Qt.LeftButton:
            return
        # record offset between mouse and window top-left
        self._drag_start = e.globalPos() - self.frameGeometry().topLeft()
        e.accept()

    def mouseMoveEvent(self, e):
        # just dragging
        if self._drag_start is not None:
            self.move(e.globalPos() - self._drag_start)
        e.accept()

    def mouseReleaseEvent(self, e):
        # clear drag flag
        self._drag_start = None
        super().mouseReleaseEvent(e)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ov = OverlayWindow()
    ov.show()
    sys.exit(app.exec_())

