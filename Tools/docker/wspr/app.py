"""Local, receive-only WSPR collector for an RTL-SDR."""

import datetime as dt
import os
import re
import sqlite3
import subprocess
import threading
import time
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

DB_PATH = os.getenv("DB_PATH", "/data/wspr.db")
FREQUENCY = os.getenv("WSPR_FREQUENCY", "14.0971M")
SAMPLE_RATE = os.getenv("RTL_SAMPLE_RATE", "12000")
GAIN = os.getenv("RTL_GAIN", "auto")
PPM = os.getenv("RTL_PPM", "0")
CYCLE_SECONDS = int(os.getenv("WSPR_CYCLE_SECONDS", "114"))
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8082"))
CAPTURE_PATH = Path("/tmp/wspr/capture.wav")

app = FastAPI(title="TT WSPR API", version="0.1.0")
decoder_state = {"last_decode_at": None, "last_error": None}

# wsprd output begins with date, UTC time, SNR, DT, frequency, drift, call,
# locator and power.  Callsigns and locators can contain a few special values,
# so capture the first six numeric columns and retain the remaining fields.
SPOT_RE = re.compile(
    r"^\s*(?P<date>\d{6})\s+(?P<time>\d{4})\s+"
    r"(?P<snr>-?\d+)\s+(?P<dt>-?\d+(?:\.\d+)?)\s+"
    r"(?P<frequency>\d+(?:\.\d+)?)\s+(?P<drift>-?\d+)\s+"
    r"(?P<callsign>\S+)\s+(?P<locator>\S+)\s+(?P<power>-?\d+)\s*$"
)


def get_db():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with closing(get_db()) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS spots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                received_at TEXT NOT NULL,
                spot_time TEXT NOT NULL,
                snr INTEGER NOT NULL,
                dt REAL NOT NULL,
                frequency REAL NOT NULL,
                drift INTEGER NOT NULL,
                callsign TEXT NOT NULL,
                locator TEXT NOT NULL,
                power INTEGER NOT NULL,
                raw_spot TEXT NOT NULL,
                UNIQUE(spot_time, frequency, callsign, locator, power, snr, dt)
            )
            """
        )
        db.execute("CREATE INDEX IF NOT EXISTS idx_spots_time ON spots(spot_time DESC)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_spots_call ON spots(callsign)")
        db.commit()


def parse_spot(line):
    """Return a normalized wsprd spot dict, or None for decoder diagnostics."""
    match = SPOT_RE.match(line)
    if not match:
        return None
    fields = match.groupdict()
    try:
        spot_time = dt.datetime.strptime(
            f"20{fields['date']} {fields['time']}", "%Y%m%d %H%M"
        ).replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None
    return {
        "spot_time": spot_time.isoformat(),
        "snr": int(fields["snr"]),
        "dt": float(fields["dt"]),
        "frequency": float(fields["frequency"]),
        "drift": int(fields["drift"]),
        "callsign": fields["callsign"].upper(),
        "locator": fields["locator"].upper(),
        "power": int(fields["power"]),
        "raw_spot": line.strip(),
    }


def save_spot(spot):
    with closing(get_db()) as db:
        cursor = db.execute(
            """
            INSERT OR IGNORE INTO spots
                (received_at, spot_time, snr, dt, frequency, drift, callsign,
                 locator, power, raw_spot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (dt.datetime.now(dt.timezone.utc).isoformat(), *spot.values()),
        )
        db.commit()
        return cursor.rowcount == 1


def wait_for_cycle():
    """Begin a capture on the next even UTC minute, as required by WSPR."""
    now = time.time()
    next_cycle = (int(now // 120) + 1) * 120
    time.sleep(max(0, next_cycle - now))


def capture_and_decode():
    gain_args = [] if GAIN.lower() == "auto" else ["-g", GAIN]

    # WSPR uses USB audio tones on HF. Direct sampling lets compatible RTL-SDR
    # devices tune below 28 MHz without an external upconverter.
    rtl_command = [
        "rtl_fm", "-E", "direct", "-M", "usb", "-f", FREQUENCY,
        "-s", SAMPLE_RATE, "-r", SAMPLE_RATE, "-p", PPM, *gain_args, "-",
    ]
    sox_command = [
        "sox", "-t", "raw", "-r", SAMPLE_RATE, "-e", "signed-integer",
        "-b", "16", "-c", "1", "-L", "-", str(CAPTURE_PATH),
        "trim", "0", str(CYCLE_SECONDS),
    ]
    print("Capturing WSPR cycle:", " ".join(rtl_command), flush=True)
    rtl = subprocess.Popen(rtl_command, stdout=subprocess.PIPE, stderr=None)
    try:
        subprocess.run(sox_command, stdin=rtl.stdout, check=True)
    finally:
        if rtl.stdout:
            rtl.stdout.close()
        rtl.terminate()
        try:
            rtl.wait(timeout=5)
        except subprocess.TimeoutExpired:
            rtl.kill()

    result = subprocess.run(
        ["wsprd", "-d", str(CAPTURE_PATH)], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout.strip() or "wsprd failed")
    saved = 0
    for line in result.stdout.splitlines():
        print(line, flush=True)
        spot = parse_spot(line)
        if spot and save_spot(spot):
            saved += 1
    decoder_state["last_decode_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    decoder_state["last_error"] = None
    print(f"WSPR decode complete: {saved} new spots", flush=True)


def decoder_loop():
    while True:
        try:
            wait_for_cycle()
            capture_and_decode()
        except Exception as error:  # Keep the receive service available after SDR errors.
            decoder_state["last_error"] = str(error)
            print(f"WSPR decoder error: {error}", flush=True)
            time.sleep(10)


@app.on_event("startup")
def startup():
    init_db()
    threading.Thread(target=decoder_loop, daemon=True).start()


@app.get("/api/health")
def health():
    with closing(get_db()) as db:
        count = db.execute("SELECT COUNT(*) FROM spots").fetchone()[0]
    return {"status": "ok", "spots_stored": count, "frequency": FREQUENCY, **decoder_state}


@app.get("/api/spots")
def spots(
    limit: int = Query(default=100, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    callsign: str | None = Query(default=None, pattern=r"^[A-Za-z0-9/]{1,16}$"),
):
    where, parameters = "", []
    if callsign:
        where, parameters = "WHERE UPPER(callsign) = UPPER(?)", [callsign]
    with closing(get_db()) as db:
        rows = db.execute(
            f"SELECT * FROM spots {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            (*parameters, limit, offset),
        ).fetchall()
    return {"count": len(rows), "limit": limit, "offset": offset,
            "callsign": callsign.upper() if callsign else None,
            "spots": [dict(row) for row in rows]}


@app.get("/api/spots/{spot_id}")
def spot(spot_id: int):
    with closing(get_db()) as db:
        row = db.execute("SELECT * FROM spots WHERE id = ?", (spot_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Spot not found")
    return dict(row)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
