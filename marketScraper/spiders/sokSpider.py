import json
import time
import requests
import scrapy
from datetime import datetime
from marketScraper.items import MarketItems


class SokSpider(scrapy.Spider):
    name = "sokSpider"
    main_url = "https://www.sokmarket.com.tr"
    start_urls = [
        "https://www.sokmarket.com.tr/api/v1/search?cat=20&sort=SCORE_DESC&page=0&size=100",
    ]

    sok_meyve_titles = [
        "Hurmalar",
        "Kabuklu Sert Meyveler",
        "Kurutulmuş  Meyve ve Sebze",
        "Meyveler",
        "Narenciye",
    ]
    sok_sebze_titles = ["Sebzeler", "Patates, Soğan, Sarımsak"]

    def start_requests(self):

        headers = headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "tr-TR",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "X-Service-Type": "MARKET",  # REQUIRED
            "X-Store-Id": "13412",  # REQUIRED
        }

        # load cookies:
        with requests.session() as s:
            isOkResponse = s.get(self.main_url, headers=headers)
        # scrapy.Request(url=self.main_url, headers=headers)
        if isOkResponse.status_code == 200:
            for url in self.start_urls:
                s.get(url, headers=headers)
                yield scrapy.Request(url, headers=headers, callback=self.parse)

    def parse(self, response):
        if response.status == 200:
            jsonResponse = json.loads(response.body)

            results = jsonResponse["results"]

            for result in results:
                title = result["sku"]["breadCrumbs"][-1]["label"]
                if title in self.sok_meyve_titles:
                    title = "Meyve"
                elif title in self.sok_sebze_titles:
                    title = "Sebze"
                else:
                    title = "Yeşillik"
                name = result["product"]["name"]
                itemURL = result["product"]["variant"]["path"]
                try:
                    imageURL = (
                        result["product"]["images"][0]["host"]
                        + "/"
                        + result["product"]["images"][0]["path"]
                    )
                except KeyError:
                    imageURL = ""
                price = result["prices"]["discounted"]["text"]

                results = MarketItems(
                    title=title,
                    scrapedDate=datetime.today().strftime("%Y-%m-%d"),
                    imageUrl=imageURL,
                    itemURL="https://www.sokmarket.com.tr/" + itemURL,
                    name=name,
                    price=price,
                    marketName="sok",
                )

                yield results
            else:
                yield scrapy.Request(
                    response.url, callback=self.parse, dont_filter=True
                )
