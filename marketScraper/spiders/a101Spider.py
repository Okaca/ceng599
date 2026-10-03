import re
import scrapy
from marketScraper.items import MarketItems

API = "https://rio.a101.com.tr/dbmk89vnr/CALL"
STORE_CODE = "VS032"  # A101 Kapida default store
CHANNEL = "SLOT"


class A101Spider(scrapy.Spider):
    name = "a101Spider"
    allowed_domains = ["rio.a101.com.tr"]
    start_urls = [
        f"{API}/ContentHub/getTree/default?platform=web&channel={CHANNEL}",
    ]

    def parse(self, response):
        # every top-level category: Meyve, Sebze / Et, Tavuk, Şarküteri / ...
        for category in response.json()["categories"]:
            # entries named "→" are promotion/collection shortcuts without products of their own
            if (category.get("action") or {}).get("type") != "category":
                continue
            yield response.follow(
                f"{API}/Store/getProductsByCategory/{STORE_CODE}?id={category['id']}&channel={CHANNEL}",
                callback=self.parse_category,
            )

    def parse_category(self, response):
        data = response.json()
        for child in data["children"]:
            # e.g. "Süt Ürünleri, Kahvaltılık > Süt"
            category = f"{data['name']} > {child['name']}"
            for product in child["products"]:
                attributes = product["attributes"]
                price = product["price"]
                # prices are in kuruş: 1990 = 19.90 TL
                discounted = price.get("discounted") or price["normal"]
                # 0 for items sold without a weight, e.g. electronics
                quantity = attributes.get("netWeight") or None

                yield MarketItems(
                    marketName="a101",
                    externalId=product["id"],
                    name=attributes["name"],
                    price=discounted / 100,
                    regularPrice=price["normal"] / 100,
                    discountRate=price.get("discountRate"),
                    brand=attributes.get("brand") or None,
                    barcode=self.pick_barcode(attributes.get("barcodes")),
                    category=category,
                    quantity=quantity,
                    unit=self.unit_for(attributes["name"]) if quantity else None,
                    itemURL=attributes.get("seoUrl"),
                    imageUrl=self.pick_image(product.get("images")),
                    inStock=bool(product.get("isEnabled")) and (product.get("stock") or 0) > 0,
                    storeCode=STORE_CODE,
                )

    @staticmethod
    def pick_barcode(barcodes):
        # prefer a real EAN-8/EAN-13; codes starting with "2" are A101's in-store codes
        barcodes = barcodes or []
        for code in barcodes:
            if len(code) in (8, 13) and not code.startswith("2"):
                return code
        return barcodes[0] if barcodes else None

    @staticmethod
    def pick_image(images):
        # the list also holds badge images like "yerliUretim"
        for image in images or []:
            if image.get("imageType") == "product":
                return image["url"]
        return None

    @staticmethod
    def unit_for(name):
        # netWeight is in grams, or millilitres for liquids ("Süt 1 L", "Ayran 200 ml")
        if re.search(r"\d\s*(l|lt|ml|cl)\b", name, re.IGNORECASE):
            return "ml"
        return "g"
