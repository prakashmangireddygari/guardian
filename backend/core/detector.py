from ultralytics import YOLO
import numpy as np

# YOLO class IDs to track
TRACKED_CLASSES = {
    0: 'person',
    1: 'bicycle',
    2: 'car',
    3: 'motorcycle',
    5: 'bus',
    7: 'truck',
}

# Classes that should get plate detection attempted
VEHICLE_CLASSES = {2, 3, 5, 7}


class VehicleDetector:
    def __init__(self, model_path='yolov8n.pt', confidence=0.45):
        self.model = YOLO(model_path)
        self.confidence = confidence

    def detect(self, frame: np.ndarray) -> list:
        results = self.model(frame, verbose=False)[0]
        detections = []
        for box in results.boxes:
            cls = int(box.cls[0])
            if cls not in TRACKED_CLASSES:
                continue
            conf = float(box.conf[0])
            if conf < self.confidence:
                continue
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append({
                'bbox': [x1, y1, x2, y2],
                'class': TRACKED_CLASSES[cls],
                'confidence': conf,
                'is_vehicle': cls in VEHICLE_CLASSES,
            })
        return detections
