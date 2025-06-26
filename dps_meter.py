import tkinter as tk
import threading
import time
import re
import os
import glob
import glfw
from OpenGL.GL import *
from collections import deque

# Shared stats
start_time = None
last_hit_time = None
fight_active = False
frozen_dps = 0
frozen_total = 0
total_damage = 0
damage_events = deque()  # stores (timestamp, damage) for DPS calc
pending_stop_timer = None

fight_history = deque(maxlen=5)  # last 5 fights
current_enemy = "Unknown"
# Globals needed for dropdown updates
dropdown = None
selected_fight = None

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
                    update_stats(damage, enemy)
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

    # Save this fight to history
    fight_summary = {
        "enemy": current_enemy,
        "dps": int(frozen_dps),
        "total": frozen_total,
        "duration": int(duration)
    }
    fight_history.appendleft(fight_summary)
    
    dropdown["menu"].delete(0, "end")
    dropdown["menu"].add_command(label="Live", command=lambda: selected_fight.set("Live"))
    for f in fight_history:
        name = f["enemy"]
        dropdown["menu"].add_command(label=name, command=lambda n=name: selected_fight.set(n))

    fight_active = False


def cleanup_old_events():
    now = time.time()
    while damage_events and now - damage_events[0][0] > 1.0:
        damage_events.popleft()

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
    return end_time - start_time  # returns float seconds


def gui_loop():
    global dropdown, selected_fight

    root = tk.Tk()
    root.title("DPS Overlay")
    root.geometry("300x120+100+100")
    root.minsize(300, 120)
    root.maxsize(800, 400)
    root.resizable(True, True)
    root.configure(bg='grey')
    root.attributes('-alpha', 0.75)  # make whole window semi-transparent
    # root.overrideredirect(True)  # Disable if you want resizing

    selected_fight = tk.StringVar()
    selected_fight.set("Live")

    dropdown = tk.OptionMenu(root, selected_fight, "current")
    dropdown.configure(bg="grey", fg="white", highlightthickness=0, font=("Helvetica", 10))
    dropdown.pack(fill=tk.X, padx=5, pady=2)

    canvas = tk.Canvas(root, bg="black", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    # Bind drag
    def start_move(event):
        root.x = event.x
        root.y = event.y

    def stop_move(event):
        root.x = None
        root.y = None

    def on_motion(event):
        x = event.x_root - root.x
        y = event.y_root - root.y
        root.geometry(f'+{x}+{y}')

    for widget in (root, canvas, dropdown):
        widget.bind('<ButtonPress-1>', start_move)
        widget.bind('<ButtonRelease-1>', stop_move)
        widget.bind('<B1-Motion>', on_motion)

    # ✅ Define GUI update after canvas exists
    def update_gui():
        canvas.delete("all")
        canvas.update_idletasks()

        width = canvas.winfo_width()
        height = canvas.winfo_height()

        dps = get_dps()
        combat_time = get_combat_time()
        choice = selected_fight.get()

        if choice == "Live" or fight_active:
            display_total = total_damage if fight_active else frozen_total
            display_dps = get_dps()
            label = current_enemy if fight_active else "Last fight"
        else:
            for f in fight_history:
                if f["enemy"] == choice:
                    display_total = f["total"]
                    display_dps = f["dps"]
                    label = f"{f['enemy']} ({f['duration']}s)"
                    break

        bar_margin = 50
        max_bar_width = width - 2 * bar_margin
        bar_height = int(height * 0.3)
        bar_y = height // 2 - bar_height // 2
        bar_length = min(max_bar_width, display_dps * 2)

        font_size = max(10, height // 10)
        small_font_size = max(8, height // 12)

        canvas.create_rectangle(
            bar_margin,
            bar_y,
            bar_margin + bar_length,
            bar_y + bar_height,
            fill="lime",
            outline=""
        )

        canvas.create_text(width // 2, bar_y - font_size,
                           text=f"DPS: {int(display_dps)}",
                           fill="white",
                           font=("Helvetica", font_size, "bold"))

        canvas.create_text(width // 2, bar_y + bar_height + small_font_size,
                           text=f"Total: {int(display_total)}",
                           fill="gray",
                           font=("Helvetica", small_font_size))
        canvas.create_text((width // 2) + 100, bar_y - font_size,
                           text=f"Time: {combat_time:.2f}s", 
                           fill="gray", 
                           font=("Helvetica", small_font_size))

        root.after(100, update_gui)

    update_gui()
    root.mainloop()

def get_latest_combat_log(folder):
    pattern = os.path.join(folder, "Combat_*.txt")
    files = glob.glob(pattern)
    if not files:
        return None
    # Sort by last modification time (descending)
    latest = max(files, key=os.path.getmtime)
    return latest

# ----------------------
# STARTUP LOGIC BELOW
# ----------------------

folder = "C:/Users/manus/Documents/The Lord of the Rings Online"
LOG_FILE = get_latest_combat_log(folder)

if LOG_FILE:
    print("Using log file:", LOG_FILE)
    threading.Thread(target=tail_file, args=(LOG_FILE, update_stats), daemon=True).start()
    gui_loop()
else:
    print("No combat log found.")