# mediapipe_process.py
"""
AURA v4 – MediaPipe Hand Tracking Process (Tasks API).
Supports shared memory for zero-copy frame reads.
Bundle hand_landmarker.task next to this file — no runtime download (offline-safe).
"""

import logging
import multiprocessing as mp
import os
from pathlib import Path

import numpy as np

_log = logging.getLogger("aura.mediapipe")


def _configure_file_logging():
    if logging.getLogger().handlers:
        return
    import sys
    if getattr(sys, 'frozen', False):
        log_path = Path(sys.executable).parent / "aura.log"
    else:
        log_path = Path(__file__).resolve().parent / "aura.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )


def mediapipe_process(frame_queue: mp.Queue, landmark_queue: mp.Queue,
                      stop_event: mp.Event, shm_name: str = None, lite_mode: bool = False):
    _configure_file_logging()
    import queue
    import time

    import cv2
    import mediapipe as mp_lib
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    from mediapipe.tasks.python.vision import HandLandmarkerOptions, HandLandmarker
    from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode

    _log.info("MediaPipe process started")

    # Set up shared memory if available
    shm = None
    shm_array = None
    if shm_name:
        from multiprocessing import shared_memory
        try:
            shm = shared_memory.SharedMemory(name=shm_name)
            shm_array = np.ndarray((480, 640, 3), dtype=np.uint8, buffer=shm.buf)
            _log.info("Shared memory attached — zero-copy read mode")
        except Exception as e:
            _log.warning("Shared memory failed (%s), falling back to queue mode", e)
            shm = None

    import sys
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, "hand_landmarker.task")
    # Offline / production: ship hand_landmarker.task with the app. Do not download at demo time.
    if not os.path.isfile(model_path):
        _log.error(
            "Missing %s — copy hand_landmarker.task from MediaPipe hand_landmarker bundle next to this file.",
            model_path,
        )
        if shm:
            shm.close()
        return

    base_options = mp_python.BaseOptions(model_asset_path=model_path)
    if lite_mode:
        _log.info("Lite mode active — using lower confidence thresholds")
        detect_conf = 0.60
        presence_conf = 0.50
        tracking_conf = 0.50
    else:
        detect_conf = 0.72
        presence_conf = 0.62
        tracking_conf = 0.62
    options = HandLandmarkerOptions(
        base_options=base_options,
        running_mode=VisionTaskRunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=detect_conf,
        min_hand_presence_confidence=presence_conf,
        min_tracking_confidence=tracking_conf,
    )

    landmark_buffer = np.zeros((21, 3), dtype=np.float32)
    video_frame_ms = 0

    with HandLandmarker.create_from_options(options) as detector:
        _log.info("Hand landmarker ready (VIDEO mode)")

        while not stop_event.is_set():
            try:
                raw = frame_queue.get(timeout=0.033)
            except queue.Empty:
                continue

            # Shared memory mode: queue contains just a timestamp float
            if shm_array is not None and isinstance(raw, (int, float)):
                ts = float(raw)
                frame = shm_array.copy()  # Snapshot from shared memory
            elif isinstance(raw, tuple) and len(raw) == 2:
                ts, frame = raw
            else:
                continue

            if frame is None:
                continue

            # BUG-08 fix: use real milliseconds (MediaPipe needs real time for tracking)
            video_frame_ms = max(video_frame_ms + 1, int(ts * 1000))

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if not rgb.flags["C_CONTIGUOUS"]:
                rgb = np.ascontiguousarray(rgb)
            mp_image = mp_lib.Image(image_format=mp_lib.ImageFormat.SRGB, data=rgb)

            result = detector.detect_for_video(mp_image, video_frame_ms)

            if result.hand_landmarks and result.handedness:
                lms = result.hand_landmarks[0]
                for i, lm in enumerate(lms):
                    landmark_buffer[i, 0] = lm.x
                    landmark_buffer[i, 1] = lm.y
                    landmark_buffer[i, 2] = lm.z

                confidence = result.handedness[0][0].score
                output = (ts, landmark_buffer.copy(), float(confidence))
            else:
                output = (ts, None, 0.0)

            # Release large arrays immediately — critical for low-RAM PCs
            del rgb, mp_image, result
            if shm_array is not None:
                del frame  # was a .copy() from shared memory

            if not landmark_queue.empty():
                try:
                    landmark_queue.get_nowait()
                except Exception:
                    pass
            try:
                landmark_queue.put_nowait(output)
            except Exception:
                pass

    if shm:
        shm.close()
    _log.info("MediaPipe process stopped")


if __name__ == "__main__":
    import cv2
    import threading
    import time

    logging.basicConfig(level=logging.INFO)
    test_frame_q = mp.Queue(maxsize=1)
    test_landmark_q = mp.Queue(maxsize=1)
    test_stop = mp.Event()

    t = threading.Thread(
        target=mediapipe_process,
        args=(test_frame_q, test_landmark_q, test_stop),
    )
    t.start()
    time.sleep(2)

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            ts = time.time()
            if test_frame_q.empty():
                try:
                    test_frame_q.put_nowait((ts, frame))
                except Exception:
                    pass
            if not test_landmark_q.empty():
                try:
                    test_landmark_q.get_nowait()
                except Exception:
                    pass
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        test_stop.set()
        t.join(timeout=3)
        cap.release()
        cv2.destroyAllWindows()
