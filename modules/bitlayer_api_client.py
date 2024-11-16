import time

from eth_account import Account
from eth_account.messages import encode_defunct

import settings
from models.browser import Browser
from modules.config import logger
from modules.utils import random_sleep


class BitlayerApiClient:
    def __init__(self, module_str, private_key, address, proxy=None):
        self.module_str = module_str
        self.private_key = private_key
        self.address = address
        self.browser = Browser(module_str, proxy)
        self.session = self.browser.session
        self.base_url = "https://www.bitlayer.org"
        self.login()

    # Sign a message with the private key
    def sign_message(self, message):
        """Sign a message with the private key."""
        message_encoded = encode_defunct(text=message)
        signed_message = Account.sign_message(
            message_encoded, private_key=self.private_key
        )
        return signed_message.signature.hex()

    # Authenticate with BitLayer.org
    def login(self):
        """Authenticate with BitLayer.org using the signed message."""
        self.browser.check_ip()

        signature = self.sign_message("BITLAYER")
        data = self.post(
            "/me/login", json={"address": self.address, "signature": signature}
        )

        if not data or data.get("message") != "ok":
            raise Exception(f"Authorization failed: {data}")

        # logger.debug(f"{self.module_str} Authorization successful")
        for cookie in self.session.cookies:
            self.session.cookies.set(cookie.name, cookie.value)

    # Helper methods for GET and POST requests
    def _make_request(self, method, endpoint, **kwargs):
        """Wrapper function for making requests."""
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    def get(self, endpoint, **kwargs):
        """Make a GET request to the specified endpoint."""
        return self._make_request("GET", endpoint, **kwargs)

    def post(self, endpoint, **kwargs):
        """Make a POST request to the specified endpoint."""
        return self._make_request("POST", endpoint, **kwargs)

    # API requests
    def get_user_data(self, silent=False):
        params = {"_data": "routes/($lang)._app+/me+/_index+/_layout"}
        data = self.get("/me/tasks", params=params)

        if not data:
            raise Exception(f"{self.module_str} Failed to get user data")

        points = data["profile"]["totalPoints"]
        level = data["profile"]["level"]
        days = data["profile"]["daysOnBitlayer"]
        rank = data["meInfo"]["rank"]
        txn = data["profile"]["txn"]

        if not silent:
            logger.debug(
                f"{self.module_str} Points: {points}, LVL: {level}, Rank: {rank}, Days on Bitlayer: {days}, Txn: {txn}"
            )
        return data

    def start(self, task):
        id, title, main_title = (
            task["taskId"],
            task.get("title", "Racer Center rewards"),
            task.get("mainTitle", None),
        )

        if main_title:
            title = main_title

        data = self.post("/me/task/start", json={"taskId": id})

        if not data or data.get("message") != "ok":
            raise Exception(f"Failed to start {title}: {data}")

        logger.info(f"{self.module_str} Started {title.strip()}")
        random_sleep(*settings.SLEEP_BETWEEN_ACTIONS)

    def verify(self, task):
        id, title, main_title, pts = (
            task["taskId"],
            task.get("title", "Racer Center rewards"),
            task.get("mainTitle", None),
            task["rewardPoints"],
        )

        if main_title:
            title = main_title

        data = self.post("/me/task/verify", json={"taskId": id})

        if not data or data.get("message") != "ok":
            raise Exception(f"Failed to verify task {id}: {data}")

        if title == "Racer Center rewards":
            logger.success(f"{self.module_str} Claimed {pts} points for {title}")
        random_sleep(*settings.SLEEP_BETWEEN_ACTIONS)

    def wait_for_daily_browse_status(self):
        data = self.post(
            "/me/task/report", json={"taskId": 1, "pageName": "dapp_center"}
        )

        if not data:
            raise Exception(f"Failed to report daily browse status: {data}")

        checked = data.get("checked", False)

        if not checked:
            time.sleep(5)
            logger.info(f"{self.module_str} Claimable: {checked}")
            return self.wait_for_daily_browse_status()  # Recursive call
        return checked

    def claim(self, task, silent=False) -> bool:
        id, type, title, main_title, pts = (
            task["taskId"],
            task["taskType"],
            task["title"],
            task.get("mainTitle", None),
            task["rewardPoints"],
        )

        if main_title:
            title = main_title

        data = self.post("/me/task/claim", json={"taskId": id, "taskType": type})

        if not data or data.get("message") != "ok":
            raise Exception(f"Failed to claim task {id}: {data}")

        if not silent:
            logger.success(
                f"{self.module_str} Claimed {pts} points for {title.strip()}"
            )
        random_sleep(*settings.SLEEP_BETWEEN_ACTIONS)
        return True

    def get_draw_id(self):
        data = self.get("/api/draw/car?drawType=2&drawTimes=1")

        if not data:
            raise Exception(f"Failed to get draw id: {data}")

        return data["drawId"]

    def get_draw_result(self, draw_id):
        data = self.get(f"/api/draw/result/{draw_id}")

        if not data:
            raise Exception(f"Failed to fetch draw result: {data}")

        return data
