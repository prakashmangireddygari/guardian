from collections import defaultdict, deque
from typing import List
import numpy as np

DANGER_POINTS = {
    'sudden_braking': 15,
    'weaving': 20,
    'tailgating': 25,
    'amber_running': 10,
    'school_zone_speed': 30,
}

# Cooldown in frames before the same violation can score again
VIOLATION_COOLDOWN = 90  # 3s at 30fps


class BehaviorScorer:
    def __init__(self, fps: float = 30.0, tailgate_distance_m: float = 8.0):
        self.fps = fps
        self.tailgate_distance_m = tailgate_distance_m
        self.tailgate_frames_required = int(1.5 * fps)

        self.scores: dict[int, int] = defaultdict(int)
        self.events: dict[int, list] = defaultdict(list)
        self.velocity_hist: dict[int, deque] = defaultdict(lambda: deque(maxlen=30))
        self.position_hist: dict[int, deque] = defaultdict(lambda: deque(maxlen=30))
        self.tailgate_counter: dict[int, int] = defaultdict(int)

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, vehicles: List[dict], frame_num: int, distance_alerts: List[dict]) -> List[dict]:
        new_events = []

        for v in vehicles:
            tid = v['track_id']
            vx, vy = v['velocity']
            cx, cy = v['center']
            self.velocity_hist[tid].append((vx, vy))
            self.position_hist[tid].append((cx, cy))

            if self._detect_braking(tid):
                evt = self._record(tid, 'sudden_braking', frame_num, cx, cy)
                if evt:
                    new_events.append(evt)

            if self._detect_weaving(tid):
                evt = self._record(tid, 'weaving', frame_num, cx, cy)
                if evt:
                    new_events.append(evt)

        # Tailgating: persistent close proximity
        close_pairs: set[int] = set()
        for alert in distance_alerts:
            if alert['distance_m'] <= self.tailgate_distance_m:
                close_pairs.update(alert['vehicle_ids'])

        for v in vehicles:
            tid = v['track_id']
            if tid in close_pairs:
                self.tailgate_counter[tid] += 1
                if self.tailgate_counter[tid] == self.tailgate_frames_required:
                    evt = self._record(tid, 'tailgating', frame_num, *v['center'])
                    if evt:
                        new_events.append(evt)
            else:
                self.tailgate_counter[tid] = max(0, self.tailgate_counter[tid] - 1)

        return new_events

    def flag_amber_running(self, tid: int, frame_num: int, cx: float, cy: float) -> dict | None:
        return self._record(tid, 'amber_running', frame_num, cx, cy)

    def flag_school_zone_speed(self, tid: int, frame_num: int, cx: float, cy: float) -> dict | None:
        return self._record(tid, 'school_zone_speed', frame_num, cx, cy)

    def get_score(self, tid: int) -> int:
        return self.scores[tid]

    def get_all_scores(self) -> dict:
        return dict(self.scores)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _record(self, tid: int, vtype: str, frame_num: int, cx: float, cy: float) -> dict | None:
        recent = [e for e in self.events[tid]
                  if e['type'] == vtype and frame_num - e['frame'] < VIOLATION_COOLDOWN]
        if recent:
            return None
        pts = DANGER_POINTS[vtype]
        self.scores[tid] += pts
        entry = {'type': vtype, 'frame': frame_num, 'pts': pts, 'x': cx, 'y': cy}
        self.events[tid].append(entry)
        return {'track_id': tid, **entry}

    def _detect_braking(self, tid: int) -> bool:
        hist = list(self.velocity_hist[tid])
        if len(hist) < 6:
            return False
        speeds = [np.hypot(vx, vy) for vx, vy in hist]
        # Deceleration = change in speed per frame over last 5 frames
        decel = (speeds[-1] - speeds[-6]) / 5
        return decel < -4.0  # px/frame² threshold

    def _detect_weaving(self, tid: int) -> bool:
        hist = list(self.position_hist[tid])
        if len(hist) < 10:
            return False
        xs = [p[0] for p in hist[-10:]]
        changes = sum(
            1 for k in range(1, len(xs) - 1)
            if (xs[k] - xs[k - 1]) * (xs[k + 1] - xs[k]) < 0
        )
        lateral_range = max(xs) - min(xs)
        return changes >= 3 and lateral_range > 15.0
