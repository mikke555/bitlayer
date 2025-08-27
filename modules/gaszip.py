import random

from web3 import Web3

import settings
from models.browser import Browser
from models.wallet import Wallet
from modules.config import (
    CHAIN_DATA,
    GASZIP_DATA,
    GASZIP_DIRECT_DEPOSIT_ADDRESS,
    MIN_SEND_VALUE,
    logger,
)
from modules.utils import sleep


class GasZipHelper(Wallet):
    def __init__(self, private_key, counter):
        super().__init__(private_key, counter)
        self.label += "GasZip |"

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

        # Select random chain
        random_chain = random.choice(balances)

        logger.debug(f"{self.label} Random chain selected: {random_chain[0].title()}")
        return random_chain

    def get_bridging_data(self):
        result = self.get_chain_with_balance()

        if not result:
            return None

        chain, balance = result

        value_range_wei = [int(value * 10**18) for value in settings.SEND_VALUE]
        transfer_value = random.randint(*value_range_wei)

        if transfer_value > balance:
            logger.warning(
                f"{self.label} Generated amount {transfer_value / 10**18:.6f} exceeds wallet balance, skipping\n"
            )
            return None

        return chain, transfer_value


class GasZip(Wallet):

    def __init__(self, private_key, counter, chain, proxy=None):
        super().__init__(private_key, counter, chain)
        self.label += "GasZip |"
        self.browser = Browser(self.label, proxy)
        self.w3 = Web3(Web3.HTTPProvider(CHAIN_DATA[chain]["rpc"]))

    def transfer(self, transfer_value):
        bridge_address = self.to_checksum(GASZIP_DIRECT_DEPOSIT_ADDRESS)
        tx = self.get_tx_data(value=transfer_value, to=bridge_address, data=GASZIP_DATA)

        gas = self.web3.eth.estimate_gas(tx)
        tx["gas"] = gas

        max_priority_fee_per_gas = self.web3.eth.max_priority_fee
        base_fee = (self.web3.eth.get_block("latest"))["baseFeePerGas"]
        max_fee_per_gas = base_fee + max_priority_fee_per_gas

        tx["maxPriorityFeePerGas"] = max_priority_fee_per_gas
        tx["maxFeePerGas"] = int(max_fee_per_gas * 1.05)

        return self.send_tx(
            tx,
            tx_label=f"{self.label} Bridge {transfer_value / 10**18:.6f} ETH from {self.chain.title()} => Bitlayer",
        )
