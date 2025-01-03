import json
from datetime import datetime
from sys import stderr

from loguru import logger

logger.remove()
logger.add(stderr, format="<white>{time:HH:mm:ss}</white> | <level>{message}</level>")
logger.add(
    f"reports/debug-{datetime.today().strftime('%Y-%m-%d')}.log",
    format="<white>{time:HH:mm:ss}</white> | <level>{message}</level>",
)

# Network data
CHAIN_DATA = {
    "ethereum": {
        "rpc": "https://rpc.ankr.com/eth",
        "explorer": "https://etherscan.io",
        "token": "ETH",
        "chain_id": 1,
    },
    "linea": {
        "rpc": "https://rpc.linea.build",
        "explorer": "https://lineascan.build",
        "token": "ETH",
        "chain_id": 59144,
    },
    "arbitrum": {
        "rpc": "https://rpc.ankr.com/arbitrum",
        "explorer": "https://arbiscan.io",
        "token": "ETH",
        "chain_id": 42161,
    },
    "optimism": {
        "rpc": "https://rpc.ankr.com/optimism",
        "explorer": "https://optimistic.etherscan.io",
        "token": "ETH",
        "chain_id": 10,
    },
    "base": {
        "rpc": "https://mainnet.base.org",
        "explorer": "https://basescan.org",
        "token": "ETH",
        "chain_id": 8453,
    },
    "bitlayer": {
        # "rpc": "https://rpc.bitlayer.org",
        "rpc": "https://rpc.ankr.com/bitlayer",
        "explorer": "https://www.btrscan.com",
        "token": "BTC",
        "chain_id": 200901,
    },
}

# Bitlayer app contracts
BITLAYER_LOTTERY = "0x1fdaca95c6ba567044ea4f4c977897bebfa16b41"
BITLAYER_CHECK_IN = "0x5e63fc3ea7482b77c9750a2e9c649aa93eaf2883"
BITLAYER_MINING_GALA = "0x06b4e9599c38d41a40e4d4278f84039789215b90"

# Dapps on Bitlayer Network
OWLTO = "0xa9d27096bae2f47caa03ae6a1692119c7d19b4b0"
BITCOW = "0xf42f777538911510a38c80ad28b5e358a110b88a"
AVALON = "0x5a4247763709c251c8da359674d5c362fdac626d"
LAYERBANK = "0xf1e25704e75da0496b46bf4e3856c5480a3c247f"

# ERC-20 tokens on Bitlayer Network
WBTC = "0xfF204e2681A6fA0e2C3FaDe68a1B28fb90E4Fc5F"
BITUSD = "0x07373d112edc4570b46996ad1187bc4ac9fb5ed0"

# Hardcoded values from https://minibridge-conf.chaineye.tools/conf.json
MINIBRIDGE_ADDRESS = "0x00000000000007736e2F9aA5630B8c812E1F3fc9"
MIN_SEND_VALUE = 100000000000000  # 0.0001 ETH
MAX_SEND_VALUE = 50000000000000000  # 0.05 ETH
BITLAYER_INTERALID = 832

# Infinite amount for max approve
INFINITE_AMOUNT = (
    115792089237316195423570985008687907853269984665640564039457584007913129639935
)

# ABI
with open("data/abi/ERC20.json") as f:
    ERC20_ABI = json.load(f)

with open("data/abi/BitCow.json") as f:
    BITCOW_ABI = json.load(f)
