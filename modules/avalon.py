from modules.config import AVALON
from modules.utils import check_min_balance
from modules.wallet import Wallet


class Avalon(Wallet):
    def __init__(self, private_key, counter):
        super().__init__(private_key, counter)
        self.label += "Avalon |"
        contract_abi = [
            {
                "type": "function",
                "name": "depositETH",
                "inputs": [
                    {"name": "poolAddress", "type": "address"},
                    {"name": "onBehalfOf", "type": "address"},
                    {"name": "referralCode", "type": "uint16"},
                ],
            }
        ]
        self.contract = self.get_contract(AVALON, abi=contract_abi)

    @check_min_balance
    def deposit_native_token(self, amount):
        pool_address = self.to_checksum("0xea5c99a3cca5f95ef6870a1b989755f67b6b1939")

        contract_tx = self.contract.functions.depositETH(
            pool_address,
            self.address,
            0,  # referralCode
        ).build_transaction(self.get_tx_data(value=amount))

        return self.send_tx(
            contract_tx,
            tx_label=f"{self.label} deposit {amount / 10**18:.8f} BTC [{self.tx_count}]",
        )
