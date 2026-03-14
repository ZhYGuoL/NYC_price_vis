#!/usr/bin/env python3
"""
Flask API: load trained Random Forest and predict price for a listing.
POST /predict  body: { beds, baths, property_sqft, type, zip }  -> { predicted_price, lat, lng }
GET /types  -> { types: [...] }
"""
import json
import os

import joblib
from flask import Flask, jsonify, request

APP = Flask(__name__)


@APP.after_request
def _cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp
ARTIFACTS = os.path.join(os.path.dirname(__file__), "artifacts")
MODEL_PATH = os.path.join(ARTIFACTS, "model.joblib")
ENCODER_PATH = os.path.join(ARTIFACTS, "type_encoder.joblib")
ZIP_CENTROIDS_PATH = os.path.join(ARTIFACTS, "zip_centroids.json")

_model = None
_type_encoder = None
_type_labels = None
_zip_centroids = None


def load_artifacts():
    global _model, _type_encoder, _type_labels, _zip_centroids
    if _model is not None:
        return
    if os.path.isfile(MODEL_PATH):
        _model = joblib.load(MODEL_PATH)
        _type_encoder = joblib.load(ENCODER_PATH)
        with open(os.path.join(ARTIFACTS, "type_labels.json")) as f:
            _type_labels = json.load(f)
        if os.path.isfile(ZIP_CENTROIDS_PATH):
            with open(ZIP_CENTROIDS_PATH) as f:
                _zip_centroids = json.load(f)
        else:
            _zip_centroids = {}
        return
    # Fallback: train on startup if artifacts missing
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from train_model import main as train_main
    train_main()
    _model = joblib.load(MODEL_PATH)
    _type_encoder = joblib.load(ENCODER_PATH)
    with open(os.path.join(ARTIFACTS, "type_labels.json")) as f:
        _type_labels = json.load(f)
    if os.path.isfile(ZIP_CENTROIDS_PATH):
        with open(ZIP_CENTROIDS_PATH) as f:
            _zip_centroids = json.load(f)
    else:
        _zip_centroids = {}


@APP.route("/predict", methods=["OPTIONS"])
@APP.route("/types", methods=["OPTIONS"])
def _options():
    return "", 204


@APP.route("/types", methods=["GET"])
def get_types():
    load_artifacts()
    return jsonify({"types": _type_labels})


@APP.route("/predict", methods=["POST"])
def predict():
    load_artifacts()
    body = request.get_json() or {}
    try:
        beds = int(body.get("beds", 0))
        baths = float(body.get("baths", 0))
        property_sqft = float(body.get("property_sqft", 0))
        type_name = str(body.get("type", "")).strip() or _type_labels[0]
        zip_code = str(body.get("zip", "")).strip()
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid numeric fields"}), 400

    if type_name not in _type_encoder.classes_:
        type_name = _type_labels[0]
    type_encoded = _type_encoder.transform([type_name])[0]

    lat, lng = 40.7128, -74.006  # NYC default
    if zip_code and zip_code in _zip_centroids:
        lat, lng = _zip_centroids[zip_code]

    X = [[beds, baths, property_sqft, type_encoded, lat, lng]]
    predicted = float(_model.predict(X)[0])
    predicted = max(0, round(predicted, 0))

    return jsonify({
        "predicted_price": predicted,
        "lat": lat,
        "lng": lng,
    })


if __name__ == "__main__":
    load_artifacts()
    APP.run(host="127.0.0.1", port=5000, debug=False)
