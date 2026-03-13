#!/usr/bin/env python3
"""
Prepare NY housing CSV for the NYC apartment cost viewer.
- Reads from assignmentStuff/NY-House-Dataset-5boroughs.csv (or path passed as arg).
- Filters to 5 boroughs by ZIP.
- Outputs data/listings.json with lat/lng (from CSV or zip centroid fallback).
Uses only stdlib (csv, json, re).
"""
import csv
import json
import os
import re
import sys

# NYC 5 boroughs ZIP code ranges (inclusive)
BOROUGH_ZIP_RANGES = [
    (10001, 10292),   # Manhattan
    (10451, 10475),   # Bronx
    (10301, 10314),   # Staten Island
    (11201, 11256),   # Brooklyn (incl. 11240-11256)
    (11004, 11005),   # Queens
    (11101, 11120),   # Queens
    (11351, 11697),   # Queens
]

ZIP_PATTERN = re.compile(r"\b(\d{5})\b")


def zip_in_nyc_five_boroughs(zip_val):
    if zip_val is None or (isinstance(zip_val, float) and (zip_val != zip_val)):
        return False
    try:
        z = int(re.sub(r"\D", "", str(zip_val))[:5])
    except (ValueError, TypeError):
        return False
    for lo, hi in BOROUGH_ZIP_RANGES:
        if lo <= z <= hi:
            return True
    return False


def parse_zip_from_state(state_val):
    """From STATE column e.g. 'New York, NY 10022'."""
    if not state_val:
        return None
    m = re.search(r",\s*NY\s+(\d{5})", str(state_val))
    return int(m.group(1)) if m else None


def extract_zip_from_text(text):
    """Extract first 5-digit ZIP from MAIN_ADDRESS or FORMATTED_ADDRESS."""
    if not text or not str(text).strip():
        return None
    m = ZIP_PATTERN.search(str(text))
    return int(m.group(1)) if m else None


def get_zip(row):
    """ZIP from STATE, then MAIN_ADDRESS, then FORMATTED_ADDRESS."""
    z = parse_zip_from_state(row.get("STATE", ""))
    if z is not None:
        return z
    z = extract_zip_from_text(row.get("MAIN_ADDRESS", ""))
    if z is not None:
        return z
    return extract_zip_from_text(row.get("FORMATTED_ADDRESS", ""))


def safe_float(val, default=None):
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val, default=None):
    if val is None or val == "":
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    # Prefer 5-boroughs CSV in assignmentStuff
    default_csv = os.path.join(repo_root, "assignmentStuff", "NY-House-Dataset-5boroughs.csv")
    if not os.path.isfile(default_csv):
        default_csv = os.path.join(repo_root, "data", "NY-House-Dataset.csv")
    if not os.path.isfile(default_csv):
        default_csv = os.path.join(repo_root, "NY-House-Dataset.csv")
    csv_path = sys.argv[1] if len(sys.argv) > 1 else default_csv
    zip_centroids_path = os.path.join(script_dir, "nyc_zip_centroids.json")
    out_path = os.path.join(repo_root, "data", "listings.json")

    if not os.path.isfile(csv_path):
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        print("Use assignmentStuff/NY-House-Dataset-5boroughs.csv or pass path: python prepare_data.py <path>", file=sys.stderr)
        sys.exit(1)

    zip_centroids = {}
    if os.path.isfile(zip_centroids_path):
        with open(zip_centroids_path) as f:
            zip_centroids = json.load(f)

    rows = []
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for r in reader:
            z = get_zip(r)
            if not zip_in_nyc_five_boroughs(z):
                continue
            price = safe_float(r.get("PRICE", r.get("price")))
            if price is not None and (price <= 0 or price > 1e9):
                continue
            lat = safe_float(r.get("LATITUDE", r.get("lat")))
            lon = safe_float(r.get("LONGITUDE", r.get("lon")))
            if lat is None or lon is None:
                centroid = zip_centroids.get(str(z))
                if centroid:
                    lat, lon = centroid[0], centroid[1]
                else:
                    continue
            address = (r.get("ADDRESS") or r.get("address") or "").strip()
            rows.append({
                "address": address,
                "zip": z,
                "price": price,
                "lat": round(lat, 6),
                "lng": round(lon, 6),
                "beds": safe_int(r.get("BEDS", r.get("beds"))),
                "baths": safe_float(r.get("BATH", r.get("bath"))),
                "type": (r.get("TYPE") or r.get("type") or "").strip(),
            })

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as out:
        json.dump(rows, out, separators=(",", ":"))

    print(f"Wrote {len(rows)} listings to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
