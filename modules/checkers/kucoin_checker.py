import base64
import hmac
import hashlib
import time
from typing import Dict, Optional, List
import requests
import urllib3

from modules.utils.logger import logger, info_log, error_log, debug_log

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _get_all_prices(
    proxies: Optional[Dict] = None,
    timeout: int = 30
) -> Dict[str, float]:
    try:
        url = "https://api.kucoin.com/api/v1/market/allTickers"
        response = requests.get(url, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        if data.get('code') != '200000':
            logger.error(f"KuCoin prices API error: {data.get('msg')}")
            return {}

        prices = {}
        tickers = data.get('data', {}).get('ticker', [])

        for ticker in tickers:
            symbol = ticker.get('symbol', '')
            if '-USDT' in symbol:
                currency = symbol.replace('-USDT', '')
                last_price_str = ticker.get('last') or ticker.get('lastTradedPrice') or '0'
                try:
                    last_price = float(last_price_str)
                    if last_price > 0:
                        prices[currency] = last_price
                except (ValueError, TypeError):
                    continue

        prices['USDT'] = 1.0
        prices['USDC'] = 1.0
        prices['DAI'] = 1.0

        return prices

    except Exception as e:
        logger.error(f"Ошибка получения цен токенов: {str(e)}")
        return {}


def _create_signature(
    api_secret: str,
    timestamp: str,
    method: str,
    endpoint: str,
    body: str = ""
) -> str:
    str_to_sign = timestamp + method + endpoint + body

    signature = base64.b64encode(
        hmac.new(
            api_secret.encode('utf-8'),
            str_to_sign.encode('utf-8'),
            hashlib.sha256
        ).digest()
    )

    return signature.decode('utf-8')


def _encrypt_passphrase(api_secret: str, passphrase: str) -> str:
    encrypted = base64.b64encode(
        hmac.new(
            api_secret.encode('utf-8'),
            passphrase.encode('utf-8'),
            hashlib.sha256
        ).digest()
    )

    return encrypted.decode('utf-8')


def _get_spot_balance(
    api_key: str,
    api_secret: str,
    api_passphrase: str,
    proxies: Optional[Dict] = None,
    timeout: int = 30
) -> Optional[float]:
    try:
        url = "https://api.kucoin.com/api/v1/accounts"
        method = "GET"
        endpoint = "/api/v1/accounts"
        timestamp = str(int(time.time() * 1000))

        signature = _create_signature(api_secret, timestamp, method, endpoint)
        encrypted_passphrase = _encrypt_passphrase(api_secret, api_passphrase)

        headers = {
            "KC-API-KEY": api_key,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": timestamp,
            "KC-API-PASSPHRASE": encrypted_passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        if data.get('code') != '200000':
            logger.error(f"KuCoin Spot API error: {data.get('msg')}")
            return None

        accounts = data.get('data', [])

        prices = _get_all_prices(proxies, timeout)

        total_balance = 0.0

        for account in accounts:
            token_amount = float(account.get('balance', '0'))
            currency = account.get('currency', 'UNKNOWN')
            account_type = account.get('type', 'UNKNOWN')

            if token_amount > 0:
                price_usd = prices.get(currency, 0)
                usd_value = token_amount * price_usd
                total_balance += usd_value

        return total_balance

    except Exception as e:
        logger.error(f"Ошибка получения Spot баланса: {str(e)}")
        return None


def _get_cross_margin_balance(
    api_key: str,
    api_secret: str,
    api_passphrase: str,
    proxies: Optional[Dict] = None,
    timeout: int = 30
) -> float:
    try:
        url = "https://api.kucoin.com/api/v3/margin/accounts"
        method = "GET"
        endpoint = "/api/v3/margin/accounts"
        timestamp = str(int(time.time() * 1000))

        signature = _create_signature(api_secret, timestamp, method, endpoint)
        encrypted_passphrase = _encrypt_passphrase(api_secret, api_passphrase)

        headers = {
            "KC-API-KEY": api_key,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": timestamp,
            "KC-API-PASSPHRASE": encrypted_passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        if data.get('code') != '200000':
            return 0.0

        accounts = data.get('data', [])
        total_balance = 0.0

        for account in accounts:
            total_asset = float(account.get('totalAsset', '0'))
            total_balance += total_asset

        return total_balance

    except Exception as e:
        return 0.0


def _get_isolated_margin_balance(
    api_key: str,
    api_secret: str,
    api_passphrase: str,
    proxies: Optional[Dict] = None,
    timeout: int = 30
) -> float:
    try:
        url = "https://api.kucoin.com/api/v3/isolated/accounts"
        method = "GET"
        endpoint = "/api/v3/isolated/accounts"
        timestamp = str(int(time.time() * 1000))

        signature = _create_signature(api_secret, timestamp, method, endpoint)
        encrypted_passphrase = _encrypt_passphrase(api_secret, api_passphrase)

        headers = {
            "KC-API-KEY": api_key,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": timestamp,
            "KC-API-PASSPHRASE": encrypted_passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        if data.get('code') != '200000':
            return 0.0

        assets = data.get('data', {}).get('assets', [])
        total_balance = 0.0

        for asset in assets:
            total_asset = float(asset.get('totalAsset', '0'))
            total_balance += total_asset

        return total_balance

    except Exception as e:
        return 0.0


def _get_futures_balance(
    api_key: str,
    api_secret: str,
    api_passphrase: str,
    proxies: Optional[Dict] = None,
    timeout: int = 30
) -> float:
    try:
        url = "https://api-futures.kucoin.com/api/v1/account-overview"
        method = "GET"
        endpoint = "/api/v1/account-overview"
        timestamp = str(int(time.time() * 1000))

        signature = _create_signature(api_secret, timestamp, method, endpoint)
        encrypted_passphrase = _encrypt_passphrase(api_secret, api_passphrase)

        headers = {
            "KC-API-KEY": api_key,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": timestamp,
            "KC-API-PASSPHRASE": encrypted_passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        if data.get('code') != '200000':
            return 0.0

        account_data = data.get('data', {})
        account_equity = float(account_data.get('accountEquity', '0'))

        return account_equity

    except Exception as e:
        return 0.0


def _get_spot_tokens(
    api_key: str,
    api_secret: str,
    api_passphrase: str,
    proxies: Optional[Dict],
    timeout: int
) -> Optional[List[Dict]]:
    try:
        url = "https://api.kucoin.com/api/v1/accounts"
        method = "GET"
        endpoint = "/api/v1/accounts"
        timestamp = str(int(time.time() * 1000))

        signature = _create_signature(api_secret, timestamp, method, endpoint)
        encrypted_passphrase = _encrypt_passphrase(api_secret, api_passphrase)

        headers = {
            "KC-API-KEY": api_key,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": timestamp,
            "KC-API-PASSPHRASE": encrypted_passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        if data.get('code') != '200000':
            debug_log(f"Ошибка получения Spot токенов: {data.get('msg')}")
            return None

        accounts = data.get('data', [])
        tokens = []

        for account in accounts:
            currency = account.get('currency', '')
            balance = float(account.get('balance', '0'))

            if balance > 0:
                tokens.append({
                    "asset": currency,
                    "amount": balance,
                    "category": "Spot"
                })

        return tokens

    except Exception as e:
        debug_log(f"Ошибка получения Spot токенов: {str(e)}")
        return None


def _get_cross_margin_tokens(
    api_key: str,
    api_secret: str,
    api_passphrase: str,
    proxies: Optional[Dict],
    timeout: int
) -> Optional[List[Dict]]:
    try:
        url = "https://api.kucoin.com/api/v3/margin/accounts"
        method = "GET"
        endpoint = "/api/v3/margin/accounts"
        timestamp = str(int(time.time() * 1000))

        signature = _create_signature(api_secret, timestamp, method, endpoint)
        encrypted_passphrase = _encrypt_passphrase(api_secret, api_passphrase)

        headers = {
            "KC-API-KEY": api_key,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": timestamp,
            "KC-API-PASSPHRASE": encrypted_passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        if data.get('code') != '200000':
            return []

        accounts = data.get('data', [])
        tokens = []

        for account in accounts:
            balances = account.get('balances', [])
            for bal in balances:
                currency = bal.get('currency', '')
                total_balance = float(bal.get('totalBalance', '0'))

                if total_balance > 0:
                    tokens.append({
                        "asset": currency,
                        "amount": total_balance,
                        "category": "Cross Margin"
                    })

        return tokens

    except Exception as e:
        debug_log(f"Ошибка получения Cross Margin токенов: {str(e)}")
        return []


def _get_isolated_margin_tokens(
    api_key: str,
    api_secret: str,
    api_passphrase: str,
    proxies: Optional[Dict],
    timeout: int
) -> Optional[List[Dict]]:
    try:
        url = "https://api.kucoin.com/api/v3/isolated/accounts"
        method = "GET"
        endpoint = "/api/v3/isolated/accounts"
        timestamp = str(int(time.time() * 1000))

        signature = _create_signature(api_secret, timestamp, method, endpoint)
        encrypted_passphrase = _encrypt_passphrase(api_secret, api_passphrase)

        headers = {
            "KC-API-KEY": api_key,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": timestamp,
            "KC-API-PASSPHRASE": encrypted_passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        if data.get('code') != '200000':
            return []

        assets = data.get('data', {}).get('assets', [])
        tokens = []

        for asset in assets:
            balances = asset.get('balances', [])
            for bal in balances:
                currency = bal.get('currency', '')
                total_balance = float(bal.get('totalBalance', '0'))

                if total_balance > 0:
                    tokens.append({
                        "asset": currency,
                        "amount": total_balance,
                        "category": "Isolated Margin"
                    })

        return tokens

    except Exception as e:
        debug_log(f"Ошибка получения Isolated Margin токенов: {str(e)}")
        return []


def _get_futures_tokens(
    api_key: str,
    api_secret: str,
    api_passphrase: str,
    proxies: Optional[Dict],
    timeout: int
) -> Optional[List[Dict]]:
    try:
        url = "https://api-futures.kucoin.com/api/v1/account-overview"
        method = "GET"
        endpoint = "/api/v1/account-overview"
        timestamp = str(int(time.time() * 1000))

        signature = _create_signature(api_secret, timestamp, method, endpoint)
        encrypted_passphrase = _encrypt_passphrase(api_secret, api_passphrase)

        headers = {
            "KC-API-KEY": api_key,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": timestamp,
            "KC-API-PASSPHRASE": encrypted_passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        if data.get('code') != '200000':
            return []

        account_data = data.get('data', {})
        currency = account_data.get('currency', 'USDT')
        account_equity = float(account_data.get('accountEquity', '0'))

        tokens = []
        if account_equity > 0:
            tokens.append({
                "asset": currency,
                "amount": account_equity,
                "category": "Futures"
            })

        return tokens

    except Exception as e:
        debug_log(f"Ошибка получения Futures токенов: {str(e)}")
        return []


def _process_kucoin_tokens(
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
        error_log(f"Ошибка обработки токенов KuCoin: {str(e)}")
        return {"error": "ERROR"}


def get_kucoin_balance(
    api_key: str,
    secret_key: str,
    passphrase: str,
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

            spot_tokens = _get_spot_tokens(api_key, secret_key, passphrase, proxies_dict, timeout)
            if spot_tokens:
                all_tokens.extend(spot_tokens)

            cross_margin_tokens = _get_cross_margin_tokens(api_key, secret_key, passphrase, proxies_dict, timeout)
            if cross_margin_tokens:
                all_tokens.extend(cross_margin_tokens)

            isolated_margin_tokens = _get_isolated_margin_tokens(api_key, secret_key, passphrase, proxies_dict, timeout)
            if isolated_margin_tokens:
                all_tokens.extend(isolated_margin_tokens)

            futures_tokens = _get_futures_tokens(api_key, secret_key, passphrase, proxies_dict, timeout)
            if futures_tokens:
                all_tokens.extend(futures_tokens)

            try:
                prices_dict = _get_all_prices(proxies_dict, timeout)

                if not prices_dict:
                    debug_log("Не удалось получить цены токенов KuCoin")
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

                    tokens_data = _process_kucoin_tokens(token_details, min_token_value)

                    if wallet_info and tokens_data and tokens_data.get("error") is None:
                        tokens_list = [f"{symbol}: ${value:,.2f}" for symbol, value in tokens_data.items() if symbol != "error"]
                        info_log(f"{wallet_info} → Токены: {', '.join(tokens_list)}")

            except Exception as e:
                debug_log(f"Ошибка получения цен токенов KuCoin: {str(e)}")
                tokens_data = {"error": "PRICE_ERROR"}


        spot_balance = _get_spot_balance(api_key, secret_key, passphrase, proxies_dict, timeout)

        if spot_balance is None:
            return {
                "total_balance": 0.0,
                "tokens": None,
                "error": "API_ERROR"
            }

        cross_margin_balance = _get_cross_margin_balance(api_key, secret_key, passphrase, proxies_dict, timeout)
        isolated_margin_balance = _get_isolated_margin_balance(api_key, secret_key, passphrase, proxies_dict, timeout)
        futures_balance = _get_futures_balance(api_key, secret_key, passphrase, proxies_dict, timeout)

        total_balance = spot_balance + cross_margin_balance + isolated_margin_balance + futures_balance

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
        logger.warning(f"{wallet_info} → Таймаут при запросе к KuCoin API")
        return {
            "total_balance": 0.0,
            "tokens": None,
            "error": "TIMEOUT"
        }
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        logger.error(f"{wallet_info} → HTTP ошибка {status_code} от KuCoin API")
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
