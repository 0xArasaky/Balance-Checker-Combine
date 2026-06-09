"""
Binance Checker - получение баланса с биржи Binance

Использует Binance API для получения баланса со всех счетов:
- Spot (спот-торговля)
- Futures (фьючерсы USDT-M и COIN-M)
- Margin (маржинальная торговля)
- Earn (стейкинг, savings)
- И другие
"""

import hmac
import hashlib
import time
from typing import Dict, Optional, List
from urllib.parse import urlencode
import httpx

from modules.utils.logger import info_log, error_log, debug_log

# Binance API
BASE_URL = "https://api.binance.com"


def get_server_time(timeout: int = 10) -> int:
    """
    Получает текущее серверное время от Binance

    Args:
        timeout: Таймаут запроса в секундах

    Returns:
        Серверное время в миллисекундах

    Raises:
        Exception: Если не удалось получить серверное время
    """
    try:
        url = f"{BASE_URL}/api/v3/time"
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            return data['serverTime']
    except Exception as e:
        # Если не удалось получить серверное время, используем локальное
        # но логируем предупреждение
        error_log(f"Не удалось получить серверное время Binance: {str(e)}, использую локальное время")
        return int(time.time() * 1000)


def generate_signature(secret_key: str, query_string: str) -> str:
    """
    Генерирует подпись для Binance API

    Args:
        secret_key: Секретный ключ API
        query_string: Строка параметров запроса

    Returns:
        HMAC SHA256 подпись в hex формате
    """
    return hmac.new(
        secret_key.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def _get_spot_tokens(
    api_key: str,
    secret_key: str,
    timeout: int,
    timestamp: int
) -> Optional[List[Dict]]:
    """
    Получить токены со Spot кошелька

    Использует GET /api/v3/account

    Args:
        api_key: API ключ
        secret_key: Секретный ключ
        timeout: Таймаут запроса
        timestamp: Серверное время

    Returns:
        Список словарей с токенами: [{"asset": "BTC", "amount": 1.5, "category": "Spot"}, ...]
        или None при ошибке
    """
    try:
        endpoint = "/api/v3/account"

        params = {
            'timestamp': timestamp,
            'recvWindow': 5000
        }

        query_string = urlencode(params)
        signature = generate_signature(secret_key, query_string)
        url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"

        headers = {"X-MBX-APIKEY": api_key}

        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            balances = data.get("balances", [])
            tokens = []

            for balance in balances:
                asset = balance.get("asset", "")
                free = float(balance.get("free", 0))
                locked = float(balance.get("locked", 0))
                total_amount = free + locked

                # Пропускаем токены с нулевым балансом
                if total_amount > 0:
                    tokens.append({
                        "asset": asset,
                        "amount": total_amount,
                        "category": "Spot"
                    })

            return tokens

    except Exception as e:
        debug_log(f"Ошибка получения Spot токенов: {str(e)}")
        return None


def _get_flexible_tokens(
    api_key: str,
    secret_key: str,
    timeout: int,
    timestamp: int
) -> Optional[List[Dict]]:
    """
    Получить токены из Simple Earn Flexible

    Использует GET /sapi/v1/simple-earn/flexible/position

    Args:
        api_key: API ключ
        secret_key: Секретный ключ
        timeout: Таймаут запроса
        timestamp: Серверное время

    Returns:
        Список словарей с токенами: [{"asset": "USDT", "amount": 75.46, "category": "Earn Flexible"}, ...]
        или None при ошибке
    """
    try:
        endpoint = "/sapi/v1/simple-earn/flexible/position"

        params = {
            'timestamp': timestamp,
            'recvWindow': 5000
        }

        query_string = urlencode(params)
        signature = generate_signature(secret_key, query_string)
        url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"

        headers = {"X-MBX-APIKEY": api_key}

        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            rows = data.get("rows", [])
            tokens = []

            for row in rows:
                asset = row.get("asset", "")
                total_amount = float(row.get("totalAmount", 0))

                # Пропускаем токены с нулевым балансом
                if total_amount > 0:
                    tokens.append({
                        "asset": asset,
                        "amount": total_amount,
                        "category": "Earn Flexible"
                    })

            return tokens

    except Exception as e:
        debug_log(f"Ошибка получения Flexible Earn токенов: {str(e)}")
        return None


def _get_locked_tokens(
    api_key: str,
    secret_key: str,
    timeout: int,
    timestamp: int
) -> Optional[List[Dict]]:
    """
    Получить токены из Simple Earn Locked

    Использует GET /sapi/v1/simple-earn/locked/position

    Args:
        api_key: API ключ
        secret_key: Секретный ключ
        timeout: Таймаут запроса
        timestamp: Серверное время

    Returns:
        Список словарей с токенами: [{"asset": "BTC", "amount": 0.5, "category": "Earn Locked"}, ...]
        или None при ошибке
    """
    try:
        endpoint = "/sapi/v1/simple-earn/locked/position"

        params = {
            'timestamp': timestamp,
            'recvWindow': 5000
        }

        query_string = urlencode(params)
        signature = generate_signature(secret_key, query_string)
        url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"

        headers = {"X-MBX-APIKEY": api_key}

        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            rows = data.get("rows", [])
            tokens = []

            for row in rows:
                asset = row.get("asset", "")
                # Для Locked positions пробуем разные названия поля
                amount = float(row.get("amount", row.get("totalAmount", 0)))

                # Пропускаем токены с нулевым балансом
                if amount > 0:
                    tokens.append({
                        "asset": asset,
                        "amount": amount,
                        "category": "Earn Locked"
                    })

            return tokens

    except Exception as e:
        debug_log(f"Ошибка получения Locked Earn токенов: {str(e)}")
        return None


def _process_binance_tokens(
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
            "USDT (Earn Flexible)": 75.46,
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
        error_log(f"Ошибка обработки токенов Binance: {str(e)}")
        return {"error": "ERROR"}


def get_binance_balance(
    api_key: str,
    secret_key: str,
    proxy_dict: dict = None,
    timeout: int = 30,
    wallet_info: str = "",
    collect_tokens: bool = False,
    min_token_value: float = 1.0
) -> dict:
    """
    Получает общий баланс со ВСЕХ счетов Binance

    Args:
        api_key: API ключ Binance
        secret_key: Секретный ключ Binance
        proxy_dict: Словарь с прокси (не используется для Binance)
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
        # Получаем серверное время от Binance (для точной синхронизации)
        timestamp = get_server_time(timeout=timeout)

        # ====================================================================
        # СБОР ТОКЕНОВ (если запрошено)
        # ====================================================================
        tokens_data = None

        if collect_tokens:
            # Собираем токены из всех источников
            all_tokens = []

            # 1. Spot токены
            spot_tokens = _get_spot_tokens(api_key, secret_key, timeout, timestamp)
            if spot_tokens:
                all_tokens.extend(spot_tokens)

            # 2. Flexible Earn токены
            flexible_tokens = _get_flexible_tokens(api_key, secret_key, timeout, timestamp)
            if flexible_tokens:
                all_tokens.extend(flexible_tokens)

            # 3. Locked Earn токены
            locked_tokens = _get_locked_tokens(api_key, secret_key, timeout, timestamp)
            if locked_tokens:
                all_tokens.extend(locked_tokens)

            # Получаем все цены от Binance
            # Используем /api/v3/ticker/price без параметров - вернет все пары
            try:
                price_url = f"{BASE_URL}/api/v3/ticker/price"
                with httpx.Client(timeout=timeout) as client:
                    price_response = client.get(price_url)
                    price_response.raise_for_status()
                    all_prices = price_response.json()

                    # Создаем словарь цен: {symbol: price_usdt}
                    # Нас интересуют пары вида "BTCUSDT", "ETHUSDT" и т.д.
                    prices_dict = {}
                    for item in all_prices:
                        symbol_pair = item.get("symbol", "")
                        if symbol_pair.endswith("USDT"):
                            # Извлекаем базовый актив (BTC из BTCUSDT)
                            base_asset = symbol_pair[:-4]  # Убираем "USDT"
                            price = float(item.get("price", 0))
                            prices_dict[base_asset] = price

                    # USDT сам себе равен 1.0
                    prices_dict["USDT"] = 1.0

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
                    tokens_data = _process_binance_tokens(token_details, min_token_value)

                    # Логируем токены если есть wallet_info
                    if wallet_info and tokens_data and tokens_data.get("error") is None:
                        tokens_list = [f"{symbol}: ${value:,.2f}" for symbol, value in tokens_data.items() if symbol != "error"]
                        if tokens_list:
                            info_log(f"{wallet_info} → Токены: {', '.join(tokens_list)}")

            except Exception as e:
                debug_log(f"Ошибка получения цен токенов Binance: {str(e)}")
                tokens_data = {"error": "PRICE_ERROR"}

        # ====================================================================
        # ПОЛУЧЕНИЕ ОБЩЕГО БАЛАНСА
        # ====================================================================
        endpoint = "/sapi/v1/asset/wallet/balance"

        # Параметры запроса
        params = {
            'quoteAsset': 'USDT',  # Получаем баланс в USDT (≈ USD)
            'timestamp': timestamp,
            'recvWindow': 5000
        }

        # Генерация query string
        query_string = urlencode(params)

        # Генерация подписи
        signature = generate_signature(secret_key, query_string)

        # Полный URL с подписью
        url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"

        # Заголовки для аутентификации
        headers = {
            "X-MBX-APIKEY": api_key
        }

        # Запрос к API
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()

            # Парсинг балансов
            # data - это массив объектов {"activate": bool, "balance": str, "walletName": str}
            if not isinstance(data, list):
                error_log(f"{wallet_info} → Неожиданный формат ответа Binance API")
                return {"total_balance": 0.0, "tokens": None, "error": "API_ERROR"}

            # Суммируем балансы со всех активных кошельков
            total_balance = 0.0

            for wallet in data:
                # Проверяем что кошелек активен
                if wallet.get("activate", False):
                    balance_str = wallet.get("balance", "0")
                    try:
                        balance = float(balance_str)
                        total_balance += balance
                    except ValueError:
                        # Если не удалось конвертировать в float, пропускаем
                        continue

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

    except httpx.TimeoutException:
        error_log(f"{wallet_info} → Таймаут запроса")
        return {
            "total_balance": 0.0,
            "tokens": None,
            "error": "TIMEOUT"
        }
    except httpx.HTTPStatusError as e:
        # Пытаемся получить детали ошибки из ответа API
        try:
            error_details = e.response.json()
            error_code = error_details.get('code', 'N/A')
            error_msg = error_details.get('msg', 'N/A')
            error_log(f"{wallet_info} → HTTP ошибка {e.response.status_code}: код={error_code}, сообщение={error_msg}")
        except:
            error_log(f"{wallet_info} → HTTP ошибка: {e.response.status_code}")

        return {
            "total_balance": 0.0,
            "tokens": None,
            "error": f"HTTP_{e.response.status_code}"
        }
    except Exception as e:
        error_log(f"{wallet_info} → Неожиданная ошибка: {str(e)}")
        return {
            "total_balance": 0.0,
            "tokens": None,
            "error": "UNKNOWN_ERROR"
        }
