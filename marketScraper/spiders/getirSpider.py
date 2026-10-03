import scrapy
from marketScraper.items import MarketItems
from marketScraper.utils import parse_quantity

# the JSON API behind getir.com's grocery pages (found in the site's JavaScript)
API = "https://getirx-client-api-gateway.getirapi.com"
# without it, names and categories come back in English
HEADERS = {"Accept": "application/json", "x-language": "tr"}


class GetirSpider(scrapy.Spider):
    name = "getirSpider"
    allowed_domains = ["getirx-client-api-gateway.getirapi.com"]
    custom_settings = {
        # Getir starts answering 403/504 when hit too fast, and Scrapy does not retry
        # 403 by default, so a whole category could silently go missing.
        # 18 requests a day need no speed: one at a time, a few seconds apart.
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 3,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408, 429, 403],
        "RETRY_TIMES": 5,
    }

    def request(self, url, callback):
        # send requests like a real Chrome, Getir rejects some non-browser clients
        return scrapy.Request(url, callback=callback, headers=HEADERS, meta={"impersonate": "chrome"})

    async def start(self):
        yield self.request(f"{API}/categories?countryCode=TR", self.parse)

    def parse(self, response):
        for category in response.json()["data"]["categories"]:
            yield self.request(
                f"{API}/category/products?countryCode=TR&categorySlug={category['slug']}",
                self.parse_category,
            )

    def parse_category(self, response):
        # one response holds all products of a category, grouped by subcategory
        category = response.json()["data"]["category"]
        for subcategory in category["subCategories"]:
            for product in subcategory.get("products", []):
                price = product["price"]
                regular_price = product.get("struckPrice") or price
                # size is in shortDescription ("125 g", "3 Adet"), sometimes only in the name
                quantity, unit = parse_quantity(product.get("shortDescription"))
                if quantity is None:
                    quantity, unit = parse_quantity(product["name"])

                yield MarketItems(
                    marketName="getir",
                    externalId=product["id"],
                    name=product["name"],
                    price=price,
                    regularPrice=regular_price,
                    discountRate=round(100 * (1 - price / regular_price)) if regular_price > price else None,
                    brand=(product.get("brand") or {}).get("name"),
                    category=f"{category['name']} > {subcategory['name']}",
                    quantity=quantity,
                    unit=unit,
                    itemURL=f"https://getir.com/urun/{product['slug']}/",
                    imageUrl=product.get("squareThumbnailURL") or (product.get("picURLs") or [None])[0],
                    inStock=product.get("status") == 1,
                )
