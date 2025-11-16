import hmac
import hashlib
import time
from typing import Dict, Optional, List
from urllib.parse import urlencode
import requests
import urllib3

from modules.utils.logger import logger, info_log, error_log, debug_log

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _create_spot_signature(
    secret_key: str,
    params_str: str
) -> str:
    signature = hmac.new(
        secret_key.encode('utf-8'),
        params_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return signature


def _create_futures_signature(
    access_key: str,
    secret_key: str,
    timestamp: str,
    params_str: str = ""
) -> str:
    sign_str = access_key + timestamp + params_str

    signature = hmac.new(
        secret_key.encode('utf-8'),
        sign_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return signature


def _get_all_prices(
    proxies: Optional[Dict] = None,
    timeout: int = 30
) -> Dict[str, float]:
    try:
        url = "https://api.mexc.com/api/v3/ticker/price"
        response = requests.get(url, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        prices = {}

        for ticker in data:
            symbol = ticker.get('symbol', '')
            if symbol.endswith('USDT'):
                currency = symbol.replace('USDT', '')
                price = float(ticker.get('price', '0'))
                if price > 0:
                    prices[currency] = price

        prices['USDT'] = 1.0
        prices['USDC'] = 1.0
        prices['DAI'] = 1.0

        return prices

    except Exception as e:
        logger.error(f"Ошибка получения цен токенов: {str(e)}")
        return {}


def _get_spot_tokens(
    api_key: str,
    secret_key: str,
    proxies: Optional[Dict],
    timeout: int
) -> Optional[List[Dict]]:
    try:
        url = "https://api.mexc.com/api/v3/account"
        timestamp = int(time.time() * 1000)

        params = {
            'timestamp': timestamp,
            'recvWindow': 5000
        }

        params_str = urlencode(params)

        signature = _create_spot_signature(secret_key, params_str)
        params['signature'] = signature

        headers = {
            "X-MEXC-APIKEY": api_key,
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, params=params, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        tokens = []
        balances = data.get('balances', [])

        for balance in balances:
            currency = balance.get('asset', '')
            free = float(balance.get('free', '0'))
            locked = float(balance.get('locked', '0'))
            token_amount = free + locked

            if token_amount > 0:
                tokens.append({
                    "asset": currency,
                    "amount": token_amount,
                    "category": "Spot"
                })

        return tokens

    except Exception as e:
        debug_log(f"Ошибка получения Spot токенов: {str(e)}")
        return None


def _get_spot_balance(
    api_key: str,
    secret_key: str,
    proxies: Optional[Dict] = None,
    timeout: int = 30
) -> Optional[float]:
    try:
        url = "https://api.mexc.com/api/v3/account"
        timestamp = int(time.time() * 1000)

        params = {
            'timestamp': timestamp,
            'recvWindow': 5000
        }

        params_str = urlencode(params)

        signature = _create_spot_signature(secret_key, params_str)
        params['signature'] = signature

        headers = {
            "X-MEXC-APIKEY": api_key,
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, params=params, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        prices = _get_all_prices(proxies, timeout)

        total_balance = 0.0
        balances = data.get('balances', [])

        for balance in balances:
            currency = balance.get('asset', '')
            free = float(balance.get('free', '0'))
            locked = float(balance.get('locked', '0'))
            token_amount = free + locked

            if token_amount > 0:
                price_usd = prices.get(currency, 0)
                usd_value = token_amount * price_usd
                total_balance += usd_value

        return total_balance

    except Exception as e:
        logger.error(f"Ошибка получения Spot баланса: {str(e)}")
        return None


def _get_futures_tokens(
    api_key: str,
    secret_key: str,
    proxies: Optional[Dict],
    timeout: int
) -> Optional[List[Dict]]:
    try:
        url = "https://contract.mexc.com/api/v1/private/account/assets"
        timestamp = str(int(time.time() * 1000))

        signature = _create_futures_signature(api_key, secret_key, timestamp)

        headers = {
            "ApiKey": api_key,
            "Request-Time": timestamp,
            "Signature": signature,
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        if not data.get('success'):
            return []

        tokens = []
        assets = data.get('data', [])

        for asset in assets:
            currency = asset.get('currency', '')
            equity = float(asset.get('equity', '0'))

            if equity > 0:
                tokens.append({
                    "asset": currency,
                    "amount": equity,
                    "category": "Futures"
                })

        return tokens

    except Exception as e:
        debug_log(f"Ошибка получения Futures токенов: {str(e)}")
        return []


def _get_futures_balance(
    api_key: str,
    secret_key: str,
    proxies: Optional[Dict] = None,
    timeout: int = 30
) -> float:
    try:
        url = "https://contract.mexc.com/api/v1/private/account/assets"
        timestamp = str(int(time.time() * 1000))

        signature = _create_futures_signature(api_key, secret_key, timestamp)

        headers = {
            "ApiKey": api_key,
            "Request-Time": timestamp,
            "Signature": signature,
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        if not data.get('success'):
            return 0.0

        total_balance = 0.0
        assets = data.get('data', [])

        for asset in assets:
            currency = asset.get('currency', '')
            equity = float(asset.get('equity', '0'))

            if currency == 'USDT':
                total_balance += equity

        return total_balance

    except Exception as e:
        return 0.0


def _process_mexc_tokens(
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
        error_log(f"Ошибка обработки токенов MEXC: {str(e)}")
        return {"error": "ERROR"}


def get_mexc_balance(
    api_key: str,
    secret_key: str,
    proxy_dict: Optional[Dict] = None,
    timeout: int = 30,
    wallet_info: str = "",
    collect_tokens: bool = False,
    min_token_value: float = 1.0
) -> Dict[str, Optional[float]]:
    try:
        proxies_dict = proxy_dict if proxy_dict else None

        tokens_data = None

        if collect_tokens:
            all_tokens = []

            spot_tokens = _get_spot_tokens(api_key, secret_key, proxies_dict, timeout)
            if spot_tokens:
                all_tokens.extend(spot_tokens)

            futures_tokens = _get_futures_tokens(api_key, secret_key, proxies_dict, timeout)
            if futures_tokens:
                all_tokens.extend(futures_tokens)

            try:
                prices_dict = _get_all_prices(proxies_dict, timeout)

                if not prices_dict:
                    debug_log("Не удалось получить цены токенов MEXC")
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

                    tokens_data = _process_mexc_tokens(token_details, min_token_value)

                    if wallet_info and tokens_data and tokens_data.get("error") is None:
                        tokens_list = [f"{symbol}: ${value:,.2f}" for symbol, value in tokens_data.items() if symbol != "error"]
                        info_log(f"{wallet_info} → Токены: {', '.join(tokens_list)}")

            except Exception as e:
                debug_log(f"Ошибка получения цен токенов MEXC: {str(e)}")
                tokens_data = {"error": "PRICE_ERROR"}


        spot_balance = _get_spot_balance(api_key, secret_key, proxies_dict, timeout)

        if spot_balance is None:
            return {
                "total_balance": 0.0,
                "tokens": None,
                "error": "API_ERROR"
            }

        futures_balance = _get_futures_balance(api_key, secret_key, proxies_dict, timeout)

        total_balance = spot_balance + futures_balance

        if not collect_tokens and wallet_info:
            info_log(f"{wallet_info} → Итого: ${total_balance:,.2f}")
        elif collect_tokens and wallet_info:
            info_log(f"{wallet_info} → Итого: ${total_balance:,.2f}")

        return {
            "total_balance": total_balance,
            "tokens": tokens_data,
            "error": None
        }

    except requests.exceptions.Timeout:
        logger.warning(f"{wallet_info} → Таймаут при запросе к MEXC API")
        return {
            "total_balance": 0.0,
            "tokens": None,
            "error": "TIMEOUT"
        }
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        logger.error(f"{wallet_info} → HTTP ошибка {status_code} от MEXC API")
        return {
            "total_balance": 0.0,
            "tokens": None,
            "error": f"HTTP_{status_code}"
        }
    except Exception as e:
        logger.error(f"{wallet_info} → Неожиданная ошибка: {str(e)}")
        return {
            "total_balance": 0.0,
            "tokens": None,
            "error": "API_ERROR"
        }
