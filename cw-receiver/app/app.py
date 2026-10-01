import asyncio
import os
import subprocess
import threading
import time
from pathlib import Path

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cw import CWDecoder

FREQUENCY = int(os.getenv('FREQUENCY', '7050000'))
SAMPLE_RATE = int(os.getenv('SAMPLE_RATE', '12000'))
PPM = int(os.getenv('PPM', '0'))
RTL_DEVICE = os.getenv('RTL_DEVICE', '0')
CW_TONE = int(os.getenv('CW_TONE', '700'))
CW_WPM = int(os.getenv('CW_WPM', '18'))

app = FastAPI(title='TT-CW')
app.mount('/static', StaticFiles(directory='static'), name='static')

lock = threading.Lock()
state = {'frequency': FREQUENCY, 'running': False, 'error': None, 'started': None}
decoder = CWDecoder(SAMPLE_RATE, CW_TONE, CW_WPM)
proc = None
worker = None

class TuneRequest(BaseModel):
    frequency: int


def rtl_command(freq):
    return [
        'rtl_fm', '-d', RTL_DEVICE, '-f', str(freq), '-M', 'usb',
        '-s', str(SAMPLE_RATE), '-r', str(SAMPLE_RATE), '-p', str(PPM),
        '-E', 'direct2', '-E', 'dc', '-'
    ]


def stop_receiver():
    global proc
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    proc = None
    state['running'] = False


def receiver_loop():
    global proc
    while True:
        freq = state['frequency']
        try:
            cmd = rtl_command(freq)
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
            state.update(running=True, error=None, started=time.time())
            while proc.poll() is None and freq == state['frequency']:
                data = proc.stdout.read(SAMPLE_RATE * 2 // 4)
                if not data:
                    break
                samples = np.frombuffer(data, dtype='<i2')
                with lock:
                    decoder.feed(samples)
            stop_receiver()
        except Exception as exc:
            state.update(running=False, error=str(exc))
            time.sleep(3)
        time.sleep(0.2)


@app.on_event('startup')
def startup():
    global worker
    worker = threading.Thread(target=receiver_loop, daemon=True)
    worker.start()


@app.on_event('shutdown')
def shutdown():
    stop_receiver()


@app.get('/')
def index():
    return FileResponse(Path('static/index.html'))


@app.get('/api/status')
def status():
    with lock:
        d = decoder.snapshot()
    return {**state, **d, 'sample_rate': SAMPLE_RATE, 'ppm': PPM, 'device': RTL_DEVICE}


@app.post('/api/tune')
def tune(req: TuneRequest):
    if not 500000 <= req.frequency <= 28800000:
        return {'ok': False, 'error': 'Frequency must be between 500 kHz and 28.8 MHz for V3 direct sampling.'}
    state['frequency'] = req.frequency
    stop_receiver()
    return {'ok': True, 'frequency': req.frequency}


@app.get('/api/rtl-test')
def rtl_test():
    try:
        p = subprocess.run(['rtl_test', '-t'], capture_output=True, text=True, timeout=8)
        return {'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
    except Exception as exc:
        return {'returncode': -1, 'stdout': '', 'stderr': str(exc)}


@app.websocket('/ws')
async def websocket(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            with lock:
                d = decoder.snapshot()
            await ws.send_json({**state, **d})
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        pass
