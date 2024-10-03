import random

import questionary
from rich import print as rich_print
from rich.text import Text

import settings
from modules.avalon import Avalon
from modules.bitcow import BitCow
from modules.config import logger
from modules.draw import LuckyDraw
from modules.owlto import Owlto
from modules.utils import create_csv, get_rand_amount, random_sleep, sleep
from modules.wallet import Wallet
from modules.wrapper import Wrapper


def load_keys(file_path):
    with open(file_path) as f:
        keys = [row.strip() for row in f]
        if settings.SHUFFLE_WALLETS:
            random.shuffle(keys)
        return keys


def load_proxies(file_path):
    with open(file_path) as file:
        proxies = [f"http://{row.strip()}" for row in file]
    if settings.USE_PROXY and not proxies:
        logger.warning("Turn off proxies or populate proxies.txt")
        exit(0)
    return proxies


def process_wallets(keys, action_callback, *args, **kwargs):
    for index, key in enumerate(keys, start=1):
        tx_status = action_callback(key, index, len(keys), *args, **kwargs)

        # Sleep between wallets
        if tx_status and index < len(keys):
            sleep(*settings.SLEEP_BETWEEN_WALLETS)


def parse_accounts(keys):
    logger.info(f"Parsing {len(keys)} accounts and their transaction counts...\n")
    wallets_data = []

    for index, key in enumerate(keys, start=1):
        wallet = Wallet(key, None)

        if wallet.tx_count >= 50:
            text = Text(
                f"{index} {wallet.address}: {wallet.tx_count} transaction(s)",
                style="green",
            )
        else:
            text = Text(f"{index} {wallet.address}: {wallet.tx_count} transaction(s)")

        rich_print(text)
        wallets_data.append((index, wallet.address, wallet.tx_count))

    create_csv("wallets.csv", wallets_data)
    logger.success(f"wallets.csv created \n")


# Specific action functions
def wrap_btc_action(key, index, total):
    wrapper = Wrapper(key, f"[{index}/{total}]")
    tx_count = random.randint(*settings.WRAP_TX_COUNT)

    for _ in range(tx_count):
        rand_amount = random.uniform(*settings.AMOUNT_TO_WRAP)
        tx_status = wrapper.deposit(rand_amount)

        if tx_status:
            random_sleep(*settings.SLEEP_BETWEEN_ACTIONS)

    return True


def unwrap_btc_action(key, index, total):
    wrapper = Wrapper(key, f"[{index}/{total}]")
    return wrapper.withdraw()


def check_in_owlto_action(key, index, total):
    owlto = Owlto(key, f"[{index}/{total}]")
    return owlto.check_in()


def lucky_draw_action(key, index, total, proxies=None):
    proxy = random.choice(proxies) if settings.USE_PROXY and proxies else None
    draw = LuckyDraw(key, f"[{index}/{total}]", proxy)

    return draw.get_draw()


def swap_btc_action(key, index, total, to_token):
    bitcow = BitCow(key, f"[{index}/{total}]")
    amount = get_rand_amount(*settings.SWAP_VALUES)
    rand_percentage = random.randint(*settings.SWAP_BACK_VALUES)

    return bitcow.swap(to_token, amount, rand_percentage)


def avalon_depoit(key, index, total):
    avalon = Avalon(key, f"[{index}/{total}]")
    amount = get_rand_amount(*settings.DEPOSIT_VALUE)

    avalon.deposit_native_token(amount)


def main():
    # Load keys and proxies
    keys = load_keys("keys.txt")
    proxies = load_proxies("proxies.txt") if settings.USE_PROXY else []

    # Action choices
    wrap_btc_option = (
        f"Wrap BTC {settings.WRAP_TX_COUNT[0]} to {settings.WRAP_TX_COUNT[1]} times"
    )
    action = questionary.select(
        "Select action",
        choices=[
            "Parse Accounts",
            "Lucky Draw",
            wrap_btc_option,
            "Unwrap WBTC",
            "Swap BTC > WBTC > BTC",
            "Swap BTC > BITUSD > WBTC",
            "Check in with Owlto",
            "Deposit to Avalon",
        ],
    ).ask()

    # Handle different actions
    if action == "Parse Accounts":
        parse_accounts(keys)

    elif action == wrap_btc_option:
        process_wallets(keys, wrap_btc_action)

    elif action == "Unwrap WBTC":
        process_wallets(keys, unwrap_btc_action)

    elif action == "Check in with Owlto":
        process_wallets(keys, check_in_owlto_action)

    elif action == "Lucky Draw":
        process_wallets(keys, lucky_draw_action, proxies=proxies)

    elif action == "Swap BTC > WBTC > BTC":
        process_wallets(keys, swap_btc_action, to_token="WBTC")

    elif action == "Swap BTC > BITUSD > WBTC":
        process_wallets(keys, swap_btc_action, to_token="BITUSD")

    elif action == "Deposit to Avalon":
        process_wallets(keys, avalon_depoit)

    else:
        print("Invalid action")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Cancelled by user")
