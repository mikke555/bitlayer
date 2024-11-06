import random

from modules.bitlayer_api_client import BitlayerApiClient
from modules.config import BITLAYER_LOTTERY, logger
from modules.utils import check_min_balance, create_csv, sleep
from modules.wallet import Wallet


class Bitlayer(Wallet):
    def __init__(self, private_key, counter, proxy=None):
        super().__init__(private_key, counter)
        self.module_str += "Bitlayer |"

        self.client = BitlayerApiClient(
            self.module_str, private_key, self.address, proxy
        )

        contract_abi = [
            {
                "type": "function",
                "name": "payForFree",
                "inputs": [{"name": "_drawId", "type": "string"}],
            },
        ]
        self.contract = self.get_contract(BITLAYER_LOTTERY, abi=contract_abi)

    def dump_userdata_to_csv(self):
        user_data = self.client.get_user_data()
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
        create_csv("reports/wallets.csv", "a", csv_headers, csv_data)

    def claim_txn_tasks(self):
        try:
            advanced_tasks = self.client.get_user_data()["tasks"]["advanceTasks"]
            txn_tasks = [
                task for task in advanced_tasks if "Transaction more" in task["title"]
            ]

            for task in txn_tasks:
                if task["isCompleted"]:
                    msg = f"{self.module_str} {task['title'].strip()} already completed"
                    logger.warning(msg)
                    continue

                if self.tx_count >= task["targetCount"]:
                    self.client.start(task)
                    self.client.verify(task)
                    self.client.claim(task)

        except Exception as error:
            logger.error(error)

        finally:
            self.dump_userdata_to_csv()
            print()  # line break
            return True

    def claim_daily_tasks(self):
        try:
            user_data = self.client.get_user_data()

            # Claim ongoing Racer Center rewards for past transactions
            ongoing_task = user_data["tasks"]["ongoingTask"]
            if ongoing_task.get("rewardPoints") > 0:
                self.client.start(ongoing_task)
                self.client.verify(ongoing_task)

            # Exclude taskId 3 (Daily Meson Bridge)
            daily_tasks = [
                task
                for task in user_data["tasks"]["dailyTasks"]
                if task["taskId"] in [1, 2]
            ]
            random.shuffle(daily_tasks)

            # Claim Daily Tasks
            for task in daily_tasks:
                if task["isCompleted"]:
                    msg = f"{self.module_str} {task['mainTitle']} already completed"
                    logger.warning(msg)
                    continue

                self.client.start(task)

                if task["taskId"] == 1:
                    checked = self.client.wait_for_daily_browse_status()
                    if checked:
                        self.client.claim(task)
                else:
                    self.client.claim(task)

        except Exception as error:
            logger.error(error)

        finally:
            self.dump_userdata_to_csv()
            print()  # line break
            return True

    @check_min_balance
    def draw(self, draw_id):
        """Function: payForFree(string _drawId)"""
        contract_tx = self.contract.functions.payForFree(draw_id).build_transaction(
            self.get_tx_data()
        )

        return self.send_tx(
            contract_tx,
            tx_label=f"{self.module_str} Free Draw [{self.tx_count}]",
        )

    def get_draw(self):
        draw_amount = self.client.get_user_data()["carUserInfo"]["remainFreeDrawAmount"]

        if int(draw_amount) == 0:
            logger.warning(f"{self.module_str} No free draws \n")
            return False

        draw_id = self.client.get_draw_id()
        tx_status = self.draw(draw_id)

        if not tx_status:
            return False

        sleep(
            20,
            20,
            label=f"{self.module_str} Checking draw results in",
            new_line=False,
        )

        result = self.client.get_draw_result(draw_id)
        item_name = result["itemInfos"][0]["itemName"]
        item_star = result["itemInfos"][0]["star"]

        logger.success(
            f"{self.module_str} {item_name.title()} from {item_star}-Star Collection \n"
        )

        return True
