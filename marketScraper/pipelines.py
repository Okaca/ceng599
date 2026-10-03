# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


import re
from decimal import Decimal, InvalidOperation

import psycopg
from scrapy.exceptions import DropItem


def to_decimal(value):
    """Turn 12.5, "12.50", "12,50", "₺1.234,50" or "1,234.50" into a Decimal."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    text = re.sub(r"[^\d,.]", "", str(value))
    if "," in text and "." in text:
        # whichever separator comes last is the decimal one
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    else:
        text = text.replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


class PostgresPipeline:

    REQUIRED_FIELDS = ("marketName", "externalId", "name", "price")

    UPSERT_PRODUCT = """
        INSERT INTO products
            (market_id, external_id, name, brand, barcode, category,
             quantity, unit, url, image_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (market_id, external_id) DO UPDATE SET
            name = EXCLUDED.name,
            brand = COALESCE(EXCLUDED.brand, products.brand),
            barcode = COALESCE(EXCLUDED.barcode, products.barcode),
            category = COALESCE(EXCLUDED.category, products.category),
            quantity = COALESCE(EXCLUDED.quantity, products.quantity),
            unit = COALESCE(EXCLUDED.unit, products.unit),
            url = COALESCE(EXCLUDED.url, products.url),
            image_url = COALESCE(EXCLUDED.image_url, products.image_url)
        RETURNING id
    """

    UPSERT_PRICE = """
        INSERT INTO prices
            (product_id, price, regular_price, discount_rate, in_stock, store_code)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (product_id, store_code, ((scraped_at AT TIME ZONE 'Europe/Istanbul')::date))
        DO UPDATE SET
            price = EXCLUDED.price,
            regular_price = EXCLUDED.regular_price,
            discount_rate = EXCLUDED.discount_rate,
            in_stock = EXCLUDED.in_stock,
            scraped_at = EXCLUDED.scraped_at
    """

    def __init__(self, host, port, dbname, user, password):
        self.conninfo = psycopg.conninfo.make_conninfo(
            host=host, port=port, dbname=dbname, user=user, password=password
        )

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            host=crawler.settings.get("POSTGRES_HOST"),
            port=crawler.settings.get("POSTGRES_PORT"),
            dbname=crawler.settings.get("POSTGRES_DB"),
            user=crawler.settings.get("POSTGRES_USER"),
            password=crawler.settings.get("POSTGRES_PASSWORD"),
        )

    def open_spider(self, spider):
        # autocommit, so each item's "with transaction()" block commits on its own
        self.conn = psycopg.connect(self.conninfo, autocommit=True)
        self.market_ids = dict(self.conn.execute("SELECT name, id FROM markets").fetchall())

    def close_spider(self, spider):
        self.conn.close()

    def process_item(self, item, spider):
        missing = [f for f in self.REQUIRED_FIELDS if item.get(f) in (None, "")]
        if missing:
            raise DropItem(f"Missing {', '.join(missing)}: {dict(item)}")

        market_id = self.market_ids.get(item["marketName"])
        if market_id is None:
            raise DropItem(f"Unknown market {item['marketName']!r}, add it to the markets table")

        price = to_decimal(item["price"])
        if price is None:
            raise DropItem(f"Unreadable price {item['price']!r}: {dict(item)}")

        try:
            with self.conn.transaction():
                product_id = self.conn.execute(
                    self.UPSERT_PRODUCT,
                    (
                        market_id,
                        str(item["externalId"]),
                        item["name"],
                        item.get("brand"),
                        item.get("barcode"),
                        item.get("category"),
                        to_decimal(item.get("quantity")),
                        item.get("unit"),
                        item.get("itemURL"),
                        item.get("imageUrl"),
                    ),
                ).fetchone()[0]
                self.conn.execute(
                    self.UPSERT_PRICE,
                    (
                        product_id,
                        price,
                        to_decimal(item.get("regularPrice")),
                        item.get("discountRate"),
                        item.get("inStock", True),
                        item.get("storeCode") or "",
                    ),
                )
        except psycopg.Error as e:
            raise DropItem(f"Database error {e}: {dict(item)}")
        return item


class MarketscraperPipeline:

    def __init__(self, mongo_uri, mongo_db, mongo_user, mongo_password):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.mongo_user = mongo_user
        self.mongo_password = mongo_password

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get("MONGO_URI"),
            mongo_db=crawler.settings.get("MONGO_DATABASE"),
            mongo_user=crawler.settings.get("MONGODB_USERNAME"),
            mongo_password=crawler.settings.get("MONGODB_PASSWORD"),
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(
            self.mongo_uri, username=self.mongo_user, password=self.mongo_password
        )
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        self.db[item["marketName"]].insert_one(dict(item))
        return item
