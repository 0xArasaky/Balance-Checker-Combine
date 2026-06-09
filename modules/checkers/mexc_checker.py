"""
Модуль для получения баланса с биржи MEXC.

MEXC использует HMAC SHA256 для аутентификации, но разные форматы для Spot и Futures.
"""

import hmac
import hashlib
import time
from typing import Dict, Optional, List
from urllib.parse import urlencode
import requests
import urllib3

from modules.utils.logger import logger, info_log, error_log, debug_log

# Подавляем предупреждения о непроверенных SSL сертификатах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _create_spot_signature(
    secret_key: str,
    params_str: str
) -> str:
    """
    Создает HMAC SHA256 подпись для MEXC Spot API.

    Args:
        secret_key: Secret ключ
        params_str: Строка параметров запроса

    Returns:
        Hex подпись
    """
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
    """
    Создает HMAC SHA256 подпись для MEXC Futures API.

    Args:
        access_key: Access ключ
        secret_key: Secret ключ
        timestamp: Временная метка
        params_str: Строка параметров (если есть)

    Returns:
        Hex подпись
    """
    # Строка для подписи: accessKey + timestamp + requestParam
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
    """
    Получает цены всех токенов в USDT с MEXC.

    Args:
        proxies: Прокси для requests
        timeout: Таймаут запроса

    Returns:
        Словарь {currency: price_in_usdt}
    """
    try:
        url = "https://api.mexc.com/api/v3/ticker/price"
        response = requests.get(url, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        prices = {}

        for ticker in data:
            symbol = ticker.get('symbol', '')
            # Интересуют только пары с USDT
            if symbol.endswith('USDT'):
                currency = symbol.replace('USDT', '')
                price = float(ticker.get('price', '0'))
                if price > 0:
                    prices[currency] = price

        # Добавляем стейблкоины как 1:1 к USD
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
    """
    Получить детали токенов со Spot аккаунта

    Использует GET /api/v3/account

    Args:
        api_key: API ключ
        secret_key: Secret ключ
        proxies: Прокси для requests
        timeout: Таймаут запроса

    Returns:
        Список словарей с токенами: [{"asset": "BTC", "amount": 1.5, "category": "Spot"}, ...]
        или None при ошибке
    """
    try:
        url = "https://api.mexc.com/api/v3/account"
        timestamp = int(time.time() * 1000)

        # Параметры запроса
        params = {
            'timestamp': timestamp,
            'recvWindow': 5000
        }

        # Формируем строку параметров для подписи (urlencode)
        params_str = urlencode(params)

        # Создаем подпись
        signature = _create_spot_signature(secret_key, params_str)
        params['signature'] = signature

        # Заголовки
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

            # Пропускаем токены с нулевым балансом
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
    """
    Получает баланс Spot аккаунта.

    Args:
        api_key: API ключ
        secret_key: Secret ключ
        proxies: Прокси для requests
        timeout: Таймаут запроса

    Returns:
        float: Баланс Spot в USD
        None: При ошибке API
    """
    try:
        url = "https://api.mexc.com/api/v3/account"
        timestamp = int(time.time() * 1000)

        # Параметры запроса
        params = {
            'timestamp': timestamp,
            'recvWindow': 5000
        }

        # Формируем строку параметров для подписи (urlencode)
        params_str = urlencode(params)

        # Создаем подпись
        signature = _create_spot_signature(secret_key, params_str)
        params['signature'] = signature

        # Заголовки
        headers = {
            "X-MEXC-APIKEY": api_key,
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, params=params, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        # Получаем цены
        prices = _get_all_prices(proxies, timeout)

        total_balance = 0.0
        balances = data.get('balances', [])

        # Конвертируем каждый токен в USD
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
        return None  # Ошибка API


def _get_futures_tokens(
    api_key: str,
    secret_key: str,
    proxies: Optional[Dict],
    timeout: int
) -> Optional[List[Dict]]:
    """
    Получить детали токенов с Futures аккаунта

    Использует GET /api/v1/private/account/assets

    Args:
        api_key: API ключ
        secret_key: Secret ключ
        proxies: Прокси для requests
        timeout: Таймаут запроса

    Returns:
        Список словарей с токенами: [{"asset": "USDT", "amount": 500.0, "category": "Futures"}, ...]
        или [] при ошибке (Futures может быть не активирован)
    """
    try:
        url = "https://contract.mexc.com/api/v1/private/account/assets"
        timestamp = str(int(time.time() * 1000))

        # Создаем подпись
        signature = _create_futures_signature(api_key, secret_key, timestamp)

        # Заголовки
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

            # Пропускаем токены с нулевым балансом
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
    """
    Получает баланс Futures аккаунта.

    Args:
        api_key: API ключ
        secret_key: Secret ключ
        proxies: Прокси для requests
        timeout: Таймаут запроса

    Returns:
        Баланс Futures в USD
    """
    try:
        url = "https://contract.mexc.com/api/v1/private/account/assets"
        timestamp = str(int(time.time() * 1000))

        # Создаем подпись
        signature = _create_futures_signature(api_key, secret_key, timestamp)

        # Заголовки
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

        # Суммируем equity (общий баланс) для всех валют
        for asset in assets:
            currency = asset.get('currency', '')
            equity = float(asset.get('equity', '0'))

            # Для USDT это уже USD
            if currency == 'USDT':
                total_balance += equity
            # Для других валют нужна конвертация (обычно на MEXC Futures только USDT)

        return total_balance

    except Exception as e:
        # Игнорируем ошибки (может быть futures не активирован)
        return 0.0


def _process_mexc_tokens(
    token_details: List[Dict],
    min_value: float = 1.0
) -> Optional[Dict[str, float]]:
    """
    Обработать детали токенов в статистику с группировкой и категориями

    Группирует токены по ключу "symbol (category)".
    Разделяет на отдельные токены (>= min_value) и категорию "Other" (< min_value).

    Args:
        token_details: Список словарей с деталями токенов
            [{"asset": "BTC", "value": 100.0, "category": "Spot"}, ...]
        min_value: Минимальная стоимость токена в USD для отдельного учета

    Returns:
        Словарь с токенами:
        {
            "BTC (Spot)": 100.50,
            "USDT (Futures)": 75.46,
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

            # Создаем уникальный ключ: "BTC (Spot)"
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
    """
    Получает полный баланс с биржи MEXC со всех типов аккаунтов.

    Args:
        api_key: API ключ (Access Key)
        secret_key: Secret ключ
        proxy_dict: Прокси в формате httpx (конвертируется для requests)
        timeout: Таймаут запроса
        wallet_info: Информация о кошельке для логов
        collect_tokens: Собирать ли статистику токенов
        min_token_value: Минимальная стоимость токена для отдельного учета

    Returns:
        Словарь с балансом:
        {
            "total_balance": float,  # Общий баланс в USD
            "tokens": dict или None,  # Статистика токенов
            "error": None или код ошибки
        }
    """
    try:
        # Конвертируем прокси из httpx формата в requests формат
        proxies_dict = proxy_dict if proxy_dict else None

        # ====================================================================
        # СБОР ТОКЕНОВ (если запрошено)
        # ====================================================================
        tokens_data = None

        if collect_tokens:
            # Собираем токены из всех типов аккаунтов
            all_tokens = []

            # 1. Spot токены
            spot_tokens = _get_spot_tokens(api_key, secret_key, proxies_dict, timeout)
            if spot_tokens:
                all_tokens.extend(spot_tokens)

            # 2. Futures токены
            futures_tokens = _get_futures_tokens(api_key, secret_key, proxies_dict, timeout)
            if futures_tokens:
                all_tokens.extend(futures_tokens)

            # Получаем все цены одним запросом (оптимизация)
            try:
                prices_dict = _get_all_prices(proxies_dict, timeout)

                if not prices_dict:
                    debug_log("Не удалось получить цены токенов MEXC")
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
                    tokens_data = _process_mexc_tokens(token_details, min_token_value)

                    # Логируем токены если есть wallet_info
                    if wallet_info and tokens_data and tokens_data.get("error") is None:
                        tokens_list = [f"{symbol}: ${value:,.2f}" for symbol, value in tokens_data.items() if symbol != "error"]
                        if tokens_list:
                            info_log(f"{wallet_info} → Токены: {', '.join(tokens_list)}")

            except Exception as e:
                debug_log(f"Ошибка получения цен токенов MEXC: {str(e)}")
                tokens_data = {"error": "PRICE_ERROR"}

        # ====================================================================
        # ПОЛУЧЕНИЕ ОБЩЕГО БАЛАНСА
        # ====================================================================

        # Получаем балансы с обоих типов аккаунтов
        spot_balance = _get_spot_balance(api_key, secret_key, proxies_dict, timeout)

        # Spot критичен - если зафейлился, возвращаем ошибку
        if spot_balance is None:
            return {
                "total_balance": 0.0,
                "tokens": None,
                "error": "API_ERROR"
            }

        futures_balance = _get_futures_balance(api_key, secret_key, proxies_dict, timeout)

        # Futures не критичен - если вернул 0.0, это ОК (может быть не активирован)
        # Суммируем
        total_balance = spot_balance + futures_balance

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
