import time
from datetime import datetime, timedelta, timezone
from itertools import cycle
from random import randint, shuffle

import questionary
from questionary import Style

import settings
from modules.actions import ActionHandler
from modules.config import logger
from modules.utils import sleep


def load_keys(file_path):
    with open(file_path) as f:
        keys = [row.strip() for row in f if row.strip()]
    return keys


def load_proxies(file_path):
    with open(file_path) as file:
        proxies = [f"http://{row.strip()}" for row in file if row.strip()]
    return proxies


def wait_until_midnight_utc():
    """Waits until a random UTC time between 00:02 and 05:30 on the next day."""
    now = datetime.now(timezone.utc)

    rand_minute, rand_hour = randint(2, 30), randint(0, 5)
    target_time = (now + timedelta(days=1)).replace(
        hour=rand_hour, minute=rand_minute, second=0
    )
    # Calculate waiting time until the next midnight UTC
    time_to_wait = (target_time - now).total_seconds()

    if time_to_wait > 0:
        hours, remainder = divmod(time_to_wait, 3600)
        minutes, seconds = divmod(remainder, 60)
        target_time_str = target_time.strftime("%H:%M")

        logger.info(
            f"Waiting until {target_time_str} UTC ({int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds)..."
        )
        time.sleep(time_to_wait)
    logger.info(f"It's {target_time_str} UTC. Starting execution.\n")


def process_wallets(keys, action_callback, *args, **kwargs):
    while True:
        for index, key in enumerate(keys, start=1):
            try:
                tx_status = action_callback(key, index, len(keys), *args, **kwargs)

                # Sleep between wallets
                if tx_status and index < len(keys):
                    sleep(*settings.SLEEP_BETWEEN_WALLETS)

            except Exception as error:
                logger.error(
                    f"[{index}/{len(keys)}] Error processing wallet: {error} \n"
                )

        if settings.INFINITY_LOOP:
            logger.success("All done! 🎉")
            wait_until_midnight_utc()
        else:
            break


def main():
    keys = load_keys("keys.txt")
    proxies = load_proxies("proxies.txt") if settings.USE_PROXY else []

    if settings.USE_PROXY and not proxies:
        logger.warning("Proxies are enabled but proxies.txt is empty")
        exit(0)

    # Cycle proxies if there are fewer proxies than keys
    if settings.USE_PROXY and len(keys) > len(proxies):
        proxies = [proxy for proxy, _ in zip(cycle(proxies), range(len(keys)))]

    # Shuffle together if needed
    if settings.SHUFFLE_WALLETS and settings.USE_PROXY:
        combined = list(zip(keys, proxies))
        shuffle(combined)
        keys, proxies = zip(*combined)
        keys, proxies = list(keys), list(proxies)

    elif settings.SHUFFLE_WALLETS:
        shuffle(keys)

    action_handler = ActionHandler(keys, proxies)

    action_map = action_handler.get_action_map()
    action_choices = list(action_map.keys())

    custom_style = Style(
        [
            ("pointer", "fg:#E07C1A"),
            ("highlighted", "fg:#E07C1A"),
        ]
    )

    # Present action choices to the user
    action = questionary.select(
        "Select an action to perform:",
        choices=action_choices,
        style=custom_style,
    ).ask()

    # Execute the selected action
    if action in action_map:
        if action == "📝 Parse Accounts":
            action_map[action]()
        else:
            process_wallets(keys, action_map[action])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Cancelled by the user")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
