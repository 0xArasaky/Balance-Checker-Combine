# Whether to use proxies for requests
USE_PROXY = True

# Maximum number of parallel threads when using proxies
# 0 or None = use all available proxies
# > 0 = limit parallel requests to the specified number
PROXY_MAX_WORKERS = 5

# Delay between requests (seconds), used when proxies are NOT enabled
REQUEST_DELAY = 3

# Delay between requests when using proxies (seconds)
PROXY_REQUEST_DELAY = 10

# Delay on proxy request failure (seconds)
PROXY_RETRY_DELAY = 10

# HTTP request timeout (seconds)
REQUEST_TIMEOUT = 30

# Maximum retry count for exchange accounts
# Wallet checks still use proxy rotation/retries in the processing loop.
MAX_EXCHANGE_RETRIES = 5

# Sheets to process
# Possible values: "EVM", "SOL", "BTC", "APT", "OKX", "BINANCE", "BYBIT", "BACKPACK", "KUCOIN", "MEXC", "GATE"
ENABLED_SHEETS = ["EVM", "SOL", "BTC", "APT", "OKX", "BINANCE", "BYBIT", "BACKPACK", "KUCOIN", "MEXC", "GATE"]

# Minimum token value in USD to track separately in statistics
# Applies to EVM, SOL and APT wallets
# Tokens below this value will be summed into the "Other" category
MIN_TOKEN_VALUE_TO_TRACK = 1

# Minimum token value in USD to track separately in exchange statistics
# Applies to all centralized exchanges (Binance, OKX, etc.)
# Tokens below this value will be summed into the "Other" category
MIN_EXCHANGE_TOKEN_VALUE_TO_TRACK = 0.001

# Proxy selection: random (True) or sequential (False)
RANDOM_PROXY_SELECTION = True

# Verify proxies before use
VERIFY_PROXIES = False

# Proxy verification timeout (seconds)
PROXY_VERIFY_TIMEOUT = 10

# Proxy verification thread count
PROXY_VERIFY_THREADS = 10

# Proxy file
PROXY_FILE = "proxies.txt"

# Wallet data file
DATA_FILE = "data.xlsx"

# Output directory for results
OUTPUT_DIR = "analyses"
