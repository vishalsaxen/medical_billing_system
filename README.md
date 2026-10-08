# MATOSHREE Surgical & Distributor – Billing

A single-page billing app (`index.html`) that stores its data in **Firebase**
(Cloud Firestore) and uses **Firebase Authentication** for the Super Admin login.
There is no server to run.

## Tabs

- **Main** – comes pre-filled with 15 Main Categories and their Sub Categories; add more Main Categories,
  Sub Categories, and products with their selling price.
- **1. Sale** – browse/search items with prices, add them to a bill, save and print it. Recent bills are listed below.
- **2. Purchase** – placeholder for now.

## One-time Firebase setup

1. **Web app config** – Firebase console › Project settings › *Your apps* › add a Web app (`</>`) if there
   isn't one, then copy the `firebaseConfig` values into the `firebaseConfig` block near the bottom of
   `index.html`. (These values are not secret; the security rules below protect the data.)
2. **Firestore** – Build › Firestore Database › *Create database*. If you created a named database instead of
   `(default)`, put its name in `FIRESTORE_DATABASE` in `index.html`.
3. **Super Admin login** – Build › Authentication › *Get started* › enable **Email/Password**. Under *Users* ›
   *Add user*, create the Super Admin with an email (this is the login ID) and password.
   Under Authentication › Settings › *User actions*, untick **Enable create (sign-up)** so nobody else can register.
4. **Security rules** – put the Super Admin's email in `firestore.rules` and publish it
   (paste it into Firestore › Rules, or run `firebase deploy --only firestore:rules`).
   Only that login can read or write any data.

The first time the Super Admin logs in, the starting categories are added automatically.

## Open the app

Firebase login does not work from a `file://` page, so open it over http:

- **Firebase Hosting** (recommended): `npm i -g firebase-tools`, `firebase login`, `firebase use <project-id>`,
  then `firebase deploy`. The app is then at `https://<project-id>.web.app`.
- **On this computer**: `python -m http.server 8000` in this folder, then open http://localhost:8000.

## Data layout (Firestore)

| Collection       | Fields |
| ---------------- | ------ |
| `mainCategories` | `name`, `nameKey` |
| `subCategories`  | `mainCategoryId`, `name`, `nameKey` |
| `products`       | `subCategoryId`, `name`, `nameKey`, `unit`, `sellingPrice` |
| `sales`          | `number`, `bill_no`, `bill_date`, `customer_name`, `customer_phone`, `items[]`, `total` |
| `counters/sales` | `last` (last bill number used) |
