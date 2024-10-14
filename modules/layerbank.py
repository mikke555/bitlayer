from modules.config import LAYERBANK
from modules.utils import check_min_balance
from modules.wallet import Wallet


class LayerBank(Wallet):
    def __init__(self, private_key, counter):
        super().__init__(private_key, counter)
        self.module_str += "LayerBank |"
        contract_abi = [
            {
                "type": "function",
                "name": "supply",
                "inputs": [
                    {"name": "lToken", "type": "address"},
                    {"name": "uAmount", "type": "uint256"},
                ],
            },
        ]

        self.contract = self.get_contract(LAYERBANK, abi=contract_abi)

    @check_min_balance
    def supply(self, amount):
        lToken = self.to_checksum("0x1471b4FAc13d42F3447fBA145bdfE95C6e7e7540")

        contract_tx = self.contract.functions.supply(lToken, amount).build_transaction(
            self.get_tx_data(value=amount)
        )

        return self.send_tx(
            contract_tx,
            tx_label=f"{self.module_str} deposit {amount / 10**18:.8f} BTC [{self.tx_count}]",
        )
