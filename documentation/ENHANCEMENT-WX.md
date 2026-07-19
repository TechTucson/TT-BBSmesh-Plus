# Weatherstac NOAA Weather Transcription Workflow

Weatherstac is intended to bridge local NOAA Weather Radio audio into the Meshtastic text workflow used by the BBS. It does this in two stages:

1. A Docker Compose stack runs an RTL-SDR receiver service and a small FastAPI service.
2. `wxparser.py` queries the FastAPI history endpoint and prints recent weather entries as text that can be copied, scripted, or relayed through Meshtastic/BBS workflows.

## Components

### RTL-SDR transcription container

The `weatherstac/sdr` container is the collector. It expects an RTL-SDR USB dongle to be available to Docker and continuously scans the NOAA Weather Radio frequencies:

- 162.400 MHz
- 162.425 MHz
- 162.450 MHz
- 162.475 MHz
- 162.500 MHz
- 162.525 MHz
- 162.550 MHz

For each frequency, the container:

1. Uses `rtl_fm` to receive narrowband FM audio from the RTL-SDR.
2. Pipes the raw audio into `sox` and records a short WAV sample at `/tmp/audio.wav`.
3. Runs `multimon-ng` against the sample to detect SAME alert data.
4. Runs Whisper speech-to-text against the same sample to transcribe spoken weather audio.
5. Stores any decoded SAME messages or transcribed voice text in `/data/weather.db`.

The database table created by the collector is named `messages` and includes:

| Column | Purpose |
| --- | --- |
| `id` | Auto-incrementing message ID. |
| `ts` | SQLite timestamp for when the row was inserted. |
| `freq` | NOAA frequency being sampled when the message was captured. |
| `type` | Message type, normally `same` or `voice`. |
| `content` | The decoded SAME data or Whisper transcript text. |

### FastAPI history service

The `weatherstac/api` container exposes the SQLite database over HTTP. Docker Compose maps the API to host port `9000`, while the container listens on port `8000`.

Useful endpoints:

| Endpoint | Use |
| --- | --- |
| `GET /latest` | Returns the newest row from the `messages` table. |
| `GET /history?limit=50` | Returns recent rows, newest first, with a default limit of 50. |
| `WS /ws` | Streams new message content over a websocket. |
| `GET /` | Minimal dashboard placeholder. |

Both the `sdr` and `api` services mount the same Docker volume named `data`, so the API can read the database populated by the SDR collector.

### `wxparser.py`

`wxparser.py` is the text-side consumer. By default it calls:

```text
http://localhost:9000/history
```

It then prints the most recent weather entries in a readable format:

```text
ID: 12
Time: 2026-07-19 15:30:00
Content: ...transcribed weather message...
------------------------------------------------------------
```

The script accepts one optional argument for how many recent entries to display. If no argument is supplied it shows the last entry. It caps the display count at five entries.

## Expected deployment

Run Weatherstac on a machine that has:

- An RTL-SDR compatible USB receiver.
- Docker and Docker Compose.
- USB device access from Docker.
- Network access from the Meshtastic/BBS host to the API port, or `wxparser.py` running on the same host as the API.
- A NOAA Weather Radio signal that is strong enough for transcription.

The most common layout is:

```text
NOAA Weather Radio broadcast
        ↓
RTL-SDR USB dongle
        ↓
weatherstac sdr container
        ↓
/data/weather.db shared Docker volume
        ↓
weatherstac api container on http://localhost:9000
        ↓
wxparser.py
        ↓
Meshtastic/BBS text workflow
```

## Basic usage

1. Start the Docker stack from the `Tools/docker/weatherstac` directory in the companion tools repository:

   ```bash
   docker compose up -d --build
   ```

2. Confirm both containers are running:

   ```bash
   docker compose ps
   ```

3. Check the API from the host:

   ```bash
   curl http://localhost:9000/latest
   curl 'http://localhost:9000/history?limit=5'
   ```

4. Run the parser to display the newest decoded/transcribed message:

   ```bash
   python3 wxparser.py
   ```

5. Display up to five recent messages when needed:

   ```bash
   python3 wxparser.py 5
   ```

6. Use the printed `Content` text as the weather payload for your Meshtastic/BBS workflow. The parser does not transmit by itself; it makes the captured weather audio available as text so another script, menu option, or operator can send it through the mesh.

## Operational notes

- The first startup may take longer because the SDR image installs CPU-only PyTorch and Whisper dependencies.
- Whisper transcription is CPU-intensive. Slower hardware may lag behind real-time audio capture.
- Duplicate or partial messages are possible because the collector repeatedly samples each NOAA frequency in short windows.
- SAME alert rows and voice transcript rows are both stored. Check the `type` field if your integration needs to treat alert codes differently than spoken forecasts.
- If the API is not on the same host as `wxparser.py`, update `API_URL` in `wxparser.py` to point at the correct hostname or IP address and port.
- Keep the antenna and RTL-SDR placement in mind. Poor reception will produce poor transcripts.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `wxparser.py` prints `Error fetching data from API` | Make sure the API container is running and reachable on port `9000`. |
| `/history` returns an empty list | Let the SDR container run longer, confirm the RTL-SDR is passed through to Docker, and verify NOAA reception. |
| SDR container exits or cannot open the device | Confirm `/dev/bus/usb` is mapped into the container and the host can see the RTL-SDR. |
| Transcripts are garbled | Improve antenna placement, reduce RF noise, or verify the strongest local NOAA frequency. |
| Messages are available through curl but not useful for the mesh | Confirm your Meshtastic/BBS integration is consuming the `Content` text, not the entire database row. |

## Integration expectations

Weatherstac and `wxparser.py` intentionally keep responsibilities separate:

- Weatherstac records, decodes, transcribes, stores, and serves weather messages.
- `wxparser.py` retrieves a small number of recent rows and formats them for humans or simple scripts.
- The Meshtastic/BBS side decides when and how to send the text across the mesh.

This separation makes it possible to run the SDR receiver continuously while only posting to the mesh on demand, on a schedule, or when an operator decides a weather update is useful.
