import datetime as dt
import os
import re
import sqlite3
import subprocess
import threading
from contextlib import closing

from fastapi import FastAPI, HTTPException, Query

DB_PATH = os.getenv("DB_PATH", "/data/aprs.db")
FREQUENCY = os.getenv("APRS_FREQUENCY", "144.390M")
SAMPLE_RATE = os.getenv("RTL_SAMPLE_RATE", "22050")
GAIN = os.getenv("RTL_GAIN", "auto")
PPM = os.getenv("RTL_PPM", "0")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8080"))

app = FastAPI(title="TT APRS API", version="0.1.0")

PACKET_RE = re.compile(
    r"(?P<from>[A-Z0-9]{1,6}(?:-[0-9]{1,2})?)>"
    r"(?P<header>[^:\s]+):(?P<payload>.*)$"
)


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with closing(get_db()) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS packets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                received_at TEXT NOT NULL,
                from_callsign TEXT NOT NULL,
                to_callsign TEXT,
                path TEXT,
                payload TEXT NOT NULL,
                raw_packet TEXT NOT NULL
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_packets_received_at "
            "ON packets(received_at DESC)"
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_packets_from "
            "ON packets(from_callsign)"
        )
        db.commit()


def save_packet(packet):
    with closing(get_db()) as db:
        db.execute(
            """
            INSERT INTO packets
                (received_at, from_callsign, to_callsign, path, payload, raw_packet)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                dt.datetime.now(dt.timezone.utc).isoformat(),
                packet["from_callsign"],
                packet["to_callsign"],
                packet["path"],
                packet["payload"],
                packet["raw_packet"],
            ),
        )
        db.commit()


def parse_packet(raw):
    match = PACKET_RE.search(raw.strip())
    if not match:
        return None

    header = match.group("header")
    parts = header.split(",")

    return {
        "from_callsign": match.group("from"),
        "to_callsign": parts[0] if parts else None,
        "path": ",".join(parts[1:]) if len(parts) > 1 else None,
        "payload": match.group("payload"),
        "raw_packet": (
            f"{match.group('from')}>{header}:{match.group('payload')}"
        ),
    }


def decoder_loop():
    gain_args = [] if GAIN.lower() == "auto" else ["-g", GAIN]

    rtl_cmd = [
        "rtl_fm",
        "-f", FREQUENCY,
        "-s", SAMPLE_RATE,
        "-p", PPM,
        *gain_args,
        "-",
    ]

    direwolf_cmd = [
        "direwolf",
        "-c", "/app/direwolf.conf",
        "-r", SAMPLE_RATE,
        "-t", "0",
    ]

    print("Starting RTL-SDR:", " ".join(rtl_cmd), flush=True)
    print("Starting Dire Wolf:", " ".join(direwolf_cmd), flush=True)

    rtl = subprocess.Popen(
        rtl_cmd,
        stdout=subprocess.PIPE,
        stderr=None,
    )

    direwolf = subprocess.Popen(
        direwolf_cmd,
        stdin=rtl.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    assert rtl.stdout is not None
    rtl.stdout.close()
    assert direwolf.stdout is not None

    for line in direwolf.stdout:
        line = line.rstrip()
        print(line, flush=True)

        packet = parse_packet(line)
        if packet:
            save_packet(packet)
            print(
                f"APRS packet saved: "
                f"{packet['from_callsign']} -> {packet['to_callsign']}",
                flush=True,
            )


@app.on_event("startup")
def startup():
    init_db()
    threading.Thread(target=decoder_loop, daemon=True).start()


@app.get("/api/health")
def health():
    with closing(get_db()) as db:
        count = db.execute("SELECT COUNT(*) FROM packets").fetchone()[0]

    return {
        "status": "ok",
        "packets_stored": count,
        "frequency": FREQUENCY,
    }


@app.get("/api/packets")
def packets(
    limit: int = Query(default=100, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    callsign: str | None = Query(default=None, pattern=r"^[A-Za-z0-9]{1,6}(?:-[0-9]{1,2})?$"),
):
    where_clause = ""
    parameters = []
    if callsign:
        where_clause = "WHERE UPPER(from_callsign) = UPPER(?)"
        parameters.append(callsign)

    with closing(get_db()) as db:
        rows = db.execute(
            f"""
            SELECT id, received_at, from_callsign, to_callsign,
                   path, payload, raw_packet
            FROM packets
            {where_clause}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (*parameters, limit, offset),
        ).fetchall()

    return {
        "count": len(rows),
        "limit": limit,
        "offset": offset,
        "callsign": callsign.upper() if callsign else None,
        "packets": [dict(row) for row in rows],
    }


@app.get("/api/packets/{packet_id}")
def packet(packet_id: int):
    with closing(get_db()) as db:
        row = db.execute(
            """
            SELECT id, received_at, from_callsign, to_callsign,
                   path, payload, raw_packet
            FROM packets
            WHERE id = ?
            """,
            (packet_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Packet not found")

    return dict(row)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
