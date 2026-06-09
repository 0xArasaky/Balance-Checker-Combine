"""
Модуль для получения баланса с биржи Gate.io.

Gate.io использует HMAC SHA512 для аутентификации (не SHA256!).
"""

import hmac
import hashlib
import time
from typing import Dict, Optional, List
import requests
import urllib3

from modules.utils.logger import logger, info_log, error_log, debug_log

# Подавляем предупреждения о непроверенных SSL сертификатах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _create_signature(
    secret: str,
    method: str,
    url_path: str,
    query_string: str = "",
    payload: str = ""
) -> Dict[str, str]:
    """
    Создает HMAC SHA512 подпись для Gate.io API.

    Args:
        secret: Secret ключ
        method: HTTP метод (GET, POST, etc.) в верхнем регистре
        url_path: Путь URL (например, /api/v4/spot/accounts)
        query_string: Строка параметров запроса (если есть)
        payload: Тело запроса (если есть)

    Returns:
        Словарь с заголовками аутентификации
    """
    # Текущее время (целое число в секундах)
    t = str(int(time.time()))

    # Хешируем payload с SHA512
    m = hashlib.sha512()
    m.update(payload.encode('utf-8'))
    hashed_payload = m.hexdigest()

    # Формируем строку для подписи (построчно через \n)
    signature_string = f"{method}\n{url_path}\n{query_string}\n{hashed_payload}\n{t}"

    # Создаем HMAC SHA512 подпись
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
    """
    Получает цены всех токенов в USDT с Gate.io.

    Args:
        proxies: Прокси для requests
        timeout: Таймаут запроса

    Returns:
        Словарь {currency: price_in_usdt}
    """
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        response = requests.get(url, proxies=proxies, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        prices = {}

        for ticker in data:
            currency_pair = ticker.get('currency_pair', '')
            # Интересуют только пары с USDT
            if '_USDT' in currency_pair:
                currency = currency_pair.replace('_USDT', '')
                last_price = float(ticker.get('last', '0'))
                if last_price > 0:
                    prices[currency] = last_price

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

    Использует GET /api/v4/spot/accounts

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
        url = "https://api.gateio.ws/api/v4/spot/accounts"
        method = "GET"
        url_path = "/api/v4/spot/accounts"

        # Создаем подпись
        auth_headers = _create_signature(secret_key, method, url_path)

        # Заголовки
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

        # Конвертируем каждый токен
        for account in data:
            currency = account.get('currency', '')
            available = float(account.get('available', '0'))
            locked = float(account.get('locked', '0'))
            token_amount = available + locked

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
        url = "https://api.gateio.ws/api/v4/spot/accounts"
        method = "GET"
        url_path = "/api/v4/spot/accounts"

        # Создаем подпись
        auth_headers = _create_signature(secret_key, method, url_path)

        # Заголовки
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

        # Получаем цены
        prices = _get_all_prices(proxies, timeout)

        total_balance = 0.0

        # Конвертируем каждый токен в USD
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
        return None  # Ошибка API


def _get_futures_balance(
    api_key: str,
    secret_key: str,
    settle: str,
    proxies: Optional[Dict] = None,
    timeout: int = 30
) -> float:
    """
    Получает баланс Futures аккаунта.

    Args:
        api_key: API ключ
        secret_key: Secret ключ
        settle: Тип расчета (btc или usdt)
        proxies: Прокси для requests
        timeout: Таймаут запроса

    Returns:
        Баланс Futures в USD
    """
    try:
        url = f"https://api.gateio.ws/api/v4/futures/{settle}/accounts"
        method = "GET"
        url_path = f"/api/v4/futures/{settle}/accounts"

        # Создаем подпись
        auth_headers = _create_signature(secret_key, method, url_path)

        # Заголовки
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

        # total - общая стоимость аккаунта в валюте расчета
        total = float(data.get('total', '0'))

        # Конвертируем в USD
        if settle == 'usdt':
            # USDT уже в USD
            return total
        elif settle == 'btc':
            # Нужно конвертировать BTC в USD
            prices = _get_all_prices(proxies, timeout)
            btc_price = prices.get('BTC', 0)
            return total * btc_price
        else:
            return 0.0

    except Exception as e:
        # Игнорируем ошибки (может быть futures не активирован)
        return 0.0


def _get_futures_tokens(
    api_key: str,
    secret_key: str,
    settle: str,
    proxies: Optional[Dict],
    timeout: int
) -> Optional[List[Dict]]:
    """
    Получить детали токенов с Futures аккаунта

    Использует GET /api/v4/futures/{settle}/accounts

    Args:
        api_key: API ключ
        secret_key: Secret ключ
        settle: Тип расчета (btc или usdt)
        proxies: Прокси для requests
        timeout: Таймаут запроса

    Returns:
        Список словарей с токенами: [{"asset": "USDT", "amount": 500.0, "category": "Futures USDT"}, ...]
        или [] при ошибке (Futures может быть не активирован)
    """
    try:
        url = f"https://api.gateio.ws/api/v4/futures/{settle}/accounts"
        method = "GET"
        url_path = f"/api/v4/futures/{settle}/accounts"

        # Создаем подпись
        auth_headers = _create_signature(secret_key, method, url_path)

        # Заголовки
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

        # total - общая стоимость аккаунта в валюте расчета
        total = float(data.get('total', '0'))

        if total > 0:
            # Определяем валюту и категорию
            currency = settle.upper()  # BTC или USDT
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
    """
    Получить детали токенов с Margin аккаунтов

    Использует GET /api/v4/margin/accounts

    Args:
        api_key: API ключ
        secret_key: Secret ключ
        proxies: Прокси для requests
        timeout: Таймаут запроса

    Returns:
        Список словарей с токенами: [{"asset": "BTC", "amount": 0.5, "category": "Margin"}, ...]
        или [] при ошибке (Margin может быть не активирован)
    """
    try:
        url = "https://api.gateio.ws/api/v4/margin/accounts"
        method = "GET"
        url_path = "/api/v4/margin/accounts"

        # Создаем подпись
        auth_headers = _create_signature(secret_key, method, url_path)

        # Заголовки
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

        # Суммируем балансы всех margin пар
        for account in data:
            base_currency = account.get('base', {})
            quote_currency = account.get('quote', {})

            # Обрабатываем базовую валюту
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

            # Обрабатываем котируемую валюту
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
    """
    Получает баланс Margin аккаунта.

    Args:
        api_key: API ключ
        secret_key: Secret ключ
        proxies: Прокси для requests
        timeout: Таймаут запроса

    Returns:
        Баланс Margin в USD
    """
    try:
        url = "https://api.gateio.ws/api/v4/margin/accounts"
        method = "GET"
        url_path = "/api/v4/margin/accounts"

        # Создаем подпись
        auth_headers = _create_signature(secret_key, method, url_path)

        # Заголовки
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

        # Получаем цены
        prices = _get_all_prices(proxies, timeout)

        total_balance = 0.0

        # Суммируем балансы всех margin пар
        for account in data:
            currency_pair = account.get('currency_pair', '')
            base_currency = account.get('base', {})
            quote_currency = account.get('quote', {})

            # Обрабатываем базовую валюту
            if base_currency:
                currency = base_currency.get('currency', '')
                available = float(base_currency.get('available', '0'))
                locked = float(base_currency.get('locked', '0'))
                token_amount = available + locked

                if token_amount > 0:
                    price_usd = prices.get(currency, 0)
                    total_balance += token_amount * price_usd

            # Обрабатываем котируемую валюту
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
        # Игнорируем ошибки (может быть margin не активирован)
        return 0.0


def _process_gate_tokens(
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
            "USDT (Futures USDT)": 75.46,
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
    """
    Получает полный баланс с биржи Gate.io со всех типов аккаунтов.

    Args:
        api_key: API ключ
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

            # 2. Margin токены
            margin_tokens = _get_margin_tokens(api_key, secret_key, proxies_dict, timeout)
            if margin_tokens:
                all_tokens.extend(margin_tokens)

            # 3. Futures USDT токены
            futures_usdt_tokens = _get_futures_tokens(api_key, secret_key, 'usdt', proxies_dict, timeout)
            if futures_usdt_tokens:
                all_tokens.extend(futures_usdt_tokens)

            # 4. Futures BTC токены
            futures_btc_tokens = _get_futures_tokens(api_key, secret_key, 'btc', proxies_dict, timeout)
            if futures_btc_tokens:
                all_tokens.extend(futures_btc_tokens)

            # Получаем все цены одним запросом (оптимизация)
            try:
                prices_dict = _get_all_prices(proxies_dict, timeout)

                if not prices_dict:
                    debug_log("Не удалось получить цены токенов Gate.io")
                    tokens_data = {"error": "PRICE_ERROR"}
                else:
                    # Конвертируем токены в USD
                    token_details = []

                    for token in all_tokens:
                        asset = token["asset"]
                        amount = token["amount"]
                        category = token["category"]

                        # Получаем цену (BTC и USDT уже есть в prices)
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
                    tokens_data = _process_gate_tokens(token_details, min_token_value)

                    # Логируем токены если есть wallet_info
                    if wallet_info and tokens_data and tokens_data.get("error") is None:
                        tokens_list = [f"{symbol}: ${value:,.2f}" for symbol, value in tokens_data.items() if symbol != "error"]
                        if tokens_list:
                            info_log(f"{wallet_info} → Токены: {', '.join(tokens_list)}")

            except Exception as e:
                debug_log(f"Ошибка получения цен токенов Gate.io: {str(e)}")
                tokens_data = {"error": "PRICE_ERROR"}

        # ====================================================================
        # ПОЛУЧЕНИЕ ОБЩЕГО БАЛАНСА
        # ====================================================================

        # Получаем балансы со всех типов аккаунтов
        spot_balance = _get_spot_balance(api_key, secret_key, proxies_dict, timeout)

        # Spot критичен - если зафейлился, возвращаем ошибку
        if spot_balance is None:
            return {
                "total_balance": 0.0,
                "tokens": None,
                "error": "API_ERROR"
            }

        futures_usdt_balance = _get_futures_balance(api_key, secret_key, 'usdt', proxies_dict, timeout)
        futures_btc_balance = _get_futures_balance(api_key, secret_key, 'btc', proxies_dict, timeout)
        margin_balance = _get_margin_balance(api_key, secret_key, proxies_dict, timeout)

        # Futures и Margin не критичны - если вернули 0.0, это ОК (могут быть не активированы)
        # Суммируем
        total_balance = spot_balance + futures_usdt_balance + futures_btc_balance + margin_balance

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
