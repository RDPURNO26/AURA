import sys

with open('gui.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Imports
code = code.replace('import multiprocessing as mp', 'import multiprocessing as mp\nimport psutil')

# 2. Resizable & Lite mode & initial size
init_repl = '''        self.title("AURA — Gesture Control Dashboard")
        self.configure(bg=BG_DARK)
        self.resizable(True, True)

        ram = psutil.virtual_memory().total / (1024**3)
        self.lite_mode = ram < 6.0

        # Set App Icon'''
code = code.replace('''        self.title("AURA — Gesture Control Dashboard")
        self.configure(bg=BG_DARK)
        self.resizable(False, False)

        # Set App Icon''', init_repl)

geo_repl = '''        # Window size and centering
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = int(sw * 0.8), int(sh * 0.8)
        self.minsize(700, 480)
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.overrideredirect(False)

        self.scale_factor = sw / 1920.0
        self._resize_timer = None
        self.bind("<Configure>", self._on_resize)'''
code = code.replace('''        # Window size and centering
        w, h = 1050, 820
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.overrideredirect(False)''', geo_repl)

# 3. Add font update methods and resize handler before _build_ui
methods = '''
    def _update_fonts(self):
        self.title_font.configure(size=max(16, int(28 * self.scale_factor)))
        self.subtitle_font.configure(size=max(8, int(11 * self.scale_factor)))
        self.gesture_font.configure(size=max(8, int(10 * self.scale_factor)))
        self.desc_font.configure(size=max(7, int(9 * self.scale_factor)))
        self.button_font.configure(size=max(10, int(14 * self.scale_factor)))
        self.small_font.configure(size=max(7, int(8 * self.scale_factor)))
        self.stat_val_font.configure(size=max(10, int(14 * self.scale_factor)))

    def _on_resize(self, event):
        if event.widget == self:
            if self._resize_timer is not None:
                self.after_cancel(self._resize_timer)
            self._resize_timer = self.after(100, self._handle_resize)

    def _handle_resize(self):
        w = self.winfo_width()
        self.scale_factor = max(0.5, w / 1920.0)
        self._update_fonts()
        self._redraw_current_hand()
        self._hover_launch(False)

    def _redraw_current_hand(self):
        if not hasattr(self, 'current_gesture_idx'): return
        name = self.gesture_keys[self.current_gesture_idx]
        gesture = GESTURES[name]
        pts = get_hand_pose(gesture, HAND_BASE)
        
        self.hand_canvas.update_idletasks()
        cw = self.hand_canvas.winfo_width() or 500
        ch = self.hand_canvas.winfo_height() or 340
        
        draw_hand_on_canvas(self.hand_canvas, pts, gesture["color"], cw//2, ch//2, min(cw, ch)*0.8)

    def _build_ui(self):'''
code = code.replace('    def _build_ui(self):', methods)


# 4. _build_ui layout changes
build_ui_find = '''    def _build_ui(self):
        # ── Header ──
        header = tk.Frame(self, bg=BG_DARK, height=90)
        header.pack(fill="x", padx=30, pady=(20, 0))
        header.pack_propagate(False)

        tk.Label(header, text="✦ AURA", font=self.title_font,
                 fg=ACCENT_LIGHT, bg=BG_DARK).pack(side="left")
        tk.Label(header, text="AI-powered User-hand Recognition & Automation",
                 font=self.subtitle_font, fg=TEXT_SECONDARY, bg=BG_DARK).pack(
                     side="left", padx=(15, 0), pady=(12, 0))

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
        left_panel.pack_propagate(False)'''

build_ui_repl = '''    def _build_ui(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Header ──
        header = tk.Frame(self, bg=BG_DARK, height=90)
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 0))

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
        tk.Frame(self, bg=BORDER, height=1).grid(row=1, column=0, sticky="ew", padx=30, pady=(10, 15))

        # ── Main content area ──
        content = tk.Frame(self, bg=BG_DARK)
        content.grid(row=2, column=0, sticky="nsew", padx=30)
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=38)
        content.grid_columnconfigure(1, weight=62)

        # ── Left Panel: Gestures & Settings ──
        left_panel = tk.Frame(content, bg=BG_DARK)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        left_panel.grid_rowconfigure(2, weight=1)'''

code = code.replace(build_ui_find, build_ui_repl)


# Right panel layout
code = code.replace('''        # ── Right Panel: Canvas & Telemetry ──
        right_panel = tk.Frame(content, bg=BG_DARK)
        right_panel.pack(side="right", fill="both", expand=True, padx=(20, 0))''',
'''        # ── Right Panel: Canvas & Telemetry ──
        right_panel = tk.Frame(content, bg=BG_DARK)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(15, 0))''')

# Bottom layout
code = code.replace('''        # ── Bottom bar ──
        bottom = tk.Frame(self, bg=BG_DARK)
        bottom.pack(fill="x", padx=30, pady=(15, 20))''',
'''        # ── Bottom bar ──
        bottom = tk.Frame(self, bg=BG_DARK)
        bottom.grid(row=3, column=0, sticky="ew", padx=30, pady=(15, 20))''')

# Button rewrite
code = code.replace('''    def _draw_button(self, canvas, text, color, w, h):
        canvas.delete("all")
        r = 12''',
'''    def _draw_button(self, canvas, text, color):
        canvas.update_idletasks()
        w = canvas.winfo_width() or 260
        h = canvas.winfo_height() or 50
        if w < 10: w = 260
        if h < 10: h = 50
        canvas.delete("all")
        r = max(6, int(min(w, h) * 0.2))''')

# Remove w, h params from all _draw_button calls
code = code.replace(', 260, 50)', ')')


# Multiprocessing lite mode args
code = code.replace('''cam = mp.Process(target=camera_process, args=(frame_q, self.stop_ev, SHM_NAME), daemon=True)
        med = mp.Process(target=mediapipe_process, args=(frame_q, lm_q, self.stop_ev, SHM_NAME), daemon=True)''',
'''cam = mp.Process(target=camera_process, args=(frame_q, self.stop_ev, SHM_NAME, self.lite_mode), daemon=True)
        med = mp.Process(target=mediapipe_process, args=(frame_q, lm_q, self.stop_ev, SHM_NAME, self.lite_mode), daemon=True)''')


# Fix canvas sizes in redraw
code = code.replace('''cw = 500; ch = 340
        draw_hand_on_canvas(self.hand_canvas, pts, gesture["color"], cw//2, ch//2, min(cw, ch)*0.8)''',
'''self._redraw_current_hand()''')

code = code.replace('''        pts = HAND_BASE
        cw = 500; ch = 340
        draw_hand_on_canvas(self.hand_canvas, pts, TEXT_DIM, cw//2, ch//2, min(cw, ch)*0.8)''',
'''        self.after(50, self._redraw_current_hand)''')

code = code.replace('''cw = 500; ch = 340
            scolor = STATE_COLORS.get(self.live_state, ACCENT)
            # Live landmarks are normalized
            pts = [(float(self.live_landmarks[i,0]), float(self.live_landmarks[i,1])) for i in range(21)]
            draw_hand_on_canvas(self.hand_canvas, pts, scolor, cw//2, ch//2, min(cw, ch)*0.8, phase=self.canvas_phase)''',
'''self.hand_canvas.update_idletasks()
            cw = self.hand_canvas.winfo_width() or 500
            ch = self.hand_canvas.winfo_height() or 340
            scolor = STATE_COLORS.get(self.live_state, ACCENT)
            # Live landmarks are normalized
            pts = [(float(self.live_landmarks[i,0]), float(self.live_landmarks[i,1])) for i in range(21)]
            draw_hand_on_canvas(self.hand_canvas, pts, scolor, cw//2, ch//2, min(cw, ch)*0.8, phase=self.canvas_phase)''')


with open('gui_new.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("done")
