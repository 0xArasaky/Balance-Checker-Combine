import hmac
import hashlib
import time
from typing import Dict, Optional, List
from urllib.parse import urlencode
import httpx

from modules.utils.logger import info_log, error_log, debug_log

BASE_URL = "https://api.bybit.com"


def generate_signature(secret_key: str, timestamp: str, api_key: str, recv_window: str, query_string: str) -> str:
    param_str = timestamp + api_key + recv_window + query_string

    return hmac.new(
        secret_key.encode('utf-8'),
        param_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def get_all_prices(timeout: int = 30) -> Dict[str, float]:
    try:
        url = f"{BASE_URL}/v5/market/tickers?category=spot"

        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()

            data = response.json()

            if data.get("retCode") != 0:
                return {}

            tickers = data.get("result", {}).get("list", [])

            prices_dict = {}

            for ticker in tickers:
                symbol = ticker.get("symbol", "")

                if symbol.endswith("USDT"):
                    base_currency = symbol[:-4]
                    price = float(ticker.get("lastPrice", 0))

                    if price > 0:
                        prices_dict[base_currency] = price

            prices_dict["USDT"] = 1.0

            for stable in ["USDC", "USDD", "DAI", "TUSD", "USDP"]:
                if stable not in prices_dict:
                    prices_dict[stable] = 1.0

            return prices_dict

    except Exception as e:
        debug_log(f"Ошибка получения всех цен Bybit: {str(e)}")
        return {}


def get_account_balance(
    api_key: str,
    secret_key: str,
    account_type: str,
    timeout: int = 30
) -> dict:
    try:
        endpoint = "/v5/account/wallet-balance"

        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        params = {
            'accountType': account_type
        }
        query_string = urlencode(params)

        signature = generate_signature(secret_key, timestamp, api_key, recv_window, query_string)

        headers = {
            'X-BAPI-API-KEY': api_key,
            'X-BAPI-SIGN': signature,
            'X-BAPI-SIGN-TYPE': '2',
            'X-BAPI-TIMESTAMP': timestamp,
            'X-BAPI-RECV-WINDOW': recv_window,
            'Content-Type': 'application/json'
        }

        url = f"{BASE_URL}{endpoint}?{query_string}"

        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()

            if data.get("retCode") != 0:
                return {"balance": 0.0, "error": f"API_ERROR_{data.get('retCode')}"}

            result = data.get("result", {})
            account_list = result.get("list", [])

            if not account_list:
                return {"balance": 0.0, "error": None}

            total_equity = float(account_list[0].get("totalEquity", "0"))

            return {"balance": total_equity, "error": None}

    except httpx.TimeoutException:
        return {"balance": 0.0, "error": "TIMEOUT"}
    except httpx.HTTPStatusError as e:
        return {"balance": 0.0, "error": f"HTTP_{e.response.status_code}"}
    except Exception as e:
        return {"balance": 0.0, "error": "UNKNOWN_ERROR"}


def _get_account_tokens(
    api_key: str,
    secret_key: str,
    account_type: str,
    timeout: int
) -> Optional[List[Dict]]:
    try:
        endpoint = "/v5/account/wallet-balance"

        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        params = {
            'accountType': account_type
        }
        query_string = urlencode(params)

        signature = generate_signature(secret_key, timestamp, api_key, recv_window, query_string)

        headers = {
            'X-BAPI-API-KEY': api_key,
            'X-BAPI-SIGN': signature,
            'X-BAPI-SIGN-TYPE': '2',
            'X-BAPI-TIMESTAMP': timestamp,
            'X-BAPI-RECV-WINDOW': recv_window,
            'Content-Type': 'application/json'
        }

        url = f"{BASE_URL}{endpoint}?{query_string}"

        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()

            if data.get("retCode") != 0:
                debug_log(f"Ошибка получения токенов {account_type}: код {data.get('retCode')}")
                return None

            result = data.get("result", {})
            account_list = result.get("list", [])

            if not account_list:
                return []

            coin_list = account_list[0].get("coin", [])
            tokens = []

            category_map = {
                "UNIFIED": "Unified",
                "SPOT": "Spot",
                "CONTRACT": "Contract"
            }
            category = category_map.get(account_type, account_type)

            for coin_data in coin_list:
                coin_name = coin_data.get("coin", "")
                wallet_balance = float(coin_data.get("walletBalance", 0))

                if wallet_balance > 0:
                    tokens.append({
                        "asset": coin_name,
                        "amount": wallet_balance,
                        "category": category
                    })

            return tokens

    except Exception as e:
        debug_log(f"Ошибка получения токенов {account_type}: {str(e)}")
        return None


def _process_bybit_tokens(
    token_details: List[Dict],
    min_value: float = 1.0
) -> Optional[Dict[str, float]]:
    try:
        tokens_by_key = {}

        for token in token_details:
            asset = token["asset"]
            value = token["value"]
            category = token["category"]

            token_key = f"{asset} ({category})"

            tokens_by_key[token_key] = tokens_by_key.get(token_key, 0) + value

        result = {}
        other_total = 0.0

        for token_key, total_value in tokens_by_key.items():
            if total_value >= min_value:
                result[token_key] = round(total_value, 2)
            else:
                other_total += total_value

        if other_total > 0:
            result["Other"] = round(other_total, 2)

        result["error"] = None
        return result

    except Exception as e:
        error_log(f"Ошибка обработки токенов Bybit: {str(e)}")
        return {"error": "ERROR"}


def get_bybit_balance(
    api_key: str,
    secret_key: str,
    proxy_dict: dict = None,
    timeout: int = 30,
    wallet_info: str = "",
    collect_tokens: bool = False,
    min_token_value: float = 1.0
) -> dict:
    try:
        tokens_data = None

        if collect_tokens:
            all_tokens = []
            account_types = ["UNIFIED", "CONTRACT", "SPOT"]

            for account_type in account_types:
                account_tokens = _get_account_tokens(api_key, secret_key, account_type, timeout)
                if account_tokens:
                    all_tokens.extend(account_tokens)

            try:
                prices_dict = get_all_prices(timeout)

                if not prices_dict:
                    debug_log("Не удалось получить цены токенов Bybit")
                    tokens_data = {"error": "PRICE_ERROR"}
                else:
                    token_details = []

                    for token in all_tokens:
                        asset = token["asset"]
                        amount = token["amount"]
                        category = token["category"]

                        price_usdt = prices_dict.get(asset, 0)

                        if price_usdt > 0:
                            value_usd = amount * price_usdt

                            token_details.append({
                                "asset": asset,
                                "value": value_usd,
                                "category": category
                            })

                    tokens_data = _process_bybit_tokens(token_details, min_token_value)

                    if wallet_info and tokens_data and tokens_data.get("error") is None:
                        tokens_list = [f"{symbol}: ${value:,.2f}" for symbol, value in tokens_data.items() if symbol != "error"]
                        info_log(f"{wallet_info} → Токены: {', '.join(tokens_list)}")

            except Exception as e:
                debug_log(f"Ошибка получения цен токенов Bybit: {str(e)}")
                tokens_data = {"error": "PRICE_ERROR"}


        account_types = ["UNIFIED", "CONTRACT", "SPOT"]
        total_balance = 0.0
        errors = []

        for account_type in account_types:
            result = get_account_balance(api_key, secret_key, account_type, timeout)

            if result.get("error") and result["error"] not in ["TIMEOUT", "UNKNOWN_ERROR"]:
                continue
            elif result.get("error"):
                errors.append(f"{account_type}: {result['error']}")
            else:
                total_balance += result["balance"]

        if errors:
            error_log(f"{wallet_info} → Ошибки: {', '.join(errors)}")

        if not collect_tokens and wallet_info:
            info_log(f"{wallet_info} → Итого: ${total_balance:,.2f}")
        elif collect_tokens and wallet_info:
            info_log(f"{wallet_info} → Итого: ${total_balance:,.2f}")

        return {
            "total_balance": total_balance,
            "tokens": tokens_data,
            "error": None if not errors else "; ".join(errors)
        }

    except Exception as e:
        error_log(f"{wallet_info} → Неожиданная ошибка: {str(e)}")
        return {
            "total_balance": 0.0,
            "tokens": None,
            "error": "UNKNOWN_ERROR"
        }
