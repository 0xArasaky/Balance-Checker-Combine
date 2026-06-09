"""
OKX Checker - получение баланса с биржи OKX

Использует OKX API v5 для получения баланса со всех счетов:
- Trading Account (спот, маржа, фьючерсы, опционы)
- Funding Account (кошелек для депозитов/выводов)
- Savings (Simple Earn)
"""

import hmac
import base64
import hashlib
from datetime import datetime
from typing import Dict, Optional, List
import httpx

from modules.utils.logger import info_log, error_log, warning_log, debug_log

# OKX API
BASE_URL = "https://www.okx.com"


def generate_signature(secret_key: str, timestamp: str, method: str, request_path: str, body: str = "") -> str:
    """
    Генерирует подпись для OKX API

    Args:
        secret_key: Секретный ключ API
        timestamp: UTC timestamp в ISO формате
        method: HTTP метод (GET, POST, etc.)
        request_path: Путь запроса (например /api/v5/account/balance)
        body: Тело запроса (для POST)

    Returns:
        Base64 encoded HMAC SHA256 подпись
    """
    # Конкатенация: timestamp + method + requestPath + body
    message = timestamp + method + request_path + body

    # HMAC SHA256 подпись
    mac = hmac.new(
        bytes(secret_key, encoding='utf-8'),
        bytes(message, encoding='utf-8'),
        digestmod=hashlib.sha256
    )

    # Base64 кодирование
    signature = base64.b64encode(mac.digest()).decode()

    return signature


def make_request(
    api_key: str,
    secret_key: str,
    passphrase: str,
    endpoint: str,
    timeout: int = 30
) -> dict:
    """
    Делает аутентифицированный запрос к OKX API

    Args:
        api_key: API ключ
        secret_key: Секретный ключ
        passphrase: Passphrase
        endpoint: Путь эндпоинта (например /api/v5/account/balance)
        timeout: Таймаут запроса

    Returns:
        JSON ответ API или None при ошибке
    """
    try:
        # Генерация timestamp в ISO формате
        timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'

        # Генерация подписи
        method = "GET"
        signature = generate_signature(secret_key, timestamp, method, endpoint)

        # Заголовки для аутентификации
        headers = {
            "OK-ACCESS-KEY": api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": passphrase,
            "Content-Type": "application/json"
        }

        # Запрос к API
        url = BASE_URL + endpoint

        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    except Exception:
        return None


def get_currency_price(currency: str, timeout: int = 30) -> float:
    """
    Получает цену валюты в USD через публичный API (без аутентификации)

    Args:
        currency: Код валюты (например BTC, ETH)
        timeout: Таймаут запроса

    Returns:
        Цена в USD или 0.0 при ошибке
    """
    try:
        # Для стейблкоинов возвращаем 1.0
        if currency in ["USDT", "USDC", "USDD", "DAI", "TUSD", "USDP"]:
            return 1.0

        # Формируем пару для запроса
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
    """
    Получает цены ВСЕХ токенов за один запрос (оптимизация)

    Использует /api/v5/market/tickers?instType=SPOT для получения всех спот пар.
    Извлекает цены из пар вида XXX-USDT.

    Args:
        timeout: Таймаут запроса

    Returns:
        Словарь {currency: price_in_usdt}
        Например: {"BTC": 95000.0, "ETH": 3500.0, "USDT": 1.0}
    """
    try:
        url = f"{BASE_URL}/api/v5/market/tickers?instType=SPOT"

        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()

            data = response.json()

            if data.get("code") != "0":
                return {}

            tickers = data.get("data", [])

            # Создаем словарь цен
            prices_dict = {}

            for ticker in tickers:
                inst_id = ticker.get("instId", "")

                # Обрабатываем только пары с USDT
                if inst_id.endswith("-USDT"):
                    # Извлекаем базовый актив (BTC из BTC-USDT)
                    base_currency = inst_id[:-5]  # Убираем "-USDT"
                    price = float(ticker.get("last", 0))

                    if price > 0:
                        prices_dict[base_currency] = price

            # USDT = 1.0
            prices_dict["USDT"] = 1.0

            # Другие стейблкоины тоже = 1.0 (на случай если их нет в парах)
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
    """
    Получить токены из Trading Account (спот, маржа, фьючерсы, опционы)

    Использует GET /api/v5/account/balance

    Args:
        api_key: API ключ
        secret_key: Секретный ключ
        passphrase: Passphrase
        timeout: Таймаут запроса

    Returns:
        Список словарей с токенами: [{"asset": "BTC", "amount": 1.5, "category": "Trading"}, ...]
        или None при ошибке
    """
    try:
        endpoint = "/api/v5/account/balance"
        data = make_request(api_key, secret_key, passphrase, endpoint, timeout)

        if not data or data.get("code") != "0":
            debug_log("Ошибка получения Trading токенов")
            return None

        balance_data = data.get("data", [])
        if not balance_data:
            return []

        # Извлекаем детали токенов
        details = balance_data[0].get("details", [])
        tokens = []

        for detail in details:
            ccy = detail.get("ccy", "")
            # Баланс = availBal (доступный) + другие поля
            avail_bal = float(detail.get("availBal", 0))
            frozen_bal = float(detail.get("frozenBal", 0))
            eq = float(detail.get("eq", 0))  # Equity (общая сумма)

            # Используем equity как общий баланс
            total_amount = eq

            # Пропускаем токены с нулевым балансом
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
    """
    Получить токены из Funding Account (кошелек для депозитов/выводов)

    Использует GET /api/v5/asset/balances

    Args:
        api_key: API ключ
        secret_key: Секретный ключ
        passphrase: Passphrase
        timeout: Таймаут запроса

    Returns:
        Список словарей с токенами: [{"asset": "USDT", "amount": 100.0, "category": "Funding"}, ...]
        или None при ошибке
    """
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

            # Пропускаем токены с нулевым балансом
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
    """
    Получить токены из Simple Earn (Savings)

    Использует GET /api/v5/finance/savings/balance

    Args:
        api_key: API ключ
        secret_key: Секретный ключ
        passphrase: Passphrase
        timeout: Таймаут запроса

    Returns:
        Список словарей с токенами: [{"asset": "BTC", "amount": 0.5, "category": "Savings"}, ...]
        или None при ошибке
    """
    try:
        endpoint = "/api/v5/finance/savings/balance"
        data = make_request(api_key, secret_key, passphrase, endpoint, timeout)

        if not data or data.get("code") != "0":
            # Savings может быть пустым - это нормально
            return []

        balance_data = data.get("data", [])
        if not balance_data:
            return []

        tokens = []

        for item in balance_data:
            ccy = item.get("ccy", "")
            amt = float(item.get("amt", 0))

            # Пропускаем токены с нулевым балансом
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
    """
    Обработать детали токенов в статистику с группировкой и категориями

    Группирует токены по ключу "symbol (category)".
    Разделяет на отдельные токены (>= min_value) и категорию "Other" (< min_value).

    Args:
        token_details: Список словарей с деталями токенов
            [{"asset": "BTC", "value": 100.0, "category": "Trading"}, ...]
        min_value: Минимальная стоимость токена в USD для отдельного учета

    Returns:
        Словарь с токенами:
        {
            "BTC (Trading)": 100.50,
            "USDT (Funding)": 75.46,
            "Other": 2.13,
            "error": None
        }
    """
    try:
        # Группируем токены по ключу "asset (category)"
        # Формат: {token_key: value, ...}
        tokens_by_key = {}

        for token in token_details:
            asset = token["asset"]
            value = token["value"]
            category = token["category"]

            # Создаем уникальный ключ: "BTC (Trading)"
            token_key = f"{asset} ({category})"

            # Суммируем если уже есть такой ключ
            tokens_by_key[token_key] = tokens_by_key.get(token_key, 0) + value

        # Разделяем на отдельные токены и "Other"
        result = {}
        other_total = 0.0

        for token_key, total_value in tokens_by_key.items():
            if total_value >= min_value:
                result[token_key] = round(total_value, 2)
            else:
                other_total += total_value

        # Добавляем категорию "Other" если есть мелкие токены
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
    """
    Получает баланс Trading Account (спот, маржа, фьючерсы, опционы)

    Returns:
        Словарь с балансом в USD
    """
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
    """
    Получает баланс Funding Account (кошелек для депозитов/выводов)

    Returns:
        Словарь с балансом в USD
    """
    endpoint = "/api/v5/asset/balances"
    data = make_request(api_key, secret_key, passphrase, endpoint, timeout)

    if not data or data.get("code") != "0":
        return {"balance": 0.0, "error": "API_ERROR"}

    balance_data = data.get("data", [])
    if not balance_data:
        return {"balance": 0.0, "error": None}

    total_usd = 0.0

    # Суммируем баланс всех валют
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
    """
    Получает баланс Simple Earn (Savings)

    Returns:
        Словарь с балансом в USD
    """
    endpoint = "/api/v5/finance/savings/balance"
    data = make_request(api_key, secret_key, passphrase, endpoint, timeout)

    if not data or data.get("code") != "0":
        # Возможно нет savings, это нормально
        return {"balance": 0.0, "error": None}

    balance_data = data.get("data", [])
    if not balance_data:
        return {"balance": 0.0, "error": None}

    total_usd = 0.0

    # Суммируем баланс всех валют в savings
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
    """
    Получает общий баланс со ВСЕХ счетов OKX

    Args:
        api_key: API ключ OKX
        secret_key: Секретный ключ OKX
        passphrase: Passphrase OKX
        proxy_dict: Словарь с прокси (не используется для OKX)
        timeout: Таймаут запроса в секундах
        wallet_info: Строка с информацией о кошельке для логов
        collect_tokens: Собирать ли статистику токенов
        min_token_value: Минимальная стоимость токена для отдельного учета

    Returns:
        Словарь с балансом: {
            "total_balance": float,
            "tokens": dict или None,
            "error": str или None
        }
    """
    try:
        # ====================================================================
        # СБОР ТОКЕНОВ (если запрошено)
        # ====================================================================
        tokens_data = None

        if collect_tokens:
            # Собираем токены из всех источников
            all_tokens = []

            # 1. Trading Account токены
            trading_tokens = _get_trading_tokens(api_key, secret_key, passphrase, timeout)
            if trading_tokens:
                all_tokens.extend(trading_tokens)

            # 2. Funding Account токены
            funding_tokens = _get_funding_tokens(api_key, secret_key, passphrase, timeout)
            if funding_tokens:
                all_tokens.extend(funding_tokens)

            # 3. Savings токены
            savings_tokens = _get_savings_tokens(api_key, secret_key, passphrase, timeout)
            if savings_tokens:
                all_tokens.extend(savings_tokens)

            # Получаем все цены одним запросом (оптимизация)
            try:
                prices_dict = get_all_prices(timeout)

                if not prices_dict:
                    debug_log("Не удалось получить цены токенов OKX")
                    tokens_data = {"error": "PRICE_ERROR"}
                else:
                    # Конвертируем токены в USD
                    token_details = []

                    for token in all_tokens:
                        asset = token["asset"]
                        amount = token["amount"]
                        category = token["category"]

                        # Получаем цену
                        price_usdt = prices_dict.get(asset, 0)

                        if price_usdt > 0:
                            value_usd = amount * price_usdt

                            # Собираем данные для обработки
                            token_details.append({
                                "asset": asset,
                                "value": value_usd,
                                "category": category
                            })

                    # Обрабатываем токены через функцию группировки
                    tokens_data = _process_okx_tokens(token_details, min_token_value)

                    # Логируем токены если есть wallet_info
                    if wallet_info and tokens_data and tokens_data.get("error") is None:
                        tokens_list = [f"{symbol}: ${value:,.2f}" for symbol, value in tokens_data.items() if symbol != "error"]
                        if tokens_list:
                            info_log(f"{wallet_info} → Токены: {', '.join(tokens_list)}")

            except Exception as e:
                debug_log(f"Ошибка получения цен токенов OKX: {str(e)}")
                tokens_data = {"error": "PRICE_ERROR"}

        # ====================================================================
        # ПОЛУЧЕНИЕ ОБЩЕГО БАЛАНСА
        # ====================================================================

        # 1. Trading Account (спот, маржа, фьючерсы, опционы)
        trading_result = get_trading_balance(api_key, secret_key, passphrase, timeout)
        trading_balance = trading_result["balance"]

        # 2. Funding Account (кошелек)
        funding_result = get_funding_balance(api_key, secret_key, passphrase, timeout)
        funding_balance = funding_result["balance"]

        # 3. Savings (Simple Earn)
        savings_result = get_savings_balance(api_key, secret_key, passphrase, timeout)
        savings_balance = savings_result["balance"]

        # Проверка на ошибки
        if trading_result.get("error"):
            error_log(f"{wallet_info} → Ошибка Trading Account: {trading_result['error']}")
            return {
                "total_balance": 0.0,
                "tokens": None,
                "error": "TRADING_ERROR"
            }

        # Funding и Savings ошибки не критичные (могут быть пустыми)

        # Общий баланс
        total_balance = trading_balance + funding_balance + savings_balance

        # Вывод в лог (только если не собирали токены, чтобы не дублировать)
        if not collect_tokens and wallet_info:
            info_log(f"{wallet_info} → Итого: ${total_balance:,.2f}")
        elif collect_tokens and wallet_info:
            # Если собирали токены, выводим баланс после токенов
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
