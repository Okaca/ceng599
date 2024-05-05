import json
import cloudscraper
import scrapy
from datetime import datetime
from marketScraper.items import MarketItems


class SokSpider(scrapy.Spider):
    name = "sokSpider"
    main_url = "https://www.sokmarket.com.tr"
    dummy_url = "https://quotes.toscrape.com/page/1/"  # we only need to scrape start_url and send the result with meta
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

        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "tr-TR",
            "Content-Type": "application/json",
            "Cookie": "_ga=GA1.3.226652657.1693654828; _clck=3sfmxx|2|feo|0|1340; _ym_uid=1693654828412992324; _ym_d=1693654828; OfferMiner_ID=KDESAKIAOUQEEHHN20230902144204; VL_CM_0=%7B%22Items%22%3A%5B%7B%22K%22%3A%22VL_LastPageViewTime%22%2C%22V%22%3A%222023-09-02%252014%253A46%253A06%22%2C%22E%22%3A%222025-08-22%2014%3A46%3A06%22%7D%2C%7B%22K%22%3A%22VL_LastPVTimeForTD%22%2C%22V%22%3A%222023-09-02%252014%253A46%253A06%22%2C%22E%22%3A%222023-09-02%2015%3A16%3A06%22%7D%2C%7B%22K%22%3A%22VL_TotalDuration%22%2C%22V%22%3A%22242%22%2C%22E%22%3A%222025-08-22%2014%3A46%3A06%22%7D%2C%7B%22K%22%3A%22VL_FirstVisitTime%22%2C%22V%22%3A%222023-09-02%252014%253A42%253A04%22%2C%22E%22%3A%222025-08-22%2014%3A42%3A04%22%7D%2C%7B%22K%22%3A%22VL_TotalPV%22%2C%22V%22%3A%222%22%2C%22E%22%3A%222025-08-22%2014%3A46%3A06%22%7D%2C%7B%22K%22%3A%22VL_PVCountInVisit%22%2C%22V%22%3A%222%22%2C%22E%22%3A%222023-09-02%2015%3A16%3A06%22%7D%2C%7B%22K%22%3A%22VL_VisitStartTime%22%2C%22V%22%3A%222023-09-02%252014%253A42%253A04%22%2C%22E%22%3A%222023-09-02%2015%3A12%3A04%22%7D%2C%7B%22K%22%3A%22VL_TotalVisit%22%2C%22V%22%3A%221%22%2C%22E%22%3A%222025-08-22%2014%3A42%3A04%22%7D%2C%7B%22K%22%3A%22OfferMiner_ID%22%2C%22V%22%3A%22KDESAKIAOUQEEHHN20230902144204%22%2C%22E%22%3A%222025-08-22%2014%3A42%3A04%22%7D%2C%7B%22K%22%3A%22OM_INW%22%2C%22V%22%3A%221%22%2C%22E%22%3A%222025-08-22%2014%3A42%3A04%22%7D%2C%7B%22K%22%3A%22OMB_New%22%2C%22V%22%3A%221%22%2C%22E%22%3A%222023-09-02%2015%3A16%3A06%22%7D%2C%7B%22K%22%3A%22OM_rDomain%22%2C%22V%22%3A%22https%253A%252F%252Fwww.sokmarket.com.tr%252F%22%2C%22E%22%3A%222025-08-22%2014%3A46%3A06%22%7D%2C%7B%22K%22%3A%22VLTVisitorC%22%2C%22V%22%3A%22%257B%2522data%2522%253A%257B%257D%257D%22%2C%22E%22%3A%222025-08-22%2014%3A46%3A06%22%7D%5D%7D; _ga_QXGSM4YJ83=GS1.3.1693654828.1.1.1693655303.59.0.0; _ga_QW0MDP6E6B=GS1.1.1693654827.1.1.1693655312.0.0.0; X-Ecommerce-Deviceid=b7effdf1-e510-42d5-bd1c-ffe76b591621-4cae8bfc-3924-4c8b-a9b3-d28ada93ed90; OptanonAlertBoxClosed=2024-03-13T19:10:45.377Z; X-Ecommerce-Sid=0a94fcfb-ad33-4b4d-a717-20d8a843ca6c-4722461a-cdef-4f2e-9eae-c4a069f87461; X-Platform=WEB; X-Service-Type=MARKET; X-Store-Id=13412; access_token=FNlmBCX9Ep544pj9IfZztWgr0ynlG3Dc-a8t7h5rsXEtGhsJhWLUbbFTGXw0qMmS3; OptanonConsent=isGpcEnabled=0&datestamp=Fri+May+03+2024+15%3A11%3A46+GMT%2B0300+(GMT%2B03%3A00)&version=202308.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A0%2CC0004%3A0%2CC0003%3A0&AwaitingReconsent=false&geolocation=TR%3B06",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "X-Service-Type": "MARKET",  # REQUIRED
            "X-Store-Id": "13412",  # REQUIRED
        }

        for url in self.start_urls:
            scraper = cloudscraper.create_scraper()
            isOkResponse = scraper.get(url, headers=headers, cookies=headers["Cookie"])
            yield scrapy.Request(
                url=self.dummy_url,
                callback=self.parse,
                meta={"meta": isOkResponse.text},
            )

    def parse(self, response):
        print(response.meta["meta"])
        print(type(response.meta["meta"]))
        jsonResponse = json.loads(response.meta["meta"])

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
