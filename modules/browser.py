import time

import requests
from eth_account import Account
from eth_account.messages import encode_defunct
from fake_useragent import UserAgent
from rich import print_json

import settings
from modules.config import logger
from modules.utils import random_sleep


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

    def get_user_stats(self):
        url = "https://www.bitlayer.org/me?_data=routes%2F%28%24lang%29._app%2B%2Fme%2B%2F_index"

        resp = self.session.get(url)
        data = resp.json()

        total_points = data["profile"]["totalPoints"]
        level = data["profile"]["level"]
        daily_tasks = data["tasks"]["dailyTasks"]
        tasks_of_interest = [task for task in daily_tasks if task["taskId"] in [1, 2]]
        ongoing_task = data["tasks"]["ongoingTask"]

        logger.info(f"{self.module_str} Total points: {total_points}, lvl {level}")

        return total_points, level, tasks_of_interest, ongoing_task

    def start_task(self, task_id, task_name):
        url = "https://www.bitlayer.org/me/task/start"

        resp = self.session.post(url, json={"taskId": task_id})
        data = resp.json()

        if data.get("message") == "ok":
            logger.info(f"{self.module_str} Started {task_name}")
            return data["message"]
        else:
            logger.error(f"{self.module_str} Something went wrong")
            raise Exception(f"Failed to start {task_name}: {data}")

    def claim_tx_rewards(self, task_id, task_name, pp):
        url = "https://www.bitlayer.org/me/task/verify"

        if not pp:
            logger.warning(f"{self.module_str} No rewards to claim or already claimed")
            return

        self.start_task(task_id, task_name)
        random_sleep(*settings.SLEEP_BETWEEN_ACTIONS)

        resp = self.session.post(url, json={"taskId": task_id})
        data = resp.json()

        if data.get("message") == "ok":
            logger.success(f"{self.module_str} Claimed {pp} points in {task_name}")
            return True
        else:
            logger.error(f"{self.module_str} Something went wrong")
            raise Exception(f"Failed to claim task {task_id}: {data}")

    def wait_for_daily_browse_status(self):
        url = "https://www.bitlayer.org/me/task/report"

        resp = self.session.post(url, json={"taskId": 1, "pageName": "dapp_center"})
        checked = resp.json().get("checked", False)

        if not checked:
            time.sleep(5)
            logger.info(f"{self.module_str} Claimable: {checked}")
            return self.wait_for_daily_browse_status()
        else:
            return checked

    def claim_task(self, task_id, task_name, pp):
        url = "https://www.bitlayer.org/me/task/claim"

        resp = self.session.post(url, json={"taskId": task_id, "taskType": 1})
        data = resp.json()

        if data.get("message") == "ok":
            logger.success(f"{self.module_str} Claimed {pp} points for {task_name}")
        else:
            logger.error(f"{self.module_str} Something went wrong")
            raise Exception(f"Failed to claim task {task_id}: {data}")

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
