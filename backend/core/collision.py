import numpy as np
from typing import List, Optional


class CollisionPredictor:
    TTC_CRITICAL = 3.0   # seconds
    TTC_WARNING = 6.0    # seconds

    def __init__(self, fps: float = 30.0, px_to_meter: float = 0.05):
        self.fps = fps
        self.px_to_meter = px_to_meter

    def predict(self, vehicles: List[dict]) -> List[dict]:
        alerts = []
        for i in range(len(vehicles)):
            for j in range(i + 1, len(vehicles)):
                result = self._ttc(vehicles[i], vehicles[j])
                if result is None:
                    continue
                ttc, collision_pt = result
                level = 'CRITICAL' if ttc <= self.TTC_CRITICAL else 'WARNING'
                alerts.append({
                    'type': 'collision',
                    'vehicle_ids': [vehicles[i]['track_id'], vehicles[j]['track_id']],
                    'ttc_seconds': round(ttc, 2),
                    'collision_point_px': collision_pt,
                    'level': level,
                })
        return alerts

    def _ttc(self, v1: dict, v2: dict) -> Optional[tuple]:
        x1, y1 = v1['center']
        x2, y2 = v2['center']
        vx1, vy1 = v1['velocity']
        vx2, vy2 = v2['velocity']

        # Relative position and velocity (per frame)
        rx, ry = x2 - x1, y2 - y1
        rvx, rvy = vx2 - vx1, vy2 - vy1

        denom = rvx ** 2 + rvy ** 2
        if denom < 1e-6:
            return None  # vehicles not converging

        # Time of closest approach (in frames)
        t_frames = -(rx * rvx + ry * rvy) / denom
        if t_frames < 0 or t_frames > self.TTC_WARNING * self.fps:
            return None

        min_dist_px = np.hypot(rx + rvx * t_frames, ry + rvy * t_frames)
        # Only alert if vehicles will be within ~100px of each other
        if min_dist_px > 100:
            return None

        ttc_seconds = t_frames / self.fps
        col_x = x1 + vx1 * t_frames
        col_y = y1 + vy1 * t_frames
        return ttc_seconds, (round(col_x, 1), round(col_y, 1))
