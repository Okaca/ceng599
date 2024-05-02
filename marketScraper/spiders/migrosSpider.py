import scrapy
import xmltodict
from datetime import datetime
from marketScraper.items import MarketItems


class MigrosspiderSpider(scrapy.Spider):
    name = "migrosSpider"
    start_urls = [
        "https://www.migros.com.tr/rest/search/screens/sebze-c-66?sayfa=1",
        "https://www.migros.com.tr/rest/search/screens/sebze-c-66?sayfa=2",
        "https://www.migros.com.tr/rest/search/screens/sebze-c-66?sayfa=3",
        "https://www.migros.com.tr/rest/search/screens/meyve-c-65?sayfa=1",
        "https://www.migros.com.tr/rest/search/screens/meyve-c-65?sayfa=2",
        "https://www.migros.com.tr/rest/search/screens/meyve-c-65?sayfa=3",
    ]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        sourceData = xmltodict.parse(response.body)

        searchInfo = sourceData.get("AppResponse", {})["data"]["searchInfo"]
        storeProductInfos = searchInfo["storeProductInfos"]["storeProductInfos"]

        for item in storeProductInfos:

            name = item["name"]
            title = item["categoryAscendants"]["categoryAscendants"][0]["name"]
            imageSource = item["images"]["images"]
            itemURL = item["prettyName"]
            if type(imageSource) == list:
                imageUrl = item["images"]["images"][0]["urls"]["PRODUCT_DETAIL"]
            elif type(imageSource) == dict:
                imageUrl = item["images"]["images"]["urls"]["PRODUCT_DETAIL"]

            price = int(item["shownPrice"]) / 100
            formatted_price = "{:.2f}".format(float(price))

            results = MarketItems(
                title=title,
                scrapedDate=datetime.today().strftime("%Y-%m-%d"),
                imageUrl=imageUrl,
                itemURL="https://www.migros.com.tr/" + itemURL,
                name=name,
                price=formatted_price,
                marketName="migros",
            )

            yield results
