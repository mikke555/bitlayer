import requests
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import settings
from modules.config import logger


class Browser:
    def __init__(self, label, proxy=None):
        self.label = label
        self.ua = UserAgent()
        self.proxy = proxy
        self.session = self.create_session(proxy)

    def create_session(self, proxy):
        session = requests.Session()

        # Configure retries
        retries = Retry(
            total=5,  # Increase the number of retries here
            backoff_factor=0.5,  # Wait time between retries (exponential backoff)
            status_forcelist=[500, 502, 503, 504],  # Retry on these HTTP status codes
            allowed_methods=frozenset(["GET", "POST"]),  # Methods to retry
        )

        # Mount the adapter with the retry configuration
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        if proxy:
            session.proxies.update({"http": proxy, "https": proxy})

        session.headers.update(
            {
                "Accept": "*/*",
                "Content-Type": "application/json",
                "Origin": "https://www.bitlayer.org",
                "Referer": "https://www.bitlayer.org/me",
                "User-Agent": self.ua.random,
            }
        )
        return session

    def check_ip(self):
        proxy = self.proxy

        try:
            proxies = {"http": proxy, "https": proxy} if settings.USE_PROXY else None
            resp = self.session.get(
                "https://httpbin.org/ip", proxies=proxies, timeout=10
            )
            ip = resp.json()["origin"]
            logger.info(f"{self.label} Current IP: {ip}")

        except Exception as error:
            logger.error(f"{self.label} Failed to get IP: {error}")
