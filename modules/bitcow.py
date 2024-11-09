import settings
from modules.config import BITCOW, BITCOW_ABI, BITUSD, INFINITE_AMOUNT, WBTC, logger
from modules.utils import check_min_balance, sleep
from modules.wallet import Wallet


class BitCow(Wallet):
    def __init__(self, private_key, counter):
        super().__init__(private_key, counter)
        self.label += "BitCow |"
        self.contract = self.get_contract(BITCOW, abi=BITCOW_ABI)

    @check_min_balance
    def swap(self, to_token, amount, percentage):
        if to_token == "BITUSD":
            tx_status = self.swap_btc_to_bitusd(amount)
            if tx_status:
                sleep(*settings.SLEEP_BETWEEN_ACTIONS)

            # Perform reverse swap
            return self.swap_bitusd_to_btc(percentage)

        elif to_token == "WBTC":
            tx_status = self.swap_btc_to_wbtc(amount)
            if tx_status:
                sleep(*settings.SLEEP_BETWEEN_ACTIONS)

            # Perform reverse swap
            return self.swap_wbtc_to_btc(percentage)

    def swap_btc_to_bitusd(self, amount):
        """Function: swapBTCtoERC20 (address[] pools, bool[] isXtoYs, uint256 minOutputAmount)"""

        contract_tx = self.contract.functions.swapBTCtoERC20(
            ["0xDFA33A77ce4420bf4cA7bFa9c1a57A40307a092e"], [True], 0
        ).build_transaction(self.get_tx_data(value=amount))

        return self.send_tx(
            contract_tx,
            tx_label=f"{self.label} swap {amount / 10**18:.8f} BTC > BITUSD [{self.tx_count}]",
        )

    def swap_bitusd_to_btc(self, percentage):
        """Function: swap (uint256 inputAmount, address[] pools, bool[] isXtoYs, uint256 minOutputAmount)"""
        balance, decimals, symbol = self.get_token(BITUSD)

        if balance == 0:
            logger.warning(f"{self.label} No {symbol} tokens to swap \n")
            return

        amount = int((percentage / 100) * balance)

        tx_label = f"approve {amount / 10 ** decimals:.8f} {symbol}"
        self.approve(
            BITUSD,
            self.contract.address,
            INFINITE_AMOUNT,
            tx_label=f"{self.label} {tx_label} [{self.tx_count}]",
        )

        contract_tx = self.contract.functions.swap(
            amount,
            ["0xDFA33A77ce4420bf4cA7bFa9c1a57A40307a092e"],
            [False],
            0,
        ).build_transaction(self.get_tx_data())

        return self.send_tx(
            contract_tx,
            tx_label=f"{self.label} swap {amount / 10**decimals:.8f} BTIUSD > WBTC [{self.tx_count}]",
        )

    def swap_btc_to_wbtc(self, amount):
        """Function: swapBTCtoWBTC (address wbtc)"""
        contract_tx = self.contract.functions.swapBTCtoWBTC(WBTC).build_transaction(
            self.get_tx_data(value=amount)
        )

        return self.send_tx(
            contract_tx,
            tx_label=f"{self.label} swap {amount / 10**18:.8f} BTC > WBTC [{self.tx_count}]",
        )

    def swap_wbtc_to_btc(self, percentage):
        """Function: swapWBTCtoBTC (address wbtc, uint256 amount)"""
        balance, decimals, symbol = self.get_token(WBTC)

        if balance == 0:
            logger.warning(f"{self.label} No {symbol} tokens to swap \n")
            return

        amount = int((percentage / 100) * balance)

        tx_label = f"approve {amount / 10 ** decimals:.8f} {symbol}"
        self.approve(
            WBTC,
            self.contract.address,
            INFINITE_AMOUNT,
            tx_label=f"{self.label} {tx_label} [{self.tx_count}]",
        )

        contract_tx = self.contract.functions.swapWBTCtoBTC(
            WBTC, amount
        ).build_transaction(self.get_tx_data())

        return self.send_tx(
            contract_tx,
            tx_label=f"{self.label} swap {amount / 10**decimals:.8f} {symbol} > BTC [{self.tx_count}]",
        )
