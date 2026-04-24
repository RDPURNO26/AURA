# camera_process.py
"""
AURA v4 – Camera Capture Process (Shared Memory).
Writes frames directly into shared memory — zero-copy IPC.
Signals readiness via a lightweight queue with just the timestamp.
"""

import cv2
import multiprocessing as mp
import time
import numpy as np


def camera_process(frame_queue: mp.Queue, stop_event: mp.Event, shm_name: str = None, lite_mode: bool = False):
    target_fps = 20 if lite_mode else 30
    print(f"[Camera] Started (FPS target: {target_fps}, lite={lite_mode})")

    flip_buffer = None  # Pre-allocated once — reused every frame
    shm = None
    shm_array = None

    # Set up shared memory if available
    if shm_name:
        from multiprocessing import shared_memory
        try:
            shm = shared_memory.SharedMemory(name=shm_name)
            shm_array = np.ndarray((480, 640, 3), dtype=np.uint8, buffer=shm.buf)
            print("[Camera] Shared memory attached — zero-copy mode")
        except Exception as e:
            print(f"[Camera] Shared memory failed ({e}), falling back to queue mode")
            shm = None

    def open_camera():
        c = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        c.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        c.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        c.set(cv2.CAP_PROP_FPS, target_fps)
        if not c.isOpened():
            return None
        for _ in range(5):   # Warmup — CAP_DSHOW first frames are often black
            c.read()
        print("[Camera] Webcam opened successfully.")
        return c

    cap = open_camera()
    if cap is None:
        print("[Camera] ERROR: Could not open webcam. Check connection.")
        if shm:
            shm.close()
        return

    consecutive_failures = 0
    MAX_FAILURES = 30  # ~1 second at 30fps before recovery attempt

    while not stop_event.is_set():
        ret, frame = cap.read()
        ts = time.time()  # Timestamp RIGHT at capture — critical for FSM timing

        if not ret or frame is None:
            consecutive_failures += 1
            if consecutive_failures >= MAX_FAILURES:
                print("[Camera] Camera lost — attempting recovery...")
                cap.release()
                time.sleep(1.0)
                cap = open_camera()
                if cap is None:
                    print("[Camera] Recovery failed. Stopping.")
                    break
                consecutive_failures = 0
                flip_buffer = None  # Reset buffer shape after recovery
            continue

        consecutive_failures = 0

        # Allocate flip buffer once on first valid frame
        if flip_buffer is None or flip_buffer.shape != frame.shape:
            flip_buffer = np.empty_like(frame)

        cv2.flip(frame, 1, flip_buffer)  # Flip into pre-allocated buffer

        if shm_array is not None:
            # Zero-copy: write directly into shared memory
            np.copyto(shm_array, flip_buffer)
            # Signal with just the timestamp (tiny payload)
            if not frame_queue.empty():
                try:
                    frame_queue.get_nowait()
                except Exception:
                    pass
            try:
                frame_queue.put_nowait(ts)
            except Exception:
                pass
        else:
            # Fallback: old queue mode
            if not frame_queue.empty():
                try:
                    frame_queue.get_nowait()
                except Exception:
                    pass
            try:
                frame_queue.put_nowait((ts, flip_buffer.copy()))
            except Exception:
                pass

    if cap is not None:
        cap.release()
    if shm:
        shm.close()
    print("[Camera] Stopped")


if __name__ == "__main__":
    """Standalone test — run this file to verify camera works before full integration."""
    import threading

    test_queue = mp.Queue(maxsize=1)
    test_stop = mp.Event()

    t = threading.Thread(target=camera_process, args=(test_queue, test_stop))
    t.start()

    print("[Camera Test] Press Q to stop.")
    try:
        while True:
            if not test_queue.empty():
                data = test_queue.get_nowait()
                if isinstance(data, tuple):
                    ts, frame = data
                    cv2.imshow("Camera Test — AURA", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except KeyboardInterrupt:
        pass
    finally:
        test_stop.set()
        t.join(timeout=3)
        cv2.destroyAllWindows()
        print("[Camera Test] Complete.")
