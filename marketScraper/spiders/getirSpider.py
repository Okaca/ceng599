import os

import scrapy
from scrapy.exceptions import CloseSpider

from marketScraper import getir_auth
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
        # the login cookies go in one Cookie header: given as cookies=, scrapy-impersonate and
        # Scrapy's cookie middleware would both send them, and Getir answers TokenNotFound
        return scrapy.Request(
            url,
            callback=callback,
            headers={**HEADERS, "Cookie": self.cookie_header},
            meta={"impersonate": "chrome", "dont_merge_cookies": True},
        )

    async def start(self):
        # Logged out, Getir serves its public catalog: every product "in stock", and
        # products no warehouse sells keep an old price. Logged in and located, it serves
        # the catalog of the warehouse delivering to GETIR_LAT/GETIR_LON.
        try:
            session, _, _ = getir_auth.load()
        except getir_auth.GetirLoginRequired as e:
            raise CloseSpider(f"Getir login needed, run getir_login.py ({e})")
        lat, lon = os.getenv("GETIR_LAT"), os.getenv("GETIR_LON")
        if not (lat and lon):
            raise CloseSpider("Set GETIR_LAT and GETIR_LON in .env")
        # the access token cookies (the refresh token one is only for the token endpoint)
        self.cookie_header = "; ".join(
            f"{c.name}={c.value}"
            for c in session.cookies.jar
            if c.domain.endswith("getirapi.com") and c.path == "/"
        )
        # picks the warehouse for this location; Getir remembers it for the account
        yield self.request(
            f"{API}/main/parameters?countryCode=TR&lat={lat}&lon={lon}", self.parse_location
        )

    def parse_location(self, response):
        data = response.json()
        if data["result"]["code"] != 0 or data["data"].get("isPublic", True):
            raise CloseSpider(f"Getir did not connect to a warehouse: {data['result']}")
        yield self.request(f"{API}/categories?countryCode=TR", self.parse)

    def parse(self, response):
        for category in response.json()["data"]["categories"]:
            yield self.request(
                f"{API}/category/products?countryCode=TR&categorySlug={category['slug']}",
                self.parse_category,
            )

    def parse_category(self, response):
        # one response holds all products of a category, grouped by subcategory
        data = response.json()["data"]
        if data.get("isPublic", True):
            # the login stopped working mid-run; public prices would look valid but are not
            raise CloseSpider(
                f"Getir answered with its public catalog for {response.url}, run getir_login.py"
            )
        category = data["category"]
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
