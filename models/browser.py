import requests
from fake_useragent import UserAgent

import settings
from modules.config import logger


class Browser:
    def __init__(self, module_str, proxy=None):
        self.module_str = module_str
        self.ua = UserAgent()
        self.proxy = proxy
        self.session = self.create_session(proxy)

    def create_session(self, proxy):
        session = requests.Session()

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
            logger.info(f"{self.module_str} Current IP: {ip}")

        except Exception as error:
            logger.error(f"{self.module_str} Failed to get IP: {error}")
