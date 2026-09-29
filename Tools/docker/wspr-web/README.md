# TT WSPR Web Monitor

Internal web UI for the TT WSPR collector. It shows collector status and the
latest decoded spots, refreshing every 15 seconds.

Start the WSPR collector first, then run from this directory:

```sh
docker compose up -d --build
```

Open `http://DIETPI-IP:8092`. The web container proxies `/api/` to a collector
listening on port 8082 of the same Docker host.
