import os
import cv2
import numpy as np
from typing import Optional, Callable

from core.detector import VehicleDetector, VEHICLE_CLASSES
from core.tracker import VehicleTracker
from core.distance import DistanceMonitor
from core.collision import CollisionPredictor
from core.behavior import BehaviorScorer
from core.plate_reader import PlateReader
from core.weather import WeatherContext

_FPS        = float(os.getenv('FPS', 30))
_PX_TO_M    = float(os.getenv('PX_TO_METER', 0.05))
_WEATHER_SC = int(os.getenv('WEATHER_MOCK_SCENARIO', 0))

# Color per score bracket (BGR)
def _score_color(score: int) -> tuple:
    if score < 25:  return (0, 220, 0)    # green
    if score < 60:  return (0, 165, 255)  # orange
    return (0, 0, 255)                    # red


class GuardianPipeline:
    # Submit vehicle crop for plate OCR every N frames
    PLATE_SUBMIT_EVERY = 20

    def __init__(self):
        self.detector    = VehicleDetector()
        self.tracker     = VehicleTracker()
        self.distance    = DistanceMonitor(px_to_meter=_PX_TO_M)
        self.collision   = CollisionPredictor(fps=_FPS, px_to_meter=_PX_TO_M)
        self.behavior    = BehaviorScorer(fps=_FPS)
        self.plate_reader = PlateReader()
        self.weather     = WeatherContext(scenario=_WEATHER_SC)

        self.frame_num   = 0
        self._cap: Optional[cv2.VideoCapture] = None
        self.latest_jpeg: Optional[bytes] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def open(self, source) -> 'GuardianPipeline':
        self._cap = cv2.VideoCapture(source)
        if not self._cap.isOpened():
            raise RuntimeError(f'Cannot open video source: {source}')
        return self

    def close(self):
        if self._cap:
            self._cap.release()
            self._cap = None

    # ── Core frame processing (called from thread pool in main.py) ────────────

    def process_frame(self, frame: np.ndarray) -> dict:
        mult = self.weather.threshold_multiplier()
        self.distance.set_weather_multiplier(mult)

        detections = self.detector.detect(frame)
        vehicles   = self.tracker.update(detections, frame, self.frame_num)

        dist_alerts     = self.distance.compute(vehicles)
        coll_alerts     = self.collision.predict(vehicles)
        behavior_events = self.behavior.update(vehicles, self.frame_num, dist_alerts)

        # Submit vehicle (not pedestrian) crops to background OCR thread
        if self.frame_num % self.PLATE_SUBMIT_EVERY == 0:
            for v in vehicles:
                if v.get('class') != 'person':
                    self.plate_reader.submit(frame, v['bbox'], v['track_id'])

        result = {
            'frame':           self.frame_num,
            'vehicle_count':   len(vehicles),
            'distance_alerts': dist_alerts,
            'collision_alerts': coll_alerts,
            'behavior_events': behavior_events,
            'scores':          self.behavior.get_all_scores(),
            'weather':         self.weather.status(),
            'vehicles': [
                {
                    'track_id': v['track_id'],
                    'bbox':     [round(c, 1) for c in v['bbox']],
                    'center':   [round(c, 1) for c in v['center']],
                    'class':    v['class'],
                    'plate':    self.plate_reader.get(v['track_id']),
                    'score':    self.behavior.get_score(v['track_id']),
                }
                for v in vehicles
            ],
        }

        annotated = self.annotate(frame, result)
        ok, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ok:
            self.latest_jpeg = buf.tobytes()

        self.frame_num += 1
        return result

    # ── Annotation ────────────────────────────────────────────────────────────

    def annotate(self, frame: np.ndarray, result: dict) -> np.ndarray:
        out = frame.copy()
        vehicle_map = {v['track_id']: v for v in result['vehicles']}

        for vd in result['vehicles']:
            x1, y1, x2, y2 = (int(c) for c in vd['bbox'])
            score  = vd['score']
            plate  = vd.get('plate')
            is_person = vd['class'] == 'person'

            if is_person:
                # Pedestrian — purple box, no plate overlay
                color = (220, 80, 220)
                label = f"PERSON  ID:{vd['track_id']}"
                cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 2)
                ly = max(y1 - th - 8, 0)
                cv2.rectangle(out, (x1, ly), (x1 + tw + 6, ly + th + 6), color, -1)
                cv2.putText(out, label, (x1 + 3, ly + th + 1),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 0), 2)
                continue

            color = _score_color(score)
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)

            # Top label with solid background
            plate_or_id = f'[{plate}]' if plate else f"ID:{vd['track_id']}"
            top = f"{plate_or_id} {score}pts"
            (tw, th), _ = cv2.getTextSize(top, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 2)
            ly = max(y1 - th - 10, 0)
            cv2.rectangle(out, (x1, ly), (x1 + tw + 8, ly + th + 8), color, -1)
            cv2.putText(out, top, (x1 + 4, ly + th + 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 2)

            # Plate highlight + banner
            if plate:
                bh   = y2 - y1
                py1  = y2 - max(int(bh * 0.28), 18)
                lpx  = x1 + int((x2 - x1) * 0.1)
                rpx  = x2 - int((x2 - x1) * 0.1)
                cv2.rectangle(out, (lpx, py1), (rpx, y2), (0, 255, 255), 2)

                (ptw, pth), _ = cv2.getTextSize(plate, cv2.FONT_HERSHEY_SIMPLEX, 0.72, 2)
                bx = (x1 + x2) // 2 - ptw // 2
                by = y2 + 4
                cv2.rectangle(out, (bx - 6, by), (bx + ptw + 6, by + pth + 10),
                              (0, 255, 255), -1)
                cv2.putText(out, plate, (bx, by + pth + 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 0, 0), 2)

        # Distance lines
        lc_map = {'DANGER': (0, 0, 255), 'WARNING': (0, 140, 255), 'CAUTION': (0, 200, 255)}
        for a in result['distance_alerts']:
            ids = a['vehicle_ids']
            if ids[0] not in vehicle_map or ids[1] not in vehicle_map:
                continue
            lc = lc_map.get(a['level'], (150, 150, 150))
            c1 = tuple(int(c) for c in vehicle_map[ids[0]]['center'])
            c2 = tuple(int(c) for c in vehicle_map[ids[1]]['center'])
            cv2.line(out, c1, c2, lc, 2)
            mid = ((c1[0] + c2[0]) // 2, (c1[1] + c2[1]) // 2)
            dlbl = f"{a['distance_m']}m"
            (dw, dh), _ = cv2.getTextSize(dlbl, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 2)
            cv2.rectangle(out, (mid[0] - 2, mid[1] - dh - 3),
                          (mid[0] + dw + 2, mid[1] + 3), lc, -1)
            cv2.putText(out, dlbl, mid, cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 2)

        # Collision markers
        for a in result['collision_alerts']:
            px, py = (int(c) for c in a['collision_point_px'])
            col = (0, 0, 255) if a['level'] == 'CRITICAL' else (0, 140, 255)
            cv2.drawMarker(out, (px, py), col, cv2.MARKER_CROSS, 24, 3)
            cv2.putText(out, f"TTC {a['ttc_seconds']}s", (px + 10, py - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, col, 2)

        # HUD
        w = result['weather']
        hud = f"  {w['condition'].upper()}  x{w['threshold_multiplier']}  |  " \
              f"Objects: {result['vehicle_count']}  |  Frame: {result['frame']}  "
        cv2.rectangle(out, (0, 0), (out.shape[1], 34), (15, 15, 20), -1)
        cv2.putText(out, hud, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 225, 0), 2)

        return out


# Singleton shared by FastAPI
pipeline = GuardianPipeline()
