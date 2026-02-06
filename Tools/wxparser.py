#!/usr/bin/env python3

import requests
import sys

# --------- CONFIG ---------
API_URL = "http://localhost:9000/history"  # Change if different port
MAX_ENTRIES = 5  # Maximum allowed
# --------------------------

def fetch_weather_history():
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data from API: {e}")
        return []

def show_entries(entries, last_n=5):
    selected = entries[-last_n:]
    for entry in selected:
        entry_id = entry[0]
        timestamp = entry[1]
        content = entry[4]
        print(f"ID: {entry_id}\nTime: {timestamp}\nContent: {content}\n{'-'*60}")

def main():
    # Check for command-line argument
    if len(sys.argv) < 2:
        n = 1  # Default to last 1 entry
    else:
        try:
            n = int(sys.argv[1])
            if n < 1:
                n = 1
            elif n > MAX_ENTRIES:
                n = MAX_ENTRIES
        except ValueError:
            print(f"Invalid input '{sys.argv[1]}', defaulting to last 1 entry.")
            n = 1

    data = fetch_weather_history()
    if not data:
        print("No data available.")
        return

    print(f"=== Showing last {n} weather entries ===\n")
    show_entries(data, last_n=n)

if __name__ == "__main__":
    main()
