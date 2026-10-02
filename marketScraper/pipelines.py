# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
import psycopg


class PostgresPipeline:

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
        self.conn = psycopg.connect(self.conninfo)

    def close_spider(self, spider):
        self.conn.close()

    def process_item(self, item, spider):
        self.conn.execute(
            """
            INSERT INTO products
                (market_name, name, title, price, image_url, item_url, scraped_date)
            VALUES (%s, %s, %s, %s, %s, %s, COALESCE(%s::timestamp, NOW()))
            """,
            (
                item.get("marketName"),
                item.get("name"),
                item.get("title"),
                item.get("price"),
                item.get("imageUrl"),
                item.get("itemURL"),
                item.get("scrapedDate"),
            ),
        )
        self.conn.commit()
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
