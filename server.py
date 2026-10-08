"""MATOSHREE Surgical & Distributor - billing server.

Serves index.html and a small JSON API backed by SQLite.
Uses only the Python standard library, so there is nothing to install:

    python server.py            # then open http://localhost:8000
    python server.py --set-admin   # create or change the Super Admin ID/password

Only the Super Admin can log in. On first start the server asks for the
Super Admin ID and password in the terminal (or reads SUPERADMIN_ID and
SUPERADMIN_PASSWORD from the environment).
"""
import getpass
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import sys
import threading
import time
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("BILLING_DB", os.path.join(BASE_DIR, "billing.db"))
PORT = int(os.environ.get("PORT", "8000"))
SESSION_HOURS = 12

SCHEMA = """
CREATE TABLE IF NOT EXISTS admin (
    id             INTEGER PRIMARY KEY CHECK (id = 1),
    login_id       TEXT NOT NULL,
    password_salt  TEXT NOT NULL,
    password_hash  TEXT NOT NULL
);
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

# Starting Main Categories and their Sub Categories (added once, on first run).
SEED_CATEGORIES = {
    "Surgical Instruments": ["Scissors", "Forceps", "Retractors", "Needle Holders", "Scalpels & Handles", "Clamps", "Surgical Knives", "Speculums"],
    "Surgical Disposables": ["Surgical Gloves", "Masks", "Caps", "Gowns", "Shoe Covers", "Drapes", "Disposable Sheets"],
    "Wound Care": ["Gauze", "Cotton", "Bandages", "Adhesive Dressings", "Wound Dressings", "Surgical Tape"],
    "Syringes & Needles": ["Disposable Syringes", "Insulin Syringes", "Hypodermic Needles", "IV Cannulas", "Safety Needles"],
    "Infusion & IV Products": ["IV Sets", "Extension Sets", "Three-Way Stopcocks", "Blood Transfusion Sets", "Infusion Accessories"],
    "Sutures & Stapling": ["Absorbable Sutures", "Non-Absorbable Sutures", "Skin Staples", "Surgical Staplers", "Suture Needles"],
    "Medical Tubes & Catheters": ["Urinary Catheters", "Feeding Tubes", "Suction Catheters", "Drainage Tubes", "Endotracheal Tubes"],
    "Surgical & Examination Gloves": ["Latex Gloves", "Nitrile Gloves", "Vinyl Gloves", "Sterile Surgical Gloves"],
    "Sterilization Products": ["Sterilization Pouches", "Sterilization Rolls", "Autoclave Accessories", "Chemical Indicators"],
    "Operating Room Supplies": ["Surgical Drapes", "Instrument Trays", "Kidney Trays", "Bowls", "Surgical Basins"],
    "Diagnostic & Procedure Supplies": ["Examination Supplies", "Procedure Kits", "Specimen Containers", "Disposable Accessories"],
    "Orthopedic Surgical Supplies": ["Plaster Bandages", "Crepe Bandages", "Splints", "Orthopedic Supports", "Cast Accessories"],
    "Dental Surgical Supplies": ["Dental Extraction Instruments", "Dental Sutures", "Dental Surgical Kits", "Dental Forceps"],
    "Emergency & Trauma Supplies": ["First-Aid Kits", "Trauma Dressings", "Emergency Bandages", "Tourniquets", "Splints"],
    "Post-Surgical Care": ["Compression Bandages", "Wound Care Kits", "Dressing Kits", "Post-Operative Supports"],
}


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = connect()
    try:
        with conn:
            conn.executescript(SCHEMA)
            seeded = conn.execute("SELECT COUNT(*) FROM main_categories").fetchone()[0]
            if not seeded:
                for main_name, subs in SEED_CATEGORIES.items():
                    main_id = conn.execute("INSERT INTO main_categories (name) VALUES (?)", (main_name,)).lastrowid
                    conn.executemany(
                        "INSERT INTO sub_categories (main_category_id, name) VALUES (?, ?)",
                        [(main_id, sub) for sub in subs])
    finally:
        conn.close()


# ---------- Super Admin login ----------

def hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 200_000).hex()


def get_admin():
    conn = connect()
    try:
        return conn.execute("SELECT * FROM admin WHERE id = 1").fetchone()
    finally:
        conn.close()


def set_admin(login_id, password):
    salt = secrets.token_hex(16)
    conn = connect()
    try:
        with conn:
            conn.execute(
                """INSERT INTO admin (id, login_id, password_salt, password_hash) VALUES (1, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET login_id = excluded.login_id,
                       password_salt = excluded.password_salt, password_hash = excluded.password_hash""",
                (login_id, salt, hash_password(password, salt)))
    finally:
        conn.close()


def prompt_admin():
    print("Set the Super Admin login for MATOSHREE billing.")
    login_id = input("Super Admin ID: ").strip()
    while True:
        password = getpass.getpass("Password (min 6 characters): ")
        if len(password) >= 6 and password == getpass.getpass("Repeat password: "):
            break
        print("Passwords did not match or were too short. Try again.")
    if not login_id:
        sys.exit("Super Admin ID cannot be empty.")
    set_admin(login_id, password)
    print("Super Admin saved.")


def ensure_admin():
    if get_admin():
        return
    env_id, env_pw = os.environ.get("SUPERADMIN_ID"), os.environ.get("SUPERADMIN_PASSWORD")
    if env_id and env_pw:
        set_admin(env_id.strip(), env_pw)
    elif sys.stdin.isatty():
        prompt_admin()
    else:
        sys.exit("No Super Admin yet. Run `python server.py --set-admin` "
                 "or set SUPERADMIN_ID and SUPERADMIN_PASSWORD.")


SESSIONS = {}  # token -> expiry timestamp (kept in memory; restarting the server logs out)
SESSIONS_LOCK = threading.Lock()


def check_login(login_id, password):
    admin = get_admin()
    if not admin:
        return False
    id_ok = hmac.compare_digest(str(login_id).strip().lower(), admin["login_id"].lower())
    pw_ok = hmac.compare_digest(hash_password(str(password), admin["password_salt"]), admin["password_hash"])
    return id_ok and pw_ok


def new_session():
    token = secrets.token_urlsafe(32)
    with SESSIONS_LOCK:
        SESSIONS[token] = time.time() + SESSION_HOURS * 3600
    return token


def session_valid(token):
    with SESSIONS_LOCK:
        expiry = SESSIONS.get(token)
        if expiry and expiry > time.time():
            return True
        SESSIONS.pop(token, None)
        return False


def end_session(token):
    with SESSIONS_LOCK:
        SESSIONS.pop(token, None)


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

    def session_token(self):
        cookie = SimpleCookie(self.headers.get("Cookie") or "")
        return cookie["session"].value if "session" in cookie else ""

    def send_json(self, status, payload, cookie=None):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        if cookie is not None:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_api(self, method):
        parts = [p for p in urlparse(self.path).path.split("/") if p][1:]  # drop "api"
        if not parts or len(parts) > 2:
            return self.send_json(404, {"error": "Not found"})
        resource = parts[0]
        if resource in ("login", "logout", "session") and len(parts) == 1:
            return self.handle_auth(method, resource)
        if not session_valid(self.session_token()):
            return self.send_json(401, {"error": "Please log in"})
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

    def handle_auth(self, method, resource):
        if resource == "session" and method == "GET":
            return self.send_json(200, {"logged_in": session_valid(self.session_token())})
        if resource == "logout" and method == "POST":
            end_session(self.session_token())
            return self.send_json(200, {"logged_in": False}, cookie="session=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict")
        if resource == "login" and method == "POST":
            try:
                length = int(self.headers.get("Content-Length") or 0)
                data = json.loads(self.rfile.read(length) or b"{}")
            except (ValueError, json.JSONDecodeError):
                return self.send_json(400, {"error": "Invalid request"})
            if not check_login(data.get("login_id", ""), data.get("password", "")):
                time.sleep(1)  # slow down password guessing
                return self.send_json(401, {"error": "Wrong ID or password"})
            token = new_session()
            return self.send_json(200, {"logged_in": True}, cookie=(
                f"session={token}; Path=/; Max-Age={SESSION_HOURS * 3600}; HttpOnly; SameSite=Strict"))
        return self.send_json(404, {"error": "Not found"})

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
    if "--set-admin" in sys.argv:
        prompt_admin()
        sys.exit(0)
    ensure_admin()
    print(f"MATOSHREE billing running at http://localhost:{PORT}  (database: {DB_PATH})")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
