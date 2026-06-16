import numpy as np
import torch
from ultralytics import YOLO

# Auto-select fastest available device: CUDA > MPS (Apple Silicon) > CPU
if torch.cuda.is_available():
    _DEVICE = 'cuda'
elif torch.backends.mps.is_available():
    _DEVICE = 'mps'
else:
    _DEVICE = 'cpu'

# FP16 is stable on CUDA; MPS FP16 is still unreliable in many PyTorch builds
_HALF = (_DEVICE == 'cuda')

# YOLO class IDs to track
TRACKED_CLASSES = {
    0: 'person',
    1: 'bicycle',
    2: 'car',
    3: 'motorcycle',
    5: 'bus',
    7: 'truck',
}

VEHICLE_CLASSES = {2, 3, 5, 7}

# imgsz=480 is the sweet spot: detects people reliably, ~40% faster than 640
_IMGSZ = 480


class VehicleDetector:
    def __init__(self, model_path='yolov8n.pt', confidence=0.35):
        self.model = YOLO(model_path)
        self.confidence = confidence
        print(f'[Guardian] Detector running on: {_DEVICE.upper()}  half={_HALF}  imgsz={_IMGSZ}')
        # Warm up so the first real frame is not slow
        dummy = np.zeros((480, 640, 3), dtype=np.uint8)
        self.model(dummy, verbose=False, imgsz=_IMGSZ, half=_HALF, device=_DEVICE)

    def detect(self, frame: np.ndarray) -> list:
        results = self.model(
            frame, verbose=False,
            imgsz=_IMGSZ, half=_HALF, device=_DEVICE
        )[0]
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
