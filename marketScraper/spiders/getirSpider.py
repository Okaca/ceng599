from datetime import datetime
import json
import scrapy
from marketScraper.items import MarketItems


class GetirSpider(scrapy.Spider):
    name = "getirSpider"
    start_urls = ["https://getir.com/kategori/meyve-sebze-VN2A9ap5Fm/"]

    def parse(self, response):
        stringJSONData = (
            response.css("script#__NEXT_DATA__")
            .get()
            .replace('<script id="__NEXT_DATA__" type="application/json">', "")
            .replace("</script>", "")
        )

        # entire fruits and vegetables can be obtained from the script
        jsonParseData = json.loads(stringJSONData)

        getirListing = jsonParseData["props"]["pageProps"]["initialState"][
            "getirListing"
        ]

        data = getirListing["products"]["data"]

        for fruitAndVeggies in data:
            title = fruitAndVeggies["name"]
            products = fruitAndVeggies["products"]
            for product in products:
                name = product["name"]
                imgURL = product["picURLs"][0]
                price = product["price"]
                formatted_price = "{:.2f}".format(float(price))
                slug = product["slug"]

                results = MarketItems(
                    title=title,
                    scrapedDate=datetime.today().strftime("%Y-%m-%d"),
                    imageUrl=imgURL,
                    itemURL="https://getir.com/urun/" + slug,
                    name=name,
                    price=formatted_price,
                    marketName="getir",
                )

                yield results
