import requests
from eth_account import Account
from eth_account.messages import encode_defunct
from fake_useragent import UserAgent

from modules.config import logger


class Browser:
    def __init__(self, module_str, proxy=None):
        self.module_str = module_str
        self.ua = UserAgent()
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

    def sign_message(self, message, private_key):
        """Sign a message with the private key"""

        message_encoded = encode_defunct(text=message)
        signed_message = Account.sign_message(message_encoded, private_key=private_key)
        return signed_message.signature.hex()

    def login(self, signature, address):
        """Login to BitLayer.org by passing signature and address"""

        url = "https://www.bitlayer.org/me/login"

        resp = self.session.post(url, json={"address": address, "signature": signature})
        data = resp.json()

        if data.get("message") == "ok":
            logger.debug(f"{self.module_str} Authorization successful")
            for cookie in resp.cookies:
                self.session.cookies.set(cookie.name, cookie.value)
        else:
            logger.error("Authorization failed!")
            raise Exception(f"Authorization failed: {data}")

    def get_lottery_info(self):
        """Get lottery eligibility"""

        url = "https://www.bitlayer.org/api/draw/info"

        response = self.session.get(url)
        data = response.json()

        if not data:
            raise Exception(f"Failed to fetch lottery info: {data}")

        if data and data["chances"] > 0:
            logger.debug(f"{self.module_str} You have {data['chances']} Lucky Draw(s)")
        elif data and data["chances"] == 0:
            logger.warning(
                f"{self.module_str} You have {data['chances']} Lucky Draw(s) \n"
            )

        return data["chances"]

    def get_lottery_id(self):
        """Fetch lottery_id and expire_time params required by lotteryReveal contract func"""

        url = "https://www.bitlayer.org/api/draw/pre"

        response = self.session.get(url)
        data = response.json()

        if data:
            return data["lottery_id"], int(data["expire_time"])
        else:
            raise Exception(f"Failed to fetch lottery id: {data}")

    def get_draw_result(self, lottery_id):
        """Fetch the result of a draw"""

        url = f"https://www.bitlayer.org/api/draw/reply/{lottery_id}"

        response = self.session.get(url)
        data = response.json()

        if data:
            return data
        else:
            raise Exception(f"Failed to fetch draw result: {data}")
