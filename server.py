"""MATOSHREE Surgical & Distributor - billing server.

Serves index.html and a small JSON API backed by SQLite.
Uses only the Python standard library, so there is nothing to install:

    python server.py            # then open http://localhost:8000
"""
import json
import os
import sqlite3
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("BILLING_DB", os.path.join(BASE_DIR, "billing.db"))
PORT = int(os.environ.get("PORT", "8000"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS main_categories (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL UNIQUE COLLATE NOCASE
);
CREATE TABLE IF NOT EXISTS sub_categories (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    main_category_id  INTEGER NOT NULL REFERENCES main_categories(id) ON DELETE CASCADE,
    name              TEXT NOT NULL COLLATE NOCASE,
    UNIQUE (main_category_id, name)
);
CREATE TABLE IF NOT EXISTS products (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    sub_category_id  INTEGER NOT NULL REFERENCES sub_categories(id) ON DELETE CASCADE,
    name             TEXT NOT NULL COLLATE NOCASE,
    unit             TEXT NOT NULL DEFAULT 'Nos',
    selling_price    REAL NOT NULL DEFAULT 0,
    UNIQUE (sub_category_id, name)
);
CREATE TABLE IF NOT EXISTS sales (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_no        TEXT NOT NULL UNIQUE,
    bill_date      TEXT NOT NULL,
    customer_name  TEXT,
    customer_phone TEXT,
    total          REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sale_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id     INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    product_id  INTEGER REFERENCES products(id) ON DELETE SET NULL,
    name        TEXT NOT NULL,
    unit        TEXT,
    qty         REAL NOT NULL,
    price       REAL NOT NULL,
    amount      REAL NOT NULL
);
"""


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)


def rows(cur):
    return [dict(r) for r in cur.fetchall()]


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def require_text(data, key):
    value = str(data.get(key) or "").strip()
    if not value:
        raise ApiError(400, f"'{key}' is required")
    return value


def require_number(data, key, minimum=0):
    try:
        value = float(data.get(key))
    except (TypeError, ValueError):
        raise ApiError(400, f"'{key}' must be a number")
    if value < minimum:
        raise ApiError(400, f"'{key}' must be at least {minimum}")
    return value


# ---------- handlers: (conn, data, id) -> result ----------

def list_main(conn, _data, _id):
    return rows(conn.execute("SELECT * FROM main_categories ORDER BY name"))


def create_main(conn, data, _id):
    cur = conn.execute("INSERT INTO main_categories (name) VALUES (?)", (require_text(data, "name"),))
    return {"id": cur.lastrowid}


def update_main(conn, data, id_):
    conn.execute("UPDATE main_categories SET name = ? WHERE id = ?", (require_text(data, "name"), id_))
    return {"id": id_}


def delete_main(conn, _data, id_):
    conn.execute("DELETE FROM main_categories WHERE id = ?", (id_,))
    return {"deleted": id_}


def list_sub(conn, _data, _id):
    return rows(conn.execute(
        """SELECT s.*, m.name AS main_category_name
           FROM sub_categories s JOIN main_categories m ON m.id = s.main_category_id
           ORDER BY m.name, s.name"""))


def create_sub(conn, data, _id):
    cur = conn.execute(
        "INSERT INTO sub_categories (main_category_id, name) VALUES (?, ?)",
        (int(require_number(data, "main_category_id", 1)), require_text(data, "name")))
    return {"id": cur.lastrowid}


def update_sub(conn, data, id_):
    conn.execute(
        "UPDATE sub_categories SET main_category_id = ?, name = ? WHERE id = ?",
        (int(require_number(data, "main_category_id", 1)), require_text(data, "name"), id_))
    return {"id": id_}


def delete_sub(conn, _data, id_):
    conn.execute("DELETE FROM sub_categories WHERE id = ?", (id_,))
    return {"deleted": id_}


def list_products(conn, _data, _id):
    return rows(conn.execute(
        """SELECT p.*, s.name AS sub_category_name, s.main_category_id,
                  m.name AS main_category_name
           FROM products p
           JOIN sub_categories s ON s.id = p.sub_category_id
           JOIN main_categories m ON m.id = s.main_category_id
           ORDER BY m.name, s.name, p.name"""))


def product_values(data):
    return (int(require_number(data, "sub_category_id", 1)),
            require_text(data, "name"),
            str(data.get("unit") or "Nos").strip() or "Nos",
            require_number(data, "selling_price", 0))


def create_product(conn, data, _id):
    cur = conn.execute(
        "INSERT INTO products (sub_category_id, name, unit, selling_price) VALUES (?, ?, ?, ?)",
        product_values(data))
    return {"id": cur.lastrowid}


def update_product(conn, data, id_):
    conn.execute(
        "UPDATE products SET sub_category_id = ?, name = ?, unit = ?, selling_price = ? WHERE id = ?",
        product_values(data) + (id_,))
    return {"id": id_}


def delete_product(conn, _data, id_):
    conn.execute("DELETE FROM products WHERE id = ?", (id_,))
    return {"deleted": id_}


def list_sales(conn, _data, _id):
    return rows(conn.execute("SELECT * FROM sales ORDER BY id DESC LIMIT 100"))


def get_sale(conn, _data, id_):
    sale = conn.execute("SELECT * FROM sales WHERE id = ?", (id_,)).fetchone()
    if not sale:
        raise ApiError(404, "Bill not found")
    result = dict(sale)
    result["items"] = rows(conn.execute("SELECT * FROM sale_items WHERE sale_id = ? ORDER BY id", (id_,)))
    return result


def create_sale(conn, data, _id):
    items = data.get("items") or []
    if not items:
        raise ApiError(400, "Add at least one item to the bill")
    lines = []
    for item in items:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (item.get("product_id"),)).fetchone()
        if not product:
            raise ApiError(400, "One of the items no longer exists")
        qty = require_number(item, "qty", 0.001)
        price = require_number(item, "price", 0) if item.get("price") is not None else product["selling_price"]
        lines.append((product["id"], product["name"], product["unit"], qty, price, round(qty * price, 2)))
    total = round(sum(line[5] for line in lines), 2)

    now = datetime.now()
    cur = conn.execute(
        "INSERT INTO sales (bill_no, bill_date, customer_name, customer_phone, total) VALUES (?, ?, ?, ?, ?)",
        ("PENDING-" + now.strftime("%Y%m%d%H%M%S%f"), now.strftime("%Y-%m-%d %H:%M"),
         str(data.get("customer_name") or "").strip(), str(data.get("customer_phone") or "").strip(), total))
    sale_id = cur.lastrowid
    bill_no = f"MS-{sale_id:05d}"
    conn.execute("UPDATE sales SET bill_no = ? WHERE id = ?", (bill_no, sale_id))
    conn.executemany(
        "INSERT INTO sale_items (sale_id, product_id, name, unit, qty, price, amount) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(sale_id,) + line for line in lines])
    return {"id": sale_id, "bill_no": bill_no, "total": total}


ROUTES = {
    ("GET", "main-categories"): list_main,
    ("POST", "main-categories"): create_main,
    ("PUT", "main-categories"): update_main,
    ("DELETE", "main-categories"): delete_main,
    ("GET", "sub-categories"): list_sub,
    ("POST", "sub-categories"): create_sub,
    ("PUT", "sub-categories"): update_sub,
    ("DELETE", "sub-categories"): delete_sub,
    ("GET", "products"): list_products,
    ("POST", "products"): create_product,
    ("PUT", "products"): update_product,
    ("DELETE", "products"): delete_product,
    ("GET", "sales"): list_sales,
    ("POST", "sales"): create_sale,
}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_api(self, method):
        parts = [p for p in urlparse(self.path).path.split("/") if p][1:]  # drop "api"
        if not parts or len(parts) > 2:
            return self.send_json(404, {"error": "Not found"})
        resource = parts[0]
        id_ = None
        if len(parts) == 2:
            if not parts[1].isdigit():
                return self.send_json(404, {"error": "Not found"})
            id_ = int(parts[1])
        handler = get_sale if (method, resource) == ("GET", "sales") and id_ else ROUTES.get((method, resource))
        if handler is None or (method in ("PUT", "DELETE") and id_ is None):
            return self.send_json(404, {"error": "Not found"})
        data = {}
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self.send_json(400, {"error": "Invalid JSON"})
        conn = connect()
        try:
            with conn:  # commits on success, rolls back on error
                result = handler(conn, data, id_)
            self.send_json(200, result)
        except ApiError as e:
            self.send_json(e.status, {"error": e.message})
        except sqlite3.IntegrityError as e:
            message = "That name already exists" if "UNIQUE" in str(e) else "Cannot save: " + str(e)
            self.send_json(409, {"error": message})
        finally:
            conn.close()

    def route(self, method):
        if self.path.startswith("/api/"):
            return self.handle_api(method)
        if method != "GET":
            return self.send_json(405, {"error": "Method not allowed"})
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return super().do_GET()
        # Only the page itself is public; never serve the database or source files.
        self.send_error(404)

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def do_PUT(self):
        self.route("PUT")

    def do_DELETE(self):
        self.route("DELETE")


if __name__ == "__main__":
    init_db()
    print(f"MATOSHREE billing running at http://localhost:{PORT}  (database: {DB_PATH})")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
