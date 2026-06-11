import asyncio
import time
import numpy as np
import cv2

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(tags=['stream'])

_NO_SIGNAL: bytes | None = None


def _no_signal_frame() -> bytes:
    global _NO_SIGNAL
    if _NO_SIGNAL is None:
        img = np.zeros((480, 854, 3), dtype=np.uint8)
        cv2.putText(img, 'No video source', (250, 220),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (80, 80, 80), 2)
        cv2.putText(img, 'Upload a video and press Start', (190, 265),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 60), 1)
        _, buf = cv2.imencode('.jpg', img)
        _NO_SIGNAL = buf.tobytes()
    return _NO_SIGNAL


async def _mjpeg_generator():
    from pipeline import pipeline
    while True:
        frame_bytes = pipeline.latest_jpeg or _no_signal_frame()
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n'
            + frame_bytes +
            b'\r\n'
        )
        await asyncio.sleep(1 / 30)  # ~30 fps


@router.get('/video/stream')
async def mjpeg_stream():
    return StreamingResponse(
        _mjpeg_generator(),
        media_type='multipart/x-mixed-replace; boundary=frame',
    )
