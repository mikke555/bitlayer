import random

from rich import print_json

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
                "name": "lotteryReveal",
                "inputs": [
                    {"name": "lotteryId_", "type": "string"},
                    {"name": "expiredTime_", "type": "uint256"},
                ],
            }
        ]
        self.contract = self.get_contract(BITLAYER_LOTTERY, abi=contract_abi)

    def dump_userdata_to_csv(self):
        user_data = self.client.get_user_stats()
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
            advanced_tasks = self.client.get_user_stats()["tasks"]["advanceTasks"]
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
            user_data = self.client.get_user_stats()

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
    def draw(self, lottery_id, expire_time):
        """Build and send the transaction for the lottery draw."""
        contract_tx = self.contract.functions.lotteryReveal(
            lottery_id, expire_time
        ).build_transaction(self.get_tx_data())

        return self.send_tx(
            contract_tx,
            tx_label=f"{self.module_str} Lucky Draw [{self.tx_count}]",
        )

    def get_draw(self):
        """Main function for getting the lottery draw"""
        try:
            # get lottery info and send txn
            num_draws = self.client.get_lottery_info()

            if num_draws > 0:
                lottery_id, expire_time = self.client.get_lottery_id()
                tx_status = self.draw(lottery_id, expire_time)

                if tx_status:
                    sleep(
                        20,
                        20,
                        label=f"{self.module_str} Checking draw results in",
                        new_line=False,
                    )
                    result = self.client.get_draw_result(lottery_id)
                    return self.handle_draw_result(result)

        except Exception as error:
            logger.error(f"Failed to get a draw: {error}")

    def handle_draw_result(self, result):
        """Handle the result of the lottery draw."""
        lottery_type = result.get("lottery_type")

        if lottery_type == 0:
            logger.success(f"{self.module_str} You won {result['value']}$ in BTC \n")
        elif lottery_type == 1:
            logger.success(f"{self.module_str} You won {result['value']} points \n")
        else:
            logger.debug(f"{self.module_str} You won something unusual...")
            print_json(data=result)

        return True
