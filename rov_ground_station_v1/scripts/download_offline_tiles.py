#!/usr/bin/env python3
"""
Downloads offline map tiles around Nagarjuna Sagar Dam for 100% offline operation.
Tiles are saved in standard Slippy map format:
  assets/tiles/satellite/{z}/{x}/{y}.jpg
  assets/tiles/street/{z}/{x}/{y}.png
"""
import os
import sys
import math
import time
import urllib.request
import concurrent.futures

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
TILES_DIR = os.path.join(ASSETS_DIR, "tiles")

# Nagarjuna Sagar Dam coordinates
CENTER_LAT = 16.579554
CENTER_LON = 79.312759

# Tile spans around center (in tiles) for each zoom level (dx, dy)
ZOOM_CONFIG = {
    14: (1, 1),   # 3x3 = 9 tiles (regional overview)
    15: (2, 2),   # 5x5 = 25 tiles (dam approach)
    16: (3, 3),   # 7x7 = 49 tiles (reservoir & dam wall)
    17: (4, 4),   # 9x9 = 81 tiles (dam crest & spillway)
    18: (5, 5),   # 11x11 = 121 tiles (ROV dive operating zone)
}


def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)


def fetch_tile(url, dest_path, headers):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 500:
        return True, dest_path  # Already downloaded
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                if len(data) > 200:
                    with open(dest_path, "wb") as f:
                        f.write(data)
                    return True, dest_path
        except Exception:
            time.sleep(0.5)
    return False, dest_path


def download_tiles():
    print("=" * 60)
    print(" Downloading Offline Map Tiles for Nagarjuna Sagar Dam")
    print("=" * 60)
    print(f"Target Directory: {TILES_DIR}")
    print(f"Center Location: Lat {CENTER_LAT}, Lon {CENTER_LON}")

    tasks = []

    # 1. Satellite Tiles (Esri World Imagery)
    # Esri URL format: tile/{z}/{y}/{x}
    sat_headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
    # 2. Street Tiles (OSM)
    osm_headers = {"User-Agent": "ROVGroundStation-OfflineDownloader/1.0 (contact: info@coratia.com)"}

    for z, (dx, dy) in ZOOM_CONFIG.items():
        cx, cy = deg2num(CENTER_LAT, CENTER_LON, z)
        for x in range(cx - dx, cx + dx + 1):
            for y in range(cy - dy, cy + dy + 1):
                # Satellite: saved as tiles/satellite/{z}/{x}/{y}.jpg
                sat_dest = os.path.join(TILES_DIR, "satellite", str(z), str(x), f"{y}.jpg")
                sat_url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                tasks.append(("Satellite", sat_url, sat_dest, sat_headers))

                # Street Map: saved as tiles/street/{z}/{x}/{y}.png
                osm_dest = os.path.join(TILES_DIR, "street", str(z), str(x), f"{y}.png")
                osm_url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
                tasks.append(("Street", osm_url, osm_dest, osm_headers))

    print(f"Queued {len(tasks)} tiles for offline caching across zooms 14 to 18...")

    downloaded = 0
    failed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {
            executor.submit(fetch_tile, url, dest, headers): (layer, dest)
            for (layer, url, dest, headers) in tasks
        }
        for future in concurrent.futures.as_completed(future_map):
            layer, dest = future_map[future]
            try:
                success, _ = future.result()
                if success:
                    downloaded += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

            if (downloaded + failed) % 50 == 0 or (downloaded + failed) == len(tasks):
                print(f"Progress: {downloaded + failed}/{len(tasks)} tiles processed ({downloaded} saved, {failed} failed)...")

    print("\n" + "=" * 60)
    print(f"[COMPLETE] Offline tiles cached successfully!")
    print(f"Total tiles available offline: {downloaded}")
    if failed > 0:
        print(f"Failed tiles: {failed}")
    print("=" * 60)


if __name__ == "__main__":
    download_tiles()

