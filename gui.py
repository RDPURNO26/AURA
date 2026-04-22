"""
AURA Dashboard — PyQt6 Desktop Application.
Premium dark-mode gesture control dashboard with live hand visualization,
real-time stats, gesture history, system health, and tuning sliders.
"""
import sys, os, math, time, queue
import multiprocessing as mp
from multiprocessing import shared_memory
from collections import deque
from pathlib import Path

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QFrame, QSlider, QPushButton, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import (QPainter, QColor, QPen, QFont, QKeySequence,
    QLinearGradient, QRadialGradient, QShortcut)

# ── Palette ──────────────────────────────────────────────────
BG         = "#0f0f14"
BG_CARD    = "#161620"
BG_HEADER  = "#111118"
ACCENT     = "#00d4ff"
ACCENT_DIM = "#00698a"
GREEN      = "#00e676"
RED        = "#ff5252"
ORANGE     = "#ffab40"
YELLOW     = "#ffd600"
PURPLE     = "#b388ff"
MAGENTA    = "#ff4081"
PINK       = "#f48fb1"
TEXT       = "#e8e8f0"
TEXT_DIM   = "#7a7a8e"
TEXT_MUTED = "#44445a"
BORDER     = "#25253a"

STATE_COLORS = {
    "IDLE": "#555568", "MOVE": GREEN, "CLICKING": ACCENT,
    "DRAGGING": ORANGE, "SCROLLING": PURPLE, "ZOOMING": MAGENTA,
    "CLUTCH": YELLOW, "LOCKED": RED, "VOLUME": "#66bb6a",
}

CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),(0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),(5,9),(9,13),(13,17),
]

SHM_NAME = "aura_frame_buffer"
FRAME_SIZE = 640 * 480 * 3


# ═══════════════════════════════════════════════════════════════
#  Hand Skeleton Canvas with Glow
# ═══════════════════════════════════════════════════════════════
class HandCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.landmarks = None
        self.state = "IDLE"
        self.phase = 0.0
        self.setMinimumHeight(260)
        t = QTimer(self); t.timeout.connect(self._tick); t.start(33)

    def _tick(self):
        self.phase = (self.phase + 0.07) % (2 * math.pi)
        self.update()

    def set_data(self, lm, state):
        self.landmarks = lm; self.state = state

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background gradient
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor(BG_CARD)); grad.setColorAt(1, QColor(BG))
        p.fillRect(0, 0, w, h, grad)

        # Grid
        p.setPen(QPen(QColor(30, 30, 48), 1, Qt.PenStyle.DotLine))
        for i in range(1, 6):
            y = int(h * i / 6); p.drawLine(0, y, w, y)
        for i in range(1, 5):
            x = int(w * i / 5); p.drawLine(x, 0, x, h)

        # Scanning line
        sy = int(((time.time() * 0.8) % 1.0) * h)
        scan_grad = QLinearGradient(0, sy - 15, 0, sy + 15)
        scan_grad.setColorAt(0, QColor(0, 255, 100, 0))
        scan_grad.setColorAt(0.5, QColor(0, 255, 100, 40))
        scan_grad.setColorAt(1, QColor(0, 255, 100, 0))
        p.fillRect(0, sy - 15, w, 30, scan_grad)

        # Corner brackets
        L, th = 20, 2; cb = QColor(ACCENT_DIM)
        for cx, cy in [(8, 8), (w-8, 8), (8, h-8), (w-8, h-8)]:
            dx = L if cx < w//2 else -L; dy = L if cy < h//2 else -L
            p.setPen(QPen(cb, th))
            p.drawLine(cx, cy, cx+dx, cy); p.drawLine(cx, cy, cx, cy+dy)

        if self.landmarks is None:
            p.setPen(QPen(QColor(TEXT_MUTED))); f = QFont("Segoe UI", 11)
            p.setFont(f)
            p.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter,
                       "Waiting for hand…")
            p.end(); return

        lm = self.landmarks; color = QColor(STATE_COLORS.get(self.state, ACCENT))
        pulse = 0.5 + 0.5 * math.sin(self.phase)
        m = 25
        pts = [QPointF(m + lm[i][0]*(w-2*m), m + lm[i][1]*(h-2*m)) for i in range(21)]

        # Glow layer
        gc = QColor(color); gc.setAlpha(int(25 + 20*pulse))
        p.setPen(QPen(gc, 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for a, b in CONNECTIONS: p.drawLine(pts[a], pts[b])

        # Mid layer
        mc = QColor(color); mc.setAlpha(int(90 + 40*pulse))
        p.setPen(QPen(mc, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for a, b in CONNECTIONS: p.drawLine(pts[a], pts[b])

        # Core
        cc = QColor(color); cc.setAlpha(230)
        p.setPen(QPen(cc, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for a, b in CONNECTIONS: p.drawLine(pts[a], pts[b])

        # Joints
        for i, pt in enumerate(pts):
            p.setPen(Qt.PenStyle.NoPen)
            if i in (5, 9, 13, 17):
                gj = QColor(ACCENT); gj.setAlpha(int(35+25*pulse))
                p.setBrush(gj); p.drawEllipse(pt, 9, 9)
                p.setBrush(QColor(ACCENT)); p.drawEllipse(pt, 5, 5)
                p.setBrush(QColor(255,255,255,180)); p.drawEllipse(pt, 2, 2)
            elif i in (4, 8, 12, 16, 20):
                gj = QColor(color); gj.setAlpha(int(45+25*pulse))
                p.setBrush(gj); p.drawEllipse(pt, 7, 7)
                p.setBrush(color); p.drawEllipse(pt, 4, 4)
            else:
                p.setBrush(QColor(TEXT_DIM)); p.drawEllipse(pt, 3, 3)
        p.end()


# ═══════════════════════════════════════════════════════════════
#  Data Bridge Thread
# ═══════════════════════════════════════════════════════════════
class DataBridge(QThread):
    frame = pyqtSignal(object, str, object, float, float)

    def __init__(self, gui_q, stop_ev):
        super().__init__(); self.q = gui_q; self.stop = stop_ev

    def run(self):
        while not self.stop.is_set():
            try:
                d = self.q.get(timeout=0.04)
                lm, st, act, cf, ts = d
                self.frame.emit(lm, st, act, cf, ts)
            except Exception:
                continue


# ═══════════════════════════════════════════════════════════════
#  Main Dashboard
# ═══════════════════════════════════════════════════════════════
class AuraDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AURA — Gesture Control")
        self.setFixedSize(600, 720)
        self.setStyleSheet(f"background-color: {BG};")

        scr = QApplication.primaryScreen().geometry()
        self.move((scr.width()-600)//2, (scr.height()-720)//2)

        self.procs = []; self.stop_ev = None; self.gui_q = None
        self.shm = None; self.running = False; self.bridge = None
        self.fps_times = deque(maxlen=30)
        self.history = deque(maxlen=5)
        self.prev_state = "IDLE"

        # Shared settings
        self.smooth_beta = mp.Value('d', 0.005)
        self.click_sens  = mp.Value('i', 3)
        self.zone_margin = mp.Value('d', 0.10)

        self._build()
        QShortcut(QKeySequence("Escape"), self, self.close)
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._anim_tick)
        self._anim_timer.start(500)
        self._anim_phase = 0

    # ── Build UI ──────────────────────────────────────────────
    def _build(self):
        c = QWidget(); self.setCentralWidget(c)
        root = QVBoxLayout(c); root.setContentsMargins(20, 12, 20, 16); root.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("✦ AURA")
        title.setStyleSheet(f"color:{ACCENT};font:bold 20px 'Segoe UI';")
        hdr.addWidget(title)
        sub = QLabel("Gesture Control Dashboard")
        sub.setStyleSheet(f"color:{TEXT_DIM};font:10px 'Segoe UI';padding-top:6px;")
        hdr.addWidget(sub); hdr.addStretch()

        # Status dots
        self.dots = {}
        for name in ("Camera", "MediaPipe", "Controller"):
            lbl = QLabel(f"● {name}")
            lbl.setStyleSheet(f"color:{TEXT_MUTED};font:9px 'Segoe UI';")
            hdr.addWidget(lbl); self.dots[name] = lbl
        root.addLayout(hdr)

        # Separator
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{BORDER};"); root.addWidget(sep)

        # Canvas + Stats row
        row = QHBoxLayout(); row.setSpacing(14)
        self.canvas = HandCanvas(); row.addWidget(self.canvas, stretch=4)

        # Stats sidebar
        stats = QVBoxLayout(); stats.setSpacing(6)
        stats.addWidget(self._section_label("TELEMETRY"))
        self.fps_lbl = self._stat_val("FPS", "—")
        self.lat_lbl = self._stat_val("LATENCY", "—")
        self.conf_lbl = self._stat_val("CONFIDENCE", "—")
        for w in (self.fps_lbl[0], self.lat_lbl[0], self.conf_lbl[0]):
            stats.addWidget(w)
        stats.addStretch()
        row.addLayout(stats, stretch=1)
        root.addLayout(row)

        # State display
        self.state_lbl = QLabel("IDLE")
        self.state_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_lbl.setStyleSheet(
            f"color:{STATE_COLORS['IDLE']};font:bold 28px 'Segoe UI';"
            f"background:{BG_CARD};border:1px solid {BORDER};"
            f"border-radius:8px;padding:8px;")
        root.addWidget(self.state_lbl)

        # Action subtitle
        self.action_lbl = QLabel("Waiting to start…")
        self.action_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.action_lbl.setStyleSheet(f"color:{TEXT_DIM};font:10px 'Segoe UI';")
        root.addWidget(self.action_lbl)

        # Gesture history
        root.addWidget(self._section_label("GESTURE HISTORY"))
        self.hist_container = QVBoxLayout(); self.hist_container.setSpacing(2)
        hist_frame = QFrame()
        hist_frame.setStyleSheet(f"background:{BG_CARD};border:1px solid {BORDER};border-radius:6px;")
        hist_frame.setLayout(self.hist_container)
        hist_frame.setFixedHeight(105)
        # Placeholder
        ph = QLabel("  No gestures yet"); ph.setStyleSheet(f"color:{TEXT_MUTED};font:9px 'Segoe UI';")
        self.hist_container.addWidget(ph)
        self.hist_container.addStretch()
        root.addWidget(hist_frame)

        # Settings (collapsible)
        self.settings_btn = QPushButton("▶  Settings")
        self.settings_btn.setStyleSheet(
            f"QPushButton{{color:{TEXT_DIM};background:transparent;border:none;"
            f"font:bold 10px 'Segoe UI';text-align:left;padding:4px 0;}}"
            f"QPushButton:hover{{color:{ACCENT};}}")
        self.settings_btn.clicked.connect(self._toggle_settings)
        root.addWidget(self.settings_btn)

        self.settings_frame = QFrame()
        self.settings_frame.setStyleSheet(
            f"background:{BG_CARD};border:1px solid {BORDER};border-radius:6px;")
        sf_layout = QVBoxLayout(self.settings_frame); sf_layout.setContentsMargins(12,8,12,8)
        self.settings_frame.setVisible(False)

        self.sl_smooth = self._make_slider("Smoothing β", 0.001, 0.05, 0.005, sf_layout)
        self.sl_click  = self._make_slider("Click Frames", 1, 8, 3, sf_layout, decimals=0)
        self.sl_zone   = self._make_slider("Zone Margin %", 2, 25, 10, sf_layout, decimals=0)
        root.addWidget(self.settings_frame)

        # Start/Stop Button
        self.start_btn = QPushButton("▶   START AURA")
        self.start_btn.setFixedHeight(48)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_start_btn(False)
        self.start_btn.clicked.connect(self._toggle)
        root.addWidget(self.start_btn)

        # Footer
        foot = QLabel("AURA v4  •  SharedMemory IPC  •  OneEuro Smoothing  •  PyQt6")
        foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        foot.setStyleSheet(f"color:{TEXT_MUTED};font:8px 'Segoe UI';")
        root.addWidget(foot)

    # ── Helpers ───────────────────────────────────────────────
    def _section_label(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"color:{TEXT_MUTED};font:bold 9px 'Segoe UI';letter-spacing:2px;")
        return l

    def _stat_val(self, label, default):
        w = QWidget(); ly = QVBoxLayout(w); ly.setContentsMargins(0,0,0,0); ly.setSpacing(0)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color:{TEXT_MUTED};font:8px 'Segoe UI';")
        val = QLabel(default)
        val.setStyleSheet(f"color:{ACCENT};font:bold 16px 'Consolas';")
        ly.addWidget(lbl); ly.addWidget(val)
        return w, val

    def _make_slider(self, label, mn, mx, default, layout, decimals=3):
        row = QHBoxLayout(); row.setSpacing(8)
        lbl = QLabel(label)
        lbl.setFixedWidth(100)
        lbl.setStyleSheet(f"color:{TEXT_DIM};font:9px 'Segoe UI';")
        sl = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(0, 1000)
        sl.setValue(int((default - mn) / (mx - mn) * 1000))
        sl.setStyleSheet(
            f"QSlider::groove:horizontal{{background:{BORDER};height:4px;border-radius:2px;}}"
            f"QSlider::handle:horizontal{{background:{ACCENT};width:12px;height:12px;"
            f"margin:-4px 0;border-radius:6px;}}"
            f"QSlider::sub-page:horizontal{{background:{ACCENT_DIM};border-radius:2px;}}")
        vl = QLabel(f"{default:.{decimals}f}" if decimals else str(int(default)))
        vl.setFixedWidth(45); vl.setAlignment(Qt.AlignmentFlag.AlignRight)
        vl.setStyleSheet(f"color:{ACCENT};font:9px 'Consolas';")

        def on_change(v):
            rv = mn + (v / 1000.0) * (mx - mn)
            vl.setText(f"{rv:.{decimals}f}" if decimals else str(int(rv)))
        sl.valueChanged.connect(on_change)

        row.addWidget(lbl); row.addWidget(sl); row.addWidget(vl)
        layout.addLayout(row)
        return sl, mn, mx

    def _style_start_btn(self, is_running):
        if is_running:
            self.start_btn.setText("■   STOP AURA")
            self.start_btn.setStyleSheet(
                f"QPushButton{{background:{RED};color:white;font:bold 14px 'Segoe UI';"
                f"border:none;border-radius:10px;}}"
                f"QPushButton:hover{{background:#ff7777;}}")
        else:
            self.start_btn.setText("▶   START AURA")
            self.start_btn.setStyleSheet(
                f"QPushButton{{background:{ACCENT};color:white;font:bold 14px 'Segoe UI';"
                f"border:none;border-radius:10px;}}"
                f"QPushButton:hover{{background:#33dfff;}}")

    def _toggle_settings(self):
        vis = not self.settings_frame.isVisible()
        self.settings_frame.setVisible(vis)
        self.settings_btn.setText("▼  Settings" if vis else "▶  Settings")

    def _anim_tick(self):
        self._anim_phase += 1
        if self.running:
            for n, lbl in self.dots.items():
                lbl.setStyleSheet(f"color:{GREEN};font:9px 'Segoe UI';")

    # ── Data from bridge ─────────────────────────────────────
    def _on_frame(self, lm, state, action, conf, ts):
        now = time.time()
        self.fps_times.append(now)
        if len(self.fps_times) > 1:
            dt = self.fps_times[-1] - self.fps_times[0]
            fps = (len(self.fps_times)-1) / max(dt, 0.001)
            self.fps_lbl[1].setText(f"{fps:.0f}")
        lat = (now - ts) * 1000 if ts else 0
        self.lat_lbl[1].setText(f"{lat:.0f}ms")
        self.conf_lbl[1].setText(f"{conf*100:.0f}%")

        # Convert landmarks for canvas
        if lm is not None:
            pts = [(float(lm[i, 0]), float(lm[i, 1])) for i in range(21)]
            self.canvas.set_data(pts, state)
        else:
            self.canvas.set_data(None, state)

        # State label
        sc = STATE_COLORS.get(state, TEXT_DIM)
        self.state_lbl.setText(state)
        self.state_lbl.setStyleSheet(
            f"color:{sc};font:bold 28px 'Segoe UI';"
            f"background:{BG_CARD};border:1px solid {BORDER};"
            f"border-radius:8px;padding:8px;")
        self.action_lbl.setText(f"Action: {action or 'STANDBY'}")

        # History
        if state != self.prev_state:
            t_str = time.strftime("%H:%M:%S")
            self.history.appendleft((f"{self.prev_state} → {state}", t_str, sc))
            self.prev_state = state
            self._rebuild_history()

    def _rebuild_history(self):
        while self.hist_container.count():
            item = self.hist_container.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for text, ts, color in self.history:
            row = QHBoxLayout()
            bar = QLabel(); bar.setFixedSize(3, 16)
            bar.setStyleSheet(f"background:{color};border-radius:1px;")
            txt = QLabel(text)
            txt.setStyleSheet(f"color:{TEXT};font:9px 'Segoe UI';")
            tm = QLabel(ts)
            tm.setStyleSheet(f"color:{TEXT_MUTED};font:8px 'Segoe UI';")
            tm.setAlignment(Qt.AlignmentFlag.AlignRight)
            w = QWidget(); w.setLayout(row)
            row.addWidget(bar); row.addWidget(txt); row.addStretch(); row.addWidget(tm)
            row.setContentsMargins(6,1,6,1)
            self.hist_container.addWidget(w)
        self.hist_container.addStretch()

    # ── Start / Stop ─────────────────────────────────────────
    def _toggle(self):
        if self.running:
            self._stop_aura()
        else:
            self._start_aura()

    def _start_aura(self):
        import subprocess
        from camera_process import camera_process
        from mediapipe_process import mediapipe_process
        from controller_process import controller_process

        # Clean old shm
        try:
            old = shared_memory.SharedMemory(name=SHM_NAME)
            old.close(); old.unlink()
        except: pass

        self.shm = shared_memory.SharedMemory(name=SHM_NAME, create=True, size=FRAME_SIZE)
        self.stop_ev = mp.Event()
        frame_q = mp.Queue(maxsize=1)
        lm_q = mp.Queue(maxsize=1)
        self.gui_q = mp.Queue(maxsize=2)

        cam = mp.Process(target=camera_process, args=(frame_q, self.stop_ev, SHM_NAME), daemon=True)
        med = mp.Process(target=mediapipe_process, args=(frame_q, lm_q, self.stop_ev, SHM_NAME), daemon=True)
        ctrl = mp.Process(target=controller_process, args=(lm_q, self.stop_ev, self.gui_q), daemon=True)

        self.procs = [("Camera", cam), ("MediaPipe", med), ("Controller", ctrl)]
        cam.start(); time.sleep(0.3); med.start(); time.sleep(0.2); ctrl.start()

        self.bridge = DataBridge(self.gui_q, self.stop_ev)
        self.bridge.frame.connect(self._on_frame)
        self.bridge.start()

        self.running = True
        self._style_start_btn(True)
        for n, lbl in self.dots.items():
            lbl.setStyleSheet(f"color:{GREEN};font:9px 'Segoe UI';")

    def _stop_aura(self):
        import subprocess
        if self.stop_ev: self.stop_ev.set()
        if self.bridge: self.bridge.wait(3000)
        for name, p in self.procs:
            try: p.terminate(); p.join(2)
            except: pass
        # Force kill any stragglers
        for name, p in self.procs:
            if p.is_alive():
                try: subprocess.call(['taskkill','/F','/T','/PID',str(p.pid)],
                                     creationflags=0x08000000)
                except: pass
        if self.shm:
            try: self.shm.close(); self.shm.unlink()
            except: pass
        self.procs = []; self.running = False; self.bridge = None
        self._style_start_btn(False)
        self.canvas.set_data(None, "IDLE")
        self.state_lbl.setText("IDLE")
        for n, lbl in self.dots.items():
            lbl.setStyleSheet(f"color:{TEXT_MUTED};font:9px 'Segoe UI';")

    def closeEvent(self, e):
        if self.running: self._stop_aura()
        e.accept()


def main():
    mp.set_start_method("spawn", force=True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = AuraDashboard()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
