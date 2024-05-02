# Scrapy settings for marketScraper project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

# from shutil import which

# SELENIUM_DRIVER_NAME = 'chrome'
# SELENIUM_DRIVER_EXECUTIBLE_PATH = 'C:/Users/okaca/Desktop/project/chromedriver-win64/chromedriver'
# SELENIUM_DRIVER_ARGUMENTS = ['--headless']

# DOWNLOADER_MIDDLEWARES = {
#   'scrapy_selenium.SeleniumMiddleware': 800
# }

BOT_NAME = "marketComparer"

SPIDER_MODULES = ["marketScraper.spiders"]
NEWSPIDER_MODULE = "marketScraper.spiders"

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = [
    "market comparer (+https://www.migros.com.tr/)",
    "market comparer (+https://getir.com/)",
    "market comparer (+https://www.carrefoursa.com/)",
]

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# # Splash Server Endpoint
# SPLASH_URL = "http://localhost:8050"

# # Enable Splash downloader middleware and change HttpCompressionMiddleware priority
# DOWNLOADER_MIDDLEWARES = {
#     "scrapy_splash.SplashCookiesMiddleware": 723,
#     "scrapy_splash.SplashMiddleware": 725,
#     "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 810,
# }

# # Enable Splash Deduplicate Args Filter
# SPIDER_MIDDLEWARES = {
#     "scrapy_splash.SplashDeduplicateArgsMiddleware": 100,
# }

# # Define the Splash DupeFilter
# DUPEFILTER_CLASS = "scrapy_splash.SplashAwareDupeFilter"

# # Define cache storage
# HTTPCACHE_STORAGE = "scrapy_splash.SplashAwareFSCacheStorage"

# Configure maximum concurrent requests performed by Scrapy (default: 16)
# CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
# CONCURRENT_REQUESTS_PER_DOMAIN = 16
# CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
# COOKIES_ENABLED = True

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
# }

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    "marketScraper.middlewares.MarketscraperSpiderMiddleware": 543,
# }

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    "marketScraper.middlewares.MarketscraperDownloaderMiddleware": 543,
    "scrapy_cloudflare_middleware.middlewares.CloudFlareMiddleware": 560,
    "scrapy.downloadermiddlewares.httpauth.HttpAuthMiddleware": 555,
    "scrapeops_scrapy.middleware.retry.RetryMiddleware": 550,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
EXTENSIONS = {
    "scrapy.extensions.telnet.TelnetConsole": None,
    "scrapeops_scrapy.extension.ScrapeOpsMonitor": 500,
}

SCRAPEOPS_API_KEY = "a6a22b0e-2794-46f9-9334-00bf3956a59e"

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    "marketScraper.pipelines.MarketscraperPipeline": 300,
}

MONGO_URI = "mongodb+srv://admin123:admin123!@cluster0.2xrqscy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
MONGO_DATABASE = "ceng599Project"
MONGODB_USERNAME = "admin123"
MONGODB_PASSWORD = "admin123!"

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
# AUTOTHROTTLE_ENABLED = True
# The initial download delay
# AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
# AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
# AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = "httpcache"
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
