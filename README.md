##  🚀 Installation
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 🔧 General Settings

| Setting                  | Description                                                 | Default Value       |
|--------------------------|-------------------------------------------------------------|---------------------|
| **SHUFFLE_WALLETS**      | Randomize the order of wallets.                             | `False`             |
| **USE_PROXY**            | Use proxy servers for making HTTP requests.                 | `True`              |
| **RETRY_COUNT**          | Number of retries on transaction failure.                   | `1`                 |
| **SLEEP_BETWEEN_WALLETS**| Pause duration (in seconds) between wallets.                | `[10, 20]`          |
| **SLEEP_BETWEEN_ACTIONS**| Pause duration (in seconds) between actions.                | `[10, 20]`          |
| **MIN_BTC_BALANCE**      | Minimum BTC balance required to proceed with a transaction. | `0.000002` (~$0.20) |

---

## ⚙️ Module-Specific Settings

### **Bitlayer**

| Setting                  | Description                                         | Default Value       |
|--------------------------|-----------------------------------------------------|---------------------|
| **DAYLY_CHECK_IN**       | Perform daily check-ins (requires paying gas fee).  | `True`              |
| **INFINITY_LOOP**        | Keep on claiming daily tasks.                       | `True`              |

### **Wrap BTC**
| Setting         | Description                                                 | Default Value       |
|------------------|------------------------------------------------------------|---------------------|
| **WRAP_VALUE**   | Amount of BTC to wrap per transaction.                     | `[0.0000001, 0.000001]` |
| **WRAP_TX_COUNT**| Number of transactions to perform on each run.             | `[5, 10]`           |

---

### **BitCow**
| Setting            | Description                                               | Default Value       |
|--------------------|-----------------------------------------------------------|---------------------|
| **SWAP_VALUES**    | BTC value range to use for swaps.                         | `[0.000007, 0.0000204]` (~$0.5-$1.5) |
| **SWAP_BACK_VALUES**| Percentage range to swap back.                           | `[95, 99]`          |

---

### **Avalon, LayerBank**
| Setting           | Description                                                | Default Value           |
|--------------------|-----------------------------------------------------------|-------------------------|
| **DEPOSIT_VALUE**  | Amount of BTC to deposit.                                 | `[0.0000001, 0.000001]` |

---

### **MiniBridge**
| Setting              | Description                                                                                     | Default Value        |
|----------------------|-------------------------------------------------------------------------------------------------|----------------------|
| **SEND_VALUE**       | ETH amount range to bridge. Set to `"max"` for sending the entire available balance.            | `[0.00069, 0.00137]` |
| **AVAILABLE_CHAINS** | Inbound chains to use for bridging to Bitlayer. The one with highest balance will be selected.  | `["optimism", "arbitrum", "base"]` |

---

## 📘 Notes
- For settings specified as ranges, a random value within the range will be used each time.
- Ensure balances meet the **MIN_BTC_BALANCE** to keep on doing daily transactions.
