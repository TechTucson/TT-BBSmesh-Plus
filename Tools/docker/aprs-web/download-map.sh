#!/bin/sh
set -eu

DATA_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/data" && pwd)"
mkdir -p "$DATA_DIR"

URL="https://download.geofabrik.de/north-america/us/arizona-shortbread-1.0.mbtiles"
OUT="$DATA_DIR/map.mbtiles"

echo "Downloading Arizona OpenStreetMap Shortbread MBTiles..."
echo "Source: $URL"
echo "Destination: $OUT"

if command -v curl >/dev/null 2>&1; then
    curl -L --fail --retry 3 --progress-bar -o "$OUT" "$URL"
elif command -v wget >/dev/null 2>&1; then
    wget -c -O "$OUT" "$URL"
else
    echo "ERROR: install curl or wget first."
    exit 1
fi

echo
echo "Map downloaded:"
ls -lh "$OUT"
echo
echo "Next:"
echo "  docker compose up -d --build"
echo
echo "APRS web map: http://<DIETPI-IP>:8091"
