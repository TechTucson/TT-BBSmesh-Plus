# TT WSPR Collector

A local, receive-only WSPR receiver for an RTL-SDR. It records each two-minute
WSPR interval, decodes it with `wsprd`, stores unique spots in SQLite, and
exposes them through a small REST API.

`RTL-SDR → rtl_fm → SoX WAV capture → wsprd → SQLite → REST API`

## Run the collector

From this directory:

```sh
mkdir -p data
docker compose up -d --build
docker logs -f tt-wspr
```

The default is the 20 m WSPR dial frequency, 14.0971 MHz. The RTL-SDR needs to
be visible to Docker. One dongle cannot be used by the APRS, ADS-B, and WSPR
containers at the same time; use a separate SDR for each simultaneous service.

Change `WSPR_FREQUENCY`, `RTL_SAMPLE_RATE`, `RTL_GAIN`, or `RTL_PPM` in
`docker-compose.yml` to use another band or calibrate the receiver. The SQLite
database is persisted at `./data/wspr.db`.

## API

```sh
curl http://localhost:8082/api/health
curl 'http://localhost:8082/api/spots?limit=100'
curl 'http://localhost:8082/api/spots?callsign=K1ABC&limit=100'
curl http://localhost:8082/api/spots/1
```

The API and collector are local only: no spots are uploaded to WSPRnet and no
RF is transmitted.

## Web monitor

Start the companion internal web site after the collector is running:

```sh
cd ../wspr-web
docker compose up -d --build
```

Open `http://DIETPI-IP:8092`. The website proxies its API requests to the
collector on the Docker host, so browsers never need direct access to port 8082.
