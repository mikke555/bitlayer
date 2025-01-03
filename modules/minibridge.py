import random

from web3 import Web3

import settings
from models.browser import Browser
from models.wallet import Wallet
from modules.config import (
    BITLAYER_INTERALID,
    CHAIN_DATA,
    MAX_SEND_VALUE,
    MIN_SEND_VALUE,
    MINIBRIDGE_ADDRESS,
    logger,
)
from modules.utils import sleep


class MiniBridgeHelper(Wallet):
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

            if balance >= MIN_SEND_VALUE:
                balances.append((chain, balance))

        if not balances:
            logger.warning(
                f"{self.label} No balance over {MIN_SEND_VALUE / 10**18:.6f} found on any chain, skipping\n"
            )
            return None

        # Select the chain with the highest balance
        max_chain, max_balance = max(balances, key=lambda x: x[1])

        logger.debug(
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
            value_range_wei = [int(value * 10**18) for value in settings.SEND_VALUE]
            transfer_value = random.randint(*value_range_wei)

            if transfer_value < MIN_SEND_VALUE or transfer_value > MAX_SEND_VALUE:
                logger.warning(
                    f"{self.label} Generated amount {transfer_value / 10**18:.6f} is outside of allowed range {MIN_SEND_VALUE / 10**18}-{MAX_SEND_VALUE / 10**18} ETH, skipping"
                )
                return None

            if transfer_value > balance:
                logger.warning(
                    f"{self.label} Generated amount {transfer_value / 10**18:.6f} exceeds wallet balance, skipping\n"
                )
                return None
        else:
            logger.error(f"{self.label} Invalid 'SEND_VALUE' in settings.py")
            exit(0)

        # Remove last 4 digits and replace them with 8000 + dest BITLAYER_INTERALID
        confirm_code = 8000 + BITLAYER_INTERALID
        transfer_value = (transfer_value // 10000) * 10000 + confirm_code

        return chain, transfer_value


class MiniBridge(Wallet):
    MAX_STATUS_CHECKS = 10

    def __init__(self, private_key, counter, chain, proxy=None):
        super().__init__(private_key, counter, chain)
        self.label += "Minibridge |"
        self.browser = Browser(self.label, proxy)
        self.w3 = Web3(Web3.HTTPProvider(CHAIN_DATA[chain]["rpc"]))

    def transfer(self, transfer_value):
        bridge_address = self.to_checksum(MINIBRIDGE_ADDRESS)
        tx = self.get_tx_data(value=transfer_value, to=bridge_address)

        gas = self.web3.eth.estimate_gas(tx)
        tx["gas"] = gas

        max_priority_fee_per_gas = self.web3.eth.max_priority_fee
        base_fee = (self.web3.eth.get_block("latest"))["baseFeePerGas"]
        max_fee_per_gas = base_fee + max_priority_fee_per_gas

        tx["maxPriorityFeePerGas"] = max_priority_fee_per_gas
        tx["maxFeePerGas"] = int(max_fee_per_gas * 1.05)

        status = self.send_tx(
            tx,
            tx_label=f"{self.label} Bridge {transfer_value / 10**18:.6f} ETH from {self.chain.title()} => Bitlayer",
        )

        if status:
            logger.info(f"{self.label} Querying MiniBridge API for status")
            return self.check_bridge_status()

        return False

    def check_bridge_status(self, retry=0) -> bool:
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
                5,
                label=f"{self.label} Transfer <{status.upper()}>. Checking again in",
                new_line=False,
            )
            return self.check_bridge_status(retry=retry + 1)  # Recursive call

        return False
