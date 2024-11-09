import random

from web3 import Web3

import settings
from modules.browser import Browser
from modules.config import BITLAYER_INTERALID, CHAIN_DATA, MINIBRIDGE_ADDRESS, logger
from modules.utils import sleep
from modules.wallet import Wallet


class MiniBridgeHelper(Wallet):
    MIN_SEND_VALUE = int(settings.MIN_SEND_VALUE * 10**18)

    def __init__(self, private_key, counter):
        super().__init__(private_key, counter)
        self.label += "Minibridge |"

    def get_chain_with_balance(self):
        """Find the chain with the highest ETH balance"""
        if not settings.AVAILABLE_CHAINS:
            logger.error(f"{self.label} No chains sellected, check settings.py")
            exit(0)

        balances = []
        for chain in settings.AVAILABLE_CHAINS:
            w3 = Web3(Web3.HTTPProvider(CHAIN_DATA[chain]["rpc"]))
            balance = w3.eth.get_balance(self.address)

            if balance >= MiniBridgeHelper.MIN_SEND_VALUE:
                balances.append((chain, balance))

        if not balances:
            logger.warning(
                f"{self.label} No balance over {settings.MIN_SEND_VALUE} found on any chain, skipping"
            )
            return None

        # Select the chain with the highest balance
        max_chain, max_balance = max(balances, key=lambda x: x[1])

        logger.info(
            f"{self.label} Highest balance found on {max_chain.title()}: {max_balance / 10**18:.6f} ETH"
        )
        return max_chain, max_balance

    def get_bridging_data(self):
        """
        Calculate the bridging transfer value.

        Notes:
            - `SEND_VALUE` in settings can be "max" or a list defining a range in ETH.
            - The transfer value is adjusted to encode `8000 + BITLAYER_INTERALID` in its last digits.
        """
        result = self.get_chain_with_balance()

        if not result:
            return None

        chain, balance = result

        if settings.SEND_VALUE == "max":
            transfer_value = int(balance * 0.98)

        elif isinstance(settings.SEND_VALUE, list):
            value_range_wei = [value * 10**18 for value in settings.SEND_VALUE]
            transfer_value = random.randint(*value_range_wei)

            if transfer_value > balance:
                logger.warning(
                    f"{self.label} Generated value {transfer_value / 10**18:.6f} exceeds wallet balance, skipping"
                )
                return None
        else:
            logger.error(f"{self.label} Invalid 'SEND_VALUE' in settings.py")
            exit(0)

        # Remove last 4 digits and replace them with 8000 + dest internalId
        confirm_code = 8000 + BITLAYER_INTERALID
        transfer_value = (transfer_value // 10000) * 10000 + confirm_code

        return chain, transfer_value


class MiniBridge(Wallet):
    MAX_STATUS_CHECKS = 5

    def __init__(self, private_key, counter, chain, proxy=None):
        super().__init__(private_key, counter, chain)
        self.label += "Minibridge |"
        self.browser = Browser(self.label, proxy)

    def transfer(self, transfer_value):
        bridge_address = self.to_checksum(MINIBRIDGE_ADDRESS)
        tx = self.get_tx_data(value=transfer_value, to=bridge_address)
        tx["gasPrice"] = self.web3.eth.gas_price
        tx["gas"] = self.web3.eth.estimate_gas(tx)

        status = self.send_tx(
            tx,
            tx_label=f"{self.label} Bridge {transfer_value / 10**18:.6f} ETH from {self.chain.title()} => Bitlayer",
        )

        if status:
            logger.info(f"{self.label} Querying MiniBridge API for status")
            return self.check_bridge_status()

        return False

    def check_bridge_status(self, retry=0):
        url = f"https://minibridge-conf.chaineye.tools/{self.address.lower()}.json"
        resp = self.browser.session.get(url)

        while resp.status_code == 404:
            return self.check_bridge_status()  # Recursive call

        data = resp.json()
        if not data:
            raise Exception(f"{self.label} Failed to fetch bridging status: {data}")

        status = data[0]["status"]
        amount = float(data[0]["toamount_native"])

        if status == "finished":
            logger.success(
                f"{self.label} Transfer <{status.upper()}>. Recevied {amount:.8f} BTC\n"
            )

            return True

        if retry < self.MAX_STATUS_CHECKS:
            sleep(
                20,
                label=f"{self.label} Transfer <{status.upper()}>. Checking again in",
                new_line=False,
            )
            return self.check_bridge_status(retry=retry + 1)  # Recursive call

        return False
