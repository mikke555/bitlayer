import csv
import os
import random
import time
from datetime import datetime

import requests
from tqdm import tqdm
from web3 import Web3

import settings
from modules.config import logger


def get_btc_price(symbol="BTC") -> float:
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
    response = requests.get(url)
    data = response.json()

    return float(data["price"])


def check_min_balance(func):
    def wrapper(self, *args, **kwargs):
        balance = self.get_balance()
        min_balance = self.web3.to_wei(settings.MIN_BTC_BALANCE, "ether")

        if balance < min_balance:
            logger.warning(
                f"{self.label} Current balance is under {settings.MIN_BTC_BALANCE:.8f} BTC, skipping \n"
            )
            return
        return func(self, *args, **kwargs)

    return wrapper


def create_csv(path, mode, headers, data):
    directory = os.path.dirname(path)
    dir_exists = os.path.exists(directory)

    if not dir_exists:
        os.makedirs(directory, exist_ok=True)

    with open(path, mode, encoding="utf-8", newline="") as file:
        writer = csv.writer(file)

        if file.tell() == 0:
            writer.writerow(headers)
            logger.success(f"{path} created")

        writer.writerows(data)


def get_rand_amount(min, max):
    rand_amount = random.uniform(min, max)
    return Web3.to_wei(rand_amount, "ether")


def random_sleep(min_time, max_time):
    duration = random.randint(min_time, max_time)
    time.sleep(duration)


def sleep(sleep_time, to_sleep=None, label="Sleep until next account", new_line=True):
    if to_sleep is not None:
        x = random.randint(sleep_time, to_sleep)
    else:
        x = sleep_time

    desc = datetime.now().strftime("%H:%M:%S")

    for _ in tqdm(
        range(x), desc=desc, bar_format=f"{{desc}} | {label} {{n_fmt}}/{{total_fmt}}"
    ):
        time.sleep(1)

    if new_line:
        print()  # new line break
