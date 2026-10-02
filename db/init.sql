CREATE TABLE IF NOT EXISTS products (
      id           SERIAL PRIMARY KEY,
      market_name  TEXT NOT NULL,
      name         TEXT,
      title        TEXT,
      price        TEXT,
      image_url    TEXT,
      item_url     TEXT,
      scraped_date TIMESTAMP DEFAULT NOW()
  );