# TT APRS Web Monitor

Web UI for the TT APRS collector.

## Current features

- Live packet table
- Collector health/status
- Packet count and frequency
- Local map view for APRS packets with decoded latitude/longitude
- Map tiles are served locally from `/tiles/{z}/{x}/{y}.png`

## Offline map

The UI is designed to support a local MBTiles tile set. Put a raster MBTiles file at:

    ./data/map.mbtiles

The nginx container serves tiles through the companion tile service defined in `docker-compose.yml`.

The map remains usable without Internet access once the required tiles have been downloaded into the MBTiles file.

## Run

    docker compose up -d --build

Open:

    http://DIETPI-IP:8091

The map automatically plots packets that contain APRS position data. Packets without position information remain in the table.
