# MATOSHREE Surgical & Distributor – Billing

A single-page billing app (`index.html`) with a small SQLite database behind it (`server.py`).

## Run

Needs only Python 3 (no packages to install).

```
python server.py
```

On first start it asks you to set the **Super Admin ID and password** (only the
Super Admin can log in). To change them later:

```
python server.py --set-admin
```

You can also set `SUPERADMIN_ID` and `SUPERADMIN_PASSWORD` before the first start instead of typing them.

Then open http://localhost:8000 and log in. Data is stored in `billing.db` next to `server.py`
(created on first run; set `BILLING_DB` to use another path, `PORT` for another port).

## Tabs

- **Main** – comes pre-filled with 15 Main Categories and their Sub Categories; add more Main Categories, Sub Categories, and products with their selling price.
- **1. Sale** – browse/search items with prices, add them to a bill, save and print it. Recent bills are listed below.
- **2. Purchase** – placeholder for now.
