# MATOSHREE Surgical & Distributor – Billing

A single-page billing app (`index.html`) that stores its data in **Firebase**
(Cloud Firestore) and uses **Firebase Authentication** (SMS OTP on the Super Admin's mobile) for the login.
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
3. **Super Admin login (mobile OTP)** – Build › Authentication › *Get started* › *Sign-in method* › enable
   **Phone**. Firebase only sends real SMS on the **Blaze (pay-as-you-go)** plan. Make sure the address you open
   the app from (for example `<project-id>.web.app`, or `localhost`) is listed under Authentication › Settings ›
   *Authorized domains*.
   **Enrollment:** while there is no Super Admin yet, the page shows *Super Admin Enrollment*. The first person
   to enter their name, mobile number and OTP becomes the Super Admin, and enrollment closes for everyone else.
   So enroll right after publishing the app. To move the login to another number later, use
   **Change login number** in the header: enter the new number and the OTP sent to it.
   The page refuses to send an OTP to any other number, and the security rules refuse every other login.
4. **Security rules** – publish `firestore.rules` (paste it into Firestore › Rules, or run
   `firebase deploy --only firestore:rules`).

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
| `products`       | `subCategoryId`, `name`, `nameKey`, `unit`, `mrp`, `sellingPrice` |
| `sales`          | `number`, `bill_no`, `bill_date`, `customer_name`, `customer_phone`, `items[]`, `total` |
| `counters/sales` | `last` (last bill number used) |
| `settings/admin` | `uid`, `phoneHash` (SHA-256 of the login number), `name` |
