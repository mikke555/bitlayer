import csv
import os
import random
import time
from datetime import datetime

from tqdm import tqdm
from web3 import Web3

from modules.config import logger


def create_csv(path, mode, headers, data):
    directory = os.path.dirname(path)

    dir_exists = os.path.exists(directory)
    file_exists = os.path.exists(path)

    if not dir_exists:
        os.makedirs(directory, exist_ok=True)

    with open(path, mode, encoding="utf-8", newline="") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(headers)
            logger.success(f"{path} created \n")

        writer.writerows(data)


def get_rand_amount(min, max):
    rand_amount = random.uniform(min, max)
    return Web3.to_wei(rand_amount, "ether")


def random_sleep(min_time, max_time):
    duration = random.randint(min_time, max_time)
    time.sleep(duration)


def sleep(from_sleep, to_sleep, label="Sleep until next account", new_line=True):
    x = random.randint(from_sleep, to_sleep)
    desc = datetime.now().strftime("%H:%M:%S")

    for _ in tqdm(
        range(x), desc=desc, bar_format=f"{{desc}} | {label} {{n_fmt}}/{{total_fmt}}"
    ):
        time.sleep(1)

    if new_line:
        print()  # new line break
