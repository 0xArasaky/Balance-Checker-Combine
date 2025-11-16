import httpx
from typing import Optional, Dict
from modules.utils.logger import error_log, info_log, debug_log, success_log

BACKPACK_API_URL = "https://backpack-api.xnfts.dev/v3/graphql"

BACKPACK_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US",
    "apollographql-client-name": "backpack-extension",
    "apollographql-client-version": "0.10.172",
    "content-type": "application/json",
    "origin": "chrome-extension://aflkmfhebedbjioipglgcbcmnbpgliof",
    "sec-ch-ua": '"Not=A?Brand";v="24", "Chromium";v="140"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "none",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "x-backpack-cache-key-prefix": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp",
    "x-backpack-ignore-response-cache": "false",
}

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
    try:
        tokens_result = _get_tokens_data(address, proxy_dict, timeout)
        if tokens_result is None:
            return {
                "tokens_balance": 0.0,
                "defi_balance": 0.0,
                "total_balance": 0.0,
                "tokens": None,
                "error": "API_ERROR"
            }

        tokens_value, token_edges = tokens_result

        defi_value = _get_defi_value(address, proxy_dict, timeout)
        if defi_value is None:
            return {
                "tokens_balance": 0.0,
                "defi_balance": 0.0,
                "total_balance": 0.0,
                "tokens": None,
                "error": "API_ERROR"
            }

        total_balance = tokens_value + defi_value

        tokens_data = None
        if collect_tokens:
            tokens_data = _process_token_edges(token_edges, min_token_value)
            if wallet_info and tokens_data:
                tokens_list = [f"{symbol}: ${value:,.2f}" for symbol, value in tokens_data.items() if symbol != "error"]
                info_log(f"{wallet_info} → Токены: {', '.join(tokens_list)}")

        if wallet_info and not collect_tokens:
            info_log(
                f"{wallet_info} → Токены: ${tokens_value:,.2f} | "
                f"DeFi: ${defi_value:,.2f} | Итого: ${total_balance:,.2f}"
            )
        elif wallet_info and collect_tokens:
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

        with httpx.Client(proxies=proxy_dict, timeout=timeout) as client:
            response = client.post(
                BACKPACK_API_URL,
                headers=BACKPACK_HEADERS,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

        if "errors" in data:
            error_log(f"GraphQL ошибка при получении токенов: {data['errors']}")
            return None

        wallet_data = data.get("data", {}).get("wallet", {})
        balances = wallet_data.get("balances", {})

        aggregate = balances.get("aggregate", {})
        tokens_value = float(aggregate.get("value", 0))

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
    try:
        tokens_details = {}

        for edge in token_edges:
            node = edge.get("node", {})

            market_data = node.get("marketData")
            if not market_data:
                continue

            value = float(market_data.get("value", 0))
            if value <= 0:
                continue

            token_list_entry = node.get("tokenListEntry", {})
            symbol = token_list_entry.get("symbol", "UNKNOWN")
            name = token_list_entry.get("name", "")
            token_address = node.get("address", "")

            if symbol not in tokens_details:
                tokens_details[symbol] = []
            tokens_details[symbol].append((value, name, token_address))

        final_tokens = {}

        for symbol, details_list in tokens_details.items():
            if len(details_list) == 1:
                value, _, _ = details_list[0]
                final_tokens[symbol] = value
            else:
                for value, name, token_address in details_list:
                    if name:
                        token_key = f"{symbol} ({name})"
                        if token_key in final_tokens:
                            short_addr = f"{token_address[:4]}...{token_address[-4:]}" if len(token_address) > 8 else token_address
                            token_key = f"{symbol} ({short_addr})"
                    else:
                        short_addr = f"{token_address[:4]}...{token_address[-4:]}" if len(token_address) > 8 else token_address
                        token_key = f"{symbol} ({short_addr})"

                    final_tokens[token_key] = final_tokens.get(token_key, 0) + value

        result = {}
        other_total = 0.0

        for token_key, total_value in final_tokens.items():
            if total_value >= min_value:
                result[token_key] = round(total_value, 2)
            else:
                other_total += total_value

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

        with httpx.Client(proxies=proxy_dict, timeout=timeout) as client:
            response = client.post(
                BACKPACK_API_URL,
                headers=BACKPACK_HEADERS,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

        if "errors" in data:
            error_log(f"GraphQL ошибка при получении DeFi: {data['errors']}")
            return None

        wallet_data = data.get("data", {}).get("wallet", {})
        positions = wallet_data.get("positions", [])

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

        with httpx.Client(proxies=proxy_dict, timeout=timeout) as client:
            response = client.post(
                BACKPACK_API_URL,
                headers=BACKPACK_HEADERS,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

        if "errors" in data:
            error_log(f"GraphQL ошибка при получении токенов: {data['errors']}")
            return {"error": "GRAPHQL_ERROR"}

        wallet_data = data.get("data", {}).get("wallet", {})
        balances = wallet_data.get("balances", {})
        token_edges = balances.get("tokens", {}).get("edges", [])

        tokens_details = {}

        for edge in token_edges:
            node = edge.get("node", {})

            market_data = node.get("marketData")
            if not market_data:
                continue

            value = float(market_data.get("value", 0))
            if value <= 0:
                continue

            token_list_entry = node.get("tokenListEntry", {})
            symbol = token_list_entry.get("symbol", "UNKNOWN")
            name = token_list_entry.get("name", "")
            token_address = node.get("address", "")

            if symbol not in tokens_details:
                tokens_details[symbol] = []
            tokens_details[symbol].append((value, name, token_address))

        from collections import defaultdict
        final_tokens = {}

        for symbol, details_list in tokens_details.items():
            if len(details_list) == 1:
                value, _, _ = details_list[0]
                final_tokens[symbol] = value
            else:
                for value, name, token_address in details_list:
                    if name:
                        token_key = f"{symbol} ({name})"
                        if token_key in final_tokens:
                            short_addr = f"{token_address[:4]}...{token_address[-4:]}" if len(token_address) > 8 else token_address
                            token_key = f"{symbol} ({short_addr})"
                    else:
                        short_addr = f"{token_address[:4]}...{token_address[-4:]}" if len(token_address) > 8 else token_address
                        token_key = f"{symbol} ({short_addr})"

                    final_tokens[token_key] = final_tokens.get(token_key, 0) + value

        result = {}
        other_total = 0.0

        for token_key, total_value in final_tokens.items():
            if total_value >= min_value:
                result[token_key] = round(total_value, 2)
            else:
                other_total += total_value

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
