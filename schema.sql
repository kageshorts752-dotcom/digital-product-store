-- Digital Product Store schema — PostgreSQL-style spec adapted to SQLite.
-- UUIDs are TEXT, DECIMAL is REAL, TIMESTAMPTZ is TEXT (ISO-8601 UTC).
-- Never expose product_files.storage_object_key publicly; downloads go
-- through /download/<signed-token> only, after the validation query.
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE,
    password_hash TEXT, full_name TEXT, role TEXT NOT NULL DEFAULT 'customer',
    created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY, slug TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
    category TEXT, description TEXT, price REAL NOT NULL CHECK (price >= 0),
    currency TEXT NOT NULL DEFAULT 'INR',
    license_type TEXT NOT NULL DEFAULT 'standard',
    file_format TEXT, file_size TEXT, software TEXT, specs TEXT,
    preview_text TEXT, image_url TEXT,
    seller_name TEXT NOT NULL DEFAULT 'Shirish Digital Store',
    badge TEXT NOT NULL DEFAULT '', item_count TEXT NOT NULL DEFAULT '',
    requires_license_key INTEGER NOT NULL DEFAULT 0,
    is_published INTEGER NOT NULL DEFAULT 0,
    created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS product_files (
    file_id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    version_label TEXT NOT NULL DEFAULT '1.0.0', file_name TEXT NOT NULL,
    storage_object_key TEXT NOT NULL, file_size_bytes INTEGER NOT NULL,
    checksum_sha256 TEXT, is_latest INTEGER NOT NULL DEFAULT 1, uploaded_at TEXT);
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(user_id) ON DELETE SET NULL,
    buyer_email TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
    subtotal_amount REAL NOT NULL, tax_amount REAL NOT NULL DEFAULT 0,
    discount_amount REAL NOT NULL DEFAULT 0, total_amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR', payment_gateway TEXT NOT NULL,
    gateway_order_id TEXT UNIQUE, gateway_payment_id TEXT UNIQUE,
    buyer_ip TEXT, created_at TEXT, paid_at TEXT);
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id TEXT PRIMARY KEY, order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id TEXT NOT NULL REFERENCES products(product_id),
    unit_price REAL NOT NULL, download_count INTEGER NOT NULL DEFAULT 0,
    max_downloads INTEGER NOT NULL DEFAULT 5, access_expires_at TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS license_keys (
    license_id TEXT PRIMARY KEY, order_item_id TEXT NOT NULL REFERENCES order_items(order_item_id) ON DELETE CASCADE,
    product_id TEXT NOT NULL REFERENCES products(product_id), license_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active', activation_count INTEGER NOT NULL DEFAULT 0,
    max_activations INTEGER NOT NULL DEFAULT 3, expires_at TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS download_logs (
    log_id TEXT PRIMARY KEY, order_item_id TEXT NOT NULL REFERENCES order_items(order_item_id) ON DELETE CASCADE,
    file_id TEXT NOT NULL REFERENCES product_files(file_id) ON DELETE CASCADE,
    ip_address TEXT NOT NULL, user_agent TEXT, status TEXT NOT NULL DEFAULT 'success',
    downloaded_at TEXT);
CREATE TABLE IF NOT EXISTS coupons (
    code TEXT PRIMARY KEY, discount_pct REAL, discount_amount REAL,
    usage_limit INTEGER, used_count INTEGER NOT NULL DEFAULT 0,
    expires_at TEXT, active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS affiliates (
    affiliate_id TEXT PRIMARY KEY, code TEXT NOT NULL UNIQUE,
    commission_rate REAL NOT NULL DEFAULT 0.10, active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS affiliate_commissions (
    commission_id TEXT PRIMARY KEY, affiliate_id TEXT NOT NULL,
    order_id TEXT NOT NULL, amount REAL NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT);
CREATE TABLE IF NOT EXISTS bundles (
    bundle_id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT,
    bundle_price REAL NOT NULL);
CREATE TABLE IF NOT EXISTS bundle_items (
    item_id TEXT PRIMARY KEY, bundle_id TEXT NOT NULL, product_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS youpi_webhook_deliveries (
    delivery_id TEXT PRIMARY KEY, order_id TEXT NOT NULL, received_at TEXT);
CREATE TABLE IF NOT EXISTS notifications (
    notification_id TEXT PRIMARY KEY, product_id TEXT, title TEXT,
    created_at TEXT, note TEXT);
CREATE INDEX IF NOT EXISTS idx_orders_buyer_email ON orders(buyer_email);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_product_files_latest ON product_files(product_id, is_latest);
CREATE INDEX IF NOT EXISTS idx_license_keys_lookup ON license_keys(license_key);
CREATE INDEX IF NOT EXISTS idx_download_logs_order_item ON download_logs(order_item_id);
