# gui.py
"""
AURA Dashboard — Tkinter Desktop Application.
Mirrors the visual design of the original bat launcher while keeping the
premium extra features (live telemetry, tuning sliders, gesture history, and real-time hand tracking).
"""

import tkinter as tk
from tkinter import font as tkfont
import multiprocessing as mp
import psutil
from multiprocessing import shared_memory
import sys
import os
import math
import time
import queue
import threading
from collections import deque

# ── Color Palette ──────────────────────────────────────────────
BG_DARK      = "#0d0d0d"
BG_CARD      = "#1e1e2e"
BG_CARD_HOVER = "#2a2a3e"
ACCENT       = "#00d4ff"
ACCENT_LIGHT = "#33ddff"
ACCENT_GLOW  = "#00b8e6"
GREEN        = "#00cec9"
GREEN_DARK   = "#00b894"
RED          = "#ff6b6b"
ORANGE       = "#fdcb6e"
PURPLE       = "#7c3aed"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#a0a0b0"
TEXT_DIM     = "#555566"
TEXT_MUTED   = "#666677"
BORDER       = "#2a2a3a"

STATE_COLORS = {
    "IDLE": TEXT_DIM, "MOVE": GREEN, "CLICKING": ACCENT,
    "DRAGGING": ORANGE, "SCROLLING": "#b388ff", "ZOOMING": "#ff4081",
    "CLUTCH": "#ffd600", "LOCKED": RED, "VOLUME": GREEN_DARK,
}

# ── Shared Memory & IPC ───────────────────────────────────────
SHM_NAME = "aura_frame_buffer"
FRAME_SIZE = 640 * 480 * 3


# ── Hand Landmark Drawing ─────────────────────────────────────
HAND_BASE = [
    (0.50, 0.90),  # 0: Wrist
    (0.45, 0.75),  # 1: Thumb CMC
    (0.38, 0.60),  # 2: Thumb MCP
    (0.32, 0.48),  # 3: Thumb IP
    (0.27, 0.38),  # 4: Thumb TIP
    (0.43, 0.48),  # 5: Index MCP
    (0.42, 0.32),  # 6: Index PIP
    (0.41, 0.20),  # 7: Index DIP
    (0.40, 0.12),  # 8: Index TIP
    (0.50, 0.45),  # 9: Middle MCP
    (0.50, 0.28),  # 10: Middle PIP
    (0.50, 0.16),  # 11: Middle DIP
    (0.50, 0.08),  # 12: Middle TIP
    (0.57, 0.47),  # 13: Ring MCP
    (0.58, 0.32),  # 14: Ring PIP
    (0.59, 0.20),  # 15: Ring DIP
    (0.60, 0.12),  # 16: Ring TIP
    (0.63, 0.52),  # 17: Pinky MCP
    (0.65, 0.40),  # 18: Pinky PIP
    (0.67, 0.30),  # 19: Pinky DIP
    (0.68, 0.22),  # 20: Pinky TIP
]

CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17),
]

GESTURES = {
    "Peace Sign\n(Move Cursor)": {
        "desc": "Index + Middle up\nCursor follows palm",
        "color": GREEN,
        "curled": [3, 4, 14, 15, 16, 18, 19, 20],
        "thumb_in": True,
    },
    "Left Click": {
        "desc": "Drop Index finger\n(Middle stays up)",
        "color": ORANGE,
        "curled": [3, 4, 6, 7, 8, 14, 15, 16, 18, 19, 20],
        "thumb_in": True,
    },
    "Right Click": {
        "desc": "Drop Middle finger\n(Index stays up)",
        "color": ORANGE,
        "curled": [3, 4, 10, 11, 12, 14, 15, 16, 18, 19, 20],
        "thumb_in": True,
    },
    "Fist\n(Drag & Drop)": {
        "desc": "All fingers down\nHold 0.3s to drag",
        "color": RED,
        "curled": [3, 4, 6, 7, 8, 10, 11, 12, 14, 15, 16, 18, 19, 20],
        "thumb_in": True,
    },
    "Scroll\n(3 Fingers)": {
        "desc": "Index + Middle + Ring\nJoystick-style scroll",
        "color": ACCENT_LIGHT,
        "curled": [3, 4, 18, 19, 20],
        "thumb_in": True,
    },
    "Zoom\n(Open Hand)": {
        "desc": "All fingers up\nJoystick-style zoom",
        "color": ACCENT,
        "curled": [],
        "thumb_in": False,
    },
    "Volume\n(L-Shape)": {
        "desc": "Thumb + Index out\nHand up/down = volume",
        "color": GREEN_DARK,
        "curled": [10, 11, 12, 14, 15, 16, 18, 19, 20],
        "thumb_in": False,
    },
    "Lock\n(Index+Pinky)": {
        "desc": "Index + Pinky up\nPauses all tracking",
        "color": RED,
        "curled": [3, 4, 10, 11, 12, 14, 15, 16],
        "thumb_in": True,
    },
    "Clutch\n(Pinky Only)": {
        "desc": "Pinky up only\nRecenter your hand",
        "color": "#00ffff",
        "curled": [3, 4, 6, 7, 8, 10, 11, 12, 14, 15, 16],
        "thumb_in": True,
    },
    "Double Click\n(Peace+Thumb)": {
        "desc": "Index + Middle + Thumb\nFires once",
        "color": ORANGE,
        "curled": [14, 15, 16, 18, 19, 20],
        "thumb_in": False,
    },
}

def get_hand_pose(gesture_data, hand_base):
    pts = [list(p) for p in hand_base]
    curled = set(gesture_data.get("curled", []))
    for idx in curled:
        if idx < len(pts):
            mcp_map = {6: 5, 7: 5, 8: 5, 10: 9, 11: 9, 12: 9,
                       14: 13, 15: 13, 16: 13, 18: 17, 19: 17, 20: 17,
                       3: 1, 4: 1}
            mcp = mcp_map.get(idx, 0)
            wx, wy = pts[0]
            mx, my = pts[mcp]
            pts[idx][0] = mx + (wx - mx) * 0.3
            pts[idx][1] = my + (wy - my) * 0.15 + 0.05
    if gesture_data.get("thumb_in", False):
        pts[3][0] = pts[2][0] + 0.04
        pts[3][1] = pts[2][1] + 0.08
        pts[4][0] = pts[3][0] + 0.03
        pts[4][1] = pts[3][1] + 0.06
    return pts

def draw_hand_on_canvas(canvas, pts, color, cx, cy, scale, tag_prefix="hand", phase=0.0):
    canvas.delete(tag_prefix)
    screen_pts = []
    for px, py in pts:
        sx = cx + (px - 0.5) * scale
        sy = cy + (py - 0.5) * scale
        screen_pts.append((sx, sy))

    pulse = 0.5 + 0.5 * math.sin(phase)
    
    # Glow logic if active (color is not TEXT_DIM)
    is_active = color != TEXT_DIM
    if is_active:
        for a, b in CONNECTIONS:
            x1, y1 = screen_pts[a]
            x2, y2 = screen_pts[b]
            canvas.create_line(x1, y1, x2, y2, fill=color, width=4, stipple="gray50", tags=tag_prefix)

    # Core lines
    for a, b in CONNECTIONS:
        x1, y1 = screen_pts[a]
        x2, y2 = screen_pts[b]
        canvas.create_line(x1, y1, x2, y2, fill=color if is_active else TEXT_DIM, width=2, tags=tag_prefix)

    # Joints
    for i, (sx, sy) in enumerate(screen_pts):
        r = 5 if i in (5, 9, 13, 17) else 3
        jcolor = color if is_active and i in (4, 8, 12, 16, 20) else (TEXT_SECONDARY if not is_active else color)
        canvas.create_oval(sx-r, sy-r, sx+r, sy+r, fill=jcolor, outline="", tags=tag_prefix)


class AuraDashboard(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("AURA — Gesture Control Dashboard")
        self.configure(bg=BG_DARK)
        self.resizable(True, True)

        ram = psutil.virtual_memory().total / (1024**3)
        self.lite_mode = ram < 6.0

        # Set App Icon
        icon_path = os.path.join(os.path.dirname(__file__), "app_icon.ico")
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, "app_icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        # Window size and centering
        w, h = 1050, 820
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.overrideredirect(False)

        # Fonts
        self.title_font = tkfont.Font(family="Segoe UI", size=28, weight="bold")
        self.subtitle_font = tkfont.Font(family="Segoe UI", size=11)
        self.gesture_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.desc_font = tkfont.Font(family="Segoe UI", size=9)
        self.button_font = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        self.small_font = tkfont.Font(family="Segoe UI", size=8)
        self.stat_val_font = tkfont.Font(family="Consolas", size=14, weight="bold")

        # Process management
        self.procs = []
        self.stop_ev = None
        self.gui_q = None
        self.shm = None
        self.running = False
        
        # Shared settings
        self.smooth_beta = mp.Value('d', 0.005)
        self.click_sens  = mp.Value('i', 3)
        self.zone_margin = mp.Value('d', 0.10)
        
        # Telemetry & History
        self.fps_times = deque(maxlen=30)
        self.history = deque(maxlen=6)
        self.prev_state = "IDLE"
        
        # Canvas phase
        self.anim_phase = 0.0
        self.canvas_phase = 0.0
        self.live_landmarks = None
        self.live_state = "IDLE"

        self.selected_gesture = None
        self.gesture_keys = list(GESTURES.keys())
        self.current_gesture_idx = 0

        self._build_ui()
        self._start_animation()
        self._poll_queue()

    def _build_ui(self):
        # ── Header ──
        header = tk.Frame(self, bg=BG_DARK, height=90)
        header.pack(fill="x", padx=30, pady=(20, 0))
        header.pack_propagate(False)

        tk.Label(header, text="✦ AURA", font=self.title_font,
                 fg=ACCENT_LIGHT, bg=BG_DARK).pack(side="left")
        tk.Label(header, text="AI-powered User-hand Recognition & Automation",
                 font=self.subtitle_font, fg=TEXT_SECONDARY, bg=BG_DARK).pack(
                     side="left", padx=(15, 0), pady=(12, 0))

        if getattr(self, "lite_mode", False):
            tk.Label(header, text="⚡ Lite Mode", font=self.gesture_font, fg=BG_DARK, bg=ORANGE, padx=6, pady=2).pack(side="left", padx=(15, 0), pady=(12, 0))

        # Status badge
        self.status_frame = tk.Frame(header, bg=BG_DARK)
        self.status_frame.pack(side="right", pady=(10, 0))
        self.status_dot = tk.Label(self.status_frame, text="●", font=self.desc_font, fg=TEXT_DIM, bg=BG_DARK)
        self.status_dot.pack(side="left")
        self.status_label = tk.Label(self.status_frame, text="Ready", font=self.desc_font, fg=TEXT_DIM, bg=BG_DARK)
        self.status_label.pack(side="left", padx=(4, 0))

        # ── Divider ──
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=30, pady=(10, 15))

        # ── Main content area ──
        content = tk.Frame(self, bg=BG_DARK)
        content.pack(fill="both", expand=True, padx=30)

        # ── Left Panel: Gestures & Settings ──
        left_panel = tk.Frame(content, bg=BG_DARK, width=380)
        left_panel.pack(side="left", fill="y")
        left_panel.pack_propagate(False)

        # Gesture Cards
        tk.Label(left_panel, text="GESTURE CONTROLS", font=self.gesture_font, fg=TEXT_SECONDARY, bg=BG_DARK).pack(anchor="w", pady=(0, 8))

        self.card_frames = []
        cards_container = tk.Frame(left_panel, bg=BG_DARK)
        cards_container.pack(fill="x")

        for i, name in enumerate(self.gesture_keys):
            gesture = GESTURES[name]
            card = tk.Frame(cards_container, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1, cursor="hand2")
            card.pack(fill="x", pady=1)  # reduced padding
            inner = tk.Frame(card, bg=BG_CARD, padx=12, pady=2)  # reduced inner padding
            inner.pack(fill="x")
            dot = tk.Label(inner, text="●", fg=gesture["color"], bg=BG_CARD, font=self.desc_font)
            dot.pack(side="left", padx=(0, 8))
            name_label = tk.Label(inner, text=name.replace("\n", " — "), fg=TEXT_PRIMARY, bg=BG_CARD, font=self.gesture_font, anchor="w")
            name_label.pack(side="left", fill="x", expand=True)

            for widget in [card, inner, dot, name_label]:
                widget.bind("<Button-1>", lambda e, idx=i: self._select_gesture(idx))
                widget.bind("<Enter>", lambda e, c=card, inn=inner, d=dot, nl=name_label: self._card_hover(c, inn, d, nl, True))
                widget.bind("<Leave>", lambda e, c=card, inn=inner, d=dot, nl=name_label: self._card_hover(c, inn, d, nl, False))

            self.card_frames.append((card, inner, dot, name_label))

        # Settings Sliders (Scrollable Canvas)
        tk.Frame(left_panel, bg=BG_DARK, height=15).pack()
        tk.Label(left_panel, text="TUNING", font=self.gesture_font, fg=TEXT_SECONDARY, bg=BG_DARK).pack(anchor="w", pady=(0, 6))
        
        settings_outer = tk.Frame(left_panel, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        settings_outer.pack(fill="both", expand=True, pady=(0, 5))
        
        settings_canvas = tk.Canvas(settings_outer, bg=BG_CARD, highlightthickness=0)
        settings_scrollbar = tk.Scrollbar(settings_outer, orient="vertical", command=settings_canvas.yview)
        settings_frame = tk.Frame(settings_canvas, bg=BG_CARD, padx=12, pady=10)

        settings_window = settings_canvas.create_window((0, 0), window=settings_frame, anchor="nw")

        def _configure_canvas(event):
            settings_canvas.configure(scrollregion=settings_canvas.bbox("all"))
        settings_frame.bind("<Configure>", _configure_canvas)

        def _configure_window(event):
            settings_canvas.itemconfigure(settings_window, width=event.width)
        settings_canvas.bind("<Configure>", _configure_window)

        settings_canvas.configure(yscrollcommand=settings_scrollbar.set)
        
        settings_canvas.pack(side="left", fill="both", expand=True)
        settings_scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            settings_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        settings_outer.bind("<Enter>", lambda e: settings_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        settings_outer.bind("<Leave>", lambda e: settings_canvas.unbind_all("<MouseWheel>"))

        self.sliders = {}
        self._add_tk_slider(settings_frame, "Smoothing β", 0.001, 0.05, 0.005, self.smooth_beta)
        self._add_tk_slider(settings_frame, "Click Frames", 1, 8, 3, self.click_sens)
        self._add_tk_slider(settings_frame, "Zone Margin %", 2, 25, 10, self.zone_margin)

        # ── Right Panel: Canvas & Telemetry ──
        right_panel = tk.Frame(content, bg=BG_DARK)
        right_panel.pack(side="right", fill="both", expand=True, padx=(20, 0))

        # Canvas Header
        self.sim_title = tk.Label(right_panel, text="Select a gesture to preview", font=self.gesture_font, fg=TEXT_SECONDARY, bg=BG_DARK)
        self.sim_title.pack(anchor="w", pady=(0, 8))

        # Hand Canvas
        self.hand_canvas = tk.Canvas(right_panel, bg=BG_CARD, highlightthickness=0, width=500, height=340)
        self.hand_canvas.pack(fill="both", expand=True)
        self._draw_idle_hand()

        # Gesture / Action Desc
        self.gesture_desc = tk.Label(right_panel, text="", font=self.desc_font, fg=TEXT_SECONDARY, bg=BG_DARK, justify="left", wraplength=450)
        self.gesture_desc.pack(anchor="w", pady=(8, 0))
        
        # Telemetry & History container (Wrapped in dark card)
        tele_hist_card = tk.Frame(right_panel, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        tele_hist_card.pack(fill="both", expand=True, pady=(15, 0))
        
        tele_hist = tk.Frame(tele_hist_card, bg=BG_CARD, padx=20, pady=15)
        tele_hist.pack(fill="both", expand=True)

        # Telemetry (Left side of bottom-right)
        tele_frame = tk.Frame(tele_hist, bg=BG_CARD)
        tele_frame.pack(side="left", fill="y", expand=True)
        tk.Label(tele_frame, text="TELEMETRY", font=self.gesture_font, fg=TEXT_SECONDARY, bg=BG_CARD).pack(anchor="w")
        
        stats_row = tk.Frame(tele_frame, bg=BG_CARD)
        stats_row.pack(anchor="w", pady=(15,0))
        
        self.lbl_fps, self.bar_fps = self._create_stat(stats_row, "FPS", "—")
        self.lbl_lat, self.bar_lat = self._create_stat(stats_row, "LATENCY", "—")
        self.lbl_conf, self.bar_conf = self._create_stat(stats_row, "CONFIDENCE", "—")

        # History (Right side of bottom-right)
        hist_frame = tk.Frame(tele_hist, bg=BG_CARD, width=280)
        hist_frame.pack(side="right", fill="y")
        hist_frame.pack_propagate(False)
        tk.Label(hist_frame, text="GESTURE HISTORY", font=self.gesture_font, fg=TEXT_SECONDARY, bg=BG_CARD).pack(anchor="w")
        
        self.hist_canvas = tk.Canvas(hist_frame, bg=BG_CARD, highlightthickness=0)
        self.hist_canvas.pack(fill="both", expand=True, pady=(10,0))

        # ── Bottom bar ──
        bottom = tk.Frame(self, bg=BG_DARK)
        bottom.pack(fill="x", padx=30, pady=(15, 20))

        # Launch button
        self.launch_btn = tk.Canvas(bottom, width=260, height=50, bg=BG_DARK, highlightthickness=0, cursor="hand2")
        self.launch_btn.pack(side="right")
        self._draw_button(self.launch_btn, "▶  LAUNCH AURA", PURPLE, 260, 50)
        self.launch_btn.bind("<Button-1>", self._toggle_launch)
        self.launch_btn.bind("<Enter>", lambda e: self._hover_launch(True))
        self.launch_btn.bind("<Leave>", lambda e: self._hover_launch(False))

        # Version info
        tk.Label(bottom, text="AURA v4.0  •  Shared Memory IPC  •  Tkinter + Live Telemetry",
                 font=self.small_font, fg=TEXT_DIM, bg=BG_DARK).pack(side="left")

        # Select first gesture by default
        self._select_gesture(0)

    def _create_stat(self, parent, label, default):
        f = tk.Frame(parent, bg=BG_CARD)
        f.pack(side="left", padx=(0, 30))
        tk.Label(f, text=label, font=self.small_font, fg=TEXT_DIM, bg=BG_CARD).pack(anchor="w")
        val_lbl = tk.Label(f, text=default, font=tkfont.Font(family="Consolas", size=18, weight="bold"), fg=ACCENT, bg=BG_CARD)
        val_lbl.pack(anchor="w", pady=(2, 0))
        
        bar_canvas = tk.Canvas(f, bg=BG_CARD, height=4, width=60, highlightthickness=0)
        bar_canvas.pack(anchor="w", pady=(2, 0))
        bar_canvas.create_rectangle(0, 0, 60, 4, fill=BORDER, outline="")
        bar = bar_canvas.create_rectangle(0, 0, 0, 4, fill=ACCENT, outline="")
        
        return val_lbl, (bar_canvas, bar)

    def _add_tk_slider(self, parent, label, mn, mx, default, mp_value):
        row = tk.Frame(parent, bg=BG_CARD)
        row.pack(fill="x", pady=8)
        
        tk.Label(row, text=label, font=self.desc_font, fg=TEXT_PRIMARY, bg=BG_CARD, width=12, anchor="w").pack(side="left")
        
        val_lbl = tk.Label(row, text=f"{default:.3f}", font=("Consolas", 10, "bold"), fg=ACCENT, bg=BG_CARD, width=6, anchor="e")
        val_lbl.pack(side="right", padx=(5, 0))

        sv = tk.DoubleVar(value=default)
        sl = tk.Scale(row, from_=mn, to=mx, resolution=(mx-mn)/100.0, orient="horizontal", 
                      variable=sv, showvalue=0, bg=BG_CARD, fg=ACCENT, highlightthickness=0, troughcolor=BORDER, sliderlength=15, width=12)
        sl.pack(side="left", fill="x", expand=True, padx=5)
        
        def on_change(*args):
            v = sv.get()
            val_lbl.config(text=f"{v:.3f}")
            if hasattr(mp_value, 'value'):
                mp_value.value = v
        sv.trace_add("write", on_change)
        self.sliders[label] = sv

    def _draw_button(self, canvas, text, color, _w=None, _h=None):
        canvas.update_idletasks()
        w = canvas.winfo_width() or 260
        h = canvas.winfo_height() or 50
        if w < 10: w = 260
        if h < 10: h = 50
        canvas.delete("all")
        r = max(6, int(min(w, h) * 0.2))
        canvas.create_arc(0, 0, r*2, r*2, start=90, extent=90, fill=color, outline="")
        canvas.create_arc(w-r*2, 0, w, r*2, start=0, extent=90, fill=color, outline="")
        canvas.create_arc(0, h-r*2, r*2, h, start=180, extent=90, fill=color, outline="")
        canvas.create_arc(w-r*2, h-r*2, w, h, start=270, extent=90, fill=color, outline="")
        canvas.create_rectangle(r, 0, w-r, h, fill=color, outline="")
        canvas.create_rectangle(0, r, w, h-r, fill=color, outline="")
        canvas.create_text(w//2, h//2, text=text, fill="white", font=self.button_font)

    def _hover_launch(self, entering):
        color = "#8b5cf6" if entering else PURPLE # Lighter purple for glow
        if self.running:
            color = "#ff8888" if entering else RED
        text = "■  STOP AURA" if self.running else "▶  LAUNCH AURA"
        self._draw_button(self.launch_btn, text, color, 260, 50)

    def _card_hover(self, card, inner, dot, label, entering):
        bg = BG_CARD_HOVER if entering else BG_CARD
        for w in [card, inner, dot, label]:
            w.configure(bg=bg)

    def _select_gesture(self, idx):
        if self.running: return # Disable manual selection while running
        self.current_gesture_idx = idx
        name = self.gesture_keys[idx]
        gesture = GESTURES[name]

        for i, (card, inner, dot, label) in enumerate(self.card_frames):
            if i == idx:
                card.configure(highlightbackground=gesture["color"], highlightthickness=2)
            else:
                card.configure(highlightbackground=BORDER, highlightthickness=1)

        self.sim_title.configure(text=name.replace("\n", " — "), fg=gesture["color"])
        self.gesture_desc.configure(text=gesture["desc"])

        pts = get_hand_pose(gesture, HAND_BASE)
        self.hand_canvas.update_idletasks()
        cw = self.hand_canvas.winfo_width() or 500
        ch = self.hand_canvas.winfo_height() or 340
        draw_hand_on_canvas(self.hand_canvas, pts, gesture["color"], cw//2, ch//2, min(cw, ch)*0.8)

    def _draw_idle_hand(self):
        pts = HAND_BASE
        self.hand_canvas.update_idletasks()
        cw = self.hand_canvas.winfo_width() or 500
        ch = self.hand_canvas.winfo_height() or 340
        draw_hand_on_canvas(self.hand_canvas, pts, TEXT_DIM, cw//2, ch//2, min(cw, ch)*0.8)

    def _start_animation(self):
        self.anim_phase += 0.05
        self.canvas_phase += 0.15
        
        # Breathing status dot
        brightness = int(80 + 40 * math.sin(self.anim_phase))
        color = f"#{brightness:02x}{brightness:02x}{brightness + 20:02x}"
        if not self.running:
            self.status_dot.configure(fg=color)
            
        # Live canvas update
        if self.running and self.live_landmarks is not None:
            self.hand_canvas.update_idletasks()
            cw = self.hand_canvas.winfo_width() or 500
            ch = self.hand_canvas.winfo_height() or 340
            scolor = STATE_COLORS.get(self.live_state, ACCENT)
            # Live landmarks are normalized
            pts = [(float(self.live_landmarks[i,0]), float(self.live_landmarks[i,1])) for i in range(21)]
            draw_hand_on_canvas(self.hand_canvas, pts, scolor, cw//2, ch//2, min(cw, ch)*0.8, phase=self.canvas_phase)
            
        # History animation
        if hasattr(self, 'hist_canvas'):
            self.hist_canvas.delete("all")
            if not self.history:
                self.hist_canvas.create_text(10, 20, text="Waiting for gestures...", fill=TEXT_MUTED, font=self.desc_font, anchor="w")
            else:
                now = time.time()
                for i, entry in enumerate(self.history):
                    target_y = i * 28 + 15
                    # Smooth approach for animation
                    entry["y"] += (target_y - entry["y"]) * 0.2
                    
                    y = entry["y"]
                    if y > 140: continue # off screen
                    
                    # "Xs ago"
                    ago = int(now - entry["ts"])
                    ago_str = f"{ago}s ago" if ago > 0 else "Just now"
                    
                    # Colored dot
                    self.hist_canvas.create_oval(5, y-4, 13, y+4, fill=entry["color"], outline="")
                    # Gesture name
                    self.hist_canvas.create_text(22, y, text=entry["state"], fill=TEXT_PRIMARY, font=self.desc_font, anchor="w")
                    # Time
                    self.hist_canvas.create_text(260, y, text=ago_str, fill=TEXT_MUTED, font=self.small_font, anchor="e")

        self.after(33, self._start_animation)

    def _poll_queue(self):
        if self.running and self.gui_q:
            try:
                while True:
                    lm, state, action, conf, ts = self.gui_q.get_nowait()
                    self._process_frame_data(lm, state, action, conf, ts)
            except queue.Empty:
                pass
        self.after(33, self._poll_queue)

    def _process_frame_data(self, lm, state, action, conf, ts):
        now = time.time()
        self.fps_times.append(now)
        if len(self.fps_times) > 1:
            dt = self.fps_times[-1] - self.fps_times[0]
            fps = (len(self.fps_times)-1) / max(dt, 0.001)
            self.lbl_fps.configure(text=f"{fps:.0f}")
            fw = min(60, max(0, (fps / 60.0) * 60))
            self.bar_fps[0].coords(self.bar_fps[1], 0, 0, fw, 4)
            
        lat = (now - ts) * 1000 if ts else 0
        self.lbl_lat.configure(text=f"{lat:.0f}ms")
        lw = min(60, max(0, ((100 - min(lat, 100)) / 100.0) * 60)) 
        self.bar_lat[0].coords(self.bar_lat[1], 0, 0, lw, 4)
        
        self.lbl_conf.configure(text=f"{conf*100:.0f}%")
        cw = min(60, max(0, conf * 60))
        self.bar_conf[0].coords(self.bar_conf[1], 0, 0, cw, 4)

        self.live_landmarks = lm
        self.live_state = state

        sc = STATE_COLORS.get(state, TEXT_DIM)
        self.sim_title.configure(text=f"STATE: {state}", fg=sc)
        self.gesture_desc.configure(text=f"Action: {action or 'STANDBY'}")

        if state != self.prev_state:
            self.history.appendleft({
                "state": f"{self.prev_state} → {state}",
                "ts": now,
                "color": sc,
                "y": -20  # Start position for drop-in animation
            })
            self.prev_state = state

    def _toggle_launch(self, event=None):
        if self.running:
            self._stop_aura()
        else:
            self._start_aura()

    def _start_aura(self):
        from camera_process import camera_process
        from mediapipe_process import mediapipe_process
        from controller_process import controller_process

        try:
            old = shared_memory.SharedMemory(name=SHM_NAME)
            old.close(); old.unlink()
        except: pass

        self.shm = shared_memory.SharedMemory(name=SHM_NAME, create=True, size=FRAME_SIZE)
        self.stop_ev = mp.Event()
        frame_q = mp.Queue(maxsize=1)
        lm_q = mp.Queue(maxsize=1)
        self.gui_q = mp.Queue(maxsize=2)

        cam = mp.Process(target=camera_process, args=(frame_q, self.stop_ev, SHM_NAME, self.lite_mode), daemon=True)
        med = mp.Process(target=mediapipe_process, args=(frame_q, lm_q, self.stop_ev, SHM_NAME, self.lite_mode), daemon=True)
        ctrl = mp.Process(target=controller_process, args=(lm_q, self.stop_ev, self.gui_q), daemon=True)

        self.procs = [("Camera", cam), ("MediaPipe", med), ("Controller", ctrl)]
        cam.start(); time.sleep(0.3); med.start(); time.sleep(0.2); ctrl.start()

        self.running = True
        self.status_dot.configure(fg=GREEN)
        self.status_label.configure(text="Running", fg=GREEN)
        self._hover_launch(False)

        # Deselect cards
        for card, inner, dot, label in self.card_frames:
            card.configure(highlightbackground=BORDER, highlightthickness=1)

    def _stop_aura(self):
        import subprocess
        if self.stop_ev: self.stop_ev.set()
        for name, p in self.procs:
            try: p.terminate(); p.join(2)
            except: pass
        for name, p in self.procs:
            if p.is_alive():
                try: subprocess.call(['taskkill','/F','/T','/PID',str(p.pid)], creationflags=0x08000000)
                except: pass
        if self.shm:
            try: self.shm.close(); self.shm.unlink()
            except: pass
            
        self.procs = []
        self.running = False
        self.live_landmarks = None
        self.gui_q = None
        
        self.status_dot.configure(fg=TEXT_DIM)
        self.status_label.configure(text="Stopped", fg=ORANGE)
        self.lbl_fps.configure(text="—")
        self.bar_fps[0].coords(self.bar_fps[1], 0, 0, 0, 4)
        self.lbl_lat.configure(text="—")
        self.bar_lat[0].coords(self.bar_lat[1], 0, 0, 0, 4)
        self.lbl_conf.configure(text="—")
        self.bar_conf[0].coords(self.bar_conf[1], 0, 0, 0, 4)
        self._hover_launch(False)
        self._select_gesture(self.current_gesture_idx)

    def destroy(self):
        self._stop_aura()
        super().destroy()


def main():
    import ctypes
    if sys.platform == 'win32':
        myappid = 'rdpurno26.aura.gesturecontrol.5'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    mp.set_start_method("spawn", force=True)
    app = AuraDashboard()
    app.mainloop()

if __name__ == "__main__":
    main()
