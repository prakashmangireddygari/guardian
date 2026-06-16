"""
License plate reader — two steps:
  1. Crop the bottom-third of the vehicle bounding box (where plates live)
  2. Run EasyOCR with aggressive preprocessing on that small region

Runs in a background thread so it never blocks video processing.
"""
import re
import queue
import threading
from collections import defaultdict
from typing import Optional

import cv2
import numpy as np

# Permissive: 3–12 chars, allow a space in the middle (e.g. "MH 12 AB 1234")
_PLATE_RE = re.compile(r'^[A-Z0-9][A-Z0-9 ]{1,10}[A-Z0-9]$')


def _preprocess_plate(crop: np.ndarray) -> list[np.ndarray]:
    """Return several preprocessed versions of a plate crop for OCR."""
    # Upscale: OCR works much better on larger images
    h, w = crop.shape[:2]
    scale = max(1, int(120 / h))
    up = cv2.resize(crop, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)

    # CLAHE — local contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(gray)

    # Adaptive threshold (dark text on light plate)
    thresh_dark = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
    )
    # Inverted (light text on dark plate)
    thresh_light = cv2.bitwise_not(thresh_dark)

    # Bilateral filter (preserves edges, removes noise)
    smooth = cv2.bilateralFilter(enhanced, 9, 75, 75)

    return [up, enhanced, thresh_dark, thresh_light, smooth]


class PlateReader:
    def __init__(self, languages: list = None, gpu: bool = False):
        self._confirmed: dict[int, str] = {}
        self._votes: dict[int, dict[str, int]] = defaultdict(dict)
        self._submitted: set[int] = set()

        self._queue: queue.Queue = queue.Queue(maxsize=50)
        self._languages = languages or ['en']
        self._gpu = gpu
        self._running = True

        self._thread = threading.Thread(target=self._worker, daemon=True, name='plate-ocr')
        self._thread.start()

    # ── Public API ──────────────────────────────────────────────────────────

    def submit(self, frame: np.ndarray, bbox: list, track_id: int):
        """Queue a vehicle crop for async OCR. Returns immediately."""
        if track_id in self._confirmed:
            return
        if track_id in self._submitted and not self._queue.empty():
            return

        x1, y1, x2, y2 = (int(v) for v in bbox)
        h, w = frame.shape[:2]

        # Focus on the bottom third of the vehicle — that is where plates are
        plate_y1 = y1 + int((y2 - y1) * 0.55)
        crop = frame[max(0, plate_y1):min(h, y2), max(0, x1):min(w, x2)]

        if crop.size == 0 or crop.shape[0] < 10 or crop.shape[1] < 20:
            return

        try:
            self._queue.put_nowait((track_id, crop.copy()))
            self._submitted.add(track_id)
        except queue.Full:
            pass

    def get(self, track_id: int) -> Optional[str]:
        return self._confirmed.get(track_id)

    def get_all(self) -> dict[int, str]:
        return dict(self._confirmed)

    def reset(self):
        """Clear all state for a new video session."""
        self._confirmed.clear()
        self._votes.clear()
        self._submitted.clear()
        # Drain the queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def stop(self):
        self._running = False

    # ── Background worker ───────────────────────────────────────────────────

    def _worker(self):
        import easyocr
        reader = easyocr.Reader(self._languages, gpu=self._gpu, verbose=False)

        while self._running:
            try:
                track_id, crop = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if track_id in self._confirmed:
                continue

            text = self._read(reader, crop)
            if not text:
                self._submitted.discard(track_id)  # allow retry
                continue

            votes = self._votes[track_id]
            votes[text] = votes.get(text, 0) + 1

            # Confirm after first valid read (fast-moving vehicles often seen once)
            self._confirmed[track_id] = text
            self._votes.pop(track_id, None)

    def _read(self, reader, crop: np.ndarray) -> Optional[str]:
        """Try several preprocessed versions; return the best plate string."""
        candidates = []

        for img in _preprocess_plate(crop):
            results = reader.readtext(
                img,
                allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ',
                detail=1,
                paragraph=False,
                text_threshold=0.25,
                low_text=0.3,
            )
            # Concatenate all detected text segments on this image
            raw = ' '.join(r[1].upper().strip() for r in results if r[2] > 0.20)
            raw = re.sub(r'\s+', ' ', raw).strip()

            if _PLATE_RE.match(raw):
                # Score by total OCR confidence
                conf = sum(r[2] for r in results) / max(len(results), 1)
                candidates.append((raw, conf))

        if not candidates:
            return None

        # Return the highest-confidence candidate
        return max(candidates, key=lambda x: x[1])[0]
