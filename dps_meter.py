import threading
import time
import re
import os
import glob
import glfw
from OpenGL.GL import *
from collections import deque
from OpenGL.GLUT import glutInit, glutBitmapCharacter, GLUT_BITMAP_HELVETICA_18

# --- Combat tracking globals ---
start_time = None
last_hit_time = None
fight_active = False
frozen_dps = 0
frozen_total = 0
total_damage = 0
damage_events = deque()
pending_stop_timer = None

fight_history = deque(maxlen=5)
current_enemy = "Unknown"

# Dropdown simulation for selected fight (can add keyboard control later)
selected_fight = "Live"

def parse_line(line):
    if "defeated" in line:
        return "defeated", None, None
    match = re.match(r"You hit the (.+?) with .*? for (\d+)", line, re.IGNORECASE)
    if match:
        enemy = match.group(1)
        damage = int(match.group(2))
        return "hit", damage, enemy
    return None, None, None

def tail_file(file_path, callback):
    global pending_stop_timer
    with open(file_path, "r") as f:
        f.seek(0, 2)
        while True:
            line = f.readline()
            if line:
                event_type, damage, enemy = parse_line(line)
                if event_type == "hit" and damage is not None:
                    if pending_stop_timer:
                        pending_stop_timer.cancel()
                        pending_stop_timer = None
                    callback(damage, enemy)
                elif event_type == "defeated":
                    if pending_stop_timer:
                        pending_stop_timer.cancel()
                    pending_stop_timer = threading.Timer(1.0, stop_fight)
                    pending_stop_timer.start()
            else:
                time.sleep(0.05)

def update_stats(damage, enemy):
    global total_damage, start_time, last_hit_time, fight_active, damage_events, current_enemy

    now = time.time()
    if not fight_active:
        total_damage = 0
        damage_events.clear()
        start_time = now
        current_enemy = enemy

    total_damage += damage
    damage_events.append((now, damage))
    last_hit_time = now
    fight_active = True

def stop_fight():
    global fight_active, frozen_dps, frozen_total, fight_history

    end_time = last_hit_time or start_time
    duration = max(1, end_time - start_time)
    frozen_dps = total_damage / duration
    frozen_total = total_damage

    fight_summary = {
        "enemy": current_enemy,
        "dps": int(frozen_dps),
        "total": frozen_total,
        "duration": int(duration)
    }
    fight_history.appendleft(fight_summary)

    # Optionally update dropdown menu here (if implemented)
    fight_active = False

def get_dps():
    if not start_time:
        return 0
    end_time = last_hit_time if fight_active else last_hit_time or start_time
    duration = end_time - start_time
    if duration <= 0:
        return 0
    return total_damage / duration

def get_combat_time():
    if not start_time:
        return 0.0
    end_time = last_hit_time if fight_active else last_hit_time or start_time
    return end_time - start_time

def draw_text(x, y, text, color=(1,1,1,1), font=GLUT_BITMAP_HELVETICA_18):
    glColor4f(*color)
    glRasterPos2f(x, y)
    for c in text:
        glutBitmapCharacter(font, ord(c))

# --- OpenGL helper functions ---
def draw_rect(x, y, w, h, color):
    glColor4f(*color)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + w, y)
    glVertex2f(x + w, y + h)
    glVertex2f(x, y + h)
    glEnd()
    
def draw_frame(x, y, w, h, color, thickness=2):
    glColor4f(*color)
    glLineWidth(thickness)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x, y)
    glVertex2f(x + w, y)
    glVertex2f(x + w, y + h)
    glVertex2f(x, y + h)
    glEnd()

def clamp(val, minval, maxval):
    return max(minval, min(val, maxval))

def main_loop():
    if not glfw.init():
        print("Failed to initialize GLFW")
        return

    glutInit()  # Initialize GLUT (for bitmap fonts)

    # Set initial window size and limits
    init_width, init_height = 400, 120
    min_width, min_height = 300, 100
    max_width, max_height = 800, 300

    window = glfw.create_window(init_width, init_height, "DPS Overlay OpenGL", None, None)
    if not window:
        glfw.terminate()
        print("Failed to create window")
        return

    glfw.make_context_current(window)
    glfw.set_window_attrib(window, glfw.FLOATING, True)

    # Enforce min/max window size
    glfw.set_window_size_limits(window, min_width, min_height, max_width, max_height)

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    global selected_fight

    while not glfw.window_should_close(window):
        w, h = glfw.get_framebuffer_size(window)
        glViewport(0, 0, w, h)

        # Grey background with 75% opacity
        glClearColor(0.2, 0.2, 0.2, 0.75)
        glClear(GL_COLOR_BUFFER_BIT)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, w, 0, h, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Stats update
        dps = get_dps()
        combat_time = get_combat_time()
        choice = selected_fight

        if choice == "Live" or fight_active:
            display_total = total_damage if fight_active else frozen_total
            display_dps = dps
            label = current_enemy if fight_active else "Last fight"
        else:
            display_total = 0
            display_dps = 0
            label = ""
            for f in fight_history:
                if f["enemy"] == choice:
                    display_total = f["total"]
                    display_dps = f["dps"]
                    label = f"{f['enemy']} ({f['duration']}s)"
                    break

        # Layout params scaling with window size
        bar_margin_x = int(w * 0.1)
        max_bar_width = w - 2 * bar_margin_x
        bar_height = int(h * 0.3)
        bar_y = h // 2 - bar_height // 2
        bar_length = min(max_bar_width, display_dps * 2)
        bar_length = max(0, bar_length)

        # Draw bar background (dark gray, semi-transparent)
        draw_rect(bar_margin_x, bar_y, max_bar_width, bar_height, (0.1, 0.1, 0.1, 0.5))

        # Draw progress bar fill (lime green, more opaque)
        draw_rect(bar_margin_x, bar_y, bar_length, bar_height, (0, 1, 0, 0.9))

        # Draw white frame around the bar
        draw_frame(bar_margin_x, bar_y, max_bar_width, bar_height, (1, 1, 1, 1), thickness=2)

        # Font sizes clamped and scaled with window height
        font_size = clamp(int(h * 0.12), 12, 24)
        small_font_size = clamp(int(h * 0.08), 8, 16)

        # Text vertical positions (centered for bar, below for others)
        text_y_center = bar_y + bar_height // 2 - font_size // 3
        text_y_below = bar_y - font_size - 5

        # DPS text inside the bar, black color
        text_x_dps = bar_margin_x + 5
        draw_text(text_x_dps, text_y_center, f"DPS: {int(display_dps)}", (0, 0, 0, 1))

        # Total damage right side of bar, gray text
        text_x_total = bar_margin_x + max_bar_width + 10
        draw_text(text_x_total, text_y_center, f"Total: {int(display_total)}", (0.8, 0.8, 0.8, 1))

        # Combat time below bar, light gray
        draw_text(bar_margin_x, text_y_below, f"Time: {combat_time:.2f}s", (0.7, 0.7, 0.7, 1))

        # Enemy label below time, yellow
        draw_text(bar_margin_x + 150, text_y_below, f"Enemy: {label}", (1, 1, 0, 1))

        glfw.swap_buffers(window)
        glfw.poll_events()
        time.sleep(0.1)

    glfw.terminate()

def get_latest_combat_log(folder):
    pattern = os.path.join(folder, "Combat_*.txt")
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)

if __name__ == "__main__":
    folder = "C:/Users/manus/Documents/The Lord of the Rings Online"
    LOG_FILE = get_latest_combat_log(folder)
    if LOG_FILE:
        print("Using log file:", LOG_FILE)
        threading.Thread(target=tail_file, args=(LOG_FILE, update_stats), daemon=True).start()
        main_loop()
    else:
        print("No combat log found.")