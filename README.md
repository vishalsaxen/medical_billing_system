# MATOSHREE Surgical & Distributor – Billing

A single-page billing app (`index.html`) with a small SQLite database behind it (`server.py`).

## Run

Needs only Python 3 (no packages to install).

```
python server.py
```

Then open http://localhost:8000. Data is stored in `billing.db` next to `server.py`
(created on first run; set `BILLING_DB` to use another path, `PORT` for another port).

## Tabs

- **Main** – add Main Categories, Sub Categories, and products with their selling price.
- **1. Sale** – browse/search items with prices, add them to a bill, save and print it. Recent bills are listed below.
- **2. Purchase** – placeholder for now.
