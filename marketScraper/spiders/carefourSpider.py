from datetime import datetime
import scrapy
from marketScraper.items import MarketItems


class CarefourSpider(scrapy.Spider):
    name = "carefourSpider"
    start_urls = [
        "https://www.carrefoursa.com/meyve/c/1015?q=%3AbestSeller&show=All",
        "https://www.carrefoursa.com/sebze/c/1025?q=%3AbestSeller&show=All",
    ]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        gridContent = response.xpath("//div[@class='pl-grid-cont']/ul")

        # Extract all <li> elements with the class "product-listing-item"
        product_items = gridContent.xpath("./li[@class='product-listing-item']")

        cataloguePath = gridContent.xpath("./input[1]/@value").get()
        splitCatalogue = cataloguePath.split(">")
        title = splitCatalogue[1].strip()

        # Iterate over each <li> element
        for item in product_items:
            itemURLpath = item.xpath("./div/div/div/div[1]/a/@href").get()

            if itemURLpath is not None:
                itemURL = "https://www.carrefoursa.com" + itemURLpath

                name = item.xpath("./div/div/div/div[1]/a/span[2]/text()").get()

                imgURL = item.xpath("./div/div/div/div[1]/a/span[1]/img/@src").get()

                price = item.xpath(
                    "./div/div/div/div[1]/a/span[5]/div/span[contains(@class, 'item-price')]/@content"
                ).get()

                formatted_price = "{:.2f}".format(float(price))

                results = MarketItems(
                    title=title,
                    scrapedDate=datetime.today().strftime("%Y-%m-%d"),
                    imageUrl=imgURL,
                    itemURL=itemURL,
                    name=name,
                    price=formatted_price,
                    marketName="carefour",
                )

                yield results
