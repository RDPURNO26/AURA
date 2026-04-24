# AURA — User manual

AURA drives your Windows cursor with your **right hand** via the webcam. The preview window is mirrored so it feels like pointing at the screen.

## Requirements

- Windows 10/11  
- Webcam  
- Python packages: `pip install -r requirements.txt` (includes **pywin32** for focus safety)  
- **Offline:** copy **`hand_landmarker.task`** into the same folder as `mediapipe_process.py` (the app does **not** download it at runtime).  

Run:

```text
python aura_launcher.py
```
(Or run the standalone `AURA.exe`)

Logs: **`aura.log`** in the project folder. Press **Ctrl+C** to exit.

---



## Cursor Tracking

The cursor is driven by the **palm centroid** (average of the four MCP joints), **not** the fingertip. This means:

- **No jitter** when you flex or pinch your fingers.  
- The cursor tracks your **hand position**, not individual finger movements.  
- Pinching to click does **not** move the cursor — it stays locked where you aimed.  

---

## Gestures (zero overlap)

| Pose | Action |
|------|--------|
| **Peace Sign (Index + Middle up)** | Move cursor (ONLY pose that moves the cursor). |
| **Drop Index** (Middle stays up) | Left Click (Cursor freezes, fires once). |
| **Drop Middle** (Index stays up) | Right Click (Cursor freezes, fires once). |
| **Peace + Thumb out** | Double Click (Fires once). |
| **Fist** (all fingers down) | Drag (Hold 0.3s to start, Peace to release). |
| **Index + Middle + Ring** | Scroll (Joystick-style based on hand position). |
| **Open Hand** (4+ fingers) | Zoom (Joystick-style based on hand position). |
| **Thumb + Index out** (L-shape)| Volume Control (Joystick-style based on hand position). |
| **Pinky only** | Clutch (Recenter your hand). |
| **Index + Pinky** | Lock (Pauses all tracking). |
| **Thumb only** | Voice Typing (Toggles Windows dictation, Win+H). |

### Clicking & Movement

- The cursor is only moved by the **Peace Sign**.
- Lowering a finger for a click instantly **freezes** the cursor so your aim remains perfectly locked.
- Clicks fire **once** per gesture. You must return to the peace sign before clicking again.

---

## Auto-restart

If **Camera**, **MediaPipe**, or **Controller** exits unexpectedly, **main.py** respawns that worker (see log).

---

## Troubleshooting

| Issue | What to try |
|-------|-------------|
| MediaPipe exits immediately | Add **`hand_landmarker.task`** next to `mediapipe_process.py`. |
| Clicks too sensitive | The adaptive threshold should handle this automatically. If it persists, try keeping your hand still for the first 2 seconds of use to get a clean calibration. |
| Cursor wrong after clutch | Hold **pinky-only** to clutch, recenter, then **index** clearly up for 4 frames. |
| LOCKED exits too fast | Make sure to close **all** fingers into a fist. Opening requires **2+ fingers** clearly extended. |

---

## Technical

- **Cursor anchor:** Palm centroid (average of landmarks 5, 9, 13, 17 — MCP joints).  
- **Drop-finger clicking:** Uses cosine similarity between finger bone vectors to detect specific finger lowering while the rest of the hand remains stable.  
- **Scroll velocity:** Landmark 9 (middle MCP) Y-axis movement — stable, not affected by finger flexion.  
- **Queues:** blocking `get(timeout=0.033)` in MediaPipe and Controller (low busy-wait).  
- **Smoothing:** One Euro `freq=60`, `fmin=1.5`, `beta=0.007`, `dcutoff=1.0`; anti-teleport **4%** of desktop width.  
- **FSM:** `gesture_fsm.py` — `update(inputs, prev_lm)` → `state`, `action`, `pinch_threshold`, `arming`.  
- **MediaPipe timestamps:** Real milliseconds (not frame counter) for accurate internal tracking.  
