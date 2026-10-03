-- Runs once, on the first start of an empty data volume.
-- To re-run after editing: docker compose down -v && docker compose up -d

CREATE TABLE IF NOT EXISTS markets (
    id    SERIAL PRIMARY KEY,
    name  TEXT UNIQUE NOT NULL
);

INSERT INTO markets (name) VALUES
    ('a101'), ('carrefour'), ('getir'), ('migros'), ('sok')
ON CONFLICT (name) DO NOTHING;

-- One row per product per market: details that rarely change
CREATE TABLE IF NOT EXISTS products (
    id           SERIAL PRIMARY KEY,
    market_id    INT  NOT NULL REFERENCES markets(id),
    external_id  TEXT NOT NULL,          -- the market's own product id
    name         TEXT NOT NULL,
    brand        TEXT,
    barcode      TEXT,                   -- EAN, for cross-market matching
    category     TEXT,                   -- the market's own category name
    quantity     NUMERIC(10,3),          -- e.g. 500
    unit         TEXT,                   -- 'g', 'kg', 'ml', 'l', 'adet'
    url          TEXT,
    image_url    TEXT,
    UNIQUE (market_id, external_id)
);

CREATE INDEX IF NOT EXISTS idx_products_barcode ON products (barcode);

-- One row per product per store per day: the price history
CREATE TABLE IF NOT EXISTS prices (
    id             BIGSERIAL PRIMARY KEY,
    product_id     INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    price          NUMERIC(10,2) NOT NULL,   -- what the customer pays
    regular_price  NUMERIC(10,2),            -- price before discount
    discount_rate  SMALLINT,                 -- e.g. 33 for %33
    in_stock       BOOLEAN NOT NULL DEFAULT TRUE,
    store_code     TEXT NOT NULL DEFAULT '', -- '' when the market has one price
    scraped_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- At most one price per product per store per (Istanbul) day, so a rerun
-- on the same day updates the row instead of adding a duplicate
CREATE UNIQUE INDEX IF NOT EXISTS uq_prices_daily ON prices (
    product_id, store_code, ((scraped_at AT TIME ZONE 'Europe/Istanbul')::date)
);

CREATE INDEX IF NOT EXISTS idx_prices_scraped_at ON prices (scraped_at);
