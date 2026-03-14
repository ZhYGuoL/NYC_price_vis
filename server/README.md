# Price prediction API (Random Forest)

Predicts listing price from beds, baths, sq ft, type, and ZIP using a Random Forest regression model trained on the 5-boroughs dataset.

## Setup

```bash
cd server
pip install -r requirements.txt
```

## Train model (optional)

If `artifacts/` does not exist, the server will train on first request. To pre-train:

```bash
python train_model.py
```

Uses `assignmentStuff/NY-House-Dataset-5boroughs.csv` by default. Override:

```bash
python train_model.py /path/to/5boroughs.csv
```

## Run server

```bash
python app.py
```

Server runs at http://127.0.0.1:5000. The frontend calls:

- `GET /types` – list of property types for the dropdown
- `POST /predict` – body `{ beds, baths, property_sqft, type, zip }` → `{ predicted_price, lat, lng }`
