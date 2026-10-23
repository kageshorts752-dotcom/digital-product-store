"""Digital Product Store — Flask, SQLite, demo payments + real UPI option.

DEMO vs REAL — read this first:
* Stripe / PayPal / Razorpay in this build are DEMO ONLY. No keys, no real
  charges. Selecting one and clicking "Pay (demo)" marks the order paid
  (simulating payment_intent.succeeded) and unlocks files, exactly as a
  webhook would. See /webhook/<gateway> for the webhook simulation.
* UPI is a REAL payee option: checkout shows the store owner's UPI ID
  (from config.py), a upi://pay link and a QR code (generated locally if
  the `qrcode` library is installed, otherwise link + copyable ID only —
  no external QR service is ever called). UPI orders stay PENDING until
  the admin confirms receipt in Admin > Orders (or via /webhook/upi).
  Files are NOT unlocked on UPI selection alone, because UPI has no
  automatic webhook in this build.
* On Vercel, orders/downloads are EPHEMERAL without a hosted database:
  SQLite lives in /tmp and is reset on cold starts / redeploys.
"""
import base64
import hashlib
import hmac
import io
import json
import os
import re
import sqlite3
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, send_file, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from config import (DOWNLOAD_LINK_MINUTES, DOWNLOAD_MAX_DEFAULT,
                        GST_RATE_IN, SECRET_KEY, STORE_NAME, UPI_ID,
                        UPI_PAYEE_NAME, YOUPI_WEBHOOK_SECRET)
except Exception:  # config.py missing (e.g. partial copy)
    DOWNLOAD_LINK_MINUTES, DOWNLOAD_MAX_DEFAULT = 15, 5
    GST_RATE_IN, SECRET_KEY = 0.18, "change-me-before-production"
    STORE_NAME, UPI_ID, UPI_PAYEE_NAME = "Digital Store", "", "Digital Store"
    YOUPI_WEBHOOK_SECRET = os.environ.get("YOUPI_WEBHOOK_SECRET", "")

BASE = os.path.dirname(os.path.abspath(__file__))
PRIVATE = os.path.join(BASE, "private_files")
os.makedirs(PRIVATE, exist_ok=True)

# --- Product picture uploads: local disk under static/uploads/, but on
# Vercel the filesystem is read-only, so uploads go to /tmp and are served
# by the /uploads/<filename> route below (ephemeral on cold start/redeploy;
# an image URL is the durable option on the live site).
if os.environ.get("VERCEL"):
    UPLOAD_DIR = "/tmp/store_uploads"
else:
    UPLOAD_DIR = os.path.join(BASE, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def save_picture_upload(f):
    """Validate + save an uploaded picture; return its URL or (None, error)."""
    if not f or not f.filename:
        return None, "Choose a picture file."
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in ALLOWED_IMAGE_EXTS:
        return None, "Picture must be png, jpg, jpeg, webp or gif."
    from werkzeug.utils import secure_filename
    fname = f"{uuid.uuid4().hex[:12]}-{secure_filename(f.filename)}"
    path = os.path.join(UPLOAD_DIR, fname)
    f.save(path)
    if os.path.getsize(path) > MAX_IMAGE_BYTES:
        os.remove(path)
        return None, "Picture must be under 5 MB."
    return f"/uploads/{fname}", None

# --- Database path: Vercel filesystem is read-only, so seed to /tmp ---
if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/digital_store.db"
else:
    DB_PATH = os.path.join(BASE, "store.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", SECRET_KEY)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_e=None):
    d = g.pop("db", None)
    if d is not None:
        d.close()


def q(sql, args=(), one=False):
    cur = db().execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def exec_sql(sql, args=()):
    cur = db().execute(sql, args)
    db().commit()
    return cur


# ---------------- minimal PDF builder (stdlib only) ----------------
def minimal_pdf(title, lines):
    """Return bytes of a tiny valid 1-page PDF with the given text lines."""
    def esc(t):
        return t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = "BT /F1 14 Tf 50 750 Td (%s) Tj ET\n" % esc(title[:80])
    y = 720
    for line in lines:
        stream += "BT /F1 10 Tf 50 %d Td (%s) Tj ET\n" % (y, esc(line[:110]))
        y -= 16
    objs = []
    objs.append("<< /Type /Catalog /Pages 2 0 R >>")
    objs.append("<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objs.append("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>")
    objs.append("<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
    objs.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += ("%d 0 obj\n%s\nendobj\n" % (i, o)).encode()
    xref = len(out)
    out += ("xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)).encode()
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF"
            % (len(objs) + 1, xref)).encode()
    return out


def make_sample_files():
    """Generate small real sample files in private_files/ (never served raw)."""
    samples = {
        "freelance-playbook.pdf": ("pdf", ["Freelance Client-Getting Playbook — Sample Chapter",
                                     "Find clients, price work, and close deals."]),
        "reels-growth-bundle.zip": ("zip", {"README.txt": "Instagram Reels Growth Bundle — 500 vertical clips.\nSample only."}),
        "shorts-starter-pack.zip": ("zip", {"README.txt": "YouTube Shorts Starter Pack — 300 vertical videos.\nSample only."}),
        "python-course-bundle.zip": ("zip", {"README.txt": "Python for Beginners — 42 video lessons.\nSample only."}),
        "canva-template-pack.zip": ("zip", {"README.txt": "Canva Social Media Template Pack — 200 designs.\nSample only."}),
        "wedding-presets.zip": ("zip", {"presets.txt": "Wedding Photography Preset Collection — 60 looks.\nSample only."}),
        "meal-prep-guide.pdf": ("pdf", ["Healthy Meal Prep Guide — Sample Week",
                                     "Plan meals, prep once, eat well all week."]),
        "spoken-english-course.zip": ("zip", {"README.txt": "Spoken English Video Course — 60 lessons.\nSample only."}),
        "motivational-reels.zip": ("zip", {"README.txt": "Motivational Reels Bundle — 250 clips.\nSample only."}),
        "ui-kit-pro.zip": ("zip", {"README.txt": "Modern UI Kit Pro — 120 components, Figma + HTML.\nSample only."}),
        "ebook-guide.pdf": ("pdf", ["Digital Product Selling — Sample Chapter",
                                     "Sell files, not shipping. Instant delivery."]),
        "music-pack.zip": ("zip", {"tracklist.txt": "Lo-Fi Sample Pack — 20 loops, WAV, 120 BPM.\nSample only."}),
        "code-template.zip": ("zip", {"index.html": "<h1>Startup Landing Template</h1>\n<!-- sample -->"}),
        "presets.zip": ("zip", {"presets.txt": "Lightroom Presets — 15 looks, XMP + DNG.\nSample only."}),
        "notion-template.zip": ("zip", {"template.md": "# Creator OS — Notion Template\nTasks, content calendar, CRM.\n"}),
    }
    for name, (kind, payload) in samples.items():
        path = os.path.join(PRIVATE, name)
        if os.path.exists(path):
            continue
        if kind == "zip":
            with zipfile.ZipFile(path, "w") as z:
                for fn, txt in payload.items():
                    z.writestr(fn, txt)
        else:
            with open(path, "wb") as f:
                f.write(minimal_pdf(payload[0], payload[1:]))
    return samples


LICENSE_MULT = {"Personal": 1.0, "Commercial": 1.3, "Extended": 1.6}
LICENSE_LABEL = {"Personal": "Personal — 1 project",
                 "Commercial": "Commercial — up to 10 projects",
                 "Extended": "Extended — unlimited / resale in a product"}


def _seed_products():
    return [
        ("modern-ui-kit", "Modern UI Kit Pro", "Templates",
         "120 Figma + HTML components, dark/light themes, design tokens.",
         59, "INR", "zip", "18 MB", "Figma 2024+, any browser",
         "Figma, HTML, CSS", "120 components, 40 screens, tokens, icons.",
         "ui-kit-pro.zip", True, "/static/product-images/modern-ui-kit.jpg",
         "PixelCraft Studio", "top_pick", "120 components"),
        ("lofi-sample-pack", "Lo-Fi Sample Pack Vol. 1", "Music",
         "20 royalty-free lo-fi loops and drum hits for producers.",
         49, "INR", "zip", "210 MB", "Any DAW",
         "WAV, 44.1kHz", "20 loops, 30 one-shots, 120 BPM.",
         "music-pack.zip", False, "/static/product-images/lofi-sample-pack.jpg",
         "ReelForge Media", "", "50 audio files"),
        ("creator-os-notion", "Creator OS — Notion Template", "Templates",
         "Plan content, track clients and run a creator business in Notion.",
         49, "INR", "zip", "1.4 MB", "Notion (free plan works)",
         "Markdown, Notion", "Content calendar, CRM, finance tracker.",
         "notion-template.zip", False, "/static/product-images/creator-os.jpg",
         "StudyNest Press", "", "12 dashboards"),
        ("freelance-playbook", "Freelance Client-Getting Playbook", "PDF Guides",
         "An original PDF playbook for landing freelance clients: outreach scripts, pricing, proposals and follow-ups.",
         59, "INR", "pdf", "8.6 MB", "Any PDF reader",
         "PDF", "142 pages, scripts, templates, checklists.",
         "freelance-playbook.pdf", False, "/static/product-images/freelance-playbook.jpg",
         "LearnLoop Academy", "top_pick", "142 pages"),
        ("reels-growth-bundle", "Instagram Reels Growth Bundle — 500 Reels", "Reels Bundles",
         "500 ready-to-post vertical reels for creators: hooks, captions and trending formats in one bundle.",
         59, "INR", "zip", "4.8 GB", "Instagram, any editor",
         "MP4, 1080x1920", "500 reels, captions included.",
         "reels-growth-bundle.zip", False, "/static/product-images/reels-growth-bundle.jpg",
         "ReelForge Media", "staff_pick", "500 videos"),
        ("shorts-starter-pack", "YouTube Shorts Starter Pack — 300 Videos", "Video Bundles",
         "300 vertical short videos to kick-start a channel: intros, explainers and faceless formats.",
         49, "INR", "zip", "3.2 GB", "YouTube, any editor",
         "MP4, 1080x1920", "300 videos, ready to upload.",
         "shorts-starter-pack.zip", False, "/static/product-images/shorts-starter-pack.jpg",
         "ReelForge Media", "todays_choice", "300 videos"),
        ("python-course-bundle", "Python for Beginners — Complete Course Bundle", "Courses",
         "A friendly video course bundle taking you from first script to small real projects, with exercises.",
         59, "INR", "zip", "6.1 GB", "Any video player",
         "MP4, 1080p", "42 lessons, exercises, solutions.",
         "python-course-bundle.zip", False, "/static/product-images/python-beginners.jpg",
         "LearnLoop Academy", "top_pick", "42 videos"),
        ("canva-template-pack", "Canva Social Media Template Pack — 200 Designs", "Templates",
         "200 editable social templates for posts, stories and carousels, in a clean modern style.",
         49, "INR", "zip", "96 MB", "Canva (free plan works)",
         "Canva", "200 templates, posts + stories.",
         "canva-template-pack.zip", False, "/static/product-images/canva-template-pack.jpg",
         "PixelCraft Studio", "latest", "200 templates"),
        ("wedding-presets", "Wedding Photography Preset Collection — 60 Looks", "Presets",
         "60 warm, timeless wedding presets for Lightroom, with before/after examples.",
         49, "INR", "zip", "18 MB", "Lightroom Classic / Mobile",
         "XMP, DNG", "60 presets, before/after guide.",
         "wedding-presets.zip", False, "/static/product-images/wedding-presets.jpg",
         "PixelCraft Studio", "staff_pick", "60 presets"),
        ("meal-prep-guide", "Healthy Meal Prep Guide — 90-Day PDF Plan", "PDF Guides",
         "A practical 90-day meal prep PDF: weekly plans, shopping lists and simple recipes.",
         39, "INR", "pdf", "6.4 MB", "Any PDF reader",
         "PDF", "118 pages, shopping lists, recipes.",
         "meal-prep-guide.pdf", False, "/static/product-images/meal-prep-guide.jpg",
         "StudyNest Press", "latest", "118 pages"),
        ("spoken-english-course", "Spoken English Video Course — 60 Lessons", "Courses",
         "60 short video lessons for everyday spoken English: speaking drills, vocabulary and practice tasks.",
         59, "INR", "zip", "4.4 GB", "Any video player",
         "MP4, 1080p", "60 lessons, practice tasks.",
         "spoken-english-course.zip", False, "/static/product-images/spoken-english.jpg",
         "LearnLoop Academy", "todays_choice", "60 videos"),
        ("motivational-reels", "Motivational Reels Bundle — 250 Clips", "Reels Bundles",
         "250 short motivational clips with captions, ready for reels and shorts.",
         49, "INR", "zip", "2.1 GB", "Instagram, YouTube, any editor",
         "MP4, 1080x1920", "250 clips, captions included.",
         "motivational-reels.zip", False, "/static/product-images/motivational-reels.jpg",
         "ReelForge Media", "", "250 videos"),
    ]


def seed():
    make_sample_files()
    # Fresh DB only: if an admin user already exists, this DB was already
    # seeded (or deliberately wiped with Delete All) — never re-seed, or
    # Delete All would be undone on the next request.
    if q("SELECT COUNT(*) c FROM products", one=True)["c"]:
        return
    if q("SELECT COUNT(*) c FROM users", one=True)["c"]:
        return
    products = _seed_products()
    for (slug, title, cat, desc, price, cur, fmt, size, soft, fmt2, spec,
         fname, needs_key, img_url, seller, badge, item_count) in products:
        pid = str(uuid.uuid4())
        exec_sql("""INSERT INTO products (product_id, slug, title, category,
            description, price, currency, file_format, file_size, software,
            specs, preview_text, image_url, requires_license_key, is_published,
            seller_name, badge, item_count)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?)""",
                 (pid, slug, title, cat, desc, price, cur, fmt, size, soft,
                  spec, desc, img_url, 1 if needs_key else 0,
                  seller, badge, item_count))
        fpath = os.path.join(PRIVATE, fname)
        exec_sql("""INSERT INTO product_files (file_id, product_id, version_label,
            file_name, storage_object_key, file_size_bytes, is_latest)
            VALUES (?,?,?,?,?,?,1)""",
                 (str(uuid.uuid4()), pid, "1.0.0", fname, fname,
                  os.path.getsize(fpath)))
    # coupons
    exec_sql("INSERT INTO coupons VALUES (?,?,?,?,?,?,?)",
             ("WELCOME10", 10, None, 100, 0, "2099-01-01", 1))
    exec_sql("INSERT INTO coupons VALUES (?,?,?,?,?,?,?)",
             ("FLAT100", None, 100, 50, 0, "2099-01-01", 1))
    exec_sql("INSERT INTO coupons VALUES (?,?,?,?,?,?,?)",
             ("FLASH25", 25, None, 20, 0, "2099-01-01", 1))
    # affiliate
    exec_sql("INSERT INTO affiliates VALUES (?,?,?,?)",
             ("AFF1", "creator1", 0.10, 1))
    # bundles
    exec_sql("INSERT INTO bundles VALUES (?,?,?,?)",
             ("B1", "Creator Bundle", "UI Kit + Creator OS + Lo-Fi Pack", 99))
    for slug in ("modern-ui-kit", "creator-os-notion", "lofi-sample-pack"):
        row = q("SELECT product_id FROM products WHERE slug=?", (slug,), one=True)
        exec_sql("INSERT INTO bundle_items VALUES (?,?,?)",
                 (str(uuid.uuid4()), "B1", row["product_id"]))
    # admin (change password before production!)
    exec_sql("INSERT INTO users VALUES (?,?,?,?,?,?,?)",
             (str(uuid.uuid4()), "admin@store.local",
              generate_password_hash("admin123"), "Store Admin", "admin",
              datetime.now(timezone.utc).isoformat(),
              datetime.now(timezone.utc).isoformat()))


SEEDED_IMAGES = {'modern-ui-kit': '/static/product-images/modern-ui-kit.jpg', 'lofi-sample-pack': '/static/product-images/lofi-sample-pack.jpg', 'creator-os-notion': '/static/product-images/creator-os.jpg'}


def init_db():
    db().executescript(open(os.path.join(BASE, "schema.sql")).read())
    db().commit()
    # Guarded migrations for columns added after the first schema.
    for col, ddl in (
        ("image_url", "ALTER TABLE products ADD COLUMN image_url TEXT"),
        ("seller_name", "ALTER TABLE products ADD COLUMN seller_name TEXT DEFAULT 'Shirish Digital Store'"),
        ("badge", "ALTER TABLE products ADD COLUMN badge TEXT DEFAULT ''"),
        ("item_count", "ALTER TABLE products ADD COLUMN item_count TEXT DEFAULT ''"),
    ):
        try:
            db().execute(ddl)
            db().commit()
        except Exception:
            pass  # column already exists
    # Backfill seeded products (existing DBs): force new local pictures and
    # the new 39-59 price range, so old DBs match the fresh-seed catalogue.
    _SEEDED_BY_SLUG = {t[0]: t for t in _seed_products()}
    for slug, t in _SEEDED_BY_SLUG.items():
        _img = {"modern-ui-kit": "modern-ui-kit.jpg", "lofi-sample-pack": "lofi-sample-pack.jpg", "creator-os-notion": "creator-os.jpg", "freelance-playbook": "freelance-playbook.jpg", "reels-growth-bundle": "reels-growth-bundle.jpg", "shorts-starter-pack": "shorts-starter-pack.jpg", "python-course-bundle": "python-beginners.jpg", "canva-template-pack": "canva-template-pack.jpg", "wedding-presets": "wedding-presets.jpg", "meal-prep-guide": "meal-prep-guide.jpg", "spoken-english-course": "spoken-english.jpg", "motivational-reels": "motivational-reels.jpg"}[slug]
        db().execute("UPDATE products SET image_url=?, price=? WHERE slug=?",
                     (f"/static/product-images/{_img}", t[4], slug))
    db().commit()
    seed()
    # Backfill: stores seeded before the marketplace catalogue existed only
    # have the old products — insert any seeded product whose slug is missing,
    # so existing DBs gain the new PDF/video bundles without duplicates.
    for (slug, title, cat, desc, price, cur, fmt, size, soft, fmt2, spec,
         fname, needs_key, img_url, seller, badge, item_count) in _seed_products():
        row = q("SELECT product_id FROM products WHERE slug=?", (slug,), one=True)
        if row:
            continue
        pid = str(uuid.uuid4())
        exec_sql("""INSERT INTO products (product_id, slug, title, category,
            description, price, currency, file_format, file_size, software,
            specs, preview_text, image_url, requires_license_key, is_published,
            seller_name, badge, item_count)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?)""",
                 (pid, slug, title, cat, desc, price, cur, fmt, size, soft,
                  spec, desc, img_url, 1 if needs_key else 0,
                  seller, badge, item_count))
        fpath = os.path.join(PRIVATE, fname)
        if os.path.isfile(fpath):
            exec_sql("""INSERT INTO product_files (file_id, product_id, version_label,
                file_name, storage_object_key, file_size_bytes, is_latest)
                VALUES (?,?,?,?,?,?,1)""",
                     (str(uuid.uuid4()), pid, "1.0.0", fname, fname,
                      os.path.getsize(fpath)))


# ---------------- signed download tokens ----------------
def sign_token(order_item_id, minutes=DOWNLOAD_LINK_MINUTES):
    exp = int((datetime.now(timezone.utc) + timedelta(minutes=minutes)).timestamp())
    payload = f"{order_item_id}:{exp}"
    sig = hmac.new(app.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}:{sig}".encode()).decode()


def verify_token(token):
    try:
        payload_sig = base64.urlsafe_b64decode(token.encode()).decode()
        item_id, exp, sig = payload_sig.rsplit(":", 2)
        expect = hmac.new(app.secret_key.encode(), f"{item_id}:{exp}".encode(),
                          hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expect, sig):
            return None, "bad signature"
        if int(exp) < datetime.now(timezone.utc).timestamp():
            return None, "expired"
        return item_id, None
    except Exception:
        return None, "invalid token"


def stamped_download(file_path, file_name, email, txn_id):
    """Simulation of file stamping: buyer email + transaction ID baked in."""
    stamp = f"Licensed to: {email} | Transaction: {txn_id}\n"
    buf = io.BytesIO()
    if file_name.endswith(".txt"):
        with open(file_path, "rb") as f:
            buf.write(stamp.encode() + f.read())
    elif file_name.endswith(".zip"):
        with zipfile.ZipFile(file_path) as zin:
            with zipfile.ZipFile(buf, "w") as zout:
                for item in zin.infolist():
                    zout.writestr(item, zin.read(item.filename))
                zout.writestr("STAMP.txt", stamp)
    elif file_name.endswith(".pdf"):
        buf.write(minimal_pdf("Licensed copy",
                              [stamp.strip(), f"Product file: {file_name}",
                               "This stamped cover page proves licensed delivery."]))
    else:
        with open(file_path, "rb") as f:
            buf.write(f.read())
    buf.seek(0)
    return buf


def cart_items():
    items = []
    for entry in session.get("cart", []):
        if entry.get("bundle_id"):
            b = q("SELECT * FROM bundles WHERE bundle_id=?", (entry["bundle_id"],), one=True)
            if b:
                items.append({"kind": "bundle", "bundle": b, "price": b["bundle_price"],
                              "license": "Bundle", "qty": 1})
        else:
            p = q("SELECT * FROM products WHERE product_id=?", (entry["product_id"],), one=True)
            if p:
                lic = entry.get("license", "Personal")
                items.append({"kind": "product", "product": p, "license": lic,
                              "price": round(p["price"] * LICENSE_MULT.get(lic, 1.0), 2),
                              "qty": 1})
    return items


def cart_total(items, coupon=None, country="IN"):
    subtotal = sum(i["price"] for i in items)
    discount = 0
    if coupon:
        if coupon["discount_pct"]:
            discount = round(subtotal * coupon["discount_pct"] / 100, 2)
        elif coupon["discount_amount"]:
            discount = min(coupon["discount_amount"], subtotal)
    taxable = subtotal - discount
    tax = round(taxable * GST_RATE_IN, 2) if country == "IN" else 0.0
    return subtotal, discount, tax, round(taxable + tax, 2)


def create_order(email, items, totals, gateway, country, coupon_code, ref):
    subtotal, discount, tax, total = totals
    oid = str(uuid.uuid4())
    # UPI and YouPI stay pending: no auto-webhook unlocks them here.
    status = "pending" if gateway in ("upi", "youpi") else "paid"
    exec_sql("""INSERT INTO orders (order_id, user_id, buyer_email, status,
        subtotal_amount, tax_amount, discount_amount, total_amount, currency,
        payment_gateway, gateway_order_id, buyer_ip, created_at, paid_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
             (oid, session.get("user_id"), email, status, subtotal, tax,
              discount, total, "INR", gateway, f"{gateway.upper()}-{oid[:8]}",
              request.remote_addr,
              datetime.now(timezone.utc).isoformat(),
              datetime.now(timezone.utc).isoformat() if status == "paid" else None))
    for it in items:
        if it["kind"] == "bundle":
            prods = q("SELECT product_id FROM bundle_items WHERE bundle_id=?",
                      (it["bundle"]["bundle_id"],))
            share = round(it["price"] / max(len(prods), 1), 2)
            for pr in prods:
                add_order_item(oid, pr["product_id"], share, "Bundle")
        else:
            add_order_item(oid, it["product"]["product_id"], it["price"], it["license"])
    if coupon_code:
        exec_sql("UPDATE coupons SET used_count = used_count + 1 WHERE code=?", (coupon_code,))
    if ref:
        aff = q("SELECT * FROM affiliates WHERE code=?", (ref,), one=True)
        if aff:
            exec_sql("INSERT INTO affiliate_commissions VALUES (?,?,?,?,?,?)",
                     (str(uuid.uuid4()), aff["affiliate_id"], oid,
                      round(total * aff["commission_rate"], 2), "pending",
                      datetime.now(timezone.utc).isoformat()))
    return oid


def add_order_item(oid, pid, price, lic):
    p = q("SELECT * FROM products WHERE product_id=?", (pid,), one=True)
    item_id = str(uuid.uuid4())
    exec_sql("""INSERT INTO order_items VALUES (?,?,?,?,?,?,?,?)""",
             (item_id, oid, pid, price, 0, DOWNLOAD_MAX_DEFAULT, None,
              datetime.now(timezone.utc).isoformat()))
    if p and p["requires_license_key"]:
        key = "PROD-" + "-".join(uuid.uuid4().hex[i:i + 4].upper() for i in (0, 4, 8))
        exec_sql("""INSERT INTO license_keys VALUES (?,?,?,?,?,?,?,?,?)""",
                 (str(uuid.uuid4()), item_id, pid, key, "active", 0, 3, None,
                  datetime.now(timezone.utc).isoformat()))
    return item_id


# ---------------- storefront ----------------
def _seller_slug(name):
    return (name or "").strip().lower().replace(" ", "-").replace("_", "-")


@app.route("/")
def index():
    qterm = (request.args.get("q") or "").strip()
    cat = (request.args.get("category") or "").strip()
    bundles = q("SELECT * FROM bundles")
    categories = [r["category"] for r in
                  q("SELECT DISTINCT category FROM products WHERE is_published=1 ORDER BY category")
                  if r["category"]]
    if qterm or cat:
        sql = "SELECT * FROM products WHERE is_published=1"
        args = []
        if qterm:
            sql += " AND (title LIKE ? OR description LIKE ? OR seller_name LIKE ?)"
            like = f"%{qterm}%"
            args += [like, like, like]
        if cat:
            sql += " AND category=?"
            args.append(cat)
        sql += " ORDER BY title"
        products = q(sql, args)
        return render_template("index.html", products=products, bundles=bundles,
                               store=STORE_NAME, q=qterm, category=cat,
                               categories=categories, searching=True,
                               top_picks=[], new_arrivals=[], editors=[],
                               todays=[], spotlights={})
    products = q("SELECT * FROM products WHERE is_published=1 ORDER BY title")
    top_picks = q("SELECT * FROM products WHERE is_published=1 AND badge='top_pick' ORDER BY title")
    new_arrivals = q("SELECT * FROM products WHERE is_published=1 AND badge='latest' ORDER BY title")
    editors = q("SELECT * FROM products WHERE is_published=1 AND badge='staff_pick' ORDER BY title")
    todays = q("SELECT * FROM products WHERE is_published=1 AND badge='todays_choice' ORDER BY title")
    spotlights = {}
    for c in categories:
        spotlights[c] = q("SELECT * FROM products WHERE is_published=1 AND category=? ORDER BY title", (c,))
    return render_template("index.html", products=products, bundles=bundles,
                           store=STORE_NAME, q="", category="", categories=categories,
                           searching=False, top_picks=top_picks,
                           new_arrivals=new_arrivals, editors=editors,
                           todays=todays, spotlights=spotlights)


@app.route("/store/<seller>")
def seller_page(seller):
    all_products = q("SELECT * FROM products WHERE is_published=1 ORDER BY title")
    matched = [p for p in all_products if _seller_slug(p["seller_name"]) == seller.lower()]
    if not matched:
        # Fall back to a case-insensitive exact-name match (spaces decoded).
        matched = [p for p in all_products if (p["seller_name"] or "").lower() == seller.lower()]
    if not matched:
        abort(404)
    name = matched[0]["seller_name"]
    return render_template("store.html", seller=name, products=matched,
                           count=len(matched))


@app.route("/product/<slug>")
def product_page(slug):
    p = q("SELECT * FROM products WHERE slug=?", (slug,), one=True)
    if not p:
        abort(404)
    upsells = q("SELECT * FROM products WHERE is_published=1 AND product_id != ? LIMIT 3",
                (p["product_id"],))
    return render_template("product.html", p=p, upsells=upsells,
                           licenses=LICENSE_MULT, labels=LICENSE_LABEL)


@app.route("/preview/<slug>")
def preview(slug):
    p = q("SELECT * FROM products WHERE slug=?", (slug,), one=True)
    if not p:
        abort(404)
    return render_template("preview.html", p=p)


@app.route("/cart/add", methods=["POST"])
def cart_add():
    cart = session.get("cart", [])
    if request.form.get("bundle_id"):
        cart.append({"bundle_id": request.form["bundle_id"]})
    else:
        cart.append({"product_id": request.form["product_id"],
                     "license": request.form.get("license", "Personal")})
    session["cart"] = cart
    if request.form.get("ref"):
        session["ref"] = request.form["ref"]
    flash("Added to cart.")
    return redirect(url_for("cart"))


@app.route("/cart")
def cart():
    items = cart_items()
    coupon = None
    if session.get("coupon"):
        coupon = q("SELECT * FROM coupons WHERE code=?", (session["coupon"],), one=True)
    totals = cart_total(items, coupon, session.get("country", "IN"))
    upsells = q("SELECT * FROM products WHERE is_published=1 LIMIT 3")
    return render_template("cart.html", items=items, totals=totals,
                           coupon=coupon, upsells=upsells)


@app.route("/cart/clear")
def cart_clear():
    session.pop("cart", None)
    session.pop("coupon", None)
    return redirect(url_for("cart"))


@app.route("/coupon", methods=["POST"])
def apply_coupon():
    code = request.form.get("code", "").strip().upper()
    c = q("SELECT * FROM coupons WHERE code=? AND active=1", (code,), one=True)
    if not c or (c["usage_limit"] and c["used_count"] >= c["usage_limit"]):
        flash("Coupon invalid, expired, or fully used.")
    else:
        session["coupon"] = code
        flash(f"Coupon {code} applied.")
    return redirect(url_for("cart"))


# ---------------- checkout ----------------
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items = cart_items()
    if not items:
        flash("Your cart is empty.")
        return redirect(url_for("index"))
    coupon = q("SELECT * FROM coupons WHERE code=?", (session.get("coupon"),), one=True) if session.get("coupon") else None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        country = request.form.get("country", "IN")
        gateway = request.form.get("gateway", "stripe")
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            flash("Enter a valid email address.")
            return redirect(url_for("checkout"))
        session["country"] = country
        totals = cart_total(items, coupon, country)
        oid = create_order(email, items, totals, gateway, country,
                           session.get("coupon"), session.get("ref"))
        session.pop("cart", None)
        session.pop("coupon", None)
        return redirect(url_for("order_success", order_id=oid))
    totals = cart_total(items, coupon, session.get("country", "IN"))
    upi_link = None
    if UPI_ID:
        # upi://pay?pa=...&pn=...&am=...&tn=... (amount only, no keys)
        upi_link = (f"upi://pay?pa={quote(UPI_ID)}&pn={quote(UPI_PAYEE_NAME)}"
                    f"&am={totals[3]:.2f}&tn={quote('Order ')}")
    return render_template("checkout.html", items=items, totals=totals,
                           coupon=coupon, upi_id=UPI_ID, upi_link=upi_link,
                           store=STORE_NAME)


@app.route("/order/<order_id>")
def order_success(order_id):
    o = q("SELECT * FROM orders WHERE order_id=?", (order_id,), one=True)
    if not o:
        abort(404)
    items = q("""SELECT oi.*, p.title, p.slug FROM order_items oi
                 JOIN products p ON p.product_id = oi.product_id
                 WHERE oi.order_id=?""", (order_id,))
    keys = q("""SELECT lk.*, p.title FROM license_keys lk
                JOIN products p ON p.product_id = lk.product_id
                WHERE lk.order_item_id IN (SELECT order_item_id FROM order_items WHERE order_id=?)""",
             (order_id,))
    links = []
    if o["status"] == "paid":
        for it in items:
            links.append({"item": it, "token": sign_token(it["order_item_id"])})
    ylink = youpi_upi_link(o) if o["payment_gateway"] in ("upi", "youpi") else None
    return render_template("order.html", o=o, items=items, keys=keys,
                           links=links, upi_id=UPI_ID, youpi_link=ylink,
                           youpi_qr=youpi_qr_data_uri(ylink))


@app.route("/order/<order_id>/invoice")
def invoice(order_id):
    o = q("SELECT * FROM orders WHERE order_id=?", (order_id,), one=True)
    if not o:
        abort(404)
    items = q("""SELECT oi.*, p.title FROM order_items oi
                 JOIN products p ON p.product_id = oi.product_id
                 WHERE oi.order_id=?""", (order_id,))
    return render_template("invoice.html", o=o, items=items, store=STORE_NAME)


@app.route("/library", methods=["GET", "POST"])
def library():
    email = request.args.get("email") or request.form.get("email", "")
    orders = []
    if email:
        orders = q("SELECT * FROM orders WHERE buyer_email=? ORDER BY created_at DESC",
                   (email.strip().lower(),))
    return render_template("library.html", email=email, orders=orders)


# ---------------- secure download ----------------
@app.route("/download/<token>")
def download(token):
    item_id, err = verify_token(token)
    if err:
        return render_template("download_error.html", err=err), 403
    # EXACT validation logic from the spec:
    # paid AND download_count < max_downloads AND not expired AND latest file
    row = q("""SELECT oi.*, o.status, o.buyer_email, o.gateway_payment_id,
               o.order_id, pf.file_id, pf.file_name, pf.storage_object_key
               FROM order_items oi
               JOIN orders o ON oi.order_id = o.order_id
               JOIN product_files pf ON oi.product_id = pf.product_id
               WHERE oi.order_item_id = ?
                 AND o.status = 'paid'
                 AND oi.download_count < oi.max_downloads
                 AND (oi.access_expires_at IS NULL
                      OR oi.access_expires_at > CURRENT_TIMESTAMP)
                 AND pf.is_latest = 1""", (item_id,), one=True)
    if not row:
        # distinguish blocked reasons for a clear message (no file served)
        base = q("""SELECT oi.*, o.status FROM order_items oi
                    JOIN orders o ON oi.order_id = o.order_id
                    WHERE oi.order_item_id=?""", (item_id,), one=True)
        if not base:
            return render_template("download_error.html", err="order item not found"), 404
        if base["status"] != "paid":
            return render_template("download_error.html",
                                   err=f"order is {base['status']} — files unlock only after payment is confirmed"), 403
        return render_template("download_error.html",
                               err="download quota exhausted, access expired, or no latest file"), 403
    exec_sql("UPDATE order_items SET download_count = download_count + 1 WHERE order_item_id=?",
             (item_id,))
    exec_sql("""INSERT INTO download_logs VALUES (?,?,?,?,?,?,?)""",
             (str(uuid.uuid4()), item_id, row["file_id"],
              request.remote_addr or "", request.headers.get("User-Agent", ""),
              "success", datetime.now(timezone.utc).isoformat()))
    path = os.path.join(PRIVATE, row["storage_object_key"])
    if not os.path.exists(path):
        abort(404)
    stamped = stamped_download(path, row["file_name"], row["buyer_email"],
                               row["gateway_payment_id"] or row["order_id"])
    return send_file(stamped, as_attachment=True,
                     download_name=row["file_name"],
                     mimetype="application/octet-stream")


# ---------------- YouPI webhook (exact contract from YouPI-PG README) ----
def youpi_upi_link(order):
    if not UPI_ID:
        return None
    return (f"upi://pay?pa={quote(UPI_ID)}&pn={quote(UPI_PAYEE_NAME)}"
            f"&am={order['total_amount']:.2f}&tn={quote(order['order_id'])}")


def youpi_qr_data_uri(upi_link):
    """Local QR only, if qrcode is installed. Never calls an external service."""
    if not upi_link:
        return None
    try:
        import qrcode
        img = qrcode.make(upi_link)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


@app.route("/webhook/youpi", methods=["POST"])
def youpi_webhook():
    """YouPI-compatible webhook. Contract (YouPI-PG README, Step 4):
    Header X-Gateway-Signature: sha256=HMAC-SHA256(secret, rawBody)
    Header X-Gateway-Signature-V2: sha256=HMAC-SHA256(secret, "<ts>.<rawBody>")
    Headers X-Gateway-Event=SUCCESS, X-Gateway-Delivery-Id, X-Gateway-Timestamp.
    Payload: event, orderId, amount, amountPaise, utr, paymentId, deliveryId,
    timestamp, verificationTag, verificationLevel.
    Rules enforced here: signature must verify (401 if not, and if no secret
    is configured at all, auto-unlock is disabled); event must be SUCCESS;
    amountPaise must match the order total (409 on mismatch, per YouPI);
    deliveryId is deduplicated (retries resent byte-for-byte).
    This endpoint alone is NOT proof of settlement: reconcile against
    bank records, and YouPI is experimental / not production-ready."""
    raw = request.get_data()
    secret = YOUPI_WEBHOOK_SECRET or os.environ.get("YOUPI_WEBHOOK_SECRET", "")
    if not secret:
        return jsonify({"ok": False,
                        "error": "YouPI webhook secret not configured — "
                                 "use admin manual confirmation instead"}), 401
    sig = request.headers.get("X-Gateway-Signature", "")
    expect = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    sig2 = request.headers.get("X-Gateway-Signature-V2", "")
    ts = request.headers.get("X-Gateway-Timestamp", "")
    expect2 = "sha256=" + hmac.new(
        secret.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
    if not (hmac.compare_digest(sig, expect) or
            (sig2 and hmac.compare_digest(sig2, expect2))):
        return jsonify({"ok": False, "error": "Invalid webhook signature"}), 401
    try:
        data = json.loads(raw.decode())
    except Exception:
        return jsonify({"ok": False, "error": "invalid JSON"}), 400
    if data.get("event") != "SUCCESS":
        return jsonify({"ok": False, "error": "event is not SUCCESS"}), 400
    oid = data.get("orderId")
    o = q("SELECT * FROM orders WHERE order_id=?", (oid,), one=True) if oid else None
    if not o:
        return jsonify({"ok": False, "error": "order not found"}), 404
    if data.get("amountPaise") is not None and int(data["amountPaise"]) != int(round(o["total_amount"] * 100)):
        return jsonify({"ok": False, "error": "ORDER_AMOUNT_MISMATCH"}), 409
    delivery_id = data.get("deliveryId") or request.headers.get("X-Gateway-Delivery-Id")
    if delivery_id:
        seen = q("SELECT * FROM youpi_webhook_deliveries WHERE delivery_id=?",
                 (delivery_id,), one=True)
        if seen:
            return jsonify({"ok": True, "duplicate": True, "order_id": oid,
                            "status": o["status"]})
        exec_sql("INSERT INTO youpi_webhook_deliveries VALUES (?,?,?)",
                 (delivery_id, oid, datetime.now(timezone.utc).isoformat()))
    exec_sql("""UPDATE orders SET status='paid', paid_at=?,
                gateway_payment_id=? WHERE order_id=?""",
             (datetime.now(timezone.utc).isoformat(),
              data.get("utr") or data.get("paymentId"), oid))
    return jsonify({"ok": True, "order_id": oid, "status": "paid",
                    "utr": data.get("utr"),
                    "note": "Webhook signature verified. Reconcile against bank records; "
                            "YouPI alone is not proof of settlement."})


# ---------------- webhook simulation + license API ----------------
@app.route("/webhook/<gateway>", methods=["POST"])
def webhook(gateway):
    if gateway == "youpi":
        # Never auto-unlock via the generic demo webhook; use /webhook/youpi.
        return jsonify({"ok": False,
                        "error": "Use /webhook/youpi with a signed YouPI payload"}), 401
    """Simulate payment_intent.succeeded: POST {"order_id": "..."}.
    Marks a pending order paid and unlocks files. Demo gateways use this
    internally; UPI has no auto-webhook, so admin confirms UPI manually."""
    data = request.get_json(silent=True) or {}
    oid = data.get("order_id") or request.form.get("order_id")
    o = q("SELECT * FROM orders WHERE order_id=?", (oid,), one=True) if oid else None
    if not o:
        return jsonify({"ok": False, "error": "order not found"}), 404
    exec_sql("UPDATE orders SET status='paid', paid_at=? WHERE order_id=?",
             (datetime.now(timezone.utc).isoformat(), oid))
    return jsonify({"ok": True, "order_id": oid, "status": "paid",
                    "message": "payment_intent.succeeded simulated — files unlocked"})


@app.route("/api/verify-license", methods=["POST"])
def verify_license():
    data = request.get_json(silent=True) or {}
    key = data.get("license_key", "").strip()
    row = q("""SELECT lk.*, p.title FROM license_keys lk
               JOIN products p ON p.product_id = lk.product_id
               WHERE lk.license_key=?""", (key,), one=True)
    if not row:
        return jsonify({"valid": False, "reason": "unknown key"}), 404
    if row["status"] != "active":
        return jsonify({"valid": False, "reason": f"key is {row['status']}"}), 403
    return jsonify({"valid": True, "product": row["title"],
                    "activations_used": row["activation_count"],
                    "max_activations": row["max_activations"]})


@app.route("/uploads/<filename>")
def serve_upload(filename):
    # Only plain filenames, no paths, and only picture extensions.
    if "/" in filename or "\\" in filename or ".." in filename:
        abort(404)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_IMAGE_EXTS:
        abort(404)
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.isfile(path):
        abort(404)
    return send_file(path)


# ---------------- admin ----------------
def admin_required():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    return None


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        u = q("SELECT * FROM users WHERE email=? AND role='admin'",
              (request.form.get("email", "").strip().lower(),), one=True)
        if u and check_password_hash(u["password_hash"], request.form.get("password", "")):
            session["is_admin"] = True
            session["user_id"] = u["user_id"]
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin login.")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("index"))


@app.route("/admin")
def admin_dashboard():
    r = admin_required()
    if r:
        return r
    return render_template("admin.html",
                           orders=q("SELECT * FROM orders ORDER BY created_at DESC LIMIT 50"),
                           products=q("SELECT * FROM products ORDER BY title"),
                           coupons=q("SELECT * FROM coupons"),
                           affiliates=q("SELECT * FROM affiliates"),
                           notes=q("SELECT * FROM notifications ORDER BY created_at DESC LIMIT 50"))


@app.route("/admin/product", methods=["POST"])
def admin_product():
    r = admin_required()
    if r:
        return r
    pid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    # 18 columns: image_url added (was 17 after the license_type fix).
    img_url = (request.form.get("image_url") or "").strip()
    up = request.files.get("image_file")
    if up and up.filename:
        saved, err = save_picture_upload(up)
        if err:
            flash(err)
            return redirect(url_for("admin_dashboard"))
        img_url = saved
    exec_sql("""INSERT INTO products (product_id, slug, title, category, description,
                price, currency, license_type, file_format, file_size, software,
                specs, preview_text, image_url, requires_license_key, is_published,
                created_at, updated_at, seller_name, badge, item_count)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
             (pid, request.form["slug"], request.form["title"],
              request.form.get("category", "misc"), request.form.get("description", ""),
              float(request.form.get("price", 0)), "INR", "standard",
              request.form.get("file_format", "zip"),
              request.form.get("file_size", "—"),
              request.form.get("software", "—"),
              request.form.get("specs", ""), request.form.get("description", ""),
              img_url or None,
              1 if request.form.get("requires_license_key") else 0, 1, now, now,
              request.form.get("seller_name", "Shirish Digital Store") or "Shirish Digital Store",
              request.form.get("badge", "") or "",
              request.form.get("item_count", "") or ""))
    flash("Product added.")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/product/<product_id>/edit", methods=["POST"])
def admin_product_edit(product_id):
    r = admin_required()
    if r:
        return r
    p = q("SELECT * FROM products WHERE product_id=?", (product_id,), one=True)
    if not p:
        flash("Product not found.")
        return redirect(url_for("admin_dashboard"))
    try:
        price = float(request.form.get("price", p["price"]))
    except (TypeError, ValueError):
        price = p["price"]
    exec_sql("""UPDATE products SET title=?, category=?, description=?, price=?,
                file_format=?, file_size=?, software=?, specs=?, is_published=?,
                seller_name=?, badge=?, item_count=?
                WHERE product_id=?""",
             (request.form.get("title", p["title"]),
              request.form.get("category", p["category"]),
              request.form.get("description", p["description"]),
              price,
              request.form.get("file_format", p["file_format"]),
              request.form.get("file_size", p["file_size"]),
              request.form.get("software", p["software"]),
              request.form.get("specs", p["specs"]),
              1 if request.form.get("is_published") else 0,
              request.form.get("seller_name", p["seller_name"]),
              request.form.get("badge", p["badge"] or ""),
              request.form.get("item_count", p["item_count"] or ""),
              product_id))
    flash("Product updated.")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/product/<product_id>/delete", methods=["POST"])
def admin_product_delete(product_id):
    r = admin_required()
    if r:
        return r
    # Delete the product and its file versions, but leave orders/order_items
    # history untouched so past orders and invoices do not break.
    exec_sql("DELETE FROM product_files WHERE product_id=?", (product_id,))
    exec_sql("DELETE FROM products WHERE product_id=?", (product_id,))
    flash("Product deleted.")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/product/<product_id>/image", methods=["POST"])
def admin_product_image(product_id):
    r = admin_required()
    if r:
        return r
    p = q("SELECT * FROM products WHERE product_id=?", (product_id,), one=True)
    if not p:
        flash("Product not found.")
        return redirect(url_for("admin_dashboard"))
    up = request.files.get("image_file")
    if up and up.filename:
        saved, err = save_picture_upload(up)
        if err:
            flash(err)
            return redirect(url_for("admin_dashboard"))
        exec_sql("UPDATE products SET image_url=? WHERE product_id=?", (saved, product_id))
        flash("Product picture uploaded.")
    else:
        url = (request.form.get("image_url") or "").strip()
        if not url:
            flash("Paste an image URL or choose a picture file.")
            return redirect(url_for("admin_dashboard"))
        if not (url.startswith("http://") or url.startswith("https://") or url.startswith("/uploads/")):
            flash("Image URL must start with http:// or https://.")
            return redirect(url_for("admin_dashboard"))
        exec_sql("UPDATE products SET image_url=? WHERE product_id=?", (url, product_id))
        flash("Product picture saved.")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/upload-version", methods=["POST"])
def admin_upload_version():
    r = admin_required()
    if r:
        return r
    f = request.files.get("file")
    pid = request.form["product_id"]
    if not f or not f.filename:
        flash("Choose a file.")
        return redirect(url_for("admin_dashboard"))
    fname = f.filename
    f.save(os.path.join(PRIVATE, fname))
    exec_sql("UPDATE product_files SET is_latest=0 WHERE product_id=?", (pid,))
    exec_sql("""INSERT INTO product_files VALUES (?,?,?,?,?,?,?,?)""",
             (str(uuid.uuid4()), pid, request.form.get("version_label", "1.0.1"),
              fname, fname, os.path.getsize(os.path.join(PRIVATE, fname)), 1,
              datetime.now(timezone.utc).isoformat()))
    exec_sql("""INSERT INTO notifications VALUES (?,?,?,?,?)""",
             (str(uuid.uuid4()), pid,
              f"New version {request.form.get('version_label', '1.0.1')} available",
              datetime.now(timezone.utc).isoformat(),
              "All past buyers of this product were notified (logged; email only if configured)."))
    flash("New version uploaded; past buyers notified (log).")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/coupon", methods=["POST"])
def admin_coupon():
    r = admin_required()
    if r:
        return r
    exec_sql("INSERT INTO coupons VALUES (?,?,?,?,?,?,?)",
             (request.form["code"].upper(),
              float(request.form["discount_pct"]) if request.form.get("discount_pct") else None,
              float(request.form["discount_amount"]) if request.form.get("discount_amount") else None,
              int(request.form.get("usage_limit") or 0), 0,
              request.form.get("expires_at") or "2099-01-01", 1))
    flash("Coupon added.")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/order/<order_id>/confirm", methods=["POST"])
def admin_confirm(order_id):
    r = admin_required()
    if r:
        return r
    exec_sql("UPDATE orders SET status='paid', paid_at=? WHERE order_id=?",
             (datetime.now(timezone.utc).isoformat(), order_id))
    flash("Payment confirmed — files unlocked.")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/order/<order_id>/refund", methods=["POST"])
def admin_refund(order_id):
    r = admin_required()
    if r:
        return r
    exec_sql("UPDATE orders SET status='refunded' WHERE order_id=?", (order_id,))
    exec_sql("""UPDATE license_keys SET status='revoked' WHERE order_item_id IN
                (SELECT order_item_id FROM order_items WHERE order_id=?)""", (order_id,))
    flash("Order refunded — downloads and license keys revoked.")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete-all", methods=["POST"])
def admin_delete_all():
    """Delete ALL products, orders and coupons (admin only, irreversible).

    Child rows are deleted first so no orphaned rows remain. Users
    (including the admin account), affiliates themselves, and
    notifications are deliberately left untouched.
    """
    r = admin_required()
    if r:
        return r
    # Order-tied rows first.
    exec_sql("DELETE FROM download_logs")
    exec_sql("DELETE FROM license_keys")
    exec_sql("DELETE FROM affiliate_commissions")
    exec_sql("DELETE FROM youpi_webhook_deliveries")
    exec_sql("DELETE FROM order_items")
    exec_sql("DELETE FROM orders")
    # Bundles are made of products, so they must go with the products.
    exec_sql("DELETE FROM bundle_items")
    exec_sql("DELETE FROM bundles")
    exec_sql("DELETE FROM product_files")
    exec_sql("DELETE FROM products")
    exec_sql("DELETE FROM coupons")
    flash("Deleted all products, orders and coupons.")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/restore-catalogue", methods=["POST"])
def admin_restore_catalogue():
    """Re-add any missing demo catalogue products (admin only).

    Only inserts products whose slug is missing, plus missing coupons /
    bundles — never touches existing products, orders or the admin
    account. This is the way back after a Delete All, or after a deploy
    that left the live catalogue empty.
    """
    r = admin_required()
    if r:
        return r
    make_sample_files()
    added = 0
    for (slug, title, cat, desc, price, cur, fmt, size, soft, fmt2, spec,
         fname, needs_key, img_url, seller, badge, item_count) in _seed_products():
        if q("SELECT product_id FROM products WHERE slug=?", (slug,), one=True):
            continue
        pid = str(uuid.uuid4())
        exec_sql("""INSERT INTO products (product_id, slug, title, category,
            description, price, currency, file_format, file_size, software,
            specs, preview_text, image_url, requires_license_key, is_published,
            seller_name, badge, item_count)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?)""",
                 (pid, slug, title, cat, desc, price, cur, fmt, size, soft,
                  spec, desc, img_url, 1 if needs_key else 0,
                  seller, badge, item_count))
        fpath = os.path.join(PRIVATE, fname)
        if os.path.isfile(fpath):
            exec_sql("""INSERT INTO product_files (file_id, product_id, version_label,
                file_name, storage_object_key, file_size_bytes, is_latest)
                VALUES (?,?,?,?,?,?,1)""",
                     (str(uuid.uuid4()), pid, "1.0.0", fname, fname,
                      os.path.getsize(fpath)))
        added += 1
    # Missing coupons / affiliate / bundle, without duplicating existing rows.
    for code, pct, amt, limit in (("WELCOME10", 10, None, 100),
                                  ("FLAT100", None, 100, 50),
                                  ("FLASH25", 25, None, 20)):
        if not q("SELECT code FROM coupons WHERE code=?", (code,), one=True):
            exec_sql("INSERT INTO coupons VALUES (?,?,?,?,?,?,?)",
                     (code, pct, amt, limit, 0, "2099-01-01", 1))
    if not q("SELECT affiliate_id FROM affiliates WHERE code=?", ("creator1",), one=True):
        exec_sql("INSERT INTO affiliates VALUES (?,?,?,?)", ("AFF1", "creator1", 0.10, 1))
    if not q("SELECT bundle_id FROM bundles WHERE bundle_id=?", ("B1",), one=True):
        exec_sql("INSERT INTO bundles VALUES (?,?,?,?)",
                 ("B1", "Creator Bundle", "UI Kit + Creator OS + Lo-Fi Pack", 99))
        for slug in ("modern-ui-kit", "creator-os-notion", "lofi-sample-pack"):
            row = q("SELECT product_id FROM products WHERE slug=?", (slug,), one=True)
            if row:
                exec_sql("INSERT INTO bundle_items VALUES (?,?,?)",
                         (str(uuid.uuid4()), "B1", row["product_id"]))
    flash(f"Demo catalogue restored ({added} products added).")
    return redirect(url_for("admin_dashboard"))


@app.route("/ref/<code>")
def affiliate_ref(code):
    session["ref"] = code
    return redirect(url_for("index"))


with app.app_context():
    init_db()


@app.before_request
def ensure_catalogue():
    # Vercel serverless instances can lose the import-time seed (each
    # instance gets its own /tmp DB), leaving the live store empty. Only
    # seed a truly fresh DB (no products AND no users): if an admin user
    # exists, an empty catalogue means Delete All was used, and it must
    # stay empty until the admin clicks Restore. Swallow errors so a
    # seeding hiccup never turns a page load into a 500.
    try:
        row = q("SELECT COUNT(*) c FROM products", one=True)
        if row and row["c"]:
            return
        urow = q("SELECT COUNT(*) c FROM users", one=True)
        if urow and urow["c"]:
            return
        init_db()
    except Exception:
        try:
            db().rollback()
        except Exception:
            pass


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
