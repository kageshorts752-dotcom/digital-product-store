# Digital Product Store — Flask

A complete, ready-to-run digital product selling website: storefront, tiered
licenses, bundles, guest checkout, secure signed downloads, license keys,
customer library, coupons, affiliates, and an admin backend.

## Run locally

```bash
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000
python test_app.py   # route + payment + webhook tests
```

Seeded products (6): Modern UI Kit Pro, Sell Digital Products guide (PDF),
Lo-Fi Sample Pack, Startup Landing Page Template, Moody Lightroom Presets,
Creator OS Notion Template. Sample files live in `private_files/` — they are
**never served directly**; downloads go through `/download/<signed-token>` only.

Admin login (demo — change before production):
- Email: `admin@store.local`
- Password: `admin123`

Coupons to try: `WELCOME10` (10%), `FLAT100` (₹100 off), `FLASH25` (25%).
Affiliate demo link: `/ref/creator1` (10% commission logged on purchase).

## What is demo / simulated vs production-ready

| Area | Status |
|---|---|
| YouPI UPI (PRIMARY checkout method) | Experimental gateway, pending until verified webhook or admin confirmation — see YouPI section below. Demo Stripe/Razorpay/PayPal are secondary fallbacks only. |
| Stripe / PayPal / Razorpay | DEMO ONLY, secondary fallbacks. No keys, no real charges. "Pay (demo)" simulates `payment_intent.succeeded` and unlocks files. A real integration must use the gateway SDK + a verified webhook, in production mode, with keys in env vars — see Production checklist below. |
| UPI (direct) | REAL payee option. Checkout shows the store owner's UPI ID from `config.py`, a `upi://pay` link (pa, pn, am, tn=order ID), and a locally generated QR if `qrcode` is installed (no external QR service). Orders stay **pending** until admin confirms receipt (Admin > Orders) or `/webhook/upi` is called. Files do **not** unlock on UPI selection alone. |
| YouPI UPI | EXPERIMENTAL ONLY — see below. Pluggable gateway, pending until a verified signed webhook or admin confirmation. |
| Signed downloads | Production pattern: HMAC-signed tokens, 15-minute expiry, 5-download snapshot per order item, IP/user-agent logging, refunded/revoked blocking. Storage is local `private_files/` here; swap to S3/R2 signed URLs in production. |
| License keys | Generated per order item for keyed products; `/api/verify-license` checks status/activations. |
| Email notifications | LOGGED only (`notifications` table) unless you configure SMTP. Update emails are not sent for real in this build. |
| GST invoice | 18% GST for India (country selector), 0% elsewhere; printable HTML invoice per order. This is a simple calculation, not tax advice. |

## YouPI PG — read before using it for real money

YouPI PG V2 (https://github.com/youpi-pg/YouPI-PG) is, in its own README,
**a research / experimental project only. It is NOT certified, bank-approved,
NPCI-approved, audited, or production-ready.** This store respects that:

- Do NOT rely on YouPI for critical, high-value, high-volume, or
  time-sensitive payments. Do NOT use it as sole proof of settlement.
- Suggested test limit from the YouPI README: **20 transactions/day per
  receiving account** (a conservative project guideline, not a universal NPCI limit).
- This store implements only the **universal integration pattern**: a dynamic
  UPI QR / `upi://pay` link for the merchant VPA already in `config.py`,
  order amount, and the order ID as reference — plus a **YouPI-compatible
  webhook** at `POST /webhook/youpi` that verifies, over the **raw request
  body** before JSON parsing:
  - `X-Gateway-Signature: sha256=HMAC-SHA256(secret, rawBody)`
  - optionally `X-Gateway-Signature-V2: sha256=HMAC-SHA256(secret, "<ts>.<rawBody>")`
  - `X-Gateway-Event: SUCCESS`, `X-Gateway-Delivery-Id` (deduplicated),
    `X-Gateway-Timestamp`
  - Payload: `event, orderId, amount, amountPaise, utr, paymentId,
    deliveryId, timestamp, verificationTag, verificationLevel`
  - Amount mismatch returns **409 ORDER_AMOUNT_MISMATCH**; bad signature
    returns 401. If `YOUPI_WEBHOOK_SECRET` is unset, the webhook will NOT
    auto-unlock — admin manual confirmation is required instead.
- **NOT included in this build, and NOT in the Vercel deploy:** the separate
  self-hosted Node.js service stack, the Android observer APK, and Gmail /
  Google Messages ingestion. No APKs are installed, no Gmail is connected,
  and no real bank SMS data is used here. YouPI will NOT run fully on
  Vercel serverless for that reason.
- **Always reconcile YouPI payments against bank records** (amount + UTR)
  before treating an order as settled. For critical sales, use
  Razorpay/Stripe — the recommended production gateways.

Set the secret (self-hosted only, never commit it):

```bash
export YOUPI_WEBHOOK_SECRET="your-long-random-secret"
```

## Vercel

This project is Vercel-ready: `api/index.py` (Flask entry point),
`vercel.json` (all routes → `/api/index.py`), `requirements.txt` (Flask only).

**Ephemeral-data caveat (same as the Sports Question Bank app):** on Vercel,
SQLite is seeded to a writable `/tmp` copy when the `VERCEL` env var is set,
because the deployment filesystem is read-only. Orders, downloads, and
licenses created on Vercel do **not** persist across cold starts / redeploys
without a hosted database. Do not run real sales on the Vercel demo without
a hosted Postgres (or similar) + object storage.

## Production checklist (before real sales)

1. Change `SECRET_KEY` and the admin password; use env vars, never commit secrets.
2. Replace demo gateways with real Stripe/Razorpay SDK + verified webhooks.
3. Move `private_files/` to S3/R2 and serve real signed URLs (15 min, 5 downloads).
4. Replace SQLite with hosted Postgres (schema in `schema.sql` is Postgres-style).
5. Configure SMTP for order, update, and affiliate emails; add HTTPS + rate limiting.
6. For YouPI, if you ever use it: self-host its Node.js stack separately,
   complete its observer setup yourself, get legal/compliance advice, confirm
   requirements with your bank, and reconcile every payment against bank records.
7. Confirm GST/tax handling with a tax adviser for your jurisdiction.
