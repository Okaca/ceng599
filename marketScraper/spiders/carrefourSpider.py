import scrapy
from marketScraper.items import MarketItems
from marketScraper.utils import parse_quantity

BASE_URL = "https://www.carrefoursa.com"

# top-level menu entries that only repeat products from the real categories
SKIP_TOP_CATEGORIES = {"Katalog Ürünleri"}


class CarrefourSpider(scrapy.Spider):
    name = "carrefourSpider"
    allowed_domains = ["www.carrefoursa.com"]
    custom_settings = {
        # every page is 3-5 MB, go easy on the site
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "DOWNLOAD_DELAY": 0.5,
    }

    def request(self, url, callback, **kwargs):
        # the site is behind Cloudflare, so send every request like a real Chrome
        return scrapy.Request(url, callback=callback, meta={"impersonate": "chrome"}, **kwargs)

    async def start(self):
        yield self.request(BASE_URL, self.parse)

    def parse(self, response):
        # top-level categories ("Atıştırmalık") are landing pages without products,
        # so take their subcategories ("Cipsler", "Kuruyemiş", ...) from the menu
        menu = response.css("nav.main-navigation ul.navbar-nav")[0]
        for top, link in self.second_level_links(menu):
            if top in SKIP_TOP_CATEGORIES:
                continue
            yield self.category_page(link, page=1)

    def second_level_links(self, ul, path=()):
        for li in ul.xpath("./li"):
            link = li.xpath("./a[contains(@href, '/c/')]")
            current = path + (link.css("::text").get("").strip(),) if link else path
            # "Tüm Ürünleri Gör" (see all) links back to the top-level landing page
            if link and len(current) == 2 and current[1] != "Tüm Ürünleri Gör":
                yield current[0], link.attrib["href"]
            for sub in li.xpath("./ul"):
                yield from self.second_level_links(sub, current)

    def category_page(self, link, page):
        # show=All returns up to 500 products per page; sorting by name keeps the
        # pages stable (the default "bestSeller" order shifts between requests).
        # Page numbers start at 1, and the site redirects "page=1" to the URL without
        # it, so the first page is requested without a page number.
        path = link.split("?")[0]
        page_param = f"&page={page}" if page > 1 else ""
        return self.request(
            f"{BASE_URL}{path}?q=%3Aname-asc&show=All{page_param}",
            self.parse_category,
            cb_kwargs={"link": link, "page": page},
        )

    def parse_category(self, response, link, page):
        if page == 1:
            last_page = int(response.css("ul.product-listing").attrib.get("data-maxpagenumber", "1"))
            for next_page in range(2, last_page + 1):
                yield self.category_page(link, next_page)

        for product in response.css("li.product-listing-item"):
            # every product carries its details in a hidden analytics <div>
            data = product.css("div.dataLayerItemData")
            if not data:
                continue
            data = data.attrib

            name = data["data-item_name"]
            quantity, unit = parse_quantity(name)
            category = " > ".join(
                c
                for c in (data.get(k) for k in ("data-item_category", "data-item_category2", "data-item_category3"))
                if c
            )
            # discounted prices are CarrefourSA card prices ("CarrefourSA Kart ile")
            price = data["data-price"]
            regular_price = data.get("data-first_price") or price
            # data-discount is the amount off in TL, not a percentage
            discount = 100 * (1 - float(price) / float(regular_price)) if float(regular_price) else 0

            # products without a brand are labelled "MARKASIZ" or an internal "BRN-1358"
            brand = data.get("data-item_brand")
            if not brand or brand == "MARKASIZ" or brand.startswith("BRN-"):
                brand = None

            yield MarketItems(
                marketName="carrefour",
                externalId=data["data-item_id"],
                name=name,
                price=price,
                regularPrice=regular_price,
                discountRate=round(discount) if discount else None,
                brand=brand,
                category=category,
                quantity=quantity,
                unit=unit,
                itemURL=response.urljoin(product.css("a.product-return::attr(href)").get()),
                imageUrl=product.css("span.thumb img::attr(src)").get(),
                inStock=data.get("data-in_stock") == "true",
            )
