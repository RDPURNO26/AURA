# aura_launcher.py
"""
AURA Launcher — Premium GUI with interactive gesture simulation.
Dark mode, animated, professional. Fully responsive layout.
Click 'Launch AURA' to start the gesture system.
"""

import tkinter as tk
from tkinter import font as tkfont
import subprocess
import sys
import os
import math
import time
import threading

# ── Lite Mode Detection ───────────────────────────────────────
LITE_MODE = False
try:
    import psutil
    total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    if total_ram_gb < 6.0:
        LITE_MODE = True
except ImportError:
    pass

# ── Color Palette ──────────────────────────────────────────────
BG_DARK      = "#0a0a0f"
BG_CARD      = "#12121a"
BG_CARD_HOVER = "#1a1a28"
ACCENT       = "#6c5ce7"
ACCENT_LIGHT = "#a29bfe"
ACCENT_GLOW  = "#8b7ff5"
GREEN        = "#00cec9"
GREEN_DARK   = "#00b894"
RED          = "#ff6b6b"
ORANGE       = "#fdcb6e"
TEXT_PRIMARY = "#f0f0f5"
TEXT_SECONDARY = "#8a8a9a"
TEXT_DIM     = "#555566"
BORDER       = "#2a2a3a"
LITE_BADGE   = "#ffb347"


# ── Hand Landmark Drawing ─────────────────────────────────────
HAND_BASE = [
    (0.50, 0.90), (0.45, 0.75), (0.38, 0.60), (0.32, 0.48), (0.27, 0.38),
    (0.43, 0.48), (0.42, 0.32), (0.41, 0.20), (0.40, 0.12),
    (0.50, 0.45), (0.50, 0.28), (0.50, 0.16), (0.50, 0.08),
    (0.57, 0.47), (0.58, 0.32), (0.59, 0.20), (0.60, 0.12),
    (0.63, 0.52), (0.65, 0.40), (0.67, 0.30), (0.68, 0.22),
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
    """Generate hand landmark positions for a given gesture."""
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


def draw_hand_on_canvas(canvas, pts, color, cx, cy, scale, tag_prefix="hand"):
    """Draw a hand skeleton on a tkinter canvas."""
    canvas.delete(tag_prefix)
    screen_pts = []
    for px, py in pts:
        sx = cx + (px - 0.5) * scale
        sy = cy + (py - 0.5) * scale
        screen_pts.append((sx, sy))
    line_w = max(1, int(scale / 150))
    for a, b in CONNECTIONS:
        x1, y1 = screen_pts[a]
        x2, y2 = screen_pts[b]
        canvas.create_line(x1, y1, x2, y2, fill=TEXT_DIM, width=line_w, tags=tag_prefix)
    for i, (sx, sy) in enumerate(screen_pts):
        r = max(2, int(scale / 60)) if i in (5, 9, 13, 17) else max(1, int(scale / 100))
        jcolor = color if i in (4, 8, 12, 16, 20) else TEXT_SECONDARY
        canvas.create_oval(sx-r, sy-r, sx+r, sy+r, fill=jcolor, outline="", tags=tag_prefix)


class AuraLauncher(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("AURA — Gesture Control Launcher")
        self.configure(bg=BG_DARK)
        self.resizable(True, True)
        self.minsize(700, 480)

        # ── Responsive: 80% of screen, centered ──
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = int(sw * 0.80)
        h = int(sh * 0.80)
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.overrideredirect(False)

        # Scale factor (reference: 1920px wide)
        self._win_w = w
        self._win_h = h
        self.scale = max(0.45, w / 1920.0)

        # ── Scaled fonts ──
        self.title_font = tkfont.Font(family="Segoe UI", size=self._fs(28), weight="bold")
        self.subtitle_font = tkfont.Font(family="Segoe UI", size=self._fs(11))
        self.gesture_font = tkfont.Font(family="Segoe UI", size=self._fs(10), weight="bold")
        self.desc_font = tkfont.Font(family="Segoe UI", size=self._fs(9))
        self.button_font = tkfont.Font(family="Segoe UI", size=self._fs(14), weight="bold")
        self.small_font = tkfont.Font(family="Segoe UI", size=self._fs(8))
        self.badge_font = tkfont.Font(family="Segoe UI", size=self._fs(7), weight="bold")

        self.aura_process = None
        self.selected_gesture = None
        self.gesture_keys = list(GESTURES.keys())
        self.current_gesture_idx = 0
        self.anim_phase = 0.0

        # Debounce resize
        self._resize_job = None

        self._build_ui()
        self._start_animation()

        # Bind resize with debounce
        self.bind("<Configure>", self._on_window_configure)

    def _fs(self, base):
        """Scale a font size by the window scale factor, with a minimum."""
        return max(7, int(base * self.scale))

    def _pad(self, base):
        """Scale padding/margin values."""
        return max(2, int(base * self.scale))

    def _on_window_configure(self, event):
        """Debounced resize handler — only fires 100ms after the last resize event."""
        if event.widget != self:
            return
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(100, self._handle_resize)

    def _handle_resize(self):
        """Recalculate scale factor and update fonts + layout on resize."""
        self._resize_job = None
        new_w = self.winfo_width()
        new_h = self.winfo_height()
        if new_w == self._win_w and new_h == self._win_h:
            return
        self._win_w = new_w
        self._win_h = new_h
        self.scale = max(0.45, new_w / 1920.0)

        # Update all font sizes
        self.title_font.configure(size=self._fs(28))
        self.subtitle_font.configure(size=self._fs(11))
        self.gesture_font.configure(size=self._fs(10))
        self.desc_font.configure(size=self._fs(9))
        self.button_font.configure(size=self._fs(14))
        self.small_font.configure(size=self._fs(8))
        self.badge_font.configure(size=self._fs(7))

        # Update gesture description wraplength
        right_w = int(new_w * 0.62)
        self.gesture_desc.configure(wraplength=max(150, right_w - self._pad(40)))

        # Update left panel scroll canvas width
        left_w = int(new_w * 0.38) - self._pad(60)
        card_w = max(200, left_w - 20)
        if hasattr(self, '_scroll_window_id'):
            self._scroll_canvas.itemconfigure(self._scroll_window_id, width=card_w)

        # Redraw button at new scale
        btn_w = max(160, int(new_w * 0.17))
        btn_h = max(36, int(new_h * 0.06))
        self.launch_btn.configure(width=btn_w, height=btn_h)
        self._update_launch_button_visuals()

        # Redraw hand
        self._redraw_current_hand()

    def _build_ui(self):
        p = self._pad

        # ── Header ──
        header = tk.Frame(self, bg=BG_DARK)
        header.pack(fill="x", padx=p(30), pady=(p(15), 0))

        tk.Label(header, text="✦ AURA", font=self.title_font,
                 fg=ACCENT_LIGHT, bg=BG_DARK).pack(side="left")
        tk.Label(header, text="AI-powered User-hand Recognition & Automation",
                 font=self.subtitle_font, fg=TEXT_SECONDARY, bg=BG_DARK).pack(
                     side="left", padx=(p(12), 0), pady=(p(8), 0))

        # Status badge area
        self.status_frame = tk.Frame(header, bg=BG_DARK)
        self.status_frame.pack(side="right", pady=(p(8), 0))

        # Lite mode badge
        if LITE_MODE:
            tk.Label(self.status_frame, text="⚡ Lite", font=self.badge_font,
                     fg=BG_DARK, bg=LITE_BADGE, padx=4, pady=1).pack(side="left", padx=(0, 8))

        self.status_dot = tk.Label(self.status_frame, text="●", font=self.desc_font,
                                    fg=TEXT_DIM, bg=BG_DARK)
        self.status_dot.pack(side="left")
        self.status_label = tk.Label(self.status_frame, text="Ready",
                                      font=self.desc_font, fg=TEXT_DIM, bg=BG_DARK)
        self.status_label.pack(side="left", padx=(4, 0))

        # ── Divider ──
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=p(30), pady=(p(8), p(10)))

        # ── Main content area (grid for proportional split) ──
        content = tk.Frame(self, bg=BG_DARK)
        content.pack(fill="both", expand=True, padx=p(30))
        content.columnconfigure(0, weight=38, minsize=250)
        content.columnconfigure(1, weight=62, minsize=300)
        content.rowconfigure(0, weight=1)

        # ── Left: Gesture cards (scrollable) ──
        left_frame = tk.Frame(content, bg=BG_DARK)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, p(10)))

        tk.Label(left_frame, text="GESTURE CONTROLS", font=self.gesture_font,
                 fg=TEXT_SECONDARY, bg=BG_DARK).pack(anchor="w", pady=(0, p(6)))

        self.card_frames = []

        self._scroll_canvas = tk.Canvas(left_frame, bg=BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(left_frame, orient="vertical", command=self._scroll_canvas.yview)
        cards_container = tk.Frame(self._scroll_canvas, bg=BG_DARK)

        self._scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._scroll_canvas.pack(side="left", fill="both", expand=True)

        left_w = int(self._win_w * 0.38) - p(60)
        card_w = max(200, left_w - 20)
        self._scroll_window_id = self._scroll_canvas.create_window(
            (0, 0), window=cards_container, anchor="nw", width=card_w)

        def _on_mousewheel(event):
            self._scroll_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        self._scroll_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        cards_container.bind(
            "<Configure>",
            lambda e: self._scroll_canvas.configure(
                scrollregion=self._scroll_canvas.bbox("all")
            )
        )

        for i, name in enumerate(self.gesture_keys):
            gesture = GESTURES[name]
            card = tk.Frame(cards_container, bg=BG_CARD, highlightbackground=BORDER,
                           highlightthickness=1, cursor="hand2")
            card.pack(fill="x", pady=2)

            inner = tk.Frame(card, bg=BG_CARD, padx=p(10), pady=p(5))
            inner.pack(fill="x")

            dot = tk.Label(inner, text="●", fg=gesture["color"], bg=BG_CARD,
                          font=self.desc_font)
            dot.pack(side="left", padx=(0, p(6)))

            name_label = tk.Label(inner, text=name.replace("\n", " — "),
                                  fg=TEXT_PRIMARY, bg=BG_CARD, font=self.gesture_font,
                                  anchor="w")
            name_label.pack(side="left", fill="x", expand=True)

            for widget in [card, inner, dot, name_label]:
                widget.bind("<Button-1>", lambda e, idx=i: self._select_gesture(idx))
                widget.bind("<Enter>", lambda e, c=card, inn=inner, d=dot, nl=name_label:
                           self._card_hover(c, inn, d, nl, True))
                widget.bind("<Leave>", lambda e, c=card, inn=inner, d=dot, nl=name_label:
                           self._card_hover(c, inn, d, nl, False))

            self.card_frames.append((card, inner, dot, name_label))

        # ── Right: Hand simulation canvas ──
        right_frame = tk.Frame(content, bg=BG_DARK)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(p(10), 0))

        self.sim_title = tk.Label(right_frame, text="Select a gesture to preview",
                                   font=self.gesture_font, fg=TEXT_SECONDARY, bg=BG_DARK)
        self.sim_title.pack(anchor="w", pady=(0, p(6)))

        self.hand_canvas = tk.Canvas(right_frame, bg=BG_CARD, highlightthickness=0)
        self.hand_canvas.pack(fill="both", expand=True)
        self.hand_canvas.bind("<Configure>", self._on_canvas_resize)

        self._draw_idle_hand()

        right_w = int(self._win_w * 0.62)
        self.gesture_desc = tk.Label(right_frame, text="",
                                      font=self.desc_font, fg=TEXT_SECONDARY,
                                      bg=BG_DARK, justify="left",
                                      wraplength=max(150, right_w - self._pad(40)))
        self.gesture_desc.pack(anchor="w", pady=(p(8), 0))

        # ── Bottom bar ──
        bottom = tk.Frame(self, bg=BG_DARK)
        bottom.pack(fill="x", padx=p(30), pady=(p(10), p(15)))

        btn_w = max(160, int(self._win_w * 0.17))
        btn_h = max(36, int(self._win_h * 0.06))
        self.launch_btn = tk.Canvas(bottom, width=btn_w, height=btn_h, bg=BG_DARK,
                                     highlightthickness=0, cursor="hand2")
        self.launch_btn.pack(side="right")
        self._is_running = False
        self._draw_button(self.launch_btn, "▶  LAUNCH AURA", ACCENT, btn_w, btn_h)
        self.launch_btn.bind("<Button-1>", self._toggle_launch)
        self.launch_btn.bind("<Enter>", lambda e: self._draw_button(
            self.launch_btn,
            "■  STOP AURA" if self._is_running else "▶  LAUNCH AURA",
            "#ff8888" if self._is_running else ACCENT_GLOW,
            self.launch_btn.winfo_width(), self.launch_btn.winfo_height()))
        self.launch_btn.bind("<Leave>", lambda e: self._draw_button(
            self.launch_btn,
            "■  STOP AURA" if self._is_running else "▶  LAUNCH AURA",
            RED if self._is_running else ACCENT,
            self.launch_btn.winfo_width(), self.launch_btn.winfo_height()))

        version_text = "AURA v4.0  •  Shared Memory IPC  •  One Euro Smoothing"
        if LITE_MODE:
            version_text += "  •  ⚡ Lite Mode"
        tk.Label(bottom, text=version_text,
                 font=self.small_font, fg=TEXT_DIM, bg=BG_DARK).pack(side="left")

        self._select_gesture(0)

    def _update_launch_button_visuals(self):
        """Redraw launch button with current state."""
        bw = self.launch_btn.winfo_width()
        bh = self.launch_btn.winfo_height()
        if bw < 10:
            return
        if self._is_running:
            self._draw_button(self.launch_btn, "■  STOP AURA", RED, bw, bh)
        else:
            self._draw_button(self.launch_btn, "▶  LAUNCH AURA", ACCENT, bw, bh)

    def _draw_button(self, canvas, text, color, w, h):
        canvas.delete("all")
        r = max(6, int(min(w, h) * 0.2))
        canvas.create_arc(0, 0, r*2, r*2, start=90, extent=90, fill=color, outline="")
        canvas.create_arc(w-r*2, 0, w, r*2, start=0, extent=90, fill=color, outline="")
        canvas.create_arc(0, h-r*2, r*2, h, start=180, extent=90, fill=color, outline="")
        canvas.create_arc(w-r*2, h-r*2, w, h, start=270, extent=90, fill=color, outline="")
        canvas.create_rectangle(r, 0, w-r, h, fill=color, outline="")
        canvas.create_rectangle(0, r, w, h-r, fill=color, outline="")
        canvas.create_text(w//2, h//2, text=text, fill="white", font=self.button_font)

    def _card_hover(self, card, inner, dot, label, entering):
        bg = BG_CARD_HOVER if entering else BG_CARD
        for w in [card, inner, dot, label]:
            w.configure(bg=bg)

    def _select_gesture(self, idx):
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
        self._redraw_current_hand()

    def _redraw_current_hand(self):
        if not hasattr(self, 'current_gesture_idx'):
            return
        name = self.gesture_keys[self.current_gesture_idx]
        gesture = GESTURES[name]
        pts = get_hand_pose(gesture, HAND_BASE)
        cw = self.hand_canvas.winfo_width() or 300
        ch = self.hand_canvas.winfo_height() or 250
        draw_hand_on_canvas(self.hand_canvas, pts, gesture["color"],
                           cw // 2, ch // 2, min(cw, ch) * 0.8)
        self.hand_canvas.delete("label")
        self.hand_canvas.create_text(cw // 2, max(15, int(ch * 0.06)),
                                      text=name.replace("\n", " — "),
                                      fill=gesture["color"], font=self.gesture_font,
                                      tags="label")

    def _on_canvas_resize(self, event):
        self._redraw_current_hand()

    def _draw_idle_hand(self):
        pts = HAND_BASE
        cw = self.hand_canvas.winfo_width() or 300
        ch = self.hand_canvas.winfo_height() or 250
        draw_hand_on_canvas(self.hand_canvas, pts, TEXT_DIM, cw // 2, ch // 2,
                           min(cw, ch) * 0.8)

    def _start_animation(self):
        """Subtle breathing glow animation on the status dot."""
        self.anim_phase += 0.05
        brightness = int(80 + 40 * math.sin(self.anim_phase))
        color = f"#{brightness:02x}{brightness:02x}{brightness + 20:02x}"
        if not self.aura_process:
            self.status_dot.configure(fg=color)
        self.after(50, self._start_animation)

    def _toggle_launch(self, event=None):
        if self.aura_process and self.aura_process.poll() is None:
            # Stop
            self._kill_aura_process()
            self._is_running = False
            self.status_dot.configure(fg=TEXT_DIM)
            self.status_label.configure(text="Ready", fg=TEXT_DIM)
            self._update_launch_button_visuals()
        else:
            # Launch
            try:
                if getattr(sys, 'frozen', False):
                    cmd = [sys.executable, "--run-aura"]
                else:
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    main_py = os.path.join(script_dir, "main.py")
                    cmd = [sys.executable, main_py]

                if LITE_MODE:
                    cmd.append("--lite")

                self.aura_process = subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
                self._is_running = True
                self.status_dot.configure(fg=GREEN)
                self.status_label.configure(text="Running", fg=GREEN)
                self._update_launch_button_visuals()
                threading.Thread(target=self._monitor_process, daemon=True).start()
            except Exception as e:
                self.status_label.configure(text=f"Error: {e}", fg=RED)

    def _kill_aura_process(self):
        if self.aura_process:
            try:
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.aura_process.pid)],
                               creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception:
                pass
            self.aura_process = None

    def _monitor_process(self):
        """Watch the AURA process and update UI if it exits."""
        if self.aura_process:
            self.aura_process.wait()
            self.after(0, self._on_process_exit)

    def _on_process_exit(self):
        self.aura_process = None
        self._is_running = False
        self.status_dot.configure(fg=TEXT_DIM)
        self.status_label.configure(text="Stopped", fg=ORANGE)
        self._update_launch_button_visuals()

    def destroy(self):
        self._kill_aura_process()
        super().destroy()


if __name__ == "__main__":
    app = AuraLauncher()
    app.mainloop()
