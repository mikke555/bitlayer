import json
from sys import stderr

from loguru import logger

logger.remove()
logger.add(
    stderr,
    format="<white>{time:HH:mm:ss}</white> | <level>{message}</level>",
)


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
    "bitlayer": {
        # "rpc": "https://rpc.bitlayer.org",
        "rpc": "https://rpc.ankr.com/bitlayer",
        "explorer": "https://www.btrscan.com",
        "token": "BTC",
        "chain_id": 200901,
    },
}


WBTC = "0xfF204e2681A6fA0e2C3FaDe68a1B28fb90E4Fc5F"
BITUSD = "0x07373d112edc4570b46996ad1187bc4ac9fb5ed0"

OWLTO = "0xa9d27096bae2f47caa03ae6a1692119c7d19b4b0"
BITLAYER_LOTTERY = "0x1fdaca95c6ba567044ea4f4c977897bebfa16b41"
BITCOW = "0xf42f777538911510a38c80ad28b5e358a110b88a"
AVALON = "0x5a4247763709c251c8da359674d5c362fdac626d"
LAYERBANK = "0xf1e25704e75da0496b46bf4e3856c5480a3c247f"


INFINITE_AMOUNT = (
    115792089237316195423570985008687907853269984665640564039457584007913129639935
)


with open("data/abi/ERC20.json") as f:
    ERC20_ABI = json.load(f)

with open("data/abi/BitCow.json") as f:
    BITCOW_ABI = json.load(f)
