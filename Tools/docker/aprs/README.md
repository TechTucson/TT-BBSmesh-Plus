# TT APRS Collector

A small receive-only APRS service for an RTL-SDR.

## What it does

RTL-SDR -> rtl_fm -> Dire Wolf -> SQLite -> REST API

It does not include maps, a web UI, APRS-IS, or RF transmission.

The SQLite database is stored in ./data/aprs.db.

## Build and run

From this directory:

    mkdir -p data
    docker compose up -d --build

Watch APRS/Dire Wolf output:

    docker logs -f tt-aprs

## API

Latest 100 packets:

    curl "http://localhost:8080/api/packets?limit=100"

Latest 500 packets:

    curl "http://localhost:8080/api/packets?limit=500"

Latest 1000 packets:

    curl "http://localhost:8080/api/packets?limit=1000"

Packets from a callsign (case-insensitive):

    curl "http://localhost:8080/api/packets?callsign=N0CALL&limit=100"

Pagination:

    curl "http://localhost:8080/api/packets?limit=100&offset=100"

One packet:

    curl "http://localhost:8080/api/packets/123"

Health/status:

    curl "http://localhost:8080/api/health"

## Configuration

The default frequency is 144.390 MHz.

Change these environment values in docker-compose.yml if needed:

- APRS_FREQUENCY
- RTL_SAMPLE_RATE
- RTL_GAIN
- RTL_PPM

The SDR must be available to Docker. If another container is already using the same RTL-SDR, use a second dongle or stop the other SDR container.

## Next step

APRS-IS can be added later as an optional configuration switch without changing the local SQLite/API design.
