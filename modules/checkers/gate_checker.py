import hmac
import hashlib
import time
from typing import Dict, Optional, List
import requests
import urllib3

from modules.utils.logger import logger, info_log, error_log, debug_log

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _create_signature(
    secret: str,
    method: str,
    url_path: str,
    query_string: str = "",
    payload: str = ""
) -> Dict[str, str]:
    t = str(int(time.time()))

    m = hashlib.sha512()
    m.update(payload.encode('utf-8'))
    hashed_payload = m.hexdigest()

    signature_string = f"{method}\n{url_path}\n{query_string}\n{hashed_payload}\n{t}"

    sign = hmac.new(
        secret.encode('utf-8'),
        signature_string.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()

    return {
        'Timestamp': t,
        'SIGN': sign
    }


def _get_all_prices(
    proxies: Optional[Dict] = None,
    timeout: int = 30
) -> Dict[str, float]:
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        response = requests.get(url, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        prices = {}

        for ticker in data:
            currency_pair = ticker.get('currency_pair', '')
            if '_USDT' in currency_pair:
                currency = currency_pair.replace('_USDT', '')
                last_price = float(ticker.get('last', '0'))
                if last_price > 0:
                    prices[currency] = last_price

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
        url = "https://api.gateio.ws/api/v4/spot/accounts"
        method = "GET"
        url_path = "/api/v4/spot/accounts"

        auth_headers = _create_signature(secret_key, method, url_path)

        headers = {
            "KEY": api_key,
            "Timestamp": auth_headers['Timestamp'],
            "SIGN": auth_headers['SIGN'],
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        tokens = []

        for account in data:
            currency = account.get('currency', '')
            available = float(account.get('available', '0'))
            locked = float(account.get('locked', '0'))
            token_amount = available + locked

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
        url = "https://api.gateio.ws/api/v4/spot/accounts"
        method = "GET"
        url_path = "/api/v4/spot/accounts"

        auth_headers = _create_signature(secret_key, method, url_path)

        headers = {
            "KEY": api_key,
            "Timestamp": auth_headers['Timestamp'],
            "SIGN": auth_headers['SIGN'],
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        prices = _get_all_prices(proxies, timeout)

        total_balance = 0.0

        for account in data:
            currency = account.get('currency', '')
            available = float(account.get('available', '0'))
            locked = float(account.get('locked', '0'))
            token_amount = available + locked

            if token_amount > 0:
                price_usd = prices.get(currency, 0)
                usd_value = token_amount * price_usd
                total_balance += usd_value

        return total_balance

    except Exception as e:
        logger.error(f"Ошибка получения Spot баланса: {str(e)}")
        return None


def _get_futures_balance(
    api_key: str,
    secret_key: str,
    settle: str,
    proxies: Optional[Dict] = None,
    timeout: int = 30
) -> float:
    try:
        url = f"https://api.gateio.ws/api/v4/futures/{settle}/accounts"
        method = "GET"
        url_path = f"/api/v4/futures/{settle}/accounts"

        auth_headers = _create_signature(secret_key, method, url_path)

        headers = {
            "KEY": api_key,
            "Timestamp": auth_headers['Timestamp'],
            "SIGN": auth_headers['SIGN'],
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        total = float(data.get('total', '0'))

        if settle == 'usdt':
            return total
        elif settle == 'btc':
            prices = _get_all_prices(proxies, timeout)
            btc_price = prices.get('BTC', 0)
            return total * btc_price
        else:
            return 0.0

    except Exception as e:
        return 0.0


def _get_futures_tokens(
    api_key: str,
    secret_key: str,
    settle: str,
    proxies: Optional[Dict],
    timeout: int
) -> Optional[List[Dict]]:
    try:
        url = f"https://api.gateio.ws/api/v4/futures/{settle}/accounts"
        method = "GET"
        url_path = f"/api/v4/futures/{settle}/accounts"

        auth_headers = _create_signature(secret_key, method, url_path)

        headers = {
            "KEY": api_key,
            "Timestamp": auth_headers['Timestamp'],
            "SIGN": auth_headers['SIGN'],
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        tokens = []

        total = float(data.get('total', '0'))

        if total > 0:
            currency = settle.upper()
            category = f"Futures {currency}"

            tokens.append({
                "asset": currency,
                "amount": total,
                "category": category
            })

        return tokens

    except Exception as e:
        debug_log(f"Ошибка получения Futures {settle} токенов: {str(e)}")
        return []


def _get_margin_tokens(
    api_key: str,
    secret_key: str,
    proxies: Optional[Dict],
    timeout: int
) -> Optional[List[Dict]]:
    try:
        url = "https://api.gateio.ws/api/v4/margin/accounts"
        method = "GET"
        url_path = "/api/v4/margin/accounts"

        auth_headers = _create_signature(secret_key, method, url_path)

        headers = {
            "KEY": api_key,
            "Timestamp": auth_headers['Timestamp'],
            "SIGN": auth_headers['SIGN'],
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        tokens = []

        for account in data:
            base_currency = account.get('base', {})
            quote_currency = account.get('quote', {})

            if base_currency:
                currency = base_currency.get('currency', '')
                available = float(base_currency.get('available', '0'))
                locked = float(base_currency.get('locked', '0'))
                token_amount = available + locked

                if token_amount > 0:
                    tokens.append({
                        "asset": currency,
                        "amount": token_amount,
                        "category": "Margin"
                    })

            if quote_currency:
                currency = quote_currency.get('currency', '')
                available = float(quote_currency.get('available', '0'))
                locked = float(quote_currency.get('locked', '0'))
                token_amount = available + locked

                if token_amount > 0:
                    tokens.append({
                        "asset": currency,
                        "amount": token_amount,
                        "category": "Margin"
                    })

        return tokens

    except Exception as e:
        debug_log(f"Ошибка получения Margin токенов: {str(e)}")
        return []


def _get_margin_balance(
    api_key: str,
    secret_key: str,
    proxies: Optional[Dict] = None,
    timeout: int = 30
) -> float:
    try:
        url = "https://api.gateio.ws/api/v4/margin/accounts"
        method = "GET"
        url_path = "/api/v4/margin/accounts"

        auth_headers = _create_signature(secret_key, method, url_path)

        headers = {
            "KEY": api_key,
            "Timestamp": auth_headers['Timestamp'],
            "SIGN": auth_headers['SIGN'],
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        prices = _get_all_prices(proxies, timeout)

        total_balance = 0.0

        for account in data:
            currency_pair = account.get('currency_pair', '')
            base_currency = account.get('base', {})
            quote_currency = account.get('quote', {})

            if base_currency:
                currency = base_currency.get('currency', '')
                available = float(base_currency.get('available', '0'))
                locked = float(base_currency.get('locked', '0'))
                token_amount = available + locked

                if token_amount > 0:
                    price_usd = prices.get(currency, 0)
                    total_balance += token_amount * price_usd

            if quote_currency:
                currency = quote_currency.get('currency', '')
                available = float(quote_currency.get('available', '0'))
                locked = float(quote_currency.get('locked', '0'))
                token_amount = available + locked

                if token_amount > 0:
                    price_usd = prices.get(currency, 0)
                    total_balance += token_amount * price_usd

        return total_balance

    except Exception as e:
        return 0.0


def _process_gate_tokens(
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
        error_log(f"Ошибка обработки токенов Gate.io: {str(e)}")
        return {"error": "ERROR"}


def get_gate_balance(
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

            margin_tokens = _get_margin_tokens(api_key, secret_key, proxies_dict, timeout)
            if margin_tokens:
                all_tokens.extend(margin_tokens)

            futures_usdt_tokens = _get_futures_tokens(api_key, secret_key, 'usdt', proxies_dict, timeout)
            if futures_usdt_tokens:
                all_tokens.extend(futures_usdt_tokens)

            futures_btc_tokens = _get_futures_tokens(api_key, secret_key, 'btc', proxies_dict, timeout)
            if futures_btc_tokens:
                all_tokens.extend(futures_btc_tokens)

            try:
                prices_dict = _get_all_prices(proxies_dict, timeout)

                if not prices_dict:
                    debug_log("Не удалось получить цены токенов Gate.io")
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

                    tokens_data = _process_gate_tokens(token_details, min_token_value)

                    if wallet_info and tokens_data and tokens_data.get("error") is None:
                        tokens_list = [f"{symbol}: ${value:,.2f}" for symbol, value in tokens_data.items() if symbol != "error"]
                        info_log(f"{wallet_info} → Токены: {', '.join(tokens_list)}")

            except Exception as e:
                debug_log(f"Ошибка получения цен токенов Gate.io: {str(e)}")
                tokens_data = {"error": "PRICE_ERROR"}


        spot_balance = _get_spot_balance(api_key, secret_key, proxies_dict, timeout)

        if spot_balance is None:
            return {
                "total_balance": 0.0,
                "tokens": None,
                "error": "API_ERROR"
            }

        futures_usdt_balance = _get_futures_balance(api_key, secret_key, 'usdt', proxies_dict, timeout)
        futures_btc_balance = _get_futures_balance(api_key, secret_key, 'btc', proxies_dict, timeout)
        margin_balance = _get_margin_balance(api_key, secret_key, proxies_dict, timeout)

        total_balance = spot_balance + futures_usdt_balance + futures_btc_balance + margin_balance

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
        logger.warning(f"{wallet_info} → Таймаут при запросе к Gate.io API")
        return {
            "total_balance": 0.0,
            "tokens": None,
            "error": "TIMEOUT"
        }
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        logger.error(f"{wallet_info} → HTTP ошибка {status_code} от Gate.io API")
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
