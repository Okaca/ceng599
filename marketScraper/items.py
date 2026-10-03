# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class MarketItems(scrapy.Item):
    # required
    marketName = scrapy.Field()  # must match a row in the markets table, e.g. "a101"
    externalId = scrapy.Field()  # the market's own product id
    name = scrapy.Field()
    price = scrapy.Field()  # what the customer pays, number or "12,50" / "₺12,50"

    # product details
    brand = scrapy.Field()
    barcode = scrapy.Field()
    category = scrapy.Field()
    quantity = scrapy.Field()  # package size, e.g. 500
    unit = scrapy.Field()  # "g", "kg", "ml", "l", "adet"
    itemURL = scrapy.Field()
    imageUrl = scrapy.Field()

    # price details
    regularPrice = scrapy.Field()  # price before discount
    discountRate = scrapy.Field()  # e.g. 33 for %33
    inStock = scrapy.Field()  # defaults to True
    storeCode = scrapy.Field()  # defaults to "" when the market has one price
