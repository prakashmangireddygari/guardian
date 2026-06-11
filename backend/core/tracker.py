from deep_sort_realtime.deepsort_tracker import DeepSort
import numpy as np
from collections import defaultdict


class VehicleTracker:
    def __init__(self, max_age=30, n_init=3):
        self.tracker = DeepSort(max_age=max_age, n_init=n_init)
        self.track_history: dict[int, list] = defaultdict(list)

    def update(self, detections: list, frame: np.ndarray, frame_num: int) -> list:
        ds_detections = [
            ([d['bbox'][0], d['bbox'][1], d['bbox'][2] - d['bbox'][0], d['bbox'][3] - d['bbox'][1]],
             d['confidence'], d['class'])
            for d in detections
        ]
        tracks = self.tracker.update_tracks(ds_detections, frame=frame)

        vehicles = []
        for track in tracks:
            if not track.is_confirmed():
                continue
            tid = track.track_id
            x1, y1, x2, y2 = track.to_ltrb()
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

            self.track_history[tid].append((cx, cy, frame_num))
            if len(self.track_history[tid]) > 60:
                self.track_history[tid].pop(0)

            vehicles.append({
                'track_id': tid,
                'bbox': [x1, y1, x2, y2],
                'center': (cx, cy),
                'velocity': self._velocity(tid),
                'class': track.det_class or 'vehicle',
            })
        return vehicles

    def _velocity(self, tid: int) -> tuple:
        history = self.track_history[tid]
        if len(history) < 2:
            return (0.0, 0.0)
        # Average over last 5 frames for stability
        lookback = min(5, len(history))
        dx = history[-1][0] - history[-lookback][0]
        dy = history[-1][1] - history[-lookback][1]
        frames_elapsed = lookback
        return (dx / frames_elapsed, dy / frames_elapsed)
