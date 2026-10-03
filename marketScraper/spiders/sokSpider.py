import json
import re
from urllib.parse import urlparse

import scrapy
from marketScraper.items import MarketItems
from marketScraper.utils import parse_quantity

BASE_URL = "https://www.sokmarket.com.tr"
# the store the website shows to visitors without an address
STORE_CODE = "13412"

# Next.js streams the page data in chunks: self.__next_f.push([1,"..."])
FLIGHT_CHUNK = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', re.S)
SEARCH_RESULT_KEY = '"initialSearchResult":'


class SokSpider(scrapy.Spider):
    name = "sokSpider"
    allowed_domains = ["www.sokmarket.com.tr"]
    custom_settings = {
        # every page is ~1 MB of HTML, keep a polite pace and retry rate-limit answers
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 1,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408, 429, 403],
        "RETRY_TIMES": 5,
    }

    def request(self, url, callback, **kwargs):
        # the site is behind Cloudflare, so send requests like a real Chrome
        return scrapy.Request(url, callback=callback, meta={"impersonate": "chrome"}, **kwargs)

    async def start(self):
        yield self.request(BASE_URL, self.parse)

    def parse(self, response):
        # the homepage menu links every top-level category: /meyve-ve-sebze-c-20
        links = {link.split("?")[0] for link in response.css("a::attr(href)").getall() if re.search(r"-c-\d+$", link.split("?")[0])}
        for link in sorted(links):
            yield self.category_page(link, page=1)

    def category_page(self, link, page):
        # Şok's JSON API only answers requests signed by the website's own code,
        # so the products are read from the public category pages instead, which
        # embed the same search result. 20 products per page, pages start at 1.
        return self.request(
            f"{BASE_URL}{link}?page={page}",
            self.parse_category,
            cb_kwargs={"link": link, "page": page},
        )

    def search_result(self, response):
        data = "".join(json.loads(f'"{chunk}"') for chunk in FLIGHT_CHUNK.findall(response.text))
        start = data.find(SEARCH_RESULT_KEY)
        if start < 0:
            return None
        return json.JSONDecoder().raw_decode(data, start + len(SEARCH_RESULT_KEY))[0]

    def parse_category(self, response, link, page):
        result = self.search_result(response)
        if result is None:
            self.logger.warning("No search result in %s", response.url)
            return

        if page == 1:
            # some menu links are outdated and redirect to a renamed URL, dropping "?page=",
            # so build the next pages from the address page 1 actually ended up at
            link = urlparse(response.url).path
            self.logger.info("%s: %d products", link, result["page"]["totalElements"])
            for next_page in range(2, result["page"]["totalPages"] + 1):
                yield self.category_page(link, next_page)

        for entry in result["results"]:
            product = entry["product"]
            sku = entry["sku"]
            name = product["name"]

            quantity, unit = parse_quantity(name)
            if quantity is None and (sku.get("cartQuantity") or {}).get("unit") == "KG":
                quantity, unit = 1000, "g"

            # breadcrumbs start with the root "Market" category
            category = " > ".join(c["label"] for c in sku.get("breadCrumbs", []) if c["code"] != "market")

            prices = entry["prices"]
            price = prices["discounted"]["value"]
            regular_price = (prices.get("original") or {}).get("value") or price

            # products without a brand are labelled "DİĞER" (other)
            brand = (product.get("brand") or {}).get("name")
            images = product.get("images") or []

            yield MarketItems(
                marketName="sok",
                externalId=product["id"],
                name=name,
                price=price,
                regularPrice=regular_price,
                discountRate=round(100 * (1 - price / regular_price)) if regular_price > price else None,
                brand=brand if brand and brand != "DİĞER" else None,
                category=category,
                quantity=quantity,
                unit=unit,
                itemURL=f"{BASE_URL}/{product['path']}",
                imageUrl=f"{images[0]['host']}/{images[0]['path']}" if images else None,
                inStock=bool(entry.get("hasStock")),
                storeCode=STORE_CODE,
            )
