# TT APRS Web Monitor

Offline web monitor for the TT APRS collector.

This service displays locally received APRS packets and plots packets containing
decoded position data on an offline map.

## Architecture

```
RTL-SDR
   |
   v
rtl_fm
   |
   v
Dire Wolf
   |
   v
tt-aprs :8090
   |
   v
SQLite
   |
   +--------------------+
   |                    |
   v                    v
APRS API            tt-aprs-web :8091
                         |
                         +--> nginx
                         |     |
                         |     +--> /api/ -> tt-aprs :8090
                         |     |
                         |     +--> /tiles/ -> TileServer GL
                         |
                         v
                    Browser / APRS map
                         ^
                         |
                 map.mbtiles (local)
```

The web container does **not** access the APRS SQLite database directly.
It calls the collector API.

## Components

### APRS collector

The collector is the RF receiver/decoder and local API.

- RTL-SDR receives 144.390 MHz APRS
- `rtl_fm` converts the RF signal to audio
- Dire Wolf decodes 1200-baud AX.25/APRS
- Python stores packets in SQLite
- FastAPI exposes the packet API
- Collector API is normally available on port **8090**

### APRS web monitor

The web monitor is an nginx container.

- Port **8091** on the DietPi host
- Calls the collector through `/api/`
- Displays the most recent packets
- Extracts standard uncompressed APRS positions
- Plots stations on the local map
- Refreshes every 5 seconds

### Offline map

The map uses an Arizona OpenStreetMap extract from Geofabrik in
**Shortbread vector MBTiles** format.

TileServer GL runs locally and renders those vector tiles into PNG tiles for
the lightweight APRS web map.

No Internet map requests are made by the browser.

## Download the Arizona map

From this directory:

```bash
cd Tools/docker/aprs-web
bash download-map.sh
```

The script downloads:

```
https://download.geofabrik.de/north-america/us/arizona-shortbread-1.0.mbtiles
```

and saves it as:

```
Tools/docker/aprs-web/data/map.mbtiles
```

The Arizona Shortbread extract is a vector MBTiles dataset. It covers the
entire state, including Tucson and Southern Arizona.

If you prefer to download it manually:

```bash
mkdir -p data
wget -c -O data/map.mbtiles \
  https://download.geofabrik.de/north-america/us/arizona-shortbread-1.0.mbtiles
```

## Start or rebuild the web service

After the map has been downloaded:

```bash
docker compose down
docker compose up -d --build
```

Check the containers:

```bash
docker ps
```

You should see:

- `tt-aprs-web`
- `tt-aprs-tiles`

Open:

```
http://<DIETPI-IP>:8091
```

## Test the map server

Check TileServer GL:

```bash
docker logs tt-aprs-tiles
```

You can also check its health from inside the Docker network:

```bash
docker exec tt-aprs-tiles wget -qO- http://localhost:8080/health
```

The web container proxies rendered map tiles through:

```
/tiles/{z}/{x}/{y}.png
```

to TileServer GL's rendered style endpoint.

## Map storage

The MBTiles file is deliberately stored outside the Docker image:

```
./data/map.mbtiles
```

That means:

- rebuilding the web container does not redownload the map
- replacing the map does not require rebuilding nginx
- the map can be backed up separately
- the Docker image remains small

The `data` directory is mounted read-only into TileServer GL.

## Updating the map

Geofabrik publishes updated regional extracts periodically.

To replace the map:

```bash
cd Tools/docker/aprs-web
bash download-map.sh
docker compose restart aprs-tiles
```

The web container does not need to be rebuilt.

## Offline operation

Once `map.mbtiles` has been downloaded and the Docker images are present,
the map itself does not require Internet access.

The browser loads:

- the APRS web application from nginx
- APRS data from the local collector
- map tiles from the local TileServer GL container

The only Internet dependency for the map is the initial MBTiles download
and any future map updates.

## Ports

| Service | Container port | Host port |
|---|---:|---:|
| APRS collector/API | 8080 | 8090 |
| APRS web monitor | 80 | 8091 |
| TileServer GL | 8080 | internal only |

TileServer GL is intentionally not published directly to the host. Nginx
provides the browser-facing `/tiles/` path.

## APRS API

The web monitor consumes the collector API.

Examples:

```bash
curl http://localhost:8090/api/health
curl http://localhost:8090/api/packets?limit=100
curl http://localhost:8090/api/packets?limit=500
```

Through the web container, the same API is available at:

```bash
curl http://localhost:8091/api/health
```

## Important RTL-SDR limitation

The RTL-SDR can normally only be controlled by one application at a time.

If another container, such as an ADS-B/readsb container, is using the same
dongle, the APRS collector will not be able to use it simultaneously.

## Attribution

Map data comes from OpenStreetMap contributors and is distributed through
Geofabrik. The map data is provided under the OpenStreetMap ODbL.

The web interface includes OpenStreetMap attribution in the map footer.
