#!/usr/bin/env python3
"""
Train a Random Forest regression model on the 5-boroughs housing CSV.
Saves model, type encoder, and zip centroids for the prediction server.
"""
import json
import os
import re
import sys

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_CSV = os.path.join(REPO_ROOT, "assignmentStuff", "NY-House-Dataset-5boroughs.csv")
ZIP_CENTROIDS = os.path.join(SCRIPT_DIR, "..", "scripts", "nyc_zip_centroids.json")
OUT_DIR = os.path.join(SCRIPT_DIR, "artifacts")
MODEL_PATH = os.path.join(OUT_DIR, "model.joblib")
ENCODER_PATH = os.path.join(OUT_DIR, "type_encoder.joblib")


def parse_zip_from_state(state_val):
    if not state_val:
        return None
    m = re.search(r",\s*NY\s+(\d{5})", str(state_val))
    return int(m.group(1)) if m else None


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV
    if not os.path.isfile(csv_path):
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(csv_path)
    # Normalize column names (dataset may have BROKERTITLE or not)
    needed = ["TYPE", "PRICE", "BEDS", "BATH", "PROPERTYSQFT", "LATITUDE", "LONGITUDE"]
    for c in needed:
        if c not in df.columns:
            print(f"Missing column: {c}", file=sys.stderr)
            sys.exit(1)

    # Drop rows missing key fields or invalid price
    df = df.dropna(subset=["PRICE", "BEDS", "BATH", "TYPE"])
    df = df[df["PRICE"] > 0]
    df = df[df["PRICE"] < 1e9]
    df = df[df["BEDS"].between(0, 50)]
    df = df[df["BATH"].between(0, 50)]
    # Fill missing sqft with median by type
    if df["PROPERTYSQFT"].isna().any():
        med = df["PROPERTYSQFT"].median()
        df["PROPERTYSQFT"] = df["PROPERTYSQFT"].fillna(med)
    df = df[df["PROPERTYSQFT"] > 0]
    df = df.dropna(subset=["LATITUDE", "LONGITUDE"])

    # Encode TYPE
    type_encoder = LabelEncoder()
    df["type_encoded"] = type_encoder.fit_transform(df["TYPE"].astype(str))

    features = ["BEDS", "BATH", "PROPERTYSQFT", "type_encoded", "LATITUDE", "LONGITUDE"]
    X = df[features]
    y = df["PRICE"]

    model = RandomForestRegressor(n_estimators=100, max_depth=20, random_state=42, n_jobs=-1)
    model.fit(X, y)

    os.makedirs(OUT_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(type_encoder, ENCODER_PATH)

    # Save type labels for API dropdown
    type_labels = list(type_encoder.classes_)
    with open(os.path.join(OUT_DIR, "type_labels.json"), "w") as f:
        json.dump(type_labels, f, indent=0)

    # Copy zip centroids into artifacts for the server
    if os.path.isfile(ZIP_CENTROIDS):
        with open(ZIP_CENTROIDS) as f:
            centroids = json.load(f)
        with open(os.path.join(OUT_DIR, "zip_centroids.json"), "w") as f:
            json.dump(centroids, f)

    print(f"Trained on {len(X)} samples. Model saved to {OUT_DIR}", file=sys.stderr)


if __name__ == "__main__":
    main()
