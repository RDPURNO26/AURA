<div align="center">

# ✦ AURA

### **A**I-powered **U**ser-hand **R**ecognition & **A**utomation

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Hand_Tracking-00897B?style=for-the-badge&logo=google&logoColor=white)](https://mediapipe.dev)
[![PyQt6](https://img.shields.io/badge/PyQt6-GUI_Dashboard-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://www.riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows_10%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://microsoft.com)

<br>

> **Control your entire PC with hand gestures.**
> No gloves. No sensors. No special hardware. Just your webcam.

<br>

```
 █████╗ ██╗   ██╗██████╗  █████╗
██╔══██╗██║   ██║██╔══██╗██╔══██╗
███████║██║   ██║██████╔╝███████║
██╔══██║██║   ██║██╔══██╗██╔══██║
██║  ██║╚██████╔╝██║  ██║██║  ██║
╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝
```

</div>

---

## 📥 Download & Run (No Setup Required)

**For a non-technical experience, use our standalone version:**

1.  **Download:** Go to [**Releases**](https://github.com/RDPURNO26/AURA/releases) and download `AURA.exe`.
2.  **Run:** Double-click `AURA.exe`.
    *   *Note: If Windows shows a "SmartScreen" warning, click **"More info"** and then **"Run anyway."***
3.  **Launch:** Click the big **"▶ LAUNCH AURA"** button in the dashboard and start using gestures!

---

## ⚡ What is AURA?

AURA transforms your webcam into a **full mouse + keyboard replacement** using real-time hand tracking. It uses **MediaPipe's 21-point hand landmark model** to detect your hand pose and translates it into precise cursor movements, clicks, scrolls, zooms, volume control, and voice typing — all with **zero additional hardware**.

### 🏗️ Architecture

```
┌──────────┐    SharedMemory    ┌──────────────┐    Queue    ┌────────────┐
│  Camera   │ ───────────────► │  MediaPipe    │ ─────────► │ Controller │
│  Process  │   (zero-copy)    │  Process      │  landmarks │  Process   │
│  30 FPS   │                  │  Hand Tracker │            │  FSM+Input │
└──────────┘                   └──────────────┘            └─────┬──────┘
                                                                  │
                                              ┌───────────────────┤
                                              ▼                   ▼
                                        ┌──────────┐     ┌──────────────┐
                                        │  Win32    │     │  PyQt6 GUI   │
                                        │  Cursor   │     │  Dashboard   │
                                        │  Control  │     │  (optional)  │
                                        └──────────┘     └──────────────┘
```

---

## 🖐️ Gesture Map

> **Zero overlap** — every finger combination maps to exactly one action.

<table>
<thead>
<tr>
<th align="center">Gesture</th>
<th>Fingers</th>
<th>Action</th>
<th>Details</th>
</tr>
</thead>
<tbody>
<tr><td align="center">✌️</td><td><b>Index + Middle</b></td><td>🟢 Move Cursor</td><td>Only gesture that moves the cursor. Palm position drives the pointer.</td></tr>
<tr><td align="center">👇</td><td><b>Middle only</b></td><td>🔵 Left Click</td><td>Drop index finger. Fires once, cursor freezes to lock aim.</td></tr>
<tr><td align="center">☝️</td><td><b>Index only</b></td><td>🔵 Right Click</td><td>Drop middle finger. Single-shot, no spam.</td></tr>
<tr><td align="center">👍</td><td><b>Peace + Thumb</b></td><td>🔵 Double Click</td><td>Extend thumb while showing peace sign.</td></tr>
<tr><td align="center">✊</td><td><b>Fist</b></td><td>🟠 Drag & Drop</td><td>Hold fist 0.3s → drag starts. Peace sign to release.</td></tr>
<tr><td align="center">🖖</td><td><b>3 fingers</b></td><td>🟣 Scroll</td><td>Index + Middle + Ring. Joystick: hand up/down = scroll speed.</td></tr>
<tr><td align="center">🖐️</td><td><b>4+ fingers</b></td><td>🟣 Zoom</td><td>Open hand. Same joystick logic: hand up = zoom in.</td></tr>
<tr><td align="center">👉</td><td><b>Thumb + Index</b></td><td>🟢 Volume</td><td>L-shape gesture. Hand up = vol up, down = vol down.</td></tr>
<tr><td align="center">🤙</td><td><b>Pinky only</b></td><td>🟡 Clutch</td><td>Recenter your hand like lifting a mouse. Peace to resume.</td></tr>
<tr><td align="center">🤟</td><td><b>Index + Pinky</b></td><td>🔴 Lock</td><td>Full system pause. Peace sign to unlock.</td></tr>
<tr><td align="center">👍</td><td><b>Thumb only</b></td><td>🩷 Voice Typing</td><td>Toggles Windows dictation (Win+H).</td></tr>
</tbody>
</table>

---

## 🚀 Quick Start

### Option 1: Run from Source

```bash
# Clone the repository
git clone https://github.com/RDPURNO26/AURA.git
cd AURA

# Install dependencies
pip install -r requirements.txt

# Launch the PyQt6 Dashboard
python gui.py

# Or run headless (terminal only)
python main.py
```

### Option 2: Build Standalone EXE

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --icon=app_icon.ico --add-data "hand_landmarker.task;." --name "AURA" --hidden-import=PyQt6.sip entry_point.py
```

> **📦 The `hand_landmarker.task` model is included in this repo.** No downloads needed.

---

## 🎨 The Dashboard

AURA ships with a premium **PyQt6 desktop application** (`gui.py`):

| Feature | Description |
|:---|:---|
| **🖐️ Live Hand Skeleton** | Multi-layer glow rendering with animated pulse, scanning laser, and corner brackets |
| **📊 Real-time Telemetry** | FPS, latency (ms), and hand confidence (%) updated every frame |
| **🏷️ State Display** | Large, color-coded current state with action subtitle |
| **📜 Gesture History** | Last 5 state transitions with timestamps |
| **🟢 System Health** | Live status dots for Camera, MediaPipe, and Controller processes |
| **⚙️ Tuning Sliders** | Collapsible panel: Smoothing β, Click Sensitivity, Zone Margins |
| **▶️ One-Click Launch** | START / STOP button that manages all background processes |

---

## 🧠 Technical Highlights

<details>
<summary><b>🔄 Shared Memory IPC</b></summary>

Camera frames (640×480×3 = 921KB each) are written directly to a `multiprocessing.SharedMemory` block. MediaPipe reads from the **same physical RAM** — zero serialization, zero copy. The queue only carries a tiny timestamp to signal readiness.

**Result:** ~40% lower CPU usage and near-zero pipeline latency vs the old `Queue` approach.
</details>

<details>
<summary><b>🎯 One Euro Filter</b></summary>

The cursor uses a **One Euro Filter** (`freq=60, fmin=1.0, beta=0.005`) — an adaptive low-pass filter that:
- **At rest:** Extremely smooth (magnetic feel, no jitter)
- **In motion:** Near-zero lag (instant response)

A separate heavier filter (`fmin=3.0, beta=0.003`) is used during drag operations for rock-solid stability.
</details>

<details>
<summary><b>🤖 Gesture FSM</b></summary>

The `GestureStateMachine` in `gesture_fsm.py` implements a deterministic finite automaton with frame-based debouncing:

```
IDLE → MOVE → CLICKING → DRAGGING
  ↕      ↕        ↕
LOCKED  CLUTCH  SCROLLING / ZOOMING / VOLUME
```

Every transition requires sustained frames (3–6) to prevent accidental triggers. All clicks are single-shot with cooldown.
</details>

<details>
<summary><b>🖥️ Multi-Process Architecture</b></summary>

Three isolated processes run in parallel:

| Process | Job | IPC |
|---|---|---|
| **Camera** | Captures 640×480 @ 30fps via DirectShow | SharedMemory write |
| **MediaPipe** | Runs hand landmark inference | SharedMemory read → Queue |
| **Controller** | FSM + cursor + input events | Queue → Win32 API |

Auto-restart: if any worker dies, `main.py` respawns it within 1 second.
</details>

---

## 📁 Project Structure

```
AURA/
├── aura_launcher.py        # Main Tkinter Launcher with interactive UI
├── gui.py                  # Legacy PyQt6 Dashboard
├── main.py                 # Headless entry point (terminal mode)
├── entry_point.py          # EXE entry point (handles freeze_support)
├── camera_process.py       # Camera capture (SharedMemory writer)
├── mediapipe_process.py    # Hand landmark inference
├── controller_process.py   # FSM + cursor control + HUD overlay
├── gesture_fsm.py          # Gesture state machine
├── hand_landmarker.task    # MediaPipe AI model (bundled, offline-safe)
├── requirements.txt        # Python dependencies
├── Run_AURA.bat            # One-click batch launcher
├── CONTROLS_GUIDE.txt      # Complete gesture reference
├── MANUAL.md               # User manual
├── PROJECT_REPORT.md       # Academic project report
└── README.md               # This file
```

---

## 📋 Requirements

| Component | Version |
|:---|:---|
| Python | 3.10+ |
| Windows | 10 / 11 |
| Webcam | Any USB / built-in |
| MediaPipe | 0.10.14 |
| OpenCV | 4.8.1+ |
| PyQt6 | 6.5+ |
| NumPy | 1.24+ |
| pynput | 1.7+ |
| pywin32 | 306+ |

---

## 🔮 Roadmap

- [ ] GPU acceleration (MediaPipe GPU delegate / ONNX DirectML)
- [ ] Config file for all tunable parameters (`config.json`)
- [ ] Per-user calibration profiles
- [ ] Left-hand support
- [ ] System tray integration
- [ ] Gesture customization GUI
- [ ] Accessibility preset profiles
- [ ] CI/CD with GitHub Actions

---

<div align="center">

**Built with 🧠 by [RDPURNO26](https://github.com/RDPURNO26)**

*Control your computer with the wave of a hand.*

</div>
