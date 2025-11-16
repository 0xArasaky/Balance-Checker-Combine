import httpx
import json
import subprocess
import secrets
import string
import time
from pathlib import Path
from typing import Optional, Dict, Tuple
from modules.utils.logger import error_log, info_log, debug_log, success_log, warning_log

SCRIPT_DIR = Path(__file__).parent.parent.parent
SIGN_SCRIPT = SCRIPT_DIR / "scripts" / "generate_signature_with_nonce.js"

RABBY_API_BASE = "https://api.rabby.io"
RABBY_HEADERS_BASE = {
    "accept": "application/json, text/plain, */*",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "x-client": "Rabby",
    "x-version": "0.93.55"
}

def generate_nonce(length: int = 40) -> str:
    alphabet = string.ascii_letters + string.digits
    random_string = ''.join(secrets.choice(alphabet) for _ in range(length))
    return f"n_{random_string}"

def generate_signature(method: str, url: str, params: dict) -> Optional[Dict[str, str]]:
    try:
        nonce = generate_nonce()

        params_json = json.dumps(params)

        result = subprocess.run(
            ["node", str(SIGN_SCRIPT), method, url, params_json, nonce],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            error_log(f"Ошибка генерации подписи: {result.stderr}")
            return None

        headers = json.loads(result.stdout)

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
    try:
        base_result = _get_base_balance_from_curve(address, proxy_dict, timeout)
        if base_result is None:
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

        time.sleep(0.2)

        apps_balance = _get_apps_balance(address, proxy_dict, timeout)
        if apps_balance is None:
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

        time.sleep(0.2)

        polymarket_result = _get_polymarket_balance(address, proxy_dict, timeout)
        if polymarket_result is None:
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

        time.sleep(0.2)

        hyperliquid_balance = _get_hyperliquid_balance(address, proxy_dict, timeout)
        if hyperliquid_balance is None:
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

        time.sleep(0.2)

        lighter_balance = _get_lighter_balance(address, proxy_dict, timeout)
        if lighter_balance is None:
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

        total_balance = net_balance + apps_balance + polymarket_total_balance + hyperliquid_balance + lighter_balance

        tokens_data = None
        if collect_tokens:
            time.sleep(0.2)

            tokens_result = get_evm_tokens(address, proxy_dict, timeout, min_token_value)
            if tokens_result and tokens_result.get('error') is None:
                tokens_data = tokens_result
                if wallet_info:
                    tokens_list = [f"{symbol}: ${value:,.2f}" for symbol, value in tokens_data.items() if symbol != "error"]
                    info_log(f"{wallet_info} → Токены: {', '.join(tokens_list)}")

        if wallet_info and not collect_tokens:
            info_log(
                f"{wallet_info} → Сети: ${net_balance:,.2f} (данные отстают на {lag_minutes} мин {lag_secs} сек) | "
                f"DeFi & Other: ${apps_balance:,.2f} | Polymarket Positions: ${polymarket_positions_balance:,.2f} | "
                f"Polymarket Total: ${polymarket_total_balance:,.2f} | Hyperliquid: ${hyperliquid_balance:,.2f} | "
                f"Lighter: ${lighter_balance:,.2f} | Итого: ${total_balance:,.2f}"
            )
        elif wallet_info and collect_tokens:
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
    url_path = "/v1/user/total_net_curve"
    params = {
        "id": address.lower(),
        "days": "1"
    }

    try:
        auth_headers = generate_signature("GET", url_path, params)
        if not auth_headers:
            return None

        headers = {**auth_headers, **RABBY_HEADERS_BASE}

        with httpx.Client(proxies=proxy_dict, timeout=timeout) as client:
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
    url_path = "/v1/user/simple_protocol_list"
    params = {"id": address.lower()}

    try:
        auth_headers = generate_signature("GET", url_path, params)
        if not auth_headers:
            return None

        headers = {**auth_headers, **RABBY_HEADERS_BASE}

        with httpx.Client(proxies=proxy_dict, timeout=timeout) as client:
            response = client.get(
                f"{RABBY_API_BASE}{url_path}",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

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
    url_path = "/v1/user/complex_app_list"
    params = {"id": address.lower()}

    try:
        auth_headers = generate_signature("GET", url_path, params)
        if not auth_headers:
            return None

        headers = {**auth_headers, **RABBY_HEADERS_BASE}

        with httpx.Client(proxies=proxy_dict, timeout=timeout) as client:
            response = client.get(
                f"{RABBY_API_BASE}{url_path}",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

        apps = data.get('apps', [])
        for app in apps:
            app_id = app.get('id', '')
            if app_id.lower() == 'polymarket':
                positions_balance = 0.0
                total_balance = 0.0

                items = app.get('portfolio_item_list', [])
                for item in items:
                    net_value = item.get('stats', {}).get('net_usd_value', 0)
                    item_name = item.get('name', '')

                    total_balance += float(net_value)

                    if item_name == 'Prediction':
                        positions_balance += float(net_value)

                return (positions_balance, total_balance)

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
    url_path = "/v1/user/complex_app_list"
    params = {"id": address.lower()}

    try:
        auth_headers = generate_signature("GET", url_path, params)
        if not auth_headers:
            return None

        headers = {**auth_headers, **RABBY_HEADERS_BASE}

        with httpx.Client(proxies=proxy_dict, timeout=timeout) as client:
            response = client.get(
                f"{RABBY_API_BASE}{url_path}",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

        apps = data.get('apps', [])
        for app in apps:
            app_id = app.get('id', '')
            if app_id.lower() == 'hyperliquid':
                hyperliquid_balance = 0.0
                items = app.get('portfolio_item_list', [])
                for item in items:
                    net_value = item.get('stats', {}).get('net_usd_value', 0)
                    hyperliquid_balance += float(net_value)
                return hyperliquid_balance

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
    try:
        from eth_utils import to_checksum_address

        checksum_address = to_checksum_address(address)

        lighter_api_base = "https://mainnet.zklighter.elliot.ai"
        url_path = "/api/v1/account"
        params = {
            "by": "l1_address",
            "value": checksum_address
        }

        with httpx.Client(proxies=proxy_dict, timeout=timeout) as client:
            response = client.get(
                f"{lighter_api_base}{url_path}",
                params=params
            )
            response.raise_for_status()
            data = response.json()

        accounts = data.get('accounts', [])
        if accounts and len(accounts) > 0:
            total_asset_value = accounts[0].get('total_asset_value', '0')
            return float(total_asset_value)
        else:
            return 0.0

    except httpx.HTTPStatusError as e:
        if e.response.status_code in [400, 404]:
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
    url_path = "/v1/user/token_list"
    params = {"id": address.lower()}

    try:
        auth_headers = generate_signature("GET", url_path, params)
        if not auth_headers:
            return {"error": "SIGNATURE_ERROR"}

        headers = {**auth_headers, **RABBY_HEADERS_BASE}

        with httpx.Client(proxies=proxy_dict, timeout=timeout) as client:
            response = client.get(
                f"{RABBY_API_BASE}{url_path}",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            tokens = response.json()

        from collections import defaultdict
        tokens_by_symbol = defaultdict(float)

        for token in tokens:
            if not token.get('is_verified', False):
                continue

            symbol = token.get('symbol', 'UNKNOWN')
            amount = token.get('amount', 0)
            price = token.get('price', 0)

            usd_value = amount * price
            tokens_by_symbol[symbol] += usd_value

        result = {}
        other_total = 0.0

        for symbol, total_value in tokens_by_symbol.items():
            if total_value >= min_value:
                result[symbol] = round(total_value, 2)
            else:
                other_total += total_value

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
