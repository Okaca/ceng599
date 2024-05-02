import json
import re
import scrapy
from datetime import datetime
from marketScraper.items import MarketItems


class A101Spider(scrapy.Spider):
    name = "a101Spider"
    allowed_domains = ["www.a101.com.tr"]
    start_urls = [
        "https://www.a101.com.tr/kapida/meyve-sebze/meyve",
    ]

    def parse(self, response):
        stringJSONData = (
            response.css("script#__NEXT_DATA__")
            .get()
            .replace('<script id="__NEXT_DATA__" type="application/json">', "")
            .replace("</script>", "")
        )
        # entire fruits and vegetables can be obtained from the script
        jsonParseData = json.loads(stringJSONData)

        # yield {"object" : jsonParseData.keys()}

        productsByCategory = jsonParseData["props"]["pageProps"][
            "productsByCategoryOutput"
        ]

        children = productsByCategory["children"]
        for child in children:
            products = child["products"]
            # meyve || sebze || yeşillik
            title = child["name"]
            for product in products:
                if len(product["images"]) == 2:
                    imageUrl = product["images"][1]["url"]
                else:
                    imageUrl = product["images"][0]["url"]
                name = product["attributes"]["name"]
                itemURL = product["attributes"]["seoUrl"]
                price = product["price"]["discountedStr"]

                formatted_price = re.findall(r"\d+\,\d{2}", price)

                results = MarketItems(
                    title=title,
                    scrapedDate=datetime.today().strftime("%Y-%m-%d"),
                    imageUrl=imageUrl,
                    itemURL=itemURL,
                    name=name,
                    price=formatted_price[0],
                    marketName="a101",
                )
                yield results
