#!/usr/bin/env python3
import subprocess
import re
from collections import deque
import argparse

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
            ["sudo", "docker", "logs", container_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return result.stdout.splitlines()
    except subprocess.CalledProcessError as e:
        print(f"Error reading logs: {e.stderr}")
        return []

def parse_planes_from_lines(lines):
    """Parse the logs into a list of plane dicts (all planes with ICAO)"""
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

def parse_block(block):
    """Parse a single ADS-B message block for ICAO, heading, groundspeed, CPR, and altitude"""
    block_text = "\n".join(block)
    plane = {}

    icao_match = icao_pattern.search(block_text)
    if icao_match:
        plane["icao"] = icao_match.group(1)

    track_match = track_pattern.search(block_text)
    if track_match:
        plane["heading"] = float(track_match.group(1))

    gs_match = groundspeed_pattern.search(block_text)
    if gs_match:
        plane["groundspeed_kt"] = float(gs_match.group(1))

    lat_match = lat_pattern.search(block_text)
    lon_match = lon_pattern.search(block_text)
    if lat_match:
        plane["cpr_lat"] = int(lat_match.group(1))
    if lon_match:
        plane["cpr_lon"] = int(lon_match.group(1))

    alt_match = alt_pattern.search(block_text)
    if alt_match:
        plane["altitude_ft"] = float(alt_match.group(1))

    return plane

def get_last_unique_planes(planes, max_planes=10):
    """Return the last N unique planes by ICAO (most recent first)"""
    seen = set()
    unique_planes = []
    # iterate in reverse (most recent last in log is at end)
    for plane in reversed(planes):
        icao = plane.get("icao")
        if icao and icao not in seen:
            unique_planes.append(plane)
            seen.add(icao)
            if len(unique_planes) >= max_planes:
                break
    # reverse back to oldest->newest for display
    return list(reversed(unique_planes))

def main():
    parser = argparse.ArgumentParser(description="Parse readsb Docker logs for last planes")
    parser.add_argument("mode", choices=["latest", "last10"], help="Show latest plane or last 10 planes")
    parser.add_argument("--container", default="readsb3", help="Docker container name (default: readsb3)")
    args = parser.parse_args()

    lines = get_docker_logs(args.container)
    all_planes = parse_planes_from_lines(lines)

    if args.mode == "latest":
        planes_to_show = all_planes[-1:] if all_planes else []
    else:  # last10 with unique ICAO
        planes_to_show = get_last_unique_planes(all_planes, max_planes=10)

    if planes_to_show:
        print(f"{'Latest plane:' if args.mode=='latest' else f'Last {len(planes_to_show)} unique planes:'}")
        for idx, plane in enumerate(planes_to_show, 1):
            if args.mode == "last10":
                print(f"\nPlane #{idx}:")
            for k, v in plane.items():
                print(f"  {k}: {v}")
    else:
        print("No planes with ICAO found in the logs.")

if __name__ == "__main__":
    main()
