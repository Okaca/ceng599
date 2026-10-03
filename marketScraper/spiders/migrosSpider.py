import scrapy
from marketScraper.items import MarketItems
from marketScraper.utils import parse_quantity

BASE_URL = "https://www.migros.com.tr"
# without these the API answers in XML, with English category names
HEADERS = {"Accept": "application/json", "Accept-Language": "tr-TR,tr;q=0.9"}
ASCENDING = "once-en-dusuk-fiyat"  # lowest price first
DESCENDING = "once-en-yuksek-fiyat"  # highest price first


class MigrosSpider(scrapy.Spider):
    name = "migrosSpider"
    allowed_domains = ["www.migros.com.tr"]
    custom_settings = {
        # ~1000 small JSON pages, keep a polite pace and retry rate-limit answers
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "DOWNLOAD_DELAY": 0.25,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408, 429, 403],
        "RETRY_TIMES": 5,
    }

    def request(self, url, callback, **kwargs):
        # the site is behind Cloudflare, so send requests like a real Chrome
        return scrapy.Request(url, callback=callback, headers=HEADERS, meta={"impersonate": "chrome"}, **kwargs)

    async def start(self):
        yield self.request(f"{BASE_URL}/rest/categories", self.parse)

    def parse(self, response):
        for entry in response.json()["data"]:
            # "-c-" are product categories; "-dt-"/"-ptt-" are filtered views
            # (all discounted products, lifestyle filters) that repeat them
            if "-c-" in entry["data"]["prettyName"]:
                for slug in self.leaf_categories(entry):
                    yield self.category_page(slug, ASCENDING, page=1)

    def leaf_categories(self, entry):
        children = entry.get("children") or []
        if not children:
            return [entry["data"]["prettyName"]]
        return [slug for child in children for slug in self.leaf_categories(child)]

    def category_page(self, slug, sort, page):
        return self.request(
            f"{BASE_URL}/rest/search/screens/{slug}?sayfa={page}&sirala={sort}",
            self.parse_category,
            cb_kwargs={"slug": slug, "sort": sort, "page": page},
        )

    def parse_category(self, response, slug, sort, page):
        info = response.json()["data"]["searchInfo"]
        # Pages hold 30 products and the size cannot be changed. The listing order shifts
        # between requests, so paging through a big category misses products that move
        # past the current page: 13% with the default order. Crawling the smallest
        # subcategories sorted by price leaves only equally priced products that swap
        # places, and crawling multi-page ones in both price directions catches those.
        if page == 1:
            for next_page in range(2, info["pageCount"] + 1):
                yield self.category_page(slug, sort, next_page)
            if sort == ASCENDING and info["pageCount"] > 1:
                yield self.category_page(slug, DESCENDING, page=1)

        for product in info["storeProductInfos"]:
            name = product["name"]
            quantity, unit = parse_quantity(name)
            if quantity is None and product.get("unit") == "GRAM":
                # sold by weight, priced per unitAmount grams (usually 1000 = per kg)
                quantity, unit = product.get("unitAmount"), "g"

            # categoryAscendants goes from the closest parent up to the top level
            ascendants = [c["name"] for c in reversed(product.get("categoryAscendants") or [])]
            category = " > ".join(ascendants + [product["category"]["name"]])

            # prices are in kuruş: 3395 = 33.95 TL. shownPrice is what the customer pays;
            # Migros Money basket offers (crmDiscountTags) do not change it
            regular_price = product["regularPrice"] / 100
            price = product["shownPrice"] / 100
            images = product.get("images") or []

            yield MarketItems(
                marketName="migros",
                externalId=product["sku"],
                name=name,
                price=price,
                regularPrice=regular_price,
                discountRate=product.get("discountRate") or None,
                brand=(product.get("brand") or {}).get("name"),
                category=category,
                quantity=quantity,
                unit=unit,
                itemURL=f"{BASE_URL}/{product['prettyName']}",
                imageUrl=images[0]["urls"].get("PRODUCT_DETAIL") if images else None,
                inStock=product.get("status") == "IN_SALE",
            )
