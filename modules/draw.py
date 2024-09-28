from rich import print_json

from modules.browser import Browser
from modules.config import BITLAYER_LOTTERY, logger
from modules.utils import random_sleep, sleep
from modules.wallet import Wallet


class LuckyDraw(Wallet):
    def __init__(self, private_key, counter, proxy=None):
        super().__init__(private_key, counter)
        self.module_str += "Bitlayer |"
        self.browser = Browser(self.module_str, proxy)

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
            # authorize and get session cookie
            signature = self.browser.sign_message("BITLAYER", self.private_key)
            self.browser.login(signature, self.address)
            random_sleep(1, 5)

            # get lottery info and send txn
            num_draws = self.browser.get_lottery_info()

            if num_draws > 0:
                lottery_id, expire_time = self.browser.get_lottery_id()
                tx_status = self.draw(lottery_id, expire_time)

                if tx_status:
                    sleep(20, 20, label=f"{self.module_str} Checking draw results in")
                    result = self.browser.get_draw_result(lottery_id)
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
