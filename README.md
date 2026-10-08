# MATOSHREE Surgical & Distributor – Billing

A single-page billing app (`index.html`) that stores its data in **Firebase**
(Cloud Firestore) and uses **Firebase Authentication** (email and password) for the Super Admin login.
There is no server to run.

## Tabs

- **Main** – a price list of every Main Category and Sub Category (15 and 76 to start), where you add products and type
  their **MRP** and **S.P.** (S.P. can't exceed MRP). Below it, add, rename or delete categories.
- **1. Sale** – browse/search items with prices, add them to a bill, save and print it. Recent bills are listed below.
- **2. Purchase** – placeholder for now.

## One-time Firebase setup

1. **Web app config** – the app points at the `ganesh-gaurav` project. Firebase console › Project settings › *Your apps* › add a Web app (`</>`) if there
   isn't one, then copy the `firebaseConfig` values into the `firebaseConfig` block near the bottom of
   `index.html`. (These values are not secret; the security rules below protect the data.)
2. **Firestore** – Build › Firestore Database › *Create database*. If you created a named database instead of
   `(default)`, put its name in `FIRESTORE_DATABASE` in `index.html`.
3. **Super Admin login** – Build › Authentication › *Get started* › *Sign-in method* › enable **Email/Password**.
   Under *Users* › *Add user*, create **vishalsaxen@gmail.com** (the root Super Admin username) with its password.
   The password lives only in Firebase, never in this code. Then, under Authentication › Settings › *User actions*,
   untick **Enable create (sign-up)** so nobody else can register. If the app is opened from a new address
   (for example `vishalsaxen.github.io`), add it under Authentication › Settings › *Authorized domains*.
   Once logged in, **Change password** in the header changes it. **Forgot password?** on the login screen emails a
   reset link to vishalsaxen@gmail.com.
4. **Security rules** – publish `firestore.rules` (paste it into Firestore › Rules, or run
   `firebase deploy --only firestore:rules`).

The first time the Super Admin logs in, the starting categories are added automatically.

## Open the app

Firebase login does not work from a `file://` page, so open it over http:

- **GitHub Pages**: repo Settings › Pages › *Deploy from a branch* › `main` / `(root)`. The app is then at
  https://vishalsaxen.github.io/medical_billing_system/
- **Firebase Hosting**: `npm i -g firebase-tools`, `firebase login`, `firebase use <project-id>`,
  then `firebase deploy`. The app is then at `https://<project-id>.web.app`.
- **On this computer**: `python -m http.server 8000` in this folder, then open http://localhost:8000.

## Data layout (Firestore)

| Collection       | Fields |
| ---------------- | ------ |
| `mainCategories` | `name`, `nameKey` |
| `subCategories`  | `mainCategoryId`, `name`, `nameKey` |
| `products`       | `subCategoryId`, `name`, `nameKey`, `unit`, `mrp`, `sellingPrice` |
| `sales`          | `number`, `bill_no`, `bill_date`, `customer_name`, `customer_phone`, `items[]`, `total` |
| `counters/sales` | `last` (last bill number used) |
