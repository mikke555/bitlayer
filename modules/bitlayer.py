import random
from datetime import datetime

import settings
from models.wallet import Wallet
from modules.bitlayer_api_client import BitlayerApiClient
from modules.config import BITLAYER_CHECK_IN, BITLAYER_LOTTERY, logger
from modules.utils import check_min_balance, create_csv, sleep


class Bitlayer(Wallet):
    def __init__(self, private_key, counter, proxy=None):
        super().__init__(private_key, counter)
        self.label += "Bitlayer |"

        self.client = BitlayerApiClient(self.label, private_key, self.address, proxy)

        contract_abi = [
            {
                "type": "function",
                "name": "payForFree",
                "inputs": [{"name": "_drawId", "type": "string"}],
            },
        ]
        self.lottery_contract = self.get_contract(BITLAYER_LOTTERY, abi=contract_abi)
        self.check_in_contract = self.get_contract(BITLAYER_CHECK_IN, abi=contract_abi)

    def dump_userdata_to_csv(self):
        user_data = self.client.get_user_data(end="\n")
        csv_headers = ["Wallet", "Txn count", "Points", "Level", "Rank"]
        csv_data = [
            [
                self.address,
                self.tx_count,
                user_data["profile"]["totalPoints"],
                user_data["profile"]["level"],
                user_data["meInfo"]["rank"],
            ]
        ]
        date = datetime.today().strftime("%Y-%m-%d")
        create_csv(f"reports/wallets-{date}.csv", "a", csv_headers, csv_data)

    def claim_txn_tasks(self):
        try:
            advanced_tasks = self.client.get_user_data()["tasks"]["advanceTasks"]
            task = [task for task in advanced_tasks if "Total TXN" in task["title"]][0]

            if task["canClaim"]:
                self.client.claim(task)
                self.client.get_user_data(end="\n")
                return True
            else:
                logger.warning(f"{self.label} {task['title']} already claimed\n")
                return False

        except Exception as error:
            logger.error(error)

    def handle_daily_browse(self, task: dict):
        self.client.start(task)

        checked = self.client.wait_for_daily_browse_status()
        if checked:
            self.client.claim(task)

    def handle_daily_share(self, task: dict):
        self.client.start(task)
        self.client.claim(task)

    @check_min_balance
    def check_in(self, progress):
        """Function: 0x4ea1dedb(bytes32 number)"""
        progress = str(progress).zfill(64)

        tx = {
            "chainId": self.web3.eth.chain_id,
            "from": self.address,
            "to": self.check_in_contract.address,
            "nonce": self.web3.eth.get_transaction_count(self.address),
            "value": 0,
            "data": "0x4ea1dedb" + progress,
            "gasPrice": self.web3.eth.gas_price,
        }

        gas = self.web3.eth.estimate_gas(tx)
        tx["gas"] = gas

        return self.send_tx(
            tx,
            tx_label=f"{self.label} Check-in [{self.tx_count}]",
        )

    def get_check_in_task(self) -> dict:
        return self.client.get_user_data(silent=True)["tasks"]["dailyTasks"][0]

    def get_value_for_progress(self, task: dict) -> int:
        cur_progress = task["extraData"]["cur_done_progress"]
        progress_cfg = task["action"]["payload"]["progress_cfg"]

        for item in progress_cfg:
            if item["key"] == cur_progress:
                return item["value"]
        return None

    def handle_daily_check_in(self, task: dict):
        success = self.client.start_check_in()

        if not success:
            return False

        cur_progress = task["extraData"]["cur_done_progress"]
        tx_status = self.check_in(cur_progress + 1)

        if not tx_status:
            print(tx_status)
            return False

        while True:
            task = self.get_check_in_task()

            if task["extraData"]["cur_done_progress"] > cur_progress:
                pts = self.get_value_for_progress(task)
                logger.success(f"{self.label} Claimed {pts} points for {task['title']}")
                break

            sleep(5, label=f"{self.label} Checking status in", new_line=False)

        return True

    def claim_daily_tasks(self):
        try:
            user_data = self.client.get_user_data()

            # Claim ongoing Racer Center rewards for past transactions
            ongoing_task = user_data["tasks"]["ongoingTask"]
            if ongoing_task.get("rewardPoints") > 0:
                self.client.start(ongoing_task)
                self.client.verify(ongoing_task)

            # Exclude taskId 3 (Daily Bridge)
            target_ids = [1, 2, 33] if settings.DAYLY_CHECK_IN else [1, 2]
            daily_tasks = [
                task
                for task in user_data["tasks"]["dailyTasks"]
                if task["taskId"] in target_ids
            ]
            random.shuffle(daily_tasks)

            # Claim Daily Tasks
            for task in daily_tasks:
                title = task["mainTitle"] if task["mainTitle"] else task["title"]

                if task["isCompleted"]:
                    msg = f"{self.label} {title} already completed"
                    logger.warning(msg)
                    continue

                if task["taskId"] == 1:
                    self.handle_daily_browse(task)
                elif task["taskId"] == 2:
                    self.handle_daily_share(task)
                elif task["taskId"] == 33:
                    self.handle_daily_check_in(task)

        except Exception as error:
            logger.error(error)

        finally:
            self.dump_userdata_to_csv()
            return True

    def get_bridging_task(self, silent=True) -> dict:
        return self.client.get_user_data(silent=silent)["tasks"]["dailyTasks"][-1]

    def claim_minibridge(self) -> bool:
        task = self.get_bridging_task(silent=False)

        if task["isCompleted"]:
            logger.warning(f"{self.label} {task['mainTitle']} already completed")
            return True

        if task["canClaim"]:
            self.client.claim(task)
            self.client.get_user_data(end="\n")
            return True

        self.client.start(task)  # Start the task
        sleep(20, label=f"{self.label} Checking status in", new_line=False)

        while not task["canClaim"]:
            task = self.get_bridging_task()

            if task["isCompleted"]:
                logger.warning(f"{self.label} {task['mainTitle']} already completed")
                return True

            if task["canClaim"]:
                self.client.claim(task)
                self.client.get_user_data(end="\n")
                return True

            logger.warning(f"{self.label} Claimable: {task['canClaim']}")
            self.client.start(task)
            sleep(20, label=f"{self.label} Checking status in", new_line=False)

    @check_min_balance
    def draw(self, draw_id):
        """Function: payForFree(string _drawId)"""
        contract_tx = self.lottery_contract.functions.payForFree(
            draw_id
        ).build_transaction(self.get_tx_data())

        return self.send_tx(
            contract_tx,
            tx_label=f"{self.label} Free Draw [{self.tx_count}]",
        )

    def get_draw(self):
        draw_amount = self.client.get_user_data()["carUserInfo"]["remainFreeDrawAmount"]

        if int(draw_amount) == 0:
            logger.warning(f"{self.label} No free draws \n")
            return False

        draw_id = self.client.get_draw_id()
        tx_status = self.draw(draw_id)

        if not tx_status:
            return False

        sleep(20, label=f"{self.label} Checking draw results in", new_line=False)

        result = self.client.get_draw_result(draw_id)
        item_name = result["itemInfos"][0]["itemName"]
        item_star = result["itemInfos"][0]["star"]

        logger.success(
            f"{self.label} {item_name.title()} from {item_star}-Star Collection \n"
        )

        return True
