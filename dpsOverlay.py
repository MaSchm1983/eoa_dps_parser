import configparser
import sys
import os, glob, re, time, threading
from collections import deque
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QComboBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QFont, QPen

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


def get_latest_combat_log(folder=COMBAT_LOG_FOLDER):
    pattern = os.path.join(folder, "Combat_*.txt")
    files = glob.glob(pattern)
    return max(files, key=os.path.getmtime) if files else None


# Styling & Layout
WINDOW_WIDTH = 400
MIN_HEIGHT = 250  # Increased height by 50
MAX_HEIGHT = 550
TITLE_BAR_HEIGHT = 40
BUTTON_SIZE = 30
FRAME_PADDING = 5
DROPDOWN_HEIGHT = 30
DROPDOWN_OFFSET = 15
BAR_HEIGHT = 20
BAR_PADDING = 10
BAR_TOP_OFFSET = 20

FONT_TITLE    = QFont('Arial', 16, QFont.Bold)
FONT_SUBTITLE = QFont('Arial', 12, QFont.Bold)
FONT_TEXT     = QFont('Arial', 11)

COLORS = {
    'background': QColor(170, 170, 170, int(0.5*255)),
    'title_bar':  QColor(210,  80,  80, int(0.7*255)),
    'title_line': QColor( 61,  61,  61, int(0.8*255)),
    'frame':      QColor( 95,  95,  95, int(0.8*255)),
    'frame_bg':   QColor(220, 220, 220, int(0.5*255)),  
    'bar_bg':     QColor(100, 100, 100, int(0.5*255)),
    'bar_fill':   QColor(200,  65,  65, int(0.8*255)),
    'text':       QColor( 25,  25,  25),
    'subtext':    QColor( 0,  0,  0),
    'white':      QColor(255, 255, 255, int(1.0*255)),
}

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._init_window()
        self._init_data()
        self._create_widgets()
        self._update_layout()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(100)
        self._start_log_thread()

    def _init_window(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(WINDOW_WIDTH)
        self.setMinimumHeight(MIN_HEIGHT)
        self.setMaximumHeight(MAX_HEIGHT)
        self.resize(WINDOW_WIDTH, MIN_HEIGHT)
        self.setMouseTracking(True)

    def _init_data(self):
        self.peak_dps = 0.0
        self.fill_ratio = 0.0
        self.total_damage = 0
        self.combat_time = 0.0
        self.current_enemy = ''
        self.fight_active = False
        self.start_time = None
        self.last_hit_time = None
        self.damage_events = deque()
        self.fight_history = deque(maxlen=4)
        self.pending_timer = None
        self.last_stop_time = None
        self._drag_start = None
        self._resizing = False
        self.peak_dps = 0.0
        self.peak_dps_displayed = False
        self.last_enemy_hits = {}  # New: track per-enemy hit times

    def _create_widgets(self):
        self.close_btn = QPushButton('X', self)
        self.close_btn.setFont(FONT_TEXT)
        self.close_btn.setFixedSize(BUTTON_SIZE, BUTTON_SIZE)
        self.close_btn.setFlat(True)
        border = COLORS['text'].name()
        self.close_btn.setStyleSheet(
            f"QPushButton{{color:white;background:transparent;"
            f"border:2px solid {border};border-radius:5px}}"
            "QPushButton:hover{background:rgba(61,61,61,80)}"
        )
        self.close_btn.clicked.connect(self.close)

        self.label = QLabel("Select combat:", self)
        self.label.setFont(FONT_SUBTITLE)
        self.label.setStyleSheet(f"color:{COLORS['text'].name()}")
        self.combo = QComboBox(self)
        self.combo.setFont(FONT_TEXT)
        self.combo.setFixedHeight(DROPDOWN_HEIGHT)
        self.combo.setStyleSheet("QComboBox{background:rgba(100,100,100,200);color:white;}")
        self.combo.addItem("current")
        self.combo.currentIndexChanged.connect(self.update)

        self.copy_button = QPushButton("Copy", self)
        self.copy_button.setFont(FONT_TEXT)
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

    def _update_close_btn_position(self):
        m = FRAME_PADDING
        self.close_btn.move(self.width() - BUTTON_SIZE - m, m)

    def _update_layout(self):
        y = TITLE_BAR_HEIGHT + DROPDOWN_OFFSET
        lblw = self.label.fontMetrics().boundingRect(self.label.text()).width()
        self.label.setGeometry(FRAME_PADDING, y, lblw, DROPDOWN_HEIGHT)
        x2 = FRAME_PADDING + lblw + DROPDOWN_OFFSET
        self.combo.setGeometry(x2, y, self.width() - x2 - FRAME_PADDING, DROPDOWN_HEIGHT)
        self._frame_y = y + DROPDOWN_HEIGHT + DROPDOWN_OFFSET
        self.copy_button.move(FRAME_PADDING, self.height() - 35)
        self._update_close_btn_position()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._draw_background(p)
        self._draw_title_bar(p)
        self._draw_frame(p)
        self._draw_bar_and_texts(p)

    def _draw_background(self, p):
        p.fillRect(self.rect(), COLORS['background'])

    def _draw_title_bar(self, p):
        p.fillRect(0, 0, self.width(), TITLE_BAR_HEIGHT, COLORS['title_bar'])
        p.fillRect(0, TITLE_BAR_HEIGHT - 2, self.width(), 3, COLORS['title_line'])
        p.setPen(COLORS['text'])
        p.setFont(FONT_TITLE)
        m = p.fontMetrics()
        yy = (TITLE_BAR_HEIGHT + m.ascent() - m.descent()) // 2 + m.descent() - 3
        p.drawText(FRAME_PADDING, yy, "EoA DPS parser beta 1.1")

    def _draw_frame(self, p):
        x, y = FRAME_PADDING, self._frame_y
        w = self.width() - 2 * FRAME_PADDING
        h = self.height() - self._frame_y - 50
        p.setBrush(COLORS['frame_bg'])
        p.setPen(Qt.NoPen)
        p.drawRect(x, y, w, h)
        p.setPen(QPen(COLORS['frame'], 2))
        p.setBrush(Qt.NoBrush)
        p.drawRect(x, y, w, h)
        self._bar_x = x + BAR_PADDING
        self._bar_w = w - 2 * BAR_PADDING
        self._bar_y = y + BAR_TOP_OFFSET

    def _draw_bar_and_texts(self, p):
        idx = self.combo.currentIndex()
        if idx == 0:
            enemy, duration, total = self.current_enemy, self.combat_time, self.total_damage
            ratio = self.fill_ratio
            show_peak = self.peak_dps_displayed
            peak_val = self.peak_dps
        else:
            s = self.fight_history[idx - 1]
            enemy    = s.get('enemy', 'unknown')
            total    = s.get('total', 0)
            duration = s.get('duration', 1)  # avoid div-by-zero
            avg_dps  = s.get('dps', 0) or 1
            peak_val = s.get('peak_dps', avg_dps) or avg_dps
            ratio = avg_dps / peak_val if peak_val > 0 else 0
            show_peak = True

        p.setFont(FONT_TEXT)
        p.setPen(COLORS['subtext'])
        p.drawText(self._bar_x, self._bar_y + 4, f"DPS parse: {enemy}")
        p.drawText(self._bar_x + self._bar_w - 100, self._bar_y + 4, f"Duration: {duration:.2f}s")
        p.drawText(self._bar_x, self._bar_y + BAR_HEIGHT + 28, f"Total damage: {total}")

        peak_str = f"Peak DPS: {int(peak_val)}" if show_peak else "Peak DPS: -"
        peak_val = self.peak_dps if idx == 0 else s.get('peak_dps', 0)
        fm = p.fontMetrics()
        text_w = fm.boundingRect(peak_str).width()
        p.drawText(self._bar_x + self._bar_w - text_w - 10, self._bar_y + BAR_HEIGHT + 28, peak_str)

        p.setPen(QPen(COLORS['frame'], 2))
        p.setBrush(COLORS['bar_bg'])
        p.drawRect(self._bar_x, self._bar_y + 10, self._bar_w, BAR_HEIGHT)
        p.fillRect(self._bar_x, self._bar_y + 10, int(self._bar_w * ratio), BAR_HEIGHT, COLORS['bar_fill'])

        dps = int(total / (duration or 1))
        p.setPen(COLORS['white'])
        p.drawText(self._bar_x + 5, self._bar_y + BAR_HEIGHT + 5, f"{dps} dps")

    def _start_log_thread(self):
        path = get_latest_combat_log()
        if not path:
            return
        self._running = True
        t = threading.Thread(target=self._tail_file, args=(path,), daemon=True)
        t.start()

    def _tail_file(self, path):
        with open(path) as f:
            f.seek(0, 2)
            while getattr(self, '_running', False):
                line = f.readline()
                if line:
                    et, dmg, en = self._parse_line(line)
                    if et == 'hit':
                        self._on_hit(dmg, en)
                else:
                    time.sleep(0.05)

    def _parse_line(self, line):
        m_def = re.search(r"defeated the\s+(.+?)\.", line, re.IGNORECASE)
        if m_def:
            return 'defeated', None, m_def.group(1)
        m_hit = re.search(r"You hit the\s+(.+?)\s+with.*?for\s+([\d,]+)", line, re.IGNORECASE)
        if m_hit:
            enemy = m_hit.group(1)
            dmg_str = m_hit.group(2).replace(',', '')
            try:
                dmg = int(dmg_str)
            except ValueError:
                return None, None, None
            return 'hit', dmg, enemy
        return None, None, None

    def _on_hit(self, dmg, en):
        now = time.time()
        self.last_enemy_hits[en] = now  # Update hit time
        self.copy_button.setEnabled(False)
        if not self.fight_active:
            if self.last_stop_time and (now - self.last_stop_time) < 2.0:
                return
            self.fight_active = True
            self.start_time = now
            self.current_enemy = en
            self.total_damage = 0
            self.damage_events.clear()
            self.peak_dps = 0.0
            self.peak_dps_displayed = False

        self.total_damage += dmg
        self.last_hit_time = now
        self.damage_events.append((now, dmg))

        self.combat_time = now - self.start_time
        window = 3.0
        cutoff = now - window
        while self.damage_events and self.damage_events[0][0] < cutoff:
            self.damage_events.popleft()
        win_dmg = sum(d for t, d in self.damage_events)
        win_dur = min(window, self.combat_time)
        if self.combat_time < 1.0:
            current_dps = 0  # or None, or skip updating peak
        else:
            current_dps = win_dmg / win_dur
            
        if current_dps > self.peak_dps:
            self.peak_dps = current_dps
            
        if self.combat_time >= 3.0:
            self.peak_dps_displayed = True
            
        self.fill_ratio = current_dps / self.peak_dps if self.peak_dps > 0 else 0
        self.update()
        
    def _stop_fight(self):
        self.fight_active = False
        self.combat_time = self.last_hit_time - self.start_time if self.last_hit_time else 0.0
        summary = {
            'enemy': self.current_enemy,
            'total': self.total_damage,
            'duration': self.combat_time,
            'dps': int(self.total_damage / (self.combat_time or 1)),
            'peak_dps': int(self.peak_dps),
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
        self.update()

    def _tick(self):
        if self.fight_active:
            now = time.time()
            self.combat_time = now - self.start_time
            last = self.last_enemy_hits.get(self.current_enemy, 0)
            if now - last > 3.5:
                self._stop_fight()
            else:
                self.combat_time = now - self.start_time
                if self.combat_time >= 3.0:
                    self.peak_dps_displayed = True
                self.update()

    def close(self):
        self._running = False
        super().close()

    def copy_to_clipboard(self):
        idx = self.combo.currentIndex()
        if idx == 0:
            total = self.total_damage
            duration = self.combat_time
            enemy = self.current_enemy
        else:
            if idx - 1 < len(self.fight_history):
                s = self.fight_history[idx - 1]
                total = s['total']
                duration = s['duration']
                enemy = s['enemy']
            else:
                return
        dps = int(total / (duration or 1))
        text = f"You dealt {total} over {duration:.1f}s to {enemy}. DPS: {dps}"
        QApplication.clipboard().setText(text)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        if e.y() >= self.height() - FRAME_PADDING:
            self._resizing = True
            self._resize_start = e.globalPos()
            self._start_height = self.height()
        else:
            self._drag_start = e.globalPos() - self.frameGeometry().topLeft()
        e.accept()

    def mouseMoveEvent(self, e):
        if not (e.buttons() & Qt.LeftButton):
            self.setCursor(Qt.SizeVerCursor if e.y() >= self.height() - FRAME_PADDING else Qt.ArrowCursor)
            return
        if self._resizing:
            delta = e.globalPos().y() - self._resize_start.y()
            new_h = max(MIN_HEIGHT, min(self._start_height + delta, MAX_HEIGHT))
            self.resize(WINDOW_WIDTH, new_h)
            self._update_layout()
        else:
            self.move(e.globalPos() - self._drag_start)
        e.accept()

    def mouseReleaseEvent(self, e):
        self._resizing = False
        self._drag_start = None
        super().mouseReleaseEvent(e)

    def resizeEvent(self, e):
        self._update_layout()
        super().resizeEvent(e)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ov = OverlayWindow()
    ov.show()
    sys.exit(app.exec_())

