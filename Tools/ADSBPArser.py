#!/usr/bin/env python3
import subprocess
import re
import argparse
from math import radians, sin, cos, sqrt, atan2

# Regex patterns
icao_pattern = re.compile(r"ICAO Address:\s*([0-9A-Fa-f]+)")
track_pattern = re.compile(r"Track/Heading\s*([0-9.]+)")
groundspeed_pattern = re.compile(r"Groundspeed:\s*([0-9.]+)\s*kt")
lat_pattern = re.compile(r"CPR latitude:\s*\(?([0-9.-]+)\)?")
lon_pattern = re.compile(r"CPR longitude:\s*\(?([0-9.-]+)\)?")
alt_pattern = re.compile(r"Baro altitude:\s*([0-9.]+)\s*ft")

def get_docker_logs(container_name="readsb3"):
    """Capture docker logs in memory as a list of lines"""
    try:
        result = subprocess.run(
            ["docker", "logs", container_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return result.stdout.splitlines()
    except subprocess.CalledProcessError as e:
        print(f"Error reading logs: {e.stderr}")
        return []

def parse_block(block):
    """Parse a single ADS-B message block safely"""
    block_text = "\n".join(block)
    plane = {}

    # ICAO
    m = icao_pattern.search(block_text)
    if m:
        plane["icao"] = m.group(1)

    # Heading
    m = track_pattern.search(block_text)
    if m:
        try:
            plane["heading"] = float(m.group(1))
        except ValueError:
            plane["heading"] = None

    # Groundspeed
    m = groundspeed_pattern.search(block_text)
    if m:
        try:
            plane["groundspeed_kt"] = float(m.group(1))
        except ValueError:
            plane["groundspeed_kt"] = None

    # CPR coordinates
    m = lat_pattern.search(block_text)
    if m and m.group(1):
        try:
            plane["cpr_lat"] = float(m.group(1))
        except ValueError:
            plane["cpr_lat"] = None

    m = lon_pattern.search(block_text)
    if m and m.group(1):
        try:
            plane["cpr_lon"] = float(m.group(1))
        except ValueError:
            plane["cpr_lon"] = None

    # Altitude
    m = alt_pattern.search(block_text)
    if m and m.group(1):
        try:
            plane["altitude_ft"] = float(m.group(1))
        except ValueError:
            plane["altitude_ft"] = None

    return plane

def parse_planes_from_lines(lines):
    """Parse all planes from docker logs"""
    planes = []
    current_block = []

    for line in lines:
        line = line.strip()
        if line.startswith("*"):
            if current_block:
                plane = parse_block(current_block)
                if plane.get("icao"):
                    planes.append(plane)
            current_block = [line]
        else:
            current_block.append(line)

    if current_block:
        plane = parse_block(current_block)
        if plane.get("icao"):
            planes.append(plane)

    return planes

def get_last_unique_planes(planes, max_planes=10):
    """Return the last N unique planes by ICAO"""
    seen = set()
    unique_planes = []
    for plane in reversed(planes):
        icao = plane.get("icao")
        if icao and icao not in seen:
            unique_planes.append(plane)
            seen.add(icao)
            if len(unique_planes) >= max_planes:
                break
    return list(reversed(unique_planes))

def haversine(lat1, lon1, lat2, lon2):
    """Compute distance in miles between two points"""
    R = 3958.8  # Earth radius in miles
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def main():
    parser = argparse.ArgumentParser(description="Parse readsb Docker logs")
    parser.add_argument("--mode", choices=["latest", "last10", "alert"], default="latest",
                        help="Mode: latest, last10, or alert")
    parser.add_argument("--container", default="readsb3", help="Docker container name")
    parser.add_argument("--threshold", type=float, default=50.0,
                        help="Distance threshold in miles (for alert mode)")
    args = parser.parse_args()

    lines = get_docker_logs(args.container)
    all_planes = parse_planes_from_lines(lines)

    if not all_planes:
        print("No planes with ICAO found in the logs.")
        return

    if args.mode == "latest":
        plane = all_planes[-1]
        print("Latest plane:")
        for k, v in plane.items():
            print(f"  {k}: {v}")

    elif args.mode == "last10":
        planes_to_show = get_last_unique_planes(all_planes, max_planes=10)
        print(f"Last {len(planes_to_show)} unique planes:")
        for idx, plane in enumerate(planes_to_show, 1):
            print(f"\nPlane #{idx}:")
            for k, v in plane.items():
                print(f"  {k}: {v}")

    elif args.mode == "alert":
        user_lat = float(input("Enter your latitude: "))
        user_lon = float(input("Enter your longitude: "))
        threshold = args.threshold
        alerts = []

        for plane in all_planes:
            if "cpr_lat" in plane and "cpr_lon" in plane:
                distance = haversine(user_lat, user_lon, plane["cpr_lat"], plane["cpr_lon"])
                if distance <= threshold:
                    alerts.append((plane, distance))

        if alerts:
            print(f"\n⚠️ ALERTS: Planes within {threshold} miles:\n")
            for plane, dist in alerts:
                print(f"ICAO: {plane.get('icao', 'N/A')} | Distance: {dist:.1f} mi | "
                      f"Lat: {plane.get('cpr_lat', 'N/A')} | Lon: {plane.get('cpr_lon', 'N/A')} | "
                      f"Alt: {plane.get('altitude_ft', 'N/A')} ft | "
                      f"Heading: {plane.get('heading', 'N/A')}° | "
                      f"GS: {plane.get('groundspeed_kt', 'N/A')} kt")
        else:
            print(f"No planes within {threshold} miles.")

if __name__ == "__main__":
    main()
