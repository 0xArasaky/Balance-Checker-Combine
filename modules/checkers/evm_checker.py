"""
Модуль проверки EVM кошельков через Rabby API с подписями
Получает полный баланс с детализацией:
- Chains: баланс по сетям (total_net_curve)
- Apps: DeFi протоколы через simple_protocol_list (Uniswap, Aave, Compound, Stargate и т.д.)
- Polymarket: отдельно через complex_app_list
- Hyperliquid: отдельно через complex_app_list
- Lighter: баланс на DEX через прямой API
"""

import httpx
import json
import subprocess
import secrets
import string
import time
from pathlib import Path
from typing import Optional, Dict, Tuple
import settings
from modules.utils.logger import error_log, info_log, debug_log, success_log, warning_log
from modules.utils.httpx_compat import create_httpx_client

# Путь к Node.js скрипту для генерации подписей
SCRIPT_DIR = Path(__file__).parent.parent.parent
SIGN_SCRIPT = SCRIPT_DIR / "scripts" / "generate_signature_with_nonce.js"

# Rabby API настройки
RABBY_API_BASE = "https://api.rabby.io"
RABBY_HEADERS_BASE = {
    "accept": "application/json, text/plain, */*",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "x-client": "Rabby",
    "x-version": "0.93.55"
}


def _sleep_between_rabby_requests() -> None:
    time.sleep(getattr(settings, "EVM_RABBY_STEP_DELAY", 0.2))


def generate_nonce(length: int = 40) -> str:
    """
    Генерирует случайный nonce для Rabby API

    Args:
        length: Длина случайной строки (по умолчанию 40)

    Returns:
        str: Nonce в формате "n_XXXXXXXX..."
    """
    alphabet = string.ascii_letters + string.digits
    random_string = ''.join(secrets.choice(alphabet) for _ in range(length))
    return f"n_{random_string}"


def generate_signature(method: str, url: str, params: dict) -> Optional[Dict[str, str]]:
    """
    Генерирует заголовки подписи для Rabby API

    Args:
        method: HTTP метод (GET, POST)
        url: Путь эндпоинта (например /v1/user/total_balance)
        params: Параметры запроса

    Returns:
        dict: Заголовки аутентификации или None при ошибке
    """
    try:
        # Генерируем случайный nonce в Python
        nonce = generate_nonce()

        params_json = json.dumps(params)

        result = subprocess.run(
            ["node", str(SIGN_SCRIPT), method, url, params_json, nonce],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(SCRIPT_DIR)  # Указываем рабочую директорию для поиска node_modules
        )

        if result.returncode != 0:
            error_log(f"Ошибка генерации подписи: {result.stderr}")
            return None

        headers = json.loads(result.stdout)

        # Конвертируем все значения в строки
        return {k: str(v) for k, v in headers.items()}

    except subprocess.TimeoutExpired:
        error_log("Таймаут при генерации подписи")
        return None
    except Exception as e:
        error_log(f"Ошибка генерации подписи: {str(e)}")
        return None


def get_evm_balance(
    address: str,
    proxy_dict: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    wallet_info: Optional[str] = None,
    collect_tokens: bool = False,
    min_token_value: float = 10.0
) -> Dict[str, any]:
    """
    Получить полный баланс EVM кошелька с детализацией

    Использует:
    - total_net_curve для баланса по сетям (устаревшие данные с графика)
    - simple_protocol_list для баланса DeFi протоколов (Uniswap, Aave, Compound, Stargate и т.д.)
    - complex_app_list для баланса Polymarket (актуальные данные)
    - complex_app_list для баланса Hyperliquid (актуальные данные)
    - Lighter API для баланса на DEX (актуальные данные)
    - (опционально) token_list для статистики токенов

    Args:
        address: Адрес кошелька
        proxy_dict: Словарь с прокси (формат httpx) или None
        timeout: Таймаут запроса в секундах
        wallet_info: Информация о кошельке для логов
        collect_tokens: Собирать ли статистику токенов
        min_token_value: Минимальная стоимость токена для отдельного учета

    Returns:
        Словарь с детализацией баланса:
        {
            "net_balance": float,                    # Баланс по сетям (total_net_curve)
            "apps_balance": float,                   # DeFi протоколы (simple_protocol_list)
            "polymarket_positions_balance": float,   # Открытые позиции на Polymarket
            "polymarket_total_balance": float,       # Полный баланс Polymarket (депозиты + позиции)
            "hyperliquid_balance": float,            # Баланс на Hyperliquid
            "lighter_balance": float,                # Баланс на бирже Lighter
            "total_balance": float,                  # Общий баланс
            "data_age": str,                         # Давность данных chains баланса (например "5 мин 30 сек")
            "tokens": dict или None,                 # Статистика токенов (если collect_tokens=True)
            "error": str или None                    # Код ошибки если есть
        }
    """
    try:
        # 1. Получаем базовый баланс из total_net_curve (баланс по сетям)
        base_result = _get_base_balance_from_curve(address, proxy_dict, timeout)
        if base_result is None:
            # Ошибка API - вернем error для retry
            return {
                "net_balance": 0.0,
                "apps_balance": 0.0,
                "polymarket_positions_balance": 0.0,
                "polymarket_total_balance": 0.0,
                "hyperliquid_balance": 0.0,
                "lighter_balance": 0.0,
                "total_balance": 0.0,
                "data_age": "N/A",
                "tokens": None,
                "error": "API_ERROR"
            }

        net_balance, data_lag = base_result
        lag_minutes = data_lag // 60
        lag_secs = data_lag % 60
        data_age = f"{lag_minutes} мин {lag_secs} сек"

        # Задержка между Rabby запросами
        _sleep_between_rabby_requests()

        # 2. Получаем баланс приложений и DeFi (БЕЗ Polymarket и Hyperliquid)
        apps_balance = _get_apps_balance(address, proxy_dict, timeout)
        if apps_balance is None:
            # Ошибка API - вернем error для retry
            return {
                "net_balance": 0.0,
                "apps_balance": 0.0,
                "polymarket_positions_balance": 0.0,
                "polymarket_total_balance": 0.0,
                "hyperliquid_balance": 0.0,
                "lighter_balance": 0.0,
                "total_balance": 0.0,
                "data_age": "N/A",
                "tokens": None,
                "error": "API_ERROR"
            }

        # Задержка между Rabby запросами
        _sleep_between_rabby_requests()

        # 3. Получаем баланс на Polymarket (позиции и общий)
        polymarket_result = _get_polymarket_balance(address, proxy_dict, timeout)
        if polymarket_result is None:
            # Ошибка API - вернем error для retry
            return {
                "net_balance": 0.0,
                "apps_balance": 0.0,
                "polymarket_positions_balance": 0.0,
                "polymarket_total_balance": 0.0,
                "hyperliquid_balance": 0.0,
                "lighter_balance": 0.0,
                "total_balance": 0.0,
                "data_age": "N/A",
                "tokens": None,
                "error": "API_ERROR"
            }
        else:
            polymarket_positions_balance, polymarket_total_balance = polymarket_result

        # Задержка между Rabby запросами
        _sleep_between_rabby_requests()

        # 4. Получаем баланс на Hyperliquid
        hyperliquid_balance = _get_hyperliquid_balance(address, proxy_dict, timeout)
        if hyperliquid_balance is None:
            # Ошибка API - вернем error для retry
            return {
                "net_balance": 0.0,
                "apps_balance": 0.0,
                "polymarket_positions_balance": 0.0,
                "polymarket_total_balance": 0.0,
                "hyperliquid_balance": 0.0,
                "lighter_balance": 0.0,
                "total_balance": 0.0,
                "data_age": "N/A",
                "tokens": None,
                "error": "API_ERROR"
            }

        # Задержка между Rabby запросами
        _sleep_between_rabby_requests()

        # 5. Получаем баланс на бирже Lighter
        lighter_balance = _get_lighter_balance(address, proxy_dict, timeout)
        if lighter_balance is None:
            # Ошибка API - вернем error для retry
            return {
                "net_balance": 0.0,
                "apps_balance": 0.0,
                "polymarket_positions_balance": 0.0,
                "polymarket_total_balance": 0.0,
                "hyperliquid_balance": 0.0,
                "lighter_balance": 0.0,
                "total_balance": 0.0,
                "data_age": "N/A",
                "tokens": None,
                "error": "API_ERROR"
            }

        # 6. Считаем полный баланс
        total_balance = net_balance + apps_balance + polymarket_total_balance + hyperliquid_balance + lighter_balance

        # 7. Собираем токены если запрошено
        tokens_data = None
        if collect_tokens:
            # Задержка между Rabby запросами
            _sleep_between_rabby_requests()

            tokens_result = get_evm_tokens(address, proxy_dict, timeout, min_token_value)
            if tokens_result and tokens_result.get('error') is None:
                tokens_data = tokens_result
                # Логируем токены если есть wallet_info
                if wallet_info:
                    tokens_list = [f"{symbol}: ${value:,.2f}" for symbol, value in tokens_data.items() if symbol != "error"]
                    if tokens_list:
                        info_log(f"{wallet_info} → Токены: {', '.join(tokens_list)}")

        # Выводим компактный результат одной строкой
        if wallet_info and not collect_tokens:  # Если токены уже залогированы выше, не дублируем баланс
            info_log(
                f"{wallet_info} → Сети: ${net_balance:,.2f} (данные отстают на {lag_minutes} мин {lag_secs} сек) | "
                f"DeFi & Other: ${apps_balance:,.2f} | Polymarket Positions: ${polymarket_positions_balance:,.2f} | "
                f"Polymarket Total: ${polymarket_total_balance:,.2f} | Hyperliquid: ${hyperliquid_balance:,.2f} | "
                f"Lighter: ${lighter_balance:,.2f} | Итого: ${total_balance:,.2f}"
            )
        elif wallet_info and collect_tokens:  # Если собираем токены, логируем баланс + токены вместе
            info_log(
                f"{wallet_info} → Сети: ${net_balance:,.2f} (данные отстают на {lag_minutes} мин {lag_secs} сек) | "
                f"DeFi & Other: ${apps_balance:,.2f} | Polymarket Positions: ${polymarket_positions_balance:,.2f} | "
                f"Polymarket Total: ${polymarket_total_balance:,.2f} | Hyperliquid: ${hyperliquid_balance:,.2f} | "
                f"Lighter: ${lighter_balance:,.2f} | Итого: ${total_balance:,.2f}"
            )

        return {
            "net_balance": round(net_balance, 2),
            "apps_balance": round(apps_balance, 2),
            "polymarket_positions_balance": round(polymarket_positions_balance, 2),
            "polymarket_total_balance": round(polymarket_total_balance, 2),
            "hyperliquid_balance": round(hyperliquid_balance, 2),
            "lighter_balance": round(lighter_balance, 2),
            "total_balance": round(total_balance, 2),
            "data_age": data_age,
            "tokens": tokens_data,
            "error": None
        }

    except httpx.TimeoutException:
        if wallet_info:
            error_log(f"{wallet_info} → Ошибка: TIMEOUT")
        return {
            "net_balance": 0.0,
            "apps_balance": 0.0,
            "polymarket_positions_balance": 0.0,
            "polymarket_total_balance": 0.0,
            "hyperliquid_balance": 0.0,
            "lighter_balance": 0.0,
            "total_balance": 0.0,
            "data_age": "N/A",
            "tokens": None,
            "error": "TIMEOUT"
        }
    except Exception as e:
        if wallet_info:
            error_log(f"{wallet_info} → Ошибка: {str(e)[:50]}")
        return {
            "net_balance": 0.0,
            "apps_balance": 0.0,
            "polymarket_positions_balance": 0.0,
            "polymarket_total_balance": 0.0,
            "hyperliquid_balance": 0.0,
            "lighter_balance": 0.0,
            "total_balance": 0.0,
            "data_age": "N/A",
            "tokens": None,
            "error": "ERROR"
        }


def _get_base_balance_from_curve(
    address: str,
    proxy_dict: Optional[Dict[str, str]],
    timeout: int
) -> Optional[Tuple[float, int]]:
    """
    Получить базовый баланс из total_net_curve (последняя точка)

    Args:
        address: Адрес кошелька
        proxy_dict: Прокси или None
        timeout: Таймаут запроса

    Returns:
        Tuple (balance, lag_seconds) или None при ошибке
    """
    url_path = "/v1/user/total_net_curve"
    params = {
        "id": address.lower(),
        "days": "1"
    }

    try:
        # Генерируем подписи
        auth_headers = generate_signature("GET", url_path, params)
        if not auth_headers:
            return None

        # Полные заголовки
        headers = {**auth_headers, **RABBY_HEADERS_BASE}

        with create_httpx_client(proxy_dict, timeout=timeout) as client:
            response = client.get(
                f"{RABBY_API_BASE}{url_path}",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

        if isinstance(data, list) and len(data) > 0:
            last_point = data[-1]
            balance = last_point.get('usd_value', 0)
            timestamp = last_point.get('timestamp', 0)

            # Рассчитываем задержку данных
            current_time = int(time.time())
            lag_seconds = current_time - timestamp

            return (float(balance), lag_seconds)
        else:
            error_log("Пустой ответ от total_net_curve")
            return None

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            error_log("Rate limit (429) от Rabby API")
        else:
            error_log(f"HTTP ошибка {e.response.status_code} от Rabby API")
        return None
    except Exception as e:
        error_log(f"Ошибка получения базового баланса: {str(e)}")
        return None


def _get_apps_balance(
    address: str,
    proxy_dict: Optional[Dict[str, str]],
    timeout: int
) -> Optional[float]:
    """
    Получить баланс DeFi протоколов через simple_protocol_list

    Этот эндпоинт возвращает мелкие DeFi протоколы (Uniswap, Aave, Compound, Stargate и т.д.)
    Большие приложения (Polymarket, Hyperliquid) находятся в complex_app_list и считаются отдельно

    Args:
        address: Адрес кошелька
        proxy_dict: Прокси или None
        timeout: Таймаут запроса

    Returns:
        Баланс DeFi протоколов в USD или None при ошибке
    """
    url_path = "/v1/user/simple_protocol_list"
    params = {"id": address.lower()}

    try:
        # Генерируем подписи
        auth_headers = generate_signature("GET", url_path, params)
        if not auth_headers:
            return None

        # Полные заголовки
        headers = {**auth_headers, **RABBY_HEADERS_BASE}

        with create_httpx_client(proxy_dict, timeout=timeout) as client:
            response = client.get(
                f"{RABBY_API_BASE}{url_path}",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

        # API возвращает массив протоколов, суммируем все net_usd_value
        apps_balance = 0.0

        if isinstance(data, list):
            for protocol in data:
                net_value = protocol.get('net_usd_value', 0)
                apps_balance += float(net_value)

        return apps_balance

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            error_log("Rate limit (429) от Rabby API при получении DeFi протоколов")
        else:
            error_log(f"HTTP ошибка {e.response.status_code} от Rabby API при получении DeFi протоколов")
        return None
    except Exception as e:
        error_log(f"Ошибка получения баланса DeFi протоколов: {str(e)}")
        return None


def _get_polymarket_balance(
    address: str,
    proxy_dict: Optional[Dict[str, str]],
    timeout: int
) -> Optional[Tuple[float, float]]:
    """
    Получить баланс на Polymarket с разделением на позиции и общий баланс

    Args:
        address: Адрес кошелька
        proxy_dict: Прокси или None
        timeout: Таймаут запроса

    Returns:
        Tuple (positions_balance, total_balance) или None при ошибке
        - positions_balance: баланс открытых позиций (predictions)
        - total_balance: общий баланс (депозиты + позиции)
    """
    url_path = "/v1/user/complex_app_list"
    params = {"id": address.lower()}

    try:
        # Генерируем подписи
        auth_headers = generate_signature("GET", url_path, params)
        if not auth_headers:
            return None

        # Полные заголовки
        headers = {**auth_headers, **RABBY_HEADERS_BASE}

        with create_httpx_client(proxy_dict, timeout=timeout) as client:
            response = client.get(
                f"{RABBY_API_BASE}{url_path}",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

        # Ищем Polymarket в apps
        apps = data.get('apps', [])
        for app in apps:
            app_id = app.get('id', '')
            if app_id.lower() == 'polymarket':
                # Считаем баланс Polymarket (разделяем на позиции и общий)
                positions_balance = 0.0  # Только открытые позиции (predictions)
                total_balance = 0.0      # Все вместе (deposits + predictions)

                items = app.get('portfolio_item_list', [])
                for item in items:
                    net_value = item.get('stats', {}).get('net_usd_value', 0)
                    item_name = item.get('name', '')

                    # Все позиции добавляем в total
                    total_balance += float(net_value)

                    # Только Prediction позиции добавляем в positions
                    if item_name == 'Prediction':
                        positions_balance += float(net_value)

                return (positions_balance, total_balance)

        # Polymarket не найден - это нормально
        return (0.0, 0.0)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            error_log("Rate limit (429) от Rabby API при получении Polymarket")
        else:
            error_log(f"HTTP ошибка {e.response.status_code} от Rabby API при получении Polymarket")
        return None
    except Exception as e:
        error_log(f"Ошибка получения баланса Polymarket: {str(e)}")
        return None


def _get_hyperliquid_balance(
    address: str,
    proxy_dict: Optional[Dict[str, str]],
    timeout: int
) -> Optional[float]:
    """
    Получить баланс на Hyperliquid

    Args:
        address: Адрес кошелька
        proxy_dict: Прокси или None
        timeout: Таймаут запроса

    Returns:
        Баланс на Hyperliquid в USD или None при ошибке
    """
    url_path = "/v1/user/complex_app_list"
    params = {"id": address.lower()}

    try:
        # Генерируем подписи
        auth_headers = generate_signature("GET", url_path, params)
        if not auth_headers:
            return None

        # Полные заголовки
        headers = {**auth_headers, **RABBY_HEADERS_BASE}

        with create_httpx_client(proxy_dict, timeout=timeout) as client:
            response = client.get(
                f"{RABBY_API_BASE}{url_path}",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

        # Ищем Hyperliquid в apps
        apps = data.get('apps', [])
        for app in apps:
            app_id = app.get('id', '')
            if app_id.lower() == 'hyperliquid':
                # Считаем баланс Hyperliquid (все позиции вместе)
                hyperliquid_balance = 0.0
                items = app.get('portfolio_item_list', [])
                for item in items:
                    net_value = item.get('stats', {}).get('net_usd_value', 0)
                    hyperliquid_balance += float(net_value)
                return hyperliquid_balance

        # Hyperliquid не найден - это нормально
        return 0.0

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            error_log("Rate limit (429) от Rabby API при получении Hyperliquid")
        else:
            error_log(f"HTTP ошибка {e.response.status_code} от Rabby API при получении Hyperliquid")
        return None
    except Exception as e:
        error_log(f"Ошибка получения баланса Hyperliquid: {str(e)}")
        return None


def _get_lighter_balance(
    address: str,
    proxy_dict: Optional[Dict[str, str]],
    timeout: int
) -> Optional[float]:
    """
    Получить баланс на бирже Lighter DEX

    Args:
        address: Адрес кошелька
        proxy_dict: Прокси или None
        timeout: Таймаут запроса

    Returns:
        Баланс на Lighter в USD или None при ошибке
    """
    try:
        # Импортируем eth_utils для checksum адреса
        from eth_utils import to_checksum_address

        # Конвертируем адрес в checksum формат (ОБЯЗАТЕЛЬНО!)
        checksum_address = to_checksum_address(address)

        lighter_api_base = "https://mainnet.zklighter.elliot.ai"
        url_path = "/api/v1/account"
        params = {
            "by": "l1_address",
            "value": checksum_address
        }

        with create_httpx_client(proxy_dict, timeout=timeout) as client:
            response = client.get(
                f"{lighter_api_base}{url_path}",
                params=params
            )
            response.raise_for_status()
            data = response.json()

        # Получаем total_asset_value из первого аккаунта
        accounts = data.get('accounts', [])
        if accounts and len(accounts) > 0:
            total_asset_value = accounts[0].get('total_asset_value', '0')
            # total_asset_value может быть строкой, конвертируем в float
            return float(total_asset_value)
        else:
            # Нет аккаунта на Lighter - это нормально
            return 0.0

    except httpx.HTTPStatusError as e:
        if e.response.status_code in [400, 404]:
            # 400/404 означает что аккаунт не найден - это нормально
            return 0.0
        else:
            error_log(f"HTTP ошибка {e.response.status_code} от Lighter API")
            return None
    except Exception as e:
        error_log(f"Ошибка получения баланса Lighter: {str(e)}")
        return None


def get_evm_tokens(
    address: str,
    proxy_dict: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    min_value: float = 10.0
) -> Optional[Dict[str, float]]:
    """
    Получить статистику токенов на EVM кошельке с группировкой по символу

    Использует Rabby API /v1/user/token_list для получения списка всех токенов.
    Группирует токены по символу (ETH из разных сетей = одна монета).
    Фильтрует только проверенные токены (is_verified = True).
    Разделяет на отдельные токены (>= min_value) и категорию "Other" (< min_value).

    Args:
        address: Адрес кошелька
        proxy_dict: Словарь с прокси (формат httpx) или None
        timeout: Таймаут запроса в секундах
        min_value: Минимальная стоимость токена в USD для отдельного учета

    Returns:
        Словарь с токенами:
        {
            "ETH": 97.42,
            "USDE": 8.20,
            "Other": 15.50,  # Сумма всех токенов < min_value
            "error": None
        }
        или {"error": "ERROR_CODE"} при ошибке
    """
    url_path = "/v1/user/token_list"
    params = {"id": address.lower()}

    try:
        # Генерируем подписи
        auth_headers = generate_signature("GET", url_path, params)
        if not auth_headers:
            return {"error": "SIGNATURE_ERROR"}

        # Полные заголовки
        headers = {**auth_headers, **RABBY_HEADERS_BASE}

        with create_httpx_client(proxy_dict, timeout=timeout) as client:
            response = client.get(
                f"{RABBY_API_BASE}{url_path}",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            tokens = response.json()

        # Группируем токены по символу
        from collections import defaultdict
        tokens_by_symbol = defaultdict(float)

        for token in tokens:
            # Пропускаем непроверенные токены (скамы и фейки)
            if not token.get('is_verified', False):
                continue

            symbol = token.get('symbol', 'UNKNOWN')
            amount = token.get('amount', 0)
            price = token.get('price', 0)

            usd_value = amount * price
            tokens_by_symbol[symbol] += usd_value

        # Разделяем на отдельные токены и "Other"
        result = {}
        other_total = 0.0

        for symbol, total_value in tokens_by_symbol.items():
            if total_value >= min_value:
                result[symbol] = round(total_value, 2)
            else:
                other_total += total_value

        # Добавляем категорию "Other" если есть мелкие токены
        if other_total > 0:
            result["Other"] = round(other_total, 2)

        result["error"] = None
        return result

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            error_log("Rate limit (429) от Rabby API при получении токенов")
        else:
            error_log(f"HTTP ошибка {e.response.status_code} от Rabby API при получении токенов")
        return {"error": f"HTTP_{e.response.status_code}"}
    except Exception as e:
        error_log(f"Ошибка получения токенов: {str(e)}")
        return {"error": "ERROR"}
