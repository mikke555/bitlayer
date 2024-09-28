import random

import questionary

import settings
from modules.config import logger
from modules.draw import LuckyDraw
from modules.owlto import Owlto
from modules.utils import random_sleep, sleep
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


def parse_accounts(keys):
    logger.info(f"Parsing {len(keys)} accounts and their transaction counts...\n")
    for index, key in enumerate(keys, start=1):
        wallet = Wallet(key, None)
        print(f"{index} {wallet.address}: {wallet.tx_count} transaction(s)")


def wrap_btc(keys, tx_count):
    for index, key in enumerate(keys, start=1):
        wrapper = Wrapper(key, f"[{index}/{len(keys)}]")

        for _ in range(tx_count):
            rand_amount = random.uniform(*settings.AMOUNT_TO_WRAP)
            tx_status = wrapper.deposit(rand_amount)

            # Sleep after a successful transaction
            if tx_status:
                random_sleep(*settings.SLEEP_BETWEEN_ACTIONS)

        # Sleep after all transactions for the current wallet
        if index < len(keys):
            sleep(*settings.SLEEP_BETWEEN_WALLETS)


def unwrap_btc(keys):
    for index, key in enumerate(keys, start=1):
        wrapper = Wrapper(key, f"[{index}/{len(keys)}]")
        tx_status = wrapper.withdraw()

        if tx_status and index < len(keys):
            sleep(*settings.SLEEP_BETWEEN_WALLETS)


def check_in_owlto(keys):
    for index, key in enumerate(keys, start=1):
        owlto = Owlto(key, f"[{index}/{len(keys)}]")
        tx_status = owlto.check_in()

        if tx_status and index < len(keys):
            sleep(*settings.SLEEP_BETWEEN_WALLETS)


def lucky_draw(keys, proxies):
    for index, key in enumerate(keys, start=1):
        proxy = random.choice(proxies) if settings.USE_PROXY else None
        draw = LuckyDraw(key, f"[{index}/{len(keys)}]", proxy)
        tx_status = draw.get_draw()

        if tx_status and index < len(keys):
            sleep(*settings.SLEEP_BETWEEN_WALLETS)


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
            wrap_btc_option,
            "Unwrap WBTC",
            "Check in with Owlto",
            "Lucky Draw",
            "Parse Accounts",
        ],
    ).ask()

    # Handle different actions
    if action == "Parse Accounts":
        parse_accounts(keys)
        exit(0)

    if action == wrap_btc_option:
        tx_count = random.randint(*settings.WRAP_TX_COUNT)
        wrap_btc(keys, tx_count)

    elif action == "Unwrap WBTC":
        unwrap_btc(keys)

    elif action == "Check in with Owlto":
        check_in_owlto(keys)

    elif action == "Lucky Draw":
        lucky_draw(keys, proxies)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Script interrupted by user")
