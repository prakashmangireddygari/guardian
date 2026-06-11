import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

import cv2
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
import pathlib

_executor = ThreadPoolExecutor(max_workers=2)

load_dotenv()

from database import init_db, SessionLocal
from api.police import router as police_router
from api.public import router as public_router
from api.websocket import router as ws_router, manager
from api.stream import router as stream_router

_TEMPLATES = pathlib.Path(__file__).parent / 'templates'
from pipeline import pipeline
from services.db_service import save_violation, save_alert

_processing_task: asyncio.Task | None = None
_video_source = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    pipeline.close()


app = FastAPI(title='Guardian Traffic System', version='1.0.0', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(police_router)
app.include_router(public_router)
app.include_router(ws_router)
app.include_router(stream_router)


# ── Background video processing loop ─────────────────────────────────────────

async def _process_loop():
    """
    Reads frames at the video's native FPS.
    Detection runs in a thread-pool so the event loop stays free for streaming.
    """
    db   = SessionLocal()
    loop = asyncio.get_event_loop()

    cap_fps       = pipeline._cap.get(cv2.CAP_PROP_FPS) or 30
    frame_interval = 1.0 / cap_fps      # ideal seconds per frame

    try:
        while True:
            if pipeline._cap is None or not pipeline._cap.isOpened():
                await asyncio.sleep(0.05)
                continue

            t0 = loop.time()

            ret, frame = pipeline._cap.read()
            if not ret:
                await manager.broadcast({'type': 'video_ended'})
                break

            # Run CPU-bound detection in thread pool — doesn't block the event loop
            result = await loop.run_in_executor(_executor, pipeline.process_frame, frame)

            # Persist violations
            for evt in result.get('behavior_events', []):
                tid = evt['track_id']
                plate = next(
                    (v['plate'] for v in result['vehicles']
                     if v['track_id'] == tid and v['plate']),
                    f'UNKN-{tid}'
                )
                save_violation(db, plate, tid, evt['type'], evt.get('x'), evt.get('y'))

            # Persist critical alerts
            for a in result.get('distance_alerts', []):
                if a['level'] == 'DANGER':
                    save_alert(db, 'distance', 'DANGER', a['vehicle_ids'], a)
            for a in result.get('collision_alerts', []):
                if a['level'] == 'CRITICAL':
                    save_alert(db, 'collision', 'CRITICAL', a['vehicle_ids'], a)

            # Broadcast to WebSocket clients
            await manager.broadcast({
                'type':             'frame',
                'frame':            result['frame'],
                'vehicle_count':    result['vehicle_count'],
                'distance_alerts':  result['distance_alerts'],
                'collision_alerts': result['collision_alerts'],
                'behavior_events':  result['behavior_events'],
                'weather':          result['weather'],
                'scores':           result['scores'],
                'vehicles': [
                    {'track_id': v['track_id'], 'plate': v['plate'],
                     'score': v['score'], 'class': v['class']}
                    for v in result['vehicles']
                ],
            })

            # Sleep the remainder of the frame interval to match video speed
            elapsed = loop.time() - t0
            sleep   = frame_interval - elapsed
            if sleep > 0.001:
                await asyncio.sleep(sleep)

    finally:
        db.close()


# ── Control endpoints ─────────────────────────────────────────────────────────

@app.post('/video/upload')
async def upload_video(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    global _processing_task, _video_source
    tmp_path = f'/tmp/{file.filename}'
    with open(tmp_path, 'wb') as f:
        f.write(await file.read())
    _video_source = tmp_path
    return {'message': 'Video uploaded', 'path': tmp_path}


@app.post('/video/start')
async def start_processing():
    global _processing_task
    if _processing_task and not _processing_task.done():
        raise HTTPException(status_code=400, detail='Processing already running')
    if _video_source is None:
        raise HTTPException(status_code=400, detail='No video source. POST /video/upload first')
    pipeline.open(_video_source)
    _processing_task = asyncio.create_task(_process_loop())
    return {'message': 'Processing started'}


@app.post('/video/stop')
async def stop_processing():
    global _processing_task
    if _processing_task and not _processing_task.done():
        _processing_task.cancel()
    pipeline.close()
    return {'message': 'Processing stopped'}


@app.post('/video/camera/{camera_id}')
async def start_camera(camera_id: int = 0):
    global _video_source, _processing_task
    if _processing_task and not _processing_task.done():
        _processing_task.cancel()
        pipeline.close()
    _video_source = camera_id
    pipeline.open(camera_id)
    _processing_task = asyncio.create_task(_process_loop())
    return {'message': f'Camera {camera_id} started'}


# ── Weather endpoints ─────────────────────────────────────────────────────────

@app.get('/weather')
def get_weather():
    return pipeline.weather.status()


@app.post('/weather/scenario/{scenario_id}')
def set_weather_scenario(scenario_id: int):
    pipeline.weather.set_scenario(scenario_id)
    return pipeline.weather.status()


# ── Health ────────────────────────────────────────────────────────────────────

@app.get('/', include_in_schema=False)
def root():
    return RedirectResponse(url='/view')


@app.get('/view', include_in_schema=False, response_class=HTMLResponse)
def viewer():
    return HTMLResponse((_TEMPLATES / 'viewer.html').read_text())


@app.get('/health')
def health():
    return {
        'status': 'ok',
        'frame': pipeline.frame_num,
        'processing': bool(_processing_task and not _processing_task.done()),
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=False)
