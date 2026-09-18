# APRS Collector and BBS Lookup

This enhancement makes packets received by a local APRS receiver available to
Meshtastic users through the BBS. It is **receive-only**: the collector decodes
nearby APRS traffic, saves it locally, and the BBS returns saved packets only
when a user sends an APRS command.

```text
APRS RF traffic
      ↓
RTL-SDR USB receiver
      ↓
rtl_fm + Dire Wolf in the tt-aprs container
      ↓
SQLite database (aprs.db)
      ↓
APRS HTTP API on port 8080
      ↓
TT-BBSmesh-Plus APRS command
      ↓
Meshtastic direct message
```

The collector does not transmit APRS packets, connect to APRS-IS, or provide a
map. It keeps reception local to the receiver and the BBS host.

## Requirements

- A Linux host with Docker and Docker Compose.
- An RTL-SDR USB receiver and a suitable antenna for the local APRS frequency.
- Permission for Docker to access the RTL-SDR. The supplied Compose file maps
  `/dev/bus/usb` into the collector container.
- The BBS host must be able to reach the collector API. By default both are on
  the same host, using `http://127.0.0.1:8080`.

The supplied configuration is for the North American APRS frequency,
**144.390 MHz**. Confirm the appropriate APRS frequency for the area where the
receiver is deployed before changing the collector configuration.

## Start the collector

From the repository root, build and start the collector:

```bash
cd Tools/docker/aprs
mkdir -p data
docker compose up -d --build
```

Confirm that it started and that the API can see the local database:

```bash
docker compose ps
docker compose logs -f aprs
curl http://127.0.0.1:8080/api/health
```

The health response includes the number of packets stored. A count of zero is
normal until the receiver has decoded APRS traffic.

The database is persisted in `Tools/docker/aprs/data/aprs.db`. To stop the
collector without deleting stored packets, run:

```bash
docker compose down
```

## Configure the BBS

No configuration is required when the BBS and collector are on the same host:
the BBS defaults to `http://127.0.0.1:8080`.

If the collector runs on another machine, add the following to the BBS
`config.ini`, replacing the address with the collector host's reachable IP
address or hostname:

```ini
[aprs]
api_url = http://192.168.1.50:8080
```

Restart the BBS after changing its configuration. Keep this API on a trusted
local network; it exposes received packet data and has no authentication.

## BBS commands

Send these as direct messages to the BBS node. APRS commands work from any BBS
menu because they do not require entering a separate menu first.

| Command | Result |
| --- | --- |
| `APRS` | Shows command help. |
| `APRS LATEST` | Returns the most recent 100 received packets. |
| `APRS LATEST 25` | Returns the most recent 25 packets. Choose a value from 1 through 100. |
| `APRS N0CALL` | Returns up to 100 packets received from `N0CALL`. |
| `APRS K7ABC-9` | Looks up a callsign with an SSID. |

Callsign lookups are case-insensitive. A callsign must contain one to six
letters or digits, with an optional SSID from `-0` through `-99`.

Each result contains the receive time, source callsign, destination callsign,
path (or `direct`), and packet payload. Replies are split into Meshtastic-sized
messages automatically. Requesting 100 packets can therefore produce many
messages and take some time; request a smaller count when practical.

## Collector API

The BBS uses the collector's packet endpoint. These commands are also useful
for checking the collector independently of the BBS:

```bash
# Most recent 100 packets
curl 'http://127.0.0.1:8080/api/packets?limit=100'

# Packets from one station; matching is case-insensitive
curl 'http://127.0.0.1:8080/api/packets?callsign=N0CALL&limit=100'

# Continue after the first 100 packets
curl 'http://127.0.0.1:8080/api/packets?limit=100&offset=100'

# Retrieve a single stored packet by database ID
curl 'http://127.0.0.1:8080/api/packets/123'
```

The API accepts `limit` values from 1 through 5000. The BBS deliberately caps
its replies at 100 packets to avoid overwhelming the mesh.

## Collector settings

Edit `Tools/docker/aprs/docker-compose.yml` before starting the container to
change receiver settings:

| Setting | Default | Purpose |
| --- | --- | --- |
| `APRS_FREQUENCY` | `144.390M` | Frequency passed to `rtl_fm`. |
| `RTL_SAMPLE_RATE` | `22050` | Decoder audio sample rate. |
| `RTL_GAIN` | `auto` | RTL-SDR gain, or `auto` for automatic gain. |
| `RTL_PPM` | `0` | Frequency correction for the RTL-SDR. |
| `API_PORT` | `8080` | HTTP API port inside the container. |

If another SDR application is using the same RTL-SDR, stop it before starting
the APRS collector or use a separate receiver.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `APRS service is unavailable` from the BBS | Confirm `docker compose ps` shows the collector running, check the API URL in `[aprs]`, and use `curl .../api/health` from the BBS host. |
| Health reports zero packets | Check the antenna, local APRS frequency, RTL-SDR access, and `docker compose logs -f aprs` for Dire Wolf decoder output. |
| Docker cannot open the RTL-SDR | Confirm the host can see the device (for example, `lsusb`) and that no other process owns it. |
| A callsign lookup has no results | The collector only searches packets it received locally. Check the callsign spelling and try `APRS LATEST 10` to confirm recent packets are being stored. |
| APRS replies are slow or numerous | Use `APRS LATEST 10` or another smaller count. Each reply is split to fit Meshtastic message limits. |
