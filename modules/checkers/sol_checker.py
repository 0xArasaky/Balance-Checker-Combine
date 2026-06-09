"""
Модуль проверки Solana кошельков через Backpack API
Получает полный баланс (токены + DeFi)
"""

import httpx
import json
import hashlib
import time as time_module
from typing import Optional, Dict
from modules.utils.logger import error_log, info_log, debug_log, success_log
from modules.utils.httpx_compat import create_httpx_client

# Backpack API настройки
BACKPACK_API_URL = "https://backpack-api.xnfts.dev/v3/graphql"

def generate_backpack_signature(operation_name: str, query: str, timestamp: str) -> str:
    """
    Генерирует подпись для Backpack API
    Алгоритм: SHA256(JSON.stringify([1, operationName, query, timestamp]))
    """
    signature_version = 1
    # Формируем массив как в оригинальном коде расширения
    sign_data = json.dumps([signature_version, operation_name, query, timestamp], separators=(',', ':'))
    return hashlib.sha256(sign_data.encode('utf-8')).hexdigest()

def get_backpack_headers(operation_name: str, query: str) -> dict:
    """Генерирует заголовки с подписью для Backpack API"""
    timestamp = str(int(time_module.time() * 1000))  # миллисекунды как строка
    signature = generate_backpack_signature(operation_name, query, timestamp)

    return {
        "accept": "*/*",
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "apollographql-client-name": "backpack-extension",
        "apollographql-client-version": "0.10.186",
        "content-type": "application/json",
        "origin": "chrome-extension://aflkmfhebedbjioipglgcbcmnbpgliof",
        "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "none",
        "sec-fetch-storage-access": "active",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "x-backpack-cache-key-prefix": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp",
        "x-backpack-ignore-response-cache": "false",
        "x-backpack-signature": signature,
        "x-backpack-signature-version": "1",
        "x-backpack-timestamp": str(timestamp),
        "x-blockchain-caip2": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp",
    }

# Старые заголовки для обратной совместимости (не используются)
BACKPACK_HEADERS = {
    "accept": "*/*",
    "content-type": "application/json",
}

# GraphQL запрос для токенов
TOKENS_QUERY = """
query GetTokenBalances($address: String!, $caip2: Caip2!) {
  wallet(address: $address, caip2: $caip2) {
    id
    balances {
      id
      aggregate {
        id
        percentChange
        value
        valueChange
        __typename
      }
      tokens {
        edges {
          node {
            id
            address
            amount
            decimals
            displayAmount
            marketData {
              id
              price
              value
              __typename
            }
            token
            tokenListEntry {
              id
              symbol
              name
              __typename
            }
            __typename
          }
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
}
"""

# GraphQL запрос для DeFi позиций
POSITIONS_QUERY = """
query GetPositions($address: String!, $caip2: Caip2!) {
  wallet(address: $address, caip2: $caip2) {
    id
    positions {
      id
      assets {
        amount
        category
        symbol
        type
        value
        __typename
      }
      platform
      url
      value
      __typename
    }
    __typename
  }
}
"""


def get_sol_balance(
    address: str,
    proxy_dict: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    wallet_info: Optional[str] = None,
    collect_tokens: bool = False,
    min_token_value: float = 1.0
) -> Dict[str, any]:
    """
    Получить полный баланс Solana кошелька с детализацией

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
            "tokens_balance": float,   # Баланс токенов
            "defi_balance": float,     # Баланс DeFi позиций
            "total_balance": float,    # Общий баланс
            "tokens": dict или None,   # Статистика токенов (если collect_tokens=True)
            "error": str или None      # Код ошибки если есть
        }
    """
    try:
        # Получаем токены (один запрос возвращает И сумму, И сырые данные)
        tokens_result = _get_tokens_data(address, proxy_dict, timeout)
        if tokens_result is None:
            # Ошибка API - вернем error для retry
            return {
                "tokens_balance": 0.0,
                "defi_balance": 0.0,
                "total_balance": 0.0,
                "tokens": None,
                "error": "API_ERROR"
            }

        tokens_value, token_edges = tokens_result

        # Получаем DeFi позиции
        defi_value = _get_defi_value(address, proxy_dict, timeout)
        if defi_value is None:
            # Ошибка API - вернем error для retry
            return {
                "tokens_balance": 0.0,
                "defi_balance": 0.0,
                "total_balance": 0.0,
                "tokens": None,
                "error": "API_ERROR"
            }

        # Считаем полный баланс
        total_balance = tokens_value + defi_value

        # Собираем токены если запрошено (используем уже полученные данные)
        tokens_data = None
        if collect_tokens:
            tokens_data = _process_token_edges(token_edges, min_token_value)
            # Логируем токены если есть wallet_info
            if wallet_info and tokens_data:
                tokens_list = [f"{symbol}: ${value:,.2f}" for symbol, value in tokens_data.items() if symbol != "error"]
                if tokens_list:
                    info_log(f"{wallet_info} → Токены: {', '.join(tokens_list)}")

        # Выводим компактный результат одной строкой
        if wallet_info and not collect_tokens:  # Если токены уже залогированы выше, не дублируем баланс
            info_log(
                f"{wallet_info} → Токены: ${tokens_value:,.2f} | "
                f"DeFi: ${defi_value:,.2f} | Итого: ${total_balance:,.2f}"
            )
        elif wallet_info and collect_tokens:  # Если собираем токены, логируем баланс + токены вместе
            info_log(
                f"{wallet_info} → Токены: ${tokens_value:,.2f} | "
                f"DeFi: ${defi_value:,.2f} | Итого: ${total_balance:,.2f}"
            )

        return {
            "tokens_balance": round(tokens_value, 2),
            "defi_balance": round(defi_value, 2),
            "total_balance": round(total_balance, 2),
            "tokens": tokens_data,
            "error": None
        }

    except httpx.TimeoutException:
        if wallet_info:
            error_log(f"{wallet_info} → Ошибка: TIMEOUT")
        return {
            "tokens_balance": 0.0,
            "defi_balance": 0.0,
            "total_balance": 0.0,
            "tokens": None,
            "error": "TIMEOUT"
        }
    except Exception as e:
        if wallet_info:
            error_log(f"{wallet_info} → Ошибка: {str(e)[:50]}")
        return {
            "tokens_balance": 0.0,
            "defi_balance": 0.0,
            "total_balance": 0.0,
            "tokens": None,
            "error": "ERROR"
        }


def _get_tokens_data(
    address: str,
    proxy_dict: Optional[Dict[str, str]],
    timeout: int
) -> Optional[tuple]:
    """
    Получить данные токенов через GraphQL API (ОПТИМИЗИРОВАНО)

    Один запрос возвращает И общую стоимость, И сырые данные токенов.
    Это избегает дублирования запросов при сборе статистики.

    Args:
        address: Адрес кошелька
        proxy_dict: Прокси или None
        timeout: Таймаут запроса

    Returns:
        Tuple (total_value, token_edges) или None при ошибке
        - total_value: общая стоимость токенов в USD
        - token_edges: список сырых данных токенов для обработки
    """
    try:
        payload = {
            "operationName": "GetTokenBalances",
            "variables": {
                "address": address,
                "caip2": {
                    "namespace": "solana",
                    "reference": "5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"
                }
            },
            "query": TOKENS_QUERY
        }

        body = json.dumps(payload, separators=(',', ':'))
        headers = get_backpack_headers(payload["operationName"], payload["query"])

        with create_httpx_client(proxy_dict, timeout=timeout) as client:
            response = client.post(
                BACKPACK_API_URL,
                headers=headers,
                content=body
            )
            response.raise_for_status()
            data = response.json()

        # Проверяем на GraphQL ошибки
        if "errors" in data:
            error_log(f"GraphQL ошибка при получении токенов: {data['errors']}")
            return None

        # Извлекаем данные
        wallet_data = data.get("data", {}).get("wallet", {})
        balances = wallet_data.get("balances", {})

        # Общая стоимость
        aggregate = balances.get("aggregate", {})
        tokens_value = float(aggregate.get("value", 0))

        # Сырые данные токенов
        token_edges = balances.get("tokens", {}).get("edges", [])

        return (tokens_value, token_edges)

    except httpx.HTTPStatusError as e:
        error_log(f"HTTP ошибка {e.response.status_code} от Backpack API")
        return None
    except Exception as e:
        error_log(f"Ошибка получения токенов: {str(e)}")
        return None


def _process_token_edges(
    token_edges: list,
    min_value: float = 1.0
) -> Optional[Dict[str, float]]:
    """
    Обработать сырые данные токенов в статистику с группировкой по символу

    Фильтрует токены где marketData.value > 0 (отсекает скамы без рыночных данных).
    Группирует токены по символу с умным именованием дубликатов.
    Разделяет на отдельные токены (>= min_value) и категорию "Other" (< min_value).

    Args:
        token_edges: Список сырых данных токенов из GraphQL API
        min_value: Минимальная стоимость токена в USD для отдельного учета

    Returns:
        Словарь с токенами:
        {
            "SOL": 33.68,
            "USDC": 213.31,
            "Other": 0.50,
            "error": None
        }
    """
    try:
        # Собираем детали токенов
        # Формат: {symbol: [(value, name, address), ...]}
        tokens_details = {}

        for edge in token_edges:
            node = edge.get("node", {})

            # Извлекаем market data
            market_data = node.get("marketData")
            if not market_data:
                continue  # Пропускаем токены без рыночных данных

            value = float(market_data.get("value", 0))
            if value <= 0:
                continue  # Пропускаем токены с нулевой стоимостью

            # Извлекаем символ и название
            token_list_entry = node.get("tokenListEntry", {})
            symbol = token_list_entry.get("symbol", "UNKNOWN")
            name = token_list_entry.get("name", "")
            token_address = node.get("address", "")

            # Добавляем в словарь
            if symbol not in tokens_details:
                tokens_details[symbol] = []
            tokens_details[symbol].append((value, name, token_address))

        # Группируем токены по символу с умным именованием
        final_tokens = {}

        for symbol, details_list in tokens_details.items():
            # Если токен с таким символом один - просто суммируем стоимость
            if len(details_list) == 1:
                value, _, _ = details_list[0]
                final_tokens[symbol] = value
            else:
                # Несколько токенов с одним символом - нужно различать
                for value, name, token_address in details_list:
                    # Проверяем уникальность по имени
                    if name:
                        # Проверяем есть ли уже токен с таким именем
                        token_key = f"{symbol} ({name})"
                        if token_key in final_tokens:
                            # Имя тоже совпадает - используем адрес
                            short_addr = f"{token_address[:4]}...{token_address[-4:]}" if len(token_address) > 8 else token_address
                            token_key = f"{symbol} ({short_addr})"
                    else:
                        # Нет имени - используем адрес
                        short_addr = f"{token_address[:4]}...{token_address[-4:]}" if len(token_address) > 8 else token_address
                        token_key = f"{symbol} ({short_addr})"

                    # Добавляем или суммируем
                    final_tokens[token_key] = final_tokens.get(token_key, 0) + value

        # Разделяем на отдельные токены и "Other"
        result = {}
        other_total = 0.0

        for token_key, total_value in final_tokens.items():
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
        error_log(f"Ошибка обработки токенов SOL: {str(e)}")
        return {"error": "ERROR"}


def _get_defi_value(
    address: str,
    proxy_dict: Optional[Dict[str, str]],
    timeout: int
) -> Optional[float]:
    """
    Получить стоимость DeFi позиций через GraphQL API

    Args:
        address: Адрес кошелька
        proxy_dict: Прокси или None
        timeout: Таймаут запроса

    Returns:
        Стоимость DeFi позиций в USD или None при ошибке
    """
    try:
        payload = {
            "operationName": "GetPositions",
            "variables": {
                "address": address,
                "caip2": {
                    "namespace": "solana",
                    "reference": "5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"
                }
            },
            "query": POSITIONS_QUERY
        }

        body = json.dumps(payload, separators=(',', ':'))
        headers = get_backpack_headers(payload["operationName"], payload["query"])

        with create_httpx_client(proxy_dict, timeout=timeout) as client:
            response = client.post(
                BACKPACK_API_URL,
                headers=headers,
                content=body
            )
            response.raise_for_status()
            data = response.json()

        # Проверяем на GraphQL ошибки
        if "errors" in data:
            error_log(f"GraphQL ошибка при получении DeFi: {data['errors']}")
            return None

        # Извлекаем значение
        wallet_data = data.get("data", {}).get("wallet", {})
        positions = wallet_data.get("positions", [])

        # Считаем DeFi баланс
        defi_value = sum(float(pos.get("value", 0)) for pos in positions)

        return defi_value

    except httpx.HTTPStatusError as e:
        error_log(f"HTTP ошибка {e.response.status_code} от Backpack API при получении DeFi")
        return None
    except Exception as e:
        error_log(f"Ошибка получения DeFi позиций: {str(e)}")
        return None


def get_sol_tokens(
    address: str,
    proxy_dict: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    min_value: float = 1.0
) -> Optional[Dict[str, float]]:
    """
    Получить статистику токенов на Solana кошельке с группировкой по символу

    Использует Backpack API GraphQL для получения списка всех токенов.
    Фильтрует токены где marketData.value > 0 (отсекает скамы без рыночных данных).
    Группирует токены по символу с умным именованием дубликатов.
    Разделяет на отдельные токены (>= min_value) и категорию "Other" (< min_value).

    Args:
        address: Адрес кошелька
        proxy_dict: Словарь с прокси (формат httpx) или None
        timeout: Таймаут запроса в секундах
        min_value: Минимальная стоимость токена в USD для отдельного учета

    Returns:
        Словарь с токенами:
        {
            "SOL": 33.68,
            "USDC": 213.31,
            "Other": 0.50,  # Сумма всех токенов < min_value
            "error": None
        }
        или {"error": "ERROR_CODE"} при ошибке
    """
    try:
        payload = {
            "operationName": "GetTokenBalances",
            "variables": {
                "address": address,
                "caip2": {
                    "namespace": "solana",
                    "reference": "5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"
                }
            },
            "query": TOKENS_QUERY
        }

        body = json.dumps(payload, separators=(',', ':'))
        headers = get_backpack_headers(payload["operationName"], payload["query"])

        with create_httpx_client(proxy_dict, timeout=timeout) as client:
            response = client.post(
                BACKPACK_API_URL,
                headers=headers,
                content=body
            )
            response.raise_for_status()
            data = response.json()

        # Проверяем на GraphQL ошибки
        if "errors" in data:
            error_log(f"GraphQL ошибка при получении токенов: {data['errors']}")
            return {"error": "GRAPHQL_ERROR"}

        # Извлекаем токены
        wallet_data = data.get("data", {}).get("wallet", {})
        balances = wallet_data.get("balances", {})
        token_edges = balances.get("tokens", {}).get("edges", [])

        # Собираем детали токенов
        # Формат: {symbol: [(value, name, address), ...]}
        tokens_details = {}

        for edge in token_edges:
            node = edge.get("node", {})

            # Извлекаем market data
            market_data = node.get("marketData")
            if not market_data:
                continue  # Пропускаем токены без рыночных данных

            value = float(market_data.get("value", 0))
            if value <= 0:
                continue  # Пропускаем токены с нулевой стоимостью

            # Извлекаем символ и название
            token_list_entry = node.get("tokenListEntry", {})
            symbol = token_list_entry.get("symbol", "UNKNOWN")
            name = token_list_entry.get("name", "")
            token_address = node.get("address", "")

            # Добавляем в словарь
            if symbol not in tokens_details:
                tokens_details[symbol] = []
            tokens_details[symbol].append((value, name, token_address))

        # Группируем токены по символу с умным именованием
        from collections import defaultdict
        final_tokens = {}

        for symbol, details_list in tokens_details.items():
            # Если токен с таким символом один - просто суммируем стоимость
            if len(details_list) == 1:
                value, _, _ = details_list[0]
                final_tokens[symbol] = value
            else:
                # Несколько токенов с одним символом - нужно различать
                for value, name, token_address in details_list:
                    # Проверяем уникальность по имени
                    if name:
                        # Проверяем есть ли уже токен с таким именем
                        token_key = f"{symbol} ({name})"
                        if token_key in final_tokens:
                            # Имя тоже совпадает - используем адрес
                            short_addr = f"{token_address[:4]}...{token_address[-4:]}" if len(token_address) > 8 else token_address
                            token_key = f"{symbol} ({short_addr})"
                    else:
                        # Нет имени - используем адрес
                        short_addr = f"{token_address[:4]}...{token_address[-4:]}" if len(token_address) > 8 else token_address
                        token_key = f"{symbol} ({short_addr})"

                    # Добавляем или суммируем
                    final_tokens[token_key] = final_tokens.get(token_key, 0) + value

        # Разделяем на отдельные токены и "Other"
        result = {}
        other_total = 0.0

        for token_key, total_value in final_tokens.items():
            if total_value >= min_value:
                result[token_key] = round(total_value, 2)
            else:
                other_total += total_value

        # Добавляем категорию "Other" если есть мелкие токены
        if other_total > 0:
            result["Other"] = round(other_total, 2)

        result["error"] = None
        return result

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            error_log("Rate limit (429) от Backpack API при получении токенов")
        else:
            error_log(f"HTTP ошибка {e.response.status_code} от Backpack API при получении токенов")
        return {"error": f"HTTP_{e.response.status_code}"}
    except Exception as e:
        error_log(f"Ошибка получения токенов SOL: {str(e)}")
        return {"error": "ERROR"}
