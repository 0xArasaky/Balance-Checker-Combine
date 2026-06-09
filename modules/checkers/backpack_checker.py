"""
Модуль для получения баланса с биржи Backpack Exchange.

Backpack использует ED25519 криптографическую подпись для аутентификации.
"""

import base64
from time import time
from typing import Dict, Optional, List
import requests
import urllib3
from cryptography.hazmat.primitives.asymmetric import ed25519

from modules.utils.logger import logger, info_log, error_log, debug_log

# Подавляем предупреждения о непроверенных SSL сертификатах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_all_prices(proxy_dict: Optional[Dict] = None, timeout: int = 30) -> Dict[str, float]:
    """
    Получает цены ВСЕХ токенов за один запрос (оптимизация)

    Использует /api/v1/tickers для получения всех цен в парах с USDC.

    Args:
        proxy_dict: Прокси в формате httpx
        timeout: Таймаут запроса

    Returns:
        Словарь {currency: price_in_usdc}
        Например: {"SOL": 180.5, "BTC": 95000.0, "USDC": 1.0}
    """
    try:
        url = "https://api.backpack.exchange/api/v1/tickers"

        # Конвертируем прокси для requests
        proxies_dict = proxy_dict if proxy_dict else None

        response = requests.get(url, proxies=proxies_dict, timeout=timeout, verify=False)
        response.raise_for_status()
        ticker_data = response.json()

        # Создаем словарь цен
        prices_dict = {}

        for ticker in ticker_data:
            symbol = ticker.get("symbol", "")
            # Обрабатываем только пары с _USDC
            if "_USDC" in symbol:
                # Извлекаем базовый актив (SOL из SOL_USDC)
                base_currency = symbol.replace("_USDC", "")
                price = float(ticker.get("lastPrice", "0"))

                if price > 0:
                    prices_dict[base_currency] = price

        # USDC = 1.0
        prices_dict["USDC"] = 1.0

        return prices_dict

    except Exception as e:
        debug_log(f"Ошибка получения всех цен Backpack: {str(e)}")
        return {}


def _get_token_balances(
    api_key: str,
    secret_key: str,
    proxy_dict: Optional[Dict],
    timeout: int
) -> Optional[List[Dict]]:
    """
    Получить детали токенов со всех балансов Backpack

    Использует GET /api/v1/capital

    Args:
        api_key: API ключ (base64 encoded public key)
        secret_key: Secret ключ (base64 encoded private key)
        proxy_dict: Прокси в формате httpx
        timeout: Таймаут запроса

    Returns:
        Список словарей с токенами: [{"asset": "SOL", "amount": 1.5}, ...]
        или None при ошибке
    """
    try:
        # Создаем приватный ключ из secret key
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(
            base64.b64decode(secret_key)
        )

        # Параметры для balanceQuery (пустые)
        params = {}

        # Временные метки
        timestamp = int(time() * 1000)
        window = "5000"
        instruction = "balanceQuery"

        # Создаем подпись
        signature = _create_signature(private_key, instruction, params, timestamp, window)

        # Формируем заголовки
        headers = {
            "X-API-Key": api_key,
            "X-Signature": signature,
            "X-Timestamp": str(timestamp),
            "X-Window": window,
            "Content-Type": "application/json; charset=utf-8",
        }

        # Выполняем запрос
        url = "https://api.backpack.exchange/api/v1/capital"

        # Конвертируем прокси для requests
        proxies_dict = proxy_dict if proxy_dict else None

        response = requests.get(url, headers=headers, proxies=proxies_dict, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        # Обрабатываем ответ - получаем балансы всех токенов
        # Формат ответа: {"SOL": {"available": "1.5", "locked": "0.5", "staked": "0.0"}, ...}
        tokens = []

        for token_name, balances in data.items():
            available = float(balances.get("available", "0"))
            locked = float(balances.get("locked", "0"))
            staked = float(balances.get("staked", "0"))

            # Общее количество токена (available + locked + staked)
            total_amount = available + locked + staked

            # Пропускаем токены с нулевым балансом
            if total_amount > 0:
                tokens.append({
                    "asset": token_name,
                    "amount": total_amount
                })

        return tokens

    except Exception as e:
        debug_log(f"Ошибка получения токенов Backpack: {str(e)}")
        return None


def _process_backpack_tokens(
    token_details: List[Dict],
    min_value: float = 1.0
) -> Optional[Dict[str, float]]:
    """
    Обработать детали токенов в статистику

    У Backpack нет категорий счетов, поэтому токены без скобок.
    Разделяет на отдельные токены (>= min_value) и категорию "Other" (< min_value).

    Args:
        token_details: Список словарей с деталями токенов
            [{"asset": "SOL", "value": 100.0}, ...]
        min_value: Минимальная стоимость токена в USD для отдельного учета

    Returns:
        Словарь с токенами:
        {
            "SOL": 100.50,
            "USDC": 75.46,
            "Other": 2.13,
            "error": None
        }
    """
    try:
        # Группируем токены по asset (на случай дубликатов)
        tokens_by_asset = {}

        for token in token_details:
            asset = token["asset"]
            value = token["value"]

            # Суммируем если уже есть такой актив
            tokens_by_asset[asset] = tokens_by_asset.get(asset, 0) + value

        # Разделяем на отдельные токены и "Other"
        result = {}
        other_total = 0.0

        for asset, total_value in tokens_by_asset.items():
            if total_value >= min_value:
                result[asset] = round(total_value, 2)
            else:
                other_total += total_value

        # Добавляем категорию "Other" если есть мелкие токены
        if other_total > 0:
            result["Other"] = round(other_total, 2)

        result["error"] = None
        return result

    except Exception as e:
        error_log(f"Ошибка обработки токенов Backpack: {str(e)}")
        return {"error": "ERROR"}


def _create_signature(
    private_key: ed25519.Ed25519PrivateKey,
    instruction: str,
    params: Dict[str, str],
    timestamp: int,
    window: str = "5000"
) -> str:
    """
    Создает ED25519 подпись для запроса к Backpack API.

    Args:
        private_key: Приватный ключ ED25519
        instruction: Тип инструкции (например, "balanceQuery")
        params: Параметры запроса (отсортированные)
        timestamp: Unix timestamp в миллисекундах
        window: Временное окно валидности запроса (мс)

    Returns:
        Base64 закодированная подпись
    """
    # Сортируем параметры по алфавиту
    sorted_params_list = []
    for key, value in sorted(params.items()):
        if isinstance(value, bool):
            value = str(value).lower()
        sorted_params_list.append(f"{key}={value}")
    sorted_params = "&".join(sorted_params_list)

    # Формируем строку для подписи
    sign_str = f"instruction={instruction}"
    if sorted_params:
        sign_str += "&" + sorted_params
    sign_str += f"&timestamp={timestamp}&window={window}"

    # Подписываем приватным ключом
    signature_bytes = private_key.sign(sign_str.encode())
    encoded_signature = base64.b64encode(signature_bytes).decode()

    return encoded_signature


def _get_balance(
    api_key: str,
    secret_key: str,
    proxy_dict: Optional[Dict] = None,
    timeout: int = 30
) -> float:
    """
    Получает общий баланс со всех аккаунтов Backpack.

    Args:
        api_key: API ключ (base64 encoded public key)
        secret_key: Secret ключ (base64 encoded private key)
        proxy_dict: Прокси в формате httpx
        timeout: Таймаут запроса

    Returns:
        Общий баланс в USD
    """
    try:
        # Создаем приватный ключ из secret key
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(
            base64.b64decode(secret_key)
        )

        # Параметры для balanceQuery (пустые)
        params = {}

        # Временные метки
        timestamp = int(time() * 1000)
        window = "5000"
        instruction = "balanceQuery"

        # Создаем подпись
        signature = _create_signature(private_key, instruction, params, timestamp, window)

        # Формируем заголовки
        headers = {
            "X-API-Key": api_key,
            "X-Signature": signature,
            "X-Timestamp": str(timestamp),
            "X-Window": window,
            "Content-Type": "application/json; charset=utf-8",
        }

        # Выполняем запрос
        url = "https://api.backpack.exchange/api/v1/capital"

        # Конвертируем прокси из httpx формата в requests формат
        proxies_dict = None
        if proxy_dict:
            # proxy_dict в формате httpx: {"http://": "...", "https://": "..."}
            # requests используеттот же формат
            proxies_dict = proxy_dict

        response = requests.get(url, headers=headers, proxies=proxies_dict, timeout=timeout, verify=False)
        response.raise_for_status()
        data = response.json()

        # Обрабатываем ответ - получаем балансы всех токенов
        # Формат ответа: {"SOL": {"available": "1.5", "locked": "0.5"}, ...}
        total_balance = 0.0

        # Нужно получить цены токенов, чтобы конвертировать в USD
        # Используем эндпоинт /api/v1/tickers (множественное число) для получения ВСЕХ цен
        ticker_url = "https://api.backpack.exchange/api/v1/tickers"

        ticker_response = requests.get(ticker_url, proxies=proxies_dict, timeout=timeout, verify=False)
        ticker_response.raise_for_status()
        ticker_data = ticker_response.json()

        # Создаем словарь цен (последняя цена в USDC)
        prices = {}
        for ticker in ticker_data:
            symbol = ticker.get("symbol", "")
            if "_USDC" in symbol:
                token = symbol.replace("_USDC", "")
                last_price = float(ticker.get("lastPrice", "0"))
                prices[token] = last_price

        # Добавляем USDC как 1:1 к USD
        prices["USDC"] = 1.0

        # Считаем общий баланс
        for token, balances in data.items():
            available = float(balances.get("available", "0"))
            locked = float(balances.get("locked", "0"))
            staked = float(balances.get("staked", "0"))

            total_amount = available + locked + staked

            if total_amount > 0:
                # Получаем цену токена
                token_price = prices.get(token, 0)
                token_value_usd = total_amount * token_price
                total_balance += token_value_usd


        return total_balance

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP ошибка при запросе к Backpack API: {e.response.status_code}")
        logger.error(f"Тело ответа: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении баланса Backpack: {str(e)}")
        raise


def get_backpack_balance(
    api_key: str,
    secret_key: str,
    proxy_dict: Optional[Dict] = None,
    timeout: int = 30,
    wallet_info: str = "",
    collect_tokens: bool = False,
    min_token_value: float = 1.0
) -> Dict[str, Optional[float]]:
    """
    Получает полный баланс с биржи Backpack Exchange.

    Args:
        api_key: API ключ (base64 encoded public key)
        secret_key: Secret ключ (base64 encoded private key)
        proxy_dict: Прокси в формате httpx
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
        # ====================================================================
        # СБОР ТОКЕНОВ (если запрошено)
        # ====================================================================
        tokens_data = None

        if collect_tokens:
            # Получаем детали токенов
            all_tokens = _get_token_balances(api_key, secret_key, proxy_dict, timeout)

            if all_tokens is None:
                debug_log("Не удалось получить токены Backpack")
                tokens_data = {"error": "TOKEN_ERROR"}
            else:
                # Получаем все цены одним запросом (оптимизация)
                try:
                    prices_dict = get_all_prices(proxy_dict, timeout)

                    if not prices_dict:
                        debug_log("Не удалось получить цены токенов Backpack")
                        tokens_data = {"error": "PRICE_ERROR"}
                    else:
                        # Конвертируем токены в USD
                        token_details = []

                        for token in all_tokens:
                            asset = token["asset"]
                            amount = token["amount"]

                            # Получаем цену
                            price_usdc = prices_dict.get(asset, 0)

                            if price_usdc > 0:
                                value_usd = amount * price_usdc

                                # Собираем данные для обработки
                                token_details.append({
                                    "asset": asset,
                                    "value": value_usd
                                })

                        # Обрабатываем токены через функцию группировки
                        tokens_data = _process_backpack_tokens(token_details, min_token_value)

                        # Логируем токены если есть wallet_info
                        if wallet_info and tokens_data and tokens_data.get("error") is None:
                            tokens_list = [f"{symbol}: ${value:,.2f}" for symbol, value in tokens_data.items() if symbol != "error"]
                            if tokens_list:
                                info_log(f"{wallet_info} → Токены: {', '.join(tokens_list)}")

                except Exception as e:
                    debug_log(f"Ошибка получения цен токенов Backpack: {str(e)}")
                    tokens_data = {"error": "PRICE_ERROR"}

        # ====================================================================
        # ПОЛУЧЕНИЕ ОБЩЕГО БАЛАНСА
        # ====================================================================
        total_balance = _get_balance(api_key, secret_key, proxy_dict, timeout)

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
        logger.warning(f"{wallet_info} → Таймаут при запросе к Backpack API")
        return {
            "total_balance": 0.0,
            "tokens": None,
            "error": "TIMEOUT"
        }
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        logger.error(f"{wallet_info} → HTTP ошибка {status_code} от Backpack API")
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
