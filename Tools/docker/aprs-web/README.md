# TT APRS Web Monitor

Offline web monitor for the TT APRS collector.

The monitor displays locally received APRS packets and plots packets containing
decoded position data on an offline Shortbread map.

## Architecture

```
RTL-SDR
   |
rtl_fm
   |
Dire Wolf
   |
tt-aprs :8090
   |
SQLite
   |
   +--------------------+
   |                    |
APRS API           tt-aprs-web :8091
                         |
                         +--> nginx
                         |     |
                         |     +--> /api/ -> tt-aprs :8090
                         |     |
                         |     +--> /tiles/ -> TileServer GL raw PBF
                         |
                         v
                    Browser / MapLibre
                         |
                         v
                 Shortbread vector tiles
                         ^
                         |
                    map.mbtiles
```

The browser renders the Shortbread vector tiles with MapLibre GL JS. TileServer GL
only serves the raw vector tiles; it does not need to render PNG tiles server-side.
This avoids the OpenMapTiles-only automatic preview limitation of Shortbread data.

## Components

### APRS collector

- RTL-SDR receives 144.390 MHz APRS
- `rtl_fm` converts RF to audio
- Dire Wolf decodes 1200-baud AX.25/APRS
- Python stores packets in SQLite
- FastAPI exposes the packet API
- Collector API: port **8090**

### APRS web monitor

- nginx
- host port **8091**
- local MapLibre GL JS
- local Shortbread vector tiles
- no browser dependency on an Internet map provider
- auto-refresh every 5 seconds

### Offline map

The map is an Arizona OpenStreetMap extract from Geofabrik in Shortbread vector
MBTiles format.

The browser requests local vector tiles through:

```
/tiles/{z}/{x}/{y}.pbf
```

nginx proxies those requests to TileServer GL:

```
/data/map/{z}/{x}/{y}.pbf
```

MapLibre renders the vector data locally in the browser.

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

## Start or rebuild

```bash
docker compose down
docker compose up -d --build
```

Open:

```
http://<DIETPI-IP>:8091
```

## Test the vector tile server

Check TileServer GL:

```bash
docker logs tt-aprs-tiles
```

Check the data endpoint:

```docker
docker exec tt-aprs-tiles wget -S -O /dev/null \
  http://localhost:8080/data/map/9/98/206.pbf
```

A successful response should be HTTP 200.

Test through nginx:

```bash
curl -I http://localhost:8091/tiles/9/98/206.pbf
```

## Map storage

The MBTiles file remains outside the Docker image:

```
./data/map.mbtiles
```

Rebuilding the web container does not redownload the map.

## Updating the map

```bash
cd Tools/docker/aprs-web
bash download-map.sh
docker compose restart aprs-tiles
```

## Offline operation

After the MBTiles file and Docker images have been downloaded, the map itself
does not require Internet access.

The browser loads:

- the APRS application from nginx
- MapLibre GL JS from the local web container
- APRS data from the local collector
- map vector tiles from the local TileServer GL container

Only the initial MBTiles download and future map updates require Internet access.

## Ports

| Service | Container port | Host port |
|---|---:|---:|
| APRS collector/API | 8080 | 8090 |
| APRS web monitor | 80 | 8091 |
| TileServer GL | 8080 | internal only |

## Attribution

Map data © OpenStreetMap contributors and Geofabrik. OpenStreetMap data is
licensed under the Open Database License (ODbL).
