# MATOSHREE Surgical & Distributor – Billing

A single-page billing app (`index.html`) that stores its data in **Firebase**
(Cloud Firestore) and uses **Firebase Authentication** (email and password) for the Super Admin login.
There is no server to run.

## Tabs

- **Product List** – a price list of every Main Category and Sub Category (21 and 118 to start, including Pharmacy, Vaccine, Physiotherapy Devices, Sporting Equipment, Pet Care and Nutrition Supplements), where you add products and type
  their **MRP** and **S.P.** (S.P. can't exceed MRP). Below it, add, rename or delete categories.
- **Customer Details** – add, edit and delete customers. Customer / hospital name and mobile are required; Dr. Name, email, GST No. and address are optional.
  A name that already exists is refused. Customers can be picked
  on the Sale and Purchase tabs. Mobile: pick the country (IN, UAE, EUROPE, USA, AUSTRALIA, SAUDI) and type
  the 10-digit number (a pasted +91 or leading 0 is removed); each country's length and starting digits are checked. Europe takes country code + number. Email: syntax, throwaway domains (Mailinator,
  Yopmail, ...) and the domain's mail server (MX record, looked up with Google DNS-over-HTTPS) are checked, and shared
  role addresses like info@ are flagged. Mailbox-exists (SMTP) and catch-all checks need a server and are not done.
  GST No. is checked for state code, PAN, entity number, the fixed `Z` and the check digit.
- **1. Sale** – type the customer name or pick it from the drop-down; a saved customer fills in mobile, Dr. Name and email (a new name is a walk-in, mobile still required). Then browse/search items with prices, add them to a bill, save and print it (the print shows the customer's name, mobile, email, Dr. Name, address and GST No.).
  **Generate Report** lists every bill line from one date to another (e.g. 02 Oct 2026 - 12 Oct 2026) and downloads it as Excel (.xlsx), CSV or PDF. Recent Bills below shows only today's bills.
- **2. Purchase** – choose the customer to purchase from; purchase entry comes next.

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

The first time the Super Admin logs in, the starting categories are added automatically. When a new set of starting
categories is added to the code, it is added once on the next login (`counters/seed` remembers this), so deleted ones don't come back.

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
| `customers`      | `name`, `nameKey`, `phone`, `doctor`, `email`, `gstin`, `address` |
| `sales`          | `number`, `bill_no`, `bill_date`, `customer_id`, `customer_name`, `customer_phone`, `customer_email`, `customer_doctor`, `customer_address`, `customer_gstin`, `items[]`, `total` |
| `counters/sales` | `last` (last bill number used) |
| `counters/seed`  | `version` (how many starting category sets were added) |
