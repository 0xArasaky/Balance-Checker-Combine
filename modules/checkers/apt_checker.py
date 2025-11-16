import httpx
from loguru import logger
from typing import Dict, Optional, List
from modules.utils.logger import error_log, info_log

APTOS_API_BASE = "https://api.mainnet.aptoslabs.com/v1"
APTOS_GRAPHQL_URL = f"{APTOS_API_BASE}/graphql"
APTOS_VIEW_URL = f"{APTOS_API_BASE}/view"
APTOS_PRICE_URL = f"{APTOS_API_BASE}/analytics/token/historical_prices"

APT_ADDRESS = "0x1::aptos_coin::AptosCoin"
def _get_fungible_assets(address: str, proxy: Optional[str] = None, timeout: int = 30) -> Optional[List[Dict]]:
    query = """
    query getFungibleAssetBalances($where: current_fungible_asset_balances_bool_exp, $order_by: [current_fungible_asset_balances_order_by!]) {
      current_fungible_asset_balances(where: $where, order_by: $order_by, limit: 100) {
        amount
        asset_type
        metadata {
          decimals
          name
          symbol
          asset_type
        }
      }
    }
    """

    variables = {
        "where": {
            "_and": [
                {
                    "metadata": {
                        "asset_type": {
                            "_is_null": False
                        }
                    },
                    "owner_address": {
                        "_eq": address
                    }
                },
                {
                    "is_primary": {
                        "_neq": False
                    }
                }
            ]
        },
        "order_by": {
            "amount": "desc"
        }
    }

    proxies = {"http://": proxy, "https://": proxy} if proxy else None

    try:
        response = httpx.post(
            APTOS_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            proxies=proxies,
            timeout=timeout
        )

        if response.status_code != 200:
            logger.error(f"GraphQL ошибка: {response.status_code}")
            return None

        data = response.json()
        balances = data.get("data", {}).get("current_fungible_asset_balances", [])

        tokens = []
        for balance in balances:
            metadata = balance.get("metadata", {})
            tokens.append({
                "amount": int(balance.get("amount", 0)),
                "decimals": metadata.get("decimals", 0),
                "symbol": metadata.get("symbol", "UNKNOWN"),
                "name": metadata.get("name", "Unknown Token"),
                "asset_type": balance.get("asset_type", "")
            })

        return tokens

    except Exception as e:
        logger.error(f"Ошибка получения токенов: {e}")
        return None

def _get_staked_apt(address: str, proxy: Optional[str] = None, timeout: int = 30) -> Optional[float]:

    query = """
    query getDelegatedStaking($address: String!) {
      delegator_distinct_pool(
        where: {delegator_address: {_eq: $address}}
      ) {
        pool_address
      }
    }
    """

    variables = {"address": address}
    proxies = {"http://": proxy, "https://": proxy} if proxy else None

    try:
        response = httpx.post(
            APTOS_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            proxies=proxies,
            timeout=timeout
        )

        if response.status_code != 200:
            return None

        data = response.json()
        pools = data.get("data", {}).get("delegator_distinct_pool", [])

        if not pools:
            return 0.0

        total_staked = 0

        for pool_info in pools:
            pool_address = pool_info.get("pool_address")

            view_payload = {
                "function": "0x1::delegation_pool::get_stake",
                "type_arguments": [],
                "arguments": [pool_address, address]
            }

            view_response = httpx.post(
                APTOS_VIEW_URL,
                json=view_payload,
                proxies=proxies,
                timeout=timeout
            )

            if view_response.status_code == 200:
                result = view_response.json()
                if result and len(result) > 0:
                    active_stake = int(result[0])
                    total_staked += active_stake

        return total_staked / (10 ** 8)

    except Exception as e:
        logger.error(f"Ошибка получения застейканного APT: {e}")
        return None

def _get_token_price(asset_type: str, proxy: Optional[str] = None, timeout: int = 30) -> Optional[float]:
    proxies = {"http://": proxy, "https://": proxy} if proxy else None

    try:
        response = httpx.get(
            APTOS_PRICE_URL,
            params={"address": asset_type, "lookback": "all"},
            proxies=proxies,
            timeout=timeout
        )

        if response.status_code != 200:
            return None

        data = response.json()
        price_data = data.get("data", [])

        if not price_data:
            return None

        latest = price_data[0]
        price_usd = latest.get("price_usd", 0)

        return float(price_usd) if price_usd else None

    except Exception as e:
        logger.debug(f"Ошибка получения цены для {asset_type[:50]}: {e}")
        return None

def get_apt_balance(
    address: str,
    proxy_dict: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    wallet_info: Optional[str] = None,
    collect_tokens: bool = False,
    min_token_value: float = 1.0
) -> Dict[str, any]:
    proxy_str = None
    if proxy_dict and 'http://' in proxy_dict:
        proxy_str = proxy_dict['http://']
    elif proxy_dict and 'https://' in proxy_dict:
        proxy_str = proxy_dict['https://']

    result = check_aptos_balance(address, proxy_str, timeout, collect_tokens, min_token_value)

    if wallet_info:
        if result.get('error'):
            error_log(f"{wallet_info} → Ошибка: {result['error']}")
        else:
            tokens_data = result.get('tokens')
            if tokens_data and tokens_data.get('error') is None:
                tokens_list = [f"{symbol}: ${value:,.2f}" for symbol, value in tokens_data.items() if symbol != "error"]
                info_log(f"{wallet_info} → Токены: {', '.join(tokens_list)}")

            apt_bal = result.get('apt_balance', 0)
            other_bal = result.get('other_tokens_balance', 0)
            staked_bal = result.get('staked_apt_balance', 0)
            total_bal = result.get('total_balance', 0)

            info_log(
                f"{wallet_info} → "
                f"APT: ${apt_bal:,.2f} | "
                f"Другие токены: ${other_bal:,.2f} | "
                f"APT в стейкинге: ${staked_bal:,.2f} | "
                f"Итого: ${total_bal:,.2f}"
            )

    return result

def _process_token_data(
    token_details: List[Dict],
    min_value: float = 1.0
) -> Optional[Dict[str, float]]:
    try:
        tokens_by_symbol = {}

        for token in token_details:
            symbol = token["symbol"]
            value = token["value"]
            name = token["name"]
            asset_type = token["asset_type"]

            if symbol not in tokens_by_symbol:
                tokens_by_symbol[symbol] = []
            tokens_by_symbol[symbol].append((value, name, asset_type))

        final_tokens = {}

        for symbol, details_list in tokens_by_symbol.items():
            if len(details_list) == 1:
                value, _, _ = details_list[0]
                final_tokens[symbol] = value
            else:
                for value, name, asset_type in details_list:
                    if name and name != "Unknown Token":
                        token_key = f"{symbol} ({name})"
                        if token_key in final_tokens:
                            short_addr = f"{asset_type[:6]}...{asset_type[-4:]}" if len(asset_type) > 12 else asset_type
                            token_key = f"{symbol} ({short_addr})"
                    else:
                        short_addr = f"{asset_type[:6]}...{asset_type[-4:]}" if len(asset_type) > 12 else asset_type
                        token_key = f"{symbol} ({short_addr})"

                    final_tokens[token_key] = final_tokens.get(token_key, 0) + value

        result = {}
        other_total = 0.0

        for token_key, total_value in final_tokens.items():
            if total_value >= min_value:
                result[token_key] = round(total_value, 2)
            else:
                other_total += total_value

        if other_total > 0:
            result["Other"] = round(other_total, 2)

        result["error"] = None
        return result

    except Exception as e:
        error_log(f"Ошибка обработки токенов APT: {str(e)}")
        return {"error": "ERROR"}

def check_aptos_balance(
    address: str,
    proxy: Optional[str] = None,
    timeout: int = 30,
    collect_tokens: bool = False,
    min_token_value: float = 1.0
) -> Dict:

    try:
        tokens = _get_fungible_assets(address, proxy, timeout)

        if tokens is None:
            return {
                "apt_balance": 0.0,
                "other_tokens_balance": 0.0,
                "staked_apt_balance": 0.0,
                "total_balance": 0.0,
                "tokens": None,
                "error": "API_ERROR"
            }

        apt_token = None
        other_tokens = []

        for token in tokens:
            if token["asset_type"] == APT_ADDRESS:
                apt_token = token
            else:
                other_tokens.append(token)

        apt_price = _get_token_price(APT_ADDRESS, proxy, timeout)

        if not apt_price:
            logger.warning("Не удалось получить цену APT")
            return {
                "apt_balance": 0.0,
                "other_tokens_balance": 0.0,
                "staked_apt_balance": 0.0,
                "total_balance": 0.0,
                "tokens": None,
                "error": "APT_PRICE_ERROR"
            }

        apt_balance_usd = 0.0
        if apt_token:
            apt_amount = apt_token["amount"] / (10 ** apt_token["decimals"])
            apt_balance_usd = apt_amount * apt_price

        token_details = []

        if collect_tokens and apt_token and apt_balance_usd > 0:
            token_details.append({
                "symbol": apt_token["symbol"],
                "name": apt_token["name"],
                "value": apt_balance_usd,
                "asset_type": apt_token["asset_type"]
            })

        other_tokens_balance_usd = 0.0

        for token in other_tokens:
            if token["amount"] == 0:
                continue

            token_price = _get_token_price(token["asset_type"], proxy, timeout)

            if token_price:
                token_amount = token["amount"] / (10 ** token["decimals"])
                token_value = token_amount * token_price
                other_tokens_balance_usd += token_value

                logger.debug(f"  {token['symbol']}: {token_amount:.4f} × ${token_price:.6f} = ${token_value:.2f}")

                if collect_tokens and token_value > 0:
                    token_details.append({
                        "symbol": token["symbol"],
                        "name": token["name"],
                        "value": token_value,
                        "asset_type": token["asset_type"]
                    })

        staked_apt_amount = _get_staked_apt(address, proxy, timeout)
        if staked_apt_amount is None:
            return {
                "apt_balance": 0.0,
                "other_tokens_balance": 0.0,
                "staked_apt_balance": 0.0,
                "total_balance": 0.0,
                "tokens": None,
                "error": "API_ERROR"
            }

        staked_apt_balance_usd = staked_apt_amount * apt_price

        total_balance = apt_balance_usd + other_tokens_balance_usd + staked_apt_balance_usd

        tokens_data = None
        if collect_tokens:
            tokens_data = _process_token_data(token_details, min_token_value)

        return {
            "apt_balance": apt_balance_usd,
            "other_tokens_balance": other_tokens_balance_usd,
            "staked_apt_balance": staked_apt_balance_usd,
            "total_balance": total_balance,
            "tokens": tokens_data,
            "error": None
        }

    except Exception as e:
        logger.error(f"Критическая ошибка проверки APT баланса: {e}")
        return {
            "apt_balance": 0.0,
            "other_tokens_balance": 0.0,
            "staked_apt_balance": 0.0,
            "total_balance": 0.0,
            "tokens": None,
            "error": "CRITICAL_ERROR"
        }
