import numpy as np
from typing import List

DEFAULT_PX_TO_METER = 0.05  # calibrate per camera in production


class DistanceMonitor:
    def __init__(self, px_to_meter: float = DEFAULT_PX_TO_METER):
        self.px_to_meter = px_to_meter
        self._base_safe = 20.0
        self._base_warn = 10.0
        self._base_danger = 5.0
        self._multiplier = 1.0

    def set_weather_multiplier(self, multiplier: float):
        self._multiplier = multiplier

    @property
    def safe_dist(self): return self._base_safe * self._multiplier
    @property
    def warn_dist(self): return self._base_warn * self._multiplier
    @property
    def danger_dist(self): return self._base_danger * self._multiplier

    def compute(self, vehicles: List[dict]) -> List[dict]:
        alerts = []
        n = len(vehicles)
        for i in range(n):
            for j in range(i + 1, n):
                v1, v2 = vehicles[i], vehicles[j]
                px_dist = np.hypot(
                    v2['center'][0] - v1['center'][0],
                    v2['center'][1] - v1['center'][1]
                )
                real_m = px_dist * self.px_to_meter
                level = self._level(real_m)
                if level:
                    alerts.append({
                        'type': 'distance',
                        'vehicle_ids': [v1['track_id'], v2['track_id']],
                        'distance_m': round(real_m, 2),
                        'level': level,
                        'midpoint': (
                            (v1['center'][0] + v2['center'][0]) / 2,
                            (v1['center'][1] + v2['center'][1]) / 2,
                        ),
                    })
        return alerts

    def _level(self, dist_m: float) -> str | None:
        if dist_m <= self.danger_dist:
            return 'DANGER'
        if dist_m <= self.warn_dist:
            return 'WARNING'
        if dist_m <= self.safe_dist:
            return 'CAUTION'
        return None
