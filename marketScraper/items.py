# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class MarketItems(scrapy.Item):
    title = scrapy.Field()
    scrapedDate = scrapy.Field()
    imageUrl = scrapy.Field()
    itemURL = scrapy.Field()
    name = scrapy.Field()
    price = scrapy.Field()
    marketName = scrapy.Field()
