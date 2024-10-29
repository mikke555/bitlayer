import random

from rich import print as rich_print
from rich.text import Text

import settings
from modules.avalon import Avalon
from modules.bitcow import BitCow
from modules.bitlayer import Bitlayer
from modules.config import logger
from modules.layerbank import LayerBank
from modules.owlto import Owlto
from modules.utils import create_csv, get_rand_amount, random_sleep
from modules.wallet import Wallet
from modules.wrapper import Wrapper


class ActionHandler:
    """
    Centralized handler for mapping user actions to their corresponding functions.
    """

    wrap_btc_option = (
        f"Wrap BTC {settings.WRAP_TX_COUNT[0]} to {settings.WRAP_TX_COUNT[1]} times"
    )

    def __init__(self, keys, proxies):
        self.keys = keys
        self.proxies = proxies

    def get_action_map(self):
        return {
            "Parse Accounts": self.parse_accounts,
            "Free Draw": self.lucky_draw,
            "Claim Daily Tasks": self.claim_daily_tasks,
            'Claim "Transact more than X times"': self.claim_advanced_tasks,
            self.wrap_btc_option: self.wrap_btc,
            "Unwrap WBTC": self.unwrap_wbtc,
            "Swap BTC > WBTC > BTC": lambda key, idx, total: self.swap_btc(
                key, idx, total, "WBTC"
            ),
            "Swap BTC > BITUSD > WBTC": lambda key, idx, total: self.swap_btc(
                key, idx, total, "BITUSD"
            ),
            "Check in with Owlto": self.check_in_owlto,
            "Deposit to Avalon": self.deposit_to_avalon,
            "Deposit to LayerBank": self.deposit_to_layerbank,
        }

    def get_proxy(self, index):
        """Assigns a proxy to a wallet based on its index"""
        if settings.USE_PROXY and self.proxies:
            # Zero-based index for proxy list
            proxy_index = (index - 1) % len(self.proxies)
            return self.proxies[proxy_index]
        return None

    def parse_accounts(self):
        logger.info(
            f"Parsing {len(self.keys)} accounts and their transaction counts...\n"
        )
        wallets_data = []

        for index, key in enumerate(self.keys, start=1):
            wallet = Wallet(key, None)

            if wallet.tx_count >= 100:
                text = Text(
                    f"{index} {wallet.address}: {wallet.tx_count} transaction(s)",
                    style="green",
                )
            elif wallet.tx_count >= 50:
                text = Text(
                    f"{index} {wallet.address}: {wallet.tx_count} transaction(s)",
                    style="yellow",
                )
            else:
                text = Text(
                    f"{index} {wallet.address}: {wallet.tx_count} transaction(s)"
                )

            rich_print(text)
            wallets_data.append((index, wallet.address, wallet.tx_count))

        create_csv(
            "reports/tx_count.csv", "w", ["№", "Wallet", "TX count"], wallets_data
        )

    def lucky_draw(self, key, index, total):
        proxy = self.get_proxy(index)
        draw = Bitlayer(key, f"[{index}/{total}]", proxy)
        return draw.get_draw()

    def claim_daily_tasks(self, key, index, total):
        proxy = self.get_proxy(index)
        bitlayer = Bitlayer(key, f"[{index}/{total}]", proxy)
        return bitlayer.claim_daily_tasks()

    def claim_advanced_tasks(self, key, index, total):
        proxy = self.get_proxy(index)
        bitlayer = Bitlayer(key, f"[{index}/{total}]", proxy)
        return bitlayer.claim_txn_tasks()

    def wrap_btc(self, key, index, total):
        wrapper = Wrapper(key, f"[{index}/{total}]")

        # Check for sufficient balance
        balance = wrapper.get_balance()
        min_balance = wrapper.web3.to_wei(settings.MIN_BTC_BALANCE, "ether")

        if balance < min_balance:
            logger.warning(
                f"{wrapper.module_str} Current balance is under {settings.MIN_BTC_BALANCE:.8f} BTC, will attempt to redeem BTC instead"
            )
            return wrapper.withdraw()

        tx_count = random.randint(*settings.WRAP_TX_COUNT)

        for _ in range(tx_count):
            rand_amount = random.uniform(*settings.WRAP_VALUE)
            tx_status = wrapper.deposit(rand_amount)

            if tx_status:
                random_sleep(*settings.SLEEP_BETWEEN_ACTIONS)

        return True

    def unwrap_wbtc(self, key, index, total):
        wrapper = Wrapper(key, f"[{index}/{total}]")

        return wrapper.withdraw()

    def swap_btc(self, key, index, total, to_token):
        bitcow = BitCow(key, f"[{index}/{total}]")
        amount = get_rand_amount(*settings.SWAP_VALUES)
        rand_percentage = random.randint(*settings.SWAP_BACK_VALUES)

        return bitcow.swap(to_token, amount, rand_percentage)

    def check_in_owlto(self, key, index, total):
        owlto = Owlto(key, f"[{index}/{total}]")

        return owlto.check_in()

    def deposit_to_avalon(self, key, index, total):
        avalon = Avalon(key, f"[{index}/{total}]")
        amount = get_rand_amount(*settings.DEPOSIT_VALUE)

        return avalon.deposit_native_token(amount)

    def deposit_to_layerbank(self, key, index, total):
        layerbank = LayerBank(key, f"[{index}/{total}]")
        amount = get_rand_amount(*settings.DEPOSIT_VALUE)

        return layerbank.supply(amount)
