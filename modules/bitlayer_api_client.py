import time

from eth_account import Account
from eth_account.messages import encode_defunct

import settings
from modules.browser import Browser
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
        signature = self.sign_message("BITLAYER")
        data = self.post(
            "/me/login", json={"address": self.address, "signature": signature}
        )

        if not data or data.get("message") != "ok":
            raise Exception(f"Authorization failed: {data}")

        logger.debug(f"{self.module_str} Authorization successful")
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
    def get_user_stats(self):
        data = self.get("/me?_data=routes%2F%28%24lang%29._app%2B%2Fme%2B%2F_index")

        if not data:
            raise Exception(f"{self.module_str} Failed to get user stats")

        total_points = data["profile"]["totalPoints"]
        level = data["profile"]["level"]
        daily_tasks = data["tasks"]["dailyTasks"]
        tasks_of_interest = [task for task in daily_tasks if task["taskId"] in [1, 2]]
        ongoing_task = data["tasks"]["ongoingTask"]

        logger.info(f"{self.module_str} Total points: {total_points}, lvl {level}")
        return total_points, level, tasks_of_interest, ongoing_task

    def start_task(self, task_id, task_name):
        data = self.post("/me/task/start", json={"taskId": task_id})

        if not data or data.get("message") != "ok":
            raise Exception(f"Failed to start {task_name}: {data}")

        logger.info(f"{self.module_str} Started {task_name}")

    def claim_tx_rewards(self, task_id, task_name, pp):
        if not pp:
            logger.warning(f"{self.module_str} No rewards to claim or already claimed")
            return

        self.start_task(task_id, task_name)
        random_sleep(*settings.SLEEP_BETWEEN_ACTIONS)

        data = self.post("/me/task/verify", json={"taskId": task_id})

        if not data or data.get("message") != "ok":
            raise Exception(f"Failed to claim task {task_id}: {data}")

        logger.success(f"{self.module_str} Claimed {pp} points in {task_name}")

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

    def claim_task(self, task_id, task_name, pp):
        data = self.post("/me/task/claim", json={"taskId": task_id, "taskType": 1})

        if not data or data.get("message") != "ok":
            raise Exception(f"Failed to claim task {task_id}: {data}")

        logger.success(f"{self.module_str} Claimed {pp} points for {task_name}")

    def get_lottery_info(self):
        """Get lottery eligibility"""
        data = self.get("/api/draw/info")

        if not data:
            raise Exception(f"Failed to fetch lottery info: {data}")

        chances = data.get("chances", 0)
        if chances > 0:
            logger.debug(f"{self.module_str} You have {chances} Lucky Draw(s)")
        else:
            logger.warning(f"{self.module_str} You have {chances} Lucky Draw(s)")

        return chances

    def get_lottery_id(self):
        """Fetch lottery_id and expire_time required by lotteryReveal contract function"""
        data = self.get("/api/draw/pre")

        if not data:
            raise Exception(f"Failed to fetch lottery id: {data}")

        return data["lottery_id"], int(data["expire_time"])

    def get_draw_result(self, lottery_id):
        """Fetch the result of a draw"""
        data = self.get(f"/api/draw/reply/{lottery_id}")

        if not data:
            raise Exception(f"Failed to fetch draw result: {data}")

        return data
