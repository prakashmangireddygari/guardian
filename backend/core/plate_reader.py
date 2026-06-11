"""
License plate reader — OCR runs in a dedicated background thread so it
never blocks the video processing loop.
"""
import re
import queue
import threading
from collections import defaultdict
from typing import Optional

import cv2
import numpy as np

# Accept 4-10 alphanumeric characters
_PLATE_RE = re.compile(r'^[A-Z0-9]{4,10}$')


class PlateReader:
    def __init__(self, languages: list = None, gpu: bool = False):
        self._confirmed: dict[int, str] = {}           # track_id -> confirmed plate
        self._votes: dict[int, dict[str, int]] = defaultdict(dict)   # track_id -> {text: count}
        self._submitted: set[int] = set()              # track_ids already queued

        self._queue: queue.Queue = queue.Queue(maxsize=30)
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
        # Don't flood the queue for the same vehicle
        if track_id in self._submitted and not self._queue.empty():
            return

        x1, y1, x2, y2 = (int(v) for v in bbox)
        h, w = frame.shape[:2]
        crop = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        if crop.size == 0 or crop.shape[0] < 20 or crop.shape[1] < 20:
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
                continue

            votes = self._votes[track_id]
            votes[text] = votes.get(text, 0) + 1
            # Confirm after 2 consistent reads of the same string
            if votes[text] >= 2:
                self._confirmed[track_id] = text
                self._votes.pop(track_id, None)
            else:
                # Re-queue the same vehicle so we can get a second read
                self._submitted.discard(track_id)

    def _read(self, reader, crop: np.ndarray) -> Optional[str]:
        """Try several preprocessing strategies; return best plate string found."""
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        # Three regions: full height, bottom 50%, bottom 30%
        regions = [
            crop,
            crop[crop.shape[0] // 2:, :],
            crop[int(crop.shape[0] * 0.65):, :],
        ]

        for region in regions:
            if region.shape[0] < 10 or region.shape[1] < 10:
                continue
            g = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) if len(region.shape) == 3 else region

            # CLAHE → upscale 2×
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
            enhanced = clahe.apply(g)
            up = cv2.resize(enhanced, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

            results = reader.readtext(
                up,
                allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
                detail=1,
                paragraph=False,
            )
            text = ''.join(r[1] for r in results if r[2] > 0.30).upper().replace(' ', '')
            if _PLATE_RE.match(text):
                return text

        return None
