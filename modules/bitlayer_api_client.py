import time

from eth_account import Account
from eth_account.messages import encode_defunct

import settings
from models.browser import Browser
from modules.config import logger
from modules.utils import random_sleep


class BitlayerApiClient:
    def __init__(self, label, private_key, address, proxy=None):
        self.label = label
        self.private_key = private_key
        self.address = address
        self.browser = Browser(label, proxy)
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
    def get_user_data(self, silent=False, end=""):
        params = {"_data": "routes/($lang)._app+/me+/_index+/_layout"}
        data = self.get("/me/tasks", params=params)

        if not data:
            raise Exception(f"{self.label} Failed to get user data")

        points = data["profile"]["totalPoints"]
        btr = data["profile"]["btr"]
        level = data["profile"]["level"]
        days = data["profile"]["daysOnBitlayer"]
        rank = data["meInfo"]["rank"]
        txn = data["profile"]["txn"]

        if not silent:
            logger.debug(
                f"{self.label} BTR: {btr}, Pts: {points}, LVL: {level}, Rank: {rank}, Days on Bitlayer: {days}, Txn: {txn} {end}"
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

        logger.info(f"{self.label} Started {title.strip()}")
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
            logger.success(f"{self.label} Claimed {pts} points for {title}")
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
            logger.info(f"{self.label} Claimable: {checked}")
            return self.wait_for_daily_browse_status()  # Recursive call
        return checked

    def get_value_for_progress(self, task: dict) -> int:
        cur_progress = task["extraData"]["cur_done_progress"]
        progress_cfg = task["action"]["payload"]["progress_cfg"]

        pts = 0

        for item in progress_cfg:
            if int(cur_progress) >= item["key"]:
                pts = item["value"]
            else:
                return pts

    def claim(self, task, silent=False) -> bool:
        id, type, title, main_title, pts = (
            task["taskId"],
            task["taskType"],
            task["title"],
            task.get("mainTitle", None),
            task.get("rewardPoints", 0),
        )

        if main_title:
            title = main_title

        data = self.post("/me/task/claim", json={"taskId": id, "taskType": type})

        if task["taskId"] == 34:
            pts = self.get_value_for_progress(task)

        if not data or data.get("message") != "ok":
            raise Exception(f"Failed to claim task {id}: {data}")

        if not silent:
            logger.success(f"{self.label} Claimed {pts} points for {title.strip()}")
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

    def start_daily_check(self) -> bool:
        data = self.get("/api/btcfi/daily-check")

        if not data or data.get("success") != True:
            raise Exception(f"Failed to start daily check: {data}")

        return True

    def claim_daily_check(self) -> int:
        data = self.get("/api/btcfi/claim-order")

        if not data or data.get("success") != True:
            raise Exception(f"Failed to claim daily check: {data}")

        return int(data["data"]["orderId"])

    def get_minging_gala_info(self) -> dict:
        params = {"_data": "routes/($lang)._app+/mining-gala+/_index/index"}
        data = self.get("/mining-gala", params=params)

        if not data:
            raise Exception(f"Failed to get mining gala info: {data}")

        return data

    def get_box_info(self) -> dict:
        """
        Retrieves box information, including ID, expiration timestamp and unboxed item count.

        Returns:
            dict: Example:
            {
                "box_id": "b2ef1a30-ccc0-419d-90da-0e0480c550bc",
                "expire_at": 1732095067,
                "count": 10
            }
        """
        params = {"type": "project", "count": "-1"}
        data = self.get("/api/mining-gala/box", params=params)

        if not data:
            raise Exception(f"Failed to get box info: {data}")

        return data

    def get_unboxing_status(self, box_id: str, attempts: int = 0) -> dict:
        """
        Recursively retrieves the unboxing status of a box until the status equals 3
        or the maximum number of attempts (10) is reached.

        Returns:
            dict: Example:
            {
                "btr": 20.2,
                "status": 3,
                "count": 10
            }
        """
        if attempts >= 10:
            raise Exception(f"Max attempts reached for box_id {box_id}")

        data = self.get(f"/api/mining-gala/result/{box_id}")

        if not data:
            raise Exception(f"Failed to get unboxing status for box_id {box_id}")

        # 3 is the magic number!
        if data.get("status") == 3:
            return data

        random_sleep(5, 5)
        return self.get_unboxing_status(box_id, attempts + 1)

    def get_car_info(self):
        params = {"_data": "routes/($lang)._app+/assemble-cars/_index"}
        data = self.get(f"/assemble-cars", params=params)["userInfo"]

        if not data:
            raise Exception(f"Failed to get car info")

        logger.debug(
            f"{self.label} Normal cars: {data['normalCarAmount']}, Premium cars: {data['premiumCarAmount']}, Top cars: {data['topCarAmount']}"
        )
        return data

    def assemble_car(self, star_rating: int) -> bool:
        payload = {"starRating": star_rating}
        data = self.post("/api/raffle/assemble", json=payload)

        if not data or data.get("message") != "ok":
            raise Exception(f"Failed to assemble {star_rating}-star car: {data}")

        logger.success(f"{self.label} {data['message']}")
        return True
