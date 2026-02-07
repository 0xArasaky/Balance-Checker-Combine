# Balance Checker Combine

Multi-chain wallet and CEX balance checker with web dashboard.

> **[Русская версия](README.ru.md)**

## Setup

### Create and activate virtual environment

```bash
python3 -m venv venv
```

```bash
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
npm install
```

## Data

Update `data.xlsx` with your own data. You don't need to delete unused sheets — just remove them from the `ENABLED_SHEETS` list in settings.

For exchange API keys, read-only permission is sufficient. You can also specify a per-account proxy in the "Specific Proxy" column, set it to "no proxy", or leave it empty to use the global proxy settings.

- Binance: https://www.binance.com/en/my/settings/api-management
- OKX: https://www.okx.com/account/my-api
- Bybit: https://www.bybit.com/app/user/api-management
- Backpack: https://backpack.exchange/portfolio/settings/api-keys
- KuCoin: https://www.kucoin.com/account/api
- MEXC: https://www.mexc.com/user/openapi
- Gate: https://www.gate.com/myaccount/profile/api-key/manage (type: API v4 Key)

## Settings

See `settings.py` — read the comments and adjust configuration before running.

## Proxies

Proxy list goes in `proxies.txt`.

You can get 100 shared proxies for ~$3 at webshare.io.
If running without proxies, consider increasing the request delay.

## Usage

```bash
python main.py
```

## Output

- **Excel:** `analyses/balance_YYYY-MM-DD_HH-MM-SS.xlsx`
- **JSON:** `website/data/balance_YYYY-MM-DD_HH-MM-SS.json`
- **Web:** http://localhost:8000 (mode 2)

## Requirements

- Python 3.8+
- Node.js 14+
