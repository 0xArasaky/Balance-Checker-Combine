"""
Aptos (APT) balance checker
Получает балансы токенов и застейканного APT с использованием Aptos API
"""

from loguru import logger
from typing import Dict, Optional, List
from modules.utils.logger import error_log, info_log
from modules.utils.httpx_compat import create_httpx_client


# Константы
APTOS_API_BASE = "https://api.mainnet.aptoslabs.com/v1"
APTOS_GRAPHQL_URL = f"{APTOS_API_BASE}/graphql"
APTOS_VIEW_URL = f"{APTOS_API_BASE}/view"
APTOS_PRICE_URL = f"{APTOS_API_BASE}/analytics/token/historical_prices"

APT_ADDRESS = "0x1::aptos_coin::AptosCoin"
def _get_fungible_assets(address: str, proxy: Optional[str] = None, timeout: int = 30) -> Optional[List[Dict]]:
    """
    Получает все токены кошелька через GraphQL

    Returns:
        List[Dict]: Список токенов с amount, decimals, symbol, asset_type
        None: При ошибке API
    """
    query = """
    query getFungibleAssetBalances($where: current_fungible_asset_balances_bool_exp, $order_by: [current_fungible_asset_balances_order_by!]) {
      current_fungible_asset_balances(where: $where, order_by: $order_by, limit: 100) {
        amount
        asset_type
        metadata {
          decimals
          name
          symbol
          asset_type
        }
      }
    }
    """

    variables = {
        "where": {
            "_and": [
                {
                    "metadata": {
                        "asset_type": {
                            "_is_null": False
                        }
                    },
                    "owner_address": {
                        "_eq": address
                    }
                },
                {
                    "is_primary": {
                        "_neq": False
                    }
                }
            ]
        },
        "order_by": {
            "amount": "desc"
        }
    }

    try:
        with create_httpx_client(proxy, timeout=timeout) as client:
            response = client.post(
                APTOS_GRAPHQL_URL,
                json={"query": query, "variables": variables}
            )

        if response.status_code != 200:
            logger.error(f"GraphQL ошибка: {response.status_code}")
            return None

        data = response.json()
        balances = data.get("data", {}).get("current_fungible_asset_balances", [])

        tokens = []
        for balance in balances:
            metadata = balance.get("metadata", {})
            tokens.append({
                "amount": int(balance.get("amount", 0)),
                "decimals": metadata.get("decimals", 0),
                "symbol": metadata.get("symbol", "UNKNOWN"),
                "name": metadata.get("name", "Unknown Token"),
                "asset_type": balance.get("asset_type", "")
            })

        return tokens

    except Exception as e:
        logger.error(f"Ошибка получения токенов: {e}")
        return None


def _get_staked_apt(address: str, proxy: Optional[str] = None, timeout: int = 30) -> Optional[float]:
    """
    Получает застейканный APT через view функцию delegation_pool::get_stake

    Returns:
        float: Количество застейканного APT (с учетом decimals=8)
        None: При ошибке API (НЕ путать с 0.0 когда стейкинга просто нет)
    """
    # Сначала нужно получить адрес delegation pool для кошелька
    # Используем GraphQL запрос для поиска пула

    query = """
    query getDelegatedStaking($address: String!) {
      delegator_distinct_pool(
        where: {delegator_address: {_eq: $address}}
      ) {
        pool_address
      }
    }
    """

    variables = {"address": address}

    try:
        # Получаем адрес delegation pool
        with create_httpx_client(proxy, timeout=timeout) as client:
            response = client.post(
                APTOS_GRAPHQL_URL,
                json={"query": query, "variables": variables}
            )

        if response.status_code != 200:
            return None  # Ошибка API

        data = response.json()
        pools = data.get("data", {}).get("delegator_distinct_pool", [])

        if not pools:
            return 0.0  # Нет стейкинга - это нормально

        # Получаем баланс из каждого пула
        total_staked = 0

        for pool_info in pools:
            pool_address = pool_info.get("pool_address")

            # Делаем view запрос к delegation_pool::get_stake
            view_payload = {
                "function": "0x1::delegation_pool::get_stake",
                "type_arguments": [],
                "arguments": [pool_address, address]
            }

            with create_httpx_client(proxy, timeout=timeout) as client:
                view_response = client.post(
                    APTOS_VIEW_URL,
                    json=view_payload
                )

            if view_response.status_code == 200:
                result = view_response.json()
                # Формат ответа: ["active_stake", "inactive_stake", "pending_inactive_stake"]
                if result and len(result) > 0:
                    active_stake = int(result[0])
                    total_staked += active_stake

        # Конвертируем из octas (10^8) в APT
        return total_staked / (10 ** 8)

    except Exception as e:
        logger.error(f"Ошибка получения застейканного APT: {e}")
        return None


def _get_token_price(asset_type: str, proxy: Optional[str] = None, timeout: int = 30) -> Optional[float]:
    """
    Получает текущую цену токена из Aptos Analytics API

    Args:
        asset_type: Адрес контракта токена (например, "0x1::aptos_coin::AptosCoin")
        proxy: Прокси сервер

    Returns:
        float: Цена в USD или None если цена недоступна
    """
    try:
        with create_httpx_client(proxy, timeout=timeout) as client:
            response = client.get(
                APTOS_PRICE_URL,
                params={"address": asset_type, "lookback": "all"}
            )

        if response.status_code != 200:
            return None

        data = response.json()
        price_data = data.get("data", [])

        if not price_data:
            return None

        # data[0] содержит самую свежую цену!
        latest = price_data[0]
        price_usd = latest.get("price_usd", 0)

        return float(price_usd) if price_usd else None

    except Exception as e:
        logger.debug(f"Ошибка получения цены для {asset_type[:50]}: {e}")
        return None


def get_apt_balance(
    address: str,
    proxy_dict: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    wallet_info: Optional[str] = None,
    collect_tokens: bool = False,
    min_token_value: float = 1.0
) -> Dict[str, any]:
    """
    Проверяет баланс Aptos кошелька (главная функция для main.py)

    Args:
        address: Адрес кошелька (0x...)
        proxy_dict: Прокси словарь формата httpx или None
        timeout: Таймаут запроса в секундах
        wallet_info: Информация о кошельке для логов
        collect_tokens: Собирать ли статистику токенов
        min_token_value: Минимальная стоимость токена для отдельного учета

    Returns:
        Dict с ключами:
        - apt_balance: float - баланс APT (USD)
        - other_tokens_balance: float - баланс других токенов (USD)
        - staked_apt_balance: float - застейканный APT (USD)
        - total_balance: float - общий баланс (USD)
        - tokens: dict или None - статистика токенов (если collect_tokens=True)
        - error: Optional[str] - код ошибки
    """
    # Конвертируем proxy_dict в строку для внутренних функций
    proxy_str = None
    if proxy_dict and 'http://' in proxy_dict:
        proxy_str = proxy_dict['http://']
    elif proxy_dict and 'https://' in proxy_dict:
        proxy_str = proxy_dict['https://']

    # Вызываем внутреннюю функцию
    result = check_aptos_balance(address, proxy_str, timeout, collect_tokens, min_token_value)

    # Логируем результат
    if wallet_info:
        if result.get('error'):
            error_log(f"{wallet_info} → Ошибка: {result['error']}")
        else:
            # Логируем токены если собирали статистику
            tokens_data = result.get('tokens')
            if tokens_data and tokens_data.get('error') is None:
                tokens_list = [f"{symbol}: ${value:,.2f}" for symbol, value in tokens_data.items() if symbol != "error"]
                if tokens_list:
                    info_log(f"{wallet_info} → Токены: {', '.join(tokens_list)}")

            # Логируем баланс
            apt_bal = result.get('apt_balance', 0)
            other_bal = result.get('other_tokens_balance', 0)
            staked_bal = result.get('staked_apt_balance', 0)
            total_bal = result.get('total_balance', 0)

            info_log(
                f"{wallet_info} → "
                f"APT: ${apt_bal:,.2f} | "
                f"Другие токены: ${other_bal:,.2f} | "
                f"APT в стейкинге: ${staked_bal:,.2f} | "
                f"Итого: ${total_bal:,.2f}"
            )

    return result


def _process_token_data(
    token_details: List[Dict],
    min_value: float = 1.0
) -> Optional[Dict[str, float]]:
    """
    Обработать детали токенов в статистику с группировкой по символу

    Фильтрует токены с ценой и стоимостью > 0.
    Группирует токены по символу с умным именованием дубликатов.
    Разделяет на отдельные токены (>= min_value) и категорию "Other" (< min_value).

    Args:
        token_details: Список словарей с деталями токенов
            [{symbol, name, value, asset_type}, ...]
        min_value: Минимальная стоимость токена в USD для отдельного учета

    Returns:
        Словарь с токенами:
        {
            "APT": 3.34,
            "tAPT": 0.32,
            "Other": 0.13,
            "error": None
        }
    """
    try:
        # Группируем токены по символу
        # Формат: {symbol: [(value, name, asset_type), ...]}
        tokens_by_symbol = {}

        for token in token_details:
            symbol = token["symbol"]
            value = token["value"]
            name = token["name"]
            asset_type = token["asset_type"]

            if symbol not in tokens_by_symbol:
                tokens_by_symbol[symbol] = []
            tokens_by_symbol[symbol].append((value, name, asset_type))

        # Группируем токены по символу с умным именованием
        final_tokens = {}

        for symbol, details_list in tokens_by_symbol.items():
            # Если токен с таким символом один - просто суммируем стоимость
            if len(details_list) == 1:
                value, _, _ = details_list[0]
                final_tokens[symbol] = value
            else:
                # Несколько токенов с одним символом - нужно различать
                for value, name, asset_type in details_list:
                    # Проверяем уникальность по имени
                    if name and name != "Unknown Token":
                        # Проверяем есть ли уже токен с таким именем
                        token_key = f"{symbol} ({name})"
                        if token_key in final_tokens:
                            # Имя тоже совпадает - используем короткий asset_type
                            short_addr = f"{asset_type[:6]}...{asset_type[-4:]}" if len(asset_type) > 12 else asset_type
                            token_key = f"{symbol} ({short_addr})"
                    else:
                        # Нет имени - используем короткий asset_type
                        short_addr = f"{asset_type[:6]}...{asset_type[-4:]}" if len(asset_type) > 12 else asset_type
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
        error_log(f"Ошибка обработки токенов APT: {str(e)}")
        return {"error": "ERROR"}


def check_aptos_balance(
    address: str,
    proxy: Optional[str] = None,
    timeout: int = 30,
    collect_tokens: bool = False,
    min_token_value: float = 1.0
) -> Dict:
    """
    Проверяет полный баланс Aptos кошелька

    Args:
        address: Адрес кошелька (0x...)
        proxy: Прокси сервер в формате http://user:pass@host:port
        timeout: Таймаут запроса в секундах
        collect_tokens: Собирать ли статистику токенов
        min_token_value: Минимальная стоимость токена для отдельного учета

    Returns:
        Dict с ключами:
        - apt_balance: float - баланс APT на кошельке (USD)
        - other_tokens_balance: float - баланс других токенов (USD)
        - staked_apt_balance: float - застейканный APT (USD)
        - total_balance: float - общий баланс (USD)
        - tokens: dict или None - статистика токенов (если collect_tokens=True)
        - error: Optional[str] - код ошибки или None
    """

    try:
        # 1. Получаем все токены через GraphQL
        tokens = _get_fungible_assets(address, proxy, timeout)

        if tokens is None:
            # Ошибка API - вернем error для retry
            return {
                "apt_balance": 0.0,
                "other_tokens_balance": 0.0,
                "staked_apt_balance": 0.0,
                "total_balance": 0.0,
                "tokens": None,
                "error": "API_ERROR"
            }

        # Пустой список токенов - это нормально (кошелек без токенов)

        # 2. Разделяем токены на APT и остальные
        apt_token = None
        other_tokens = []

        for token in tokens:
            if token["asset_type"] == APT_ADDRESS:
                apt_token = token
            else:
                other_tokens.append(token)

        # 3. Получаем цену APT
        apt_price = _get_token_price(APT_ADDRESS, proxy, timeout)

        if not apt_price:
            logger.warning("Не удалось получить цену APT")
            return {
                "apt_balance": 0.0,
                "other_tokens_balance": 0.0,
                "staked_apt_balance": 0.0,
                "total_balance": 0.0,
                "tokens": None,
                "error": "APT_PRICE_ERROR"
            }

        # 4. Считаем баланс APT на кошельке
        apt_balance_usd = 0.0
        if apt_token:
            apt_amount = apt_token["amount"] / (10 ** apt_token["decimals"])
            apt_balance_usd = apt_amount * apt_price

        # Инициализируем список для сбора данных токенов (если нужно)
        token_details = []

        # Добавляем APT в статистику токенов если он есть и собираем статистику
        if collect_tokens and apt_token and apt_balance_usd > 0:
            token_details.append({
                "symbol": apt_token["symbol"],
                "name": apt_token["name"],
                "value": apt_balance_usd,
                "asset_type": apt_token["asset_type"]
            })

        # 5. Считаем баланс других токенов
        other_tokens_balance_usd = 0.0

        for token in other_tokens:
            # Пропускаем токены с нулевым балансом
            if token["amount"] == 0:
                continue

            # Получаем цену токена
            token_price = _get_token_price(token["asset_type"], proxy, timeout)

            if token_price:
                token_amount = token["amount"] / (10 ** token["decimals"])
                token_value = token_amount * token_price
                other_tokens_balance_usd += token_value

                logger.debug(f"  {token['symbol']}: {token_amount:.4f} × ${token_price:.6f} = ${token_value:.2f}")

                # Собираем данные токенов для статистики (если нужно и стоимость > 0)
                if collect_tokens and token_value > 0:
                    token_details.append({
                        "symbol": token["symbol"],
                        "name": token["name"],
                        "value": token_value,
                        "asset_type": token["asset_type"]
                    })

        # 6. Получаем застейканный APT
        staked_apt_amount = _get_staked_apt(address, proxy, timeout)
        if staked_apt_amount is None:
            # Ошибка API - вернем error для retry
            return {
                "apt_balance": 0.0,
                "other_tokens_balance": 0.0,
                "staked_apt_balance": 0.0,
                "total_balance": 0.0,
                "tokens": None,
                "error": "API_ERROR"
            }

        staked_apt_balance_usd = staked_apt_amount * apt_price

        # 7. Считаем итоговый баланс
        total_balance = apt_balance_usd + other_tokens_balance_usd + staked_apt_balance_usd

        # 8. Обрабатываем токены если собирали статистику
        tokens_data = None
        if collect_tokens:
            tokens_data = _process_token_data(token_details, min_token_value)

        return {
            "apt_balance": apt_balance_usd,
            "other_tokens_balance": other_tokens_balance_usd,
            "staked_apt_balance": staked_apt_balance_usd,
            "total_balance": total_balance,
            "tokens": tokens_data,
            "error": None
        }

    except Exception as e:
        logger.error(f"Критическая ошибка проверки APT баланса: {e}")
        return {
            "apt_balance": 0.0,
            "other_tokens_balance": 0.0,
            "staked_apt_balance": 0.0,
            "total_balance": 0.0,
            "tokens": None,
            "error": "CRITICAL_ERROR"
        }
