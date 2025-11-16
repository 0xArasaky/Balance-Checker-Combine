import hmac
import base64
import hashlib
from datetime import datetime
from typing import Dict, Optional, List
import httpx

from modules.utils.logger import info_log, error_log, warning_log, debug_log

BASE_URL = "https://www.okx.com"


def generate_signature(secret_key: str, timestamp: str, method: str, request_path: str, body: str = "") -> str:
    message = timestamp + method + request_path + body

    mac = hmac.new(
        bytes(secret_key, encoding='utf-8'),
        bytes(message, encoding='utf-8'),
        digestmod=hashlib.sha256
    )

    signature = base64.b64encode(mac.digest()).decode()

    return signature


def make_request(
    api_key: str,
    secret_key: str,
    passphrase: str,
    endpoint: str,
    timeout: int = 30
) -> dict:
    try:
        timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'

        method = "GET"
        signature = generate_signature(secret_key, timestamp, method, endpoint)

        headers = {
            "OK-ACCESS-KEY": api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": passphrase,
            "Content-Type": "application/json"
        }

        url = BASE_URL + endpoint

        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    except Exception:
        return None


def get_currency_price(currency: str, timeout: int = 30) -> float:
    try:
        if currency in ["USDT", "USDC", "USDD", "DAI", "TUSD", "USDP"]:
            return 1.0

        inst_id = f"{currency}-USDT"

        url = f"{BASE_URL}/api/v5/market/ticker?instId={inst_id}"

        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()

            data = response.json()

            if data.get("code") == "0" and data.get("data"):
                price = float(data["data"][0].get("last", 0))
                return price

            return 0.0

    except Exception:
        return 0.0


def get_all_prices(timeout: int = 30) -> Dict[str, float]:
    try:
        url = f"{BASE_URL}/api/v5/market/tickers?instType=SPOT"

        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()

            data = response.json()

            if data.get("code") != "0":
                return {}

            tickers = data.get("data", [])

            prices_dict = {}

            for ticker in tickers:
                inst_id = ticker.get("instId", "")

                if inst_id.endswith("-USDT"):
                    base_currency = inst_id[:-5]
                    price = float(ticker.get("last", 0))

                    if price > 0:
                        prices_dict[base_currency] = price

            prices_dict["USDT"] = 1.0

            for stable in ["USDC", "USDD", "DAI", "TUSD", "USDP"]:
                if stable not in prices_dict:
                    prices_dict[stable] = 1.0

            return prices_dict

    except Exception as e:
        debug_log(f"Ошибка получения всех цен OKX: {str(e)}")
        return {}


def _get_trading_tokens(
    api_key: str,
    secret_key: str,
    passphrase: str,
    timeout: int
) -> Optional[List[Dict]]:
    try:
        endpoint = "/api/v5/account/balance"
        data = make_request(api_key, secret_key, passphrase, endpoint, timeout)

        if not data or data.get("code") != "0":
            debug_log("Ошибка получения Trading токенов")
            return None

        balance_data = data.get("data", [])
        if not balance_data:
            return []

        details = balance_data[0].get("details", [])
        tokens = []

        for detail in details:
            ccy = detail.get("ccy", "")
            avail_bal = float(detail.get("availBal", 0))
            frozen_bal = float(detail.get("frozenBal", 0))
            eq = float(detail.get("eq", 0))

            total_amount = eq

            if total_amount > 0:
                tokens.append({
                    "asset": ccy,
                    "amount": total_amount,
                    "category": "Trading"
                })

        return tokens

    except Exception as e:
        debug_log(f"Ошибка получения Trading токенов: {str(e)}")
        return None


def _get_funding_tokens(
    api_key: str,
    secret_key: str,
    passphrase: str,
    timeout: int
) -> Optional[List[Dict]]:
    try:
        endpoint = "/api/v5/asset/balances"
        data = make_request(api_key, secret_key, passphrase, endpoint, timeout)

        if not data or data.get("code") != "0":
            debug_log("Ошибка получения Funding токенов")
            return None

        balance_data = data.get("data", [])
        if not balance_data:
            return []

        tokens = []

        for coin in balance_data:
            ccy = coin.get("ccy", "")
            bal = float(coin.get("bal", 0))

            if bal > 0:
                tokens.append({
                    "asset": ccy,
                    "amount": bal,
                    "category": "Funding"
                })

        return tokens

    except Exception as e:
        debug_log(f"Ошибка получения Funding токенов: {str(e)}")
        return None


def _get_savings_tokens(
    api_key: str,
    secret_key: str,
    passphrase: str,
    timeout: int
) -> Optional[List[Dict]]:
    try:
        endpoint = "/api/v5/finance/savings/balance"
        data = make_request(api_key, secret_key, passphrase, endpoint, timeout)

        if not data or data.get("code") != "0":
            return []

        balance_data = data.get("data", [])
        if not balance_data:
            return []

        tokens = []

        for item in balance_data:
            ccy = item.get("ccy", "")
            amt = float(item.get("amt", 0))

            if amt > 0:
                tokens.append({
                    "asset": ccy,
                    "amount": amt,
                    "category": "Savings"
                })

        return tokens

    except Exception as e:
        debug_log(f"Ошибка получения Savings токенов: {str(e)}")
        return None


def _process_okx_tokens(
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
        error_log(f"Ошибка обработки токенов OKX: {str(e)}")
        return {"error": "ERROR"}


def get_trading_balance(
    api_key: str,
    secret_key: str,
    passphrase: str,
    timeout: int = 30
) -> dict:
    endpoint = "/api/v5/account/balance"
    data = make_request(api_key, secret_key, passphrase, endpoint, timeout)

    if not data or data.get("code") != "0":
        return {"balance": 0.0, "error": "API_ERROR"}

    balance_data = data.get("data", [])
    if not balance_data:
        return {"balance": 0.0, "error": None}

    total_eq = float(balance_data[0].get("totalEq", 0))

    return {"balance": total_eq, "error": None}


def get_funding_balance(
    api_key: str,
    secret_key: str,
    passphrase: str,
    timeout: int = 30
) -> dict:
    endpoint = "/api/v5/asset/balances"
    data = make_request(api_key, secret_key, passphrase, endpoint, timeout)

    if not data or data.get("code") != "0":
        return {"balance": 0.0, "error": "API_ERROR"}

    balance_data = data.get("data", [])
    if not balance_data:
        return {"balance": 0.0, "error": None}

    total_usd = 0.0

    for coin in balance_data:
        ccy = coin.get("ccy", "")
        bal = float(coin.get("bal", 0))

        if bal > 0:
            price = get_currency_price(ccy)
            total_usd += bal * price

    return {"balance": total_usd, "error": None}


def get_savings_balance(
    api_key: str,
    secret_key: str,
    passphrase: str,
    timeout: int = 30
) -> dict:
    endpoint = "/api/v5/finance/savings/balance"
    data = make_request(api_key, secret_key, passphrase, endpoint, timeout)

    if not data or data.get("code") != "0":
        return {"balance": 0.0, "error": None}

    balance_data = data.get("data", [])
    if not balance_data:
        return {"balance": 0.0, "error": None}

    total_usd = 0.0

    for item in balance_data:
        ccy = item.get("ccy", "")
        amt = float(item.get("amt", 0))

        if amt > 0:
            price = get_currency_price(ccy)
            total_usd += amt * price

    return {"balance": total_usd, "error": None}


def get_okx_balance(
    api_key: str,
    secret_key: str,
    passphrase: str,
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

            trading_tokens = _get_trading_tokens(api_key, secret_key, passphrase, timeout)
            if trading_tokens:
                all_tokens.extend(trading_tokens)

            funding_tokens = _get_funding_tokens(api_key, secret_key, passphrase, timeout)
            if funding_tokens:
                all_tokens.extend(funding_tokens)

            savings_tokens = _get_savings_tokens(api_key, secret_key, passphrase, timeout)
            if savings_tokens:
                all_tokens.extend(savings_tokens)

            try:
                prices_dict = get_all_prices(timeout)

                if not prices_dict:
                    debug_log("Не удалось получить цены токенов OKX")
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

                    tokens_data = _process_okx_tokens(token_details, min_token_value)

                    if wallet_info and tokens_data and tokens_data.get("error") is None:
                        tokens_list = [f"{symbol}: ${value:,.2f}" for symbol, value in tokens_data.items() if symbol != "error"]
                        info_log(f"{wallet_info} → Токены: {', '.join(tokens_list)}")

            except Exception as e:
                debug_log(f"Ошибка получения цен токенов OKX: {str(e)}")
                tokens_data = {"error": "PRICE_ERROR"}


        trading_result = get_trading_balance(api_key, secret_key, passphrase, timeout)
        trading_balance = trading_result["balance"]

        funding_result = get_funding_balance(api_key, secret_key, passphrase, timeout)
        funding_balance = funding_result["balance"]

        savings_result = get_savings_balance(api_key, secret_key, passphrase, timeout)
        savings_balance = savings_result["balance"]

        if trading_result.get("error"):
            error_log(f"{wallet_info} → Ошибка Trading Account: {trading_result['error']}")
            return {
                "total_balance": 0.0,
                "tokens": None,
                "error": "TRADING_ERROR"
            }


        total_balance = trading_balance + funding_balance + savings_balance

        if not collect_tokens and wallet_info:
            info_log(f"{wallet_info} → Итого: ${total_balance:,.2f}")
        elif collect_tokens and wallet_info:
            info_log(f"{wallet_info} → Итого: ${total_balance:,.2f}")

        return {
            "total_balance": total_balance,
            "tokens": tokens_data,
            "error": None
        }

    except Exception as e:
        error_log(f"{wallet_info} → Неожиданная ошибка: {str(e)}")
        return {
            "total_balance": 0.0,
            "tokens": None,
            "error": "UNKNOWN_ERROR"
        }
