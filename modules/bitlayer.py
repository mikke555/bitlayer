import csv
import os
import random

from rich import print_json

import settings
from modules.bitlayer_api_client import BitlayerApiClient
from modules.config import BITLAYER_LOTTERY, logger
from modules.utils import create_csv, random_sleep, sleep
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

    def claim_daily_tasks(self):
        try:
            # Get user stats
            _, _, daily_tasks, ongoing_task = self.client.get_user_stats()
            random.shuffle(daily_tasks)

            # Claim ongoing rewards for past transactions
            if ongoing_task and ongoing_task.get("rewardPoints") > 0:
                self.client.claim_tx_rewards(
                    ongoing_task["taskId"],
                    "ongoing rewards",
                    ongoing_task["rewardPoints"],
                )
                random_sleep(*settings.SLEEP_BETWEEN_ACTIONS)

            # Claim the daily tasks
            for task in daily_tasks:
                if task["isCompleted"]:
                    msg = f"{self.module_str} {task['mainTitle']} already completed"
                    logger.debug(msg)
                    continue

                self.client.start_task(task["taskId"], task["mainTitle"])

                if task["taskId"] == 1:
                    checked = self.client.wait_for_daily_browse_status()
                    if checked:
                        self.client.claim_task(
                            task["taskId"], task["mainTitle"], task["rewardPoints"]
                        )
                elif task["taskId"] == 2:
                    self.client.claim_task(
                        task["taskId"], task["mainTitle"], task["rewardPoints"]
                    )

                random_sleep(*settings.SLEEP_BETWEEN_ACTIONS)

        except Exception as error:
            logger.error(f"Failed to claim the task: {error}")

        finally:
            total_points, level, daily_tasks, _ = self.client.get_user_stats()
            csv_headers = ["Wallet", "TX count", "Points", "Level"]
            csv_data = [[self.address, self.tx_count, total_points, level]]
            create_csv("reports/wallets.csv", csv_headers, csv_data)

            return True

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
