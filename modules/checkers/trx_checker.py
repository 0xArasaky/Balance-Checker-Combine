"""
TRON (TRX) balance checker
Получает TRX, USDT и другие TRC20 токены через TronLink API.
"""

import base64
import hashlib
import hmac
import random
import time
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional, Tuple

import httpx
from modules.utils.httpx_compat import create_httpx_client
from modules.utils.logger import debug_log, error_log, info_log, warning_log


TRONLINK_API_BASES = [
    "https://list.cdeshicde.org",
    "https://list.tronlink.org",
]
TRONLINK_ASSET_LIST_PATH = "/api/wallet/v2/assetList"
TRONLINK_VERSION = "4.10.1"
TRONLINK_EXTENSION_ID = "ibnejdfjmmkpcnlpebklmnkoeoihofec"
TRONLINK_SECRET_ID = "AE68A487AA919CAE"
TRONLINK_SECRET_KEY = "FMD5MW11TIIMYFSWDXVGQDUD9XR7GVV9XR29J"

TRONGRID_API_BASE = "https://api.trongrid.io"
TRON_USDT_CONTRACT_BASE58 = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
TRON_USDT_CONTRACT_HEX = "41A614F803B6FD780986A42C78EC9C7F77E6DED13C"

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _empty_result(error: str) -> Dict[str, any]:
    return {
        "trx_balance": 0.0,
        "usdt_balance": 0.0,
        "other_tokens_balance": 0.0,
        "total_balance": 0.0,
        "tokens": None,
        "source": None,
        "error": error,
    }


def _decimal(value: any, default: Decimal = Decimal("0")) -> Decimal:
    try:
        if value is None:
            return default
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def _base58_decode(value: str) -> bytes:
    num = 0
    for char in value:
        num *= 58
        if char not in BASE58_ALPHABET:
            raise ValueError("Invalid base58 character")
        num += BASE58_ALPHABET.index(char)

    decoded = num.to_bytes((num.bit_length() + 7) // 8, byteorder="big") if num else b""
    leading_zeroes = len(value) - len(value.lstrip("1"))
    return b"\x00" * leading_zeroes + decoded


def _base58check_to_payload(address: str) -> bytes:
    decoded = _base58_decode(address)
    if len(decoded) != 25:
        raise ValueError("Invalid TRON address length")

    payload, checksum = decoded[:-4], decoded[-4:]
    expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    if checksum != expected:
        raise ValueError("Invalid TRON address checksum")
    if payload[0] != 0x41:
        raise ValueError("Invalid TRON address prefix")

    return payload


def _address_to_hex(address: str) -> str:
    address = address.strip()
    if address.startswith("T"):
        return _base58check_to_payload(address).hex().upper()

    normalized = address.upper()
    if normalized.startswith("0X"):
        normalized = normalized[2:]

    if len(normalized) == 42 and normalized.startswith("41"):
        bytes.fromhex(normalized)
        return normalized

    raise ValueError("Invalid TRON address")


def _sign_tronlink_request(method: str, path: str, headers_for_sign: Dict[str, str]) -> str:
    picked = {
        key: headers_for_sign[key]
        for key in ["Lang", "System", "Version", "address", "chain", "channel", "nonce", "secretId", "ts"]
        if key in headers_for_sign
    }
    sign_query = "&".join(f"{key}={picked[key]}" for key in sorted(picked))
    sign_payload = f"{method.upper()}{path}{headers_for_sign.get('DeviceID', '')}?{sign_query}"
    return base64.b64encode(
        hmac.new(TRONLINK_SECRET_KEY.encode(), sign_payload.encode("utf-8"), hashlib.sha1).digest()
    ).decode()


def _build_tronlink_request(address_hex: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    nonce = str(random.randrange(10000))
    ts = str(int(time.time() * 1000))

    sign_headers = {
        "Lang": "1",
        "System": "chrome-extension",
        "Version": TRONLINK_VERSION,
        "DeviceID": "",
        "address": address_hex,
        "chain": "MainChain",
        "channel": "official",
        "nonce": nonce,
        "secretId": TRONLINK_SECRET_ID,
        "ts": ts,
    }
    signature = _sign_tronlink_request("GET", TRONLINK_ASSET_LIST_PATH, sign_headers)

    params = {
        "nonce": nonce,
        "secretId": TRONLINK_SECRET_ID,
        "signature": signature,
        "address": address_hex,
        "version": "v2",
    }
    headers = {
        "accept": "application/json, text/plain, */*",
        "address": address_hex,
        "chain": "MainChain",
        "channel": "official",
        "deviceid": "",
        "devicename": "",
        "extensionid": TRONLINK_EXTENSION_ID,
        "lang": "1",
        "nonce": nonce,
        "osversion": "",
        "packagename": "chrome.extension.wallet",
        "secretid": TRONLINK_SECRET_ID,
        "system": "chrome-extension",
        "ts": ts,
        "version": TRONLINK_VERSION,
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
        ),
    }
    return params, headers


def _fetch_tronlink_assets(
    address_hex: str,
    proxy_dict: Optional[Dict[str, str]],
    timeout: int,
) -> Optional[Dict]:
    params, headers = _build_tronlink_request(address_hex)

    for api_base in TRONLINK_API_BASES:
        try:
            with create_httpx_client(proxy_dict, timeout=timeout) as client:
                response = client.get(
                    f"{api_base}{TRONLINK_ASSET_LIST_PATH}",
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()

            if int(payload.get("code", -1)) == 0 and payload.get("data"):
                debug_log(f"TRX TronLink source: {api_base}")
                return payload["data"]

            warning_log(f"TronLink assetList вернул code={payload.get('code')} на {api_base}")
        except httpx.HTTPStatusError as e:
            warning_log(f"TronLink assetList HTTP {e.response.status_code} на {api_base}")
        except Exception as e:
            warning_log(f"TronLink assetList ошибка на {api_base}: {str(e)[:120]}")

    return None


def _token_symbol(token: Dict) -> str:
    if int(token.get("type", -1)) == 0:
        return "TRX"
    symbol = (token.get("shortName") or token.get("symbol") or token.get("name") or "").strip()
    return symbol or "UNKNOWN"


def _token_display_key(token: Dict, existing: Dict[str, float]) -> str:
    symbol = _token_symbol(token)
    if symbol not in existing:
        return symbol

    name = (token.get("name") or "").strip()
    if name:
        key = f"{symbol} ({name})"
        if key not in existing:
            return key

    contract = (token.get("contractAddress") or "").strip()
    if len(contract) > 12:
        return f"{symbol} ({contract[:6]}...{contract[-4:]})"
    return f"{symbol} ({contract})" if contract else symbol


def _is_core_usdt(token: Dict) -> bool:
    contract = (token.get("contractAddress") or "").strip()
    return contract == TRON_USDT_CONTRACT_BASE58 or contract.upper() == TRON_USDT_CONTRACT_HEX


def _is_eligible_token(token: Dict, value_usd: Decimal) -> bool:
    if value_usd <= 0:
        return False
    if token.get("isShield") is True:
        return False

    # TronLink уже считает usdCount только для токенов с рыночной ценой.
    # Для именованных деталей оставляем official/followed assets, остальное ниже порога уйдет в Other.
    return bool(token.get("isOfficial") == 1 or token.get("isInAssets") is True)


def _process_tronlink_data(data: Dict, collect_tokens: bool, min_token_value: float) -> Dict[str, any]:
    token_rows = data.get("token", []) or []
    trx_balance = Decimal("0")
    usdt_balance = Decimal("0")
    other_tokens_balance = Decimal("0")
    token_values: Dict[str, float] = {}
    other_bucket = Decimal("0")

    min_value = Decimal(str(min_token_value))

    for token in token_rows:
        value_usd = _decimal(token.get("usdCount"))
        if not _is_eligible_token(token, value_usd):
            continue

        symbol = _token_symbol(token)
        is_trx = int(token.get("type", -1)) == 0
        is_usdt = _is_core_usdt(token)

        if is_trx:
            trx_balance += value_usd
        elif is_usdt:
            usdt_balance += value_usd
        else:
            other_tokens_balance += value_usd

        if not collect_tokens:
            continue

        if value_usd >= min_value:
            key = _token_display_key(token, token_values)
            token_values[key] = token_values.get(key, 0.0) + float(value_usd)
        else:
            other_bucket += value_usd

    if collect_tokens:
        if other_bucket > 0:
            token_values["Other"] = float(other_bucket)
        token_values["error"] = None
        tokens_data = token_values
    else:
        tokens_data = None

    total_balance = trx_balance + usdt_balance + other_tokens_balance

    return {
        "trx_balance": float(trx_balance),
        "usdt_balance": float(usdt_balance),
        "other_tokens_balance": float(other_tokens_balance),
        "total_balance": float(total_balance),
        "tokens": tokens_data,
        "source": "tronlink",
        "error": None,
    }


def _trongrid_post(
    path: str,
    payload: Dict,
    proxy_dict: Optional[Dict[str, str]],
    timeout: int,
) -> Optional[Dict]:
    try:
        with create_httpx_client(proxy_dict, timeout=timeout) as client:
            response = client.post(
                f"{TRONGRID_API_BASE}{path}",
                json=payload,
                headers={"content-type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        warning_log(f"TronGrid {path} ошибка: {str(e)[:120]}")
        return None


def _get_trx_usd_price(
    proxy_dict: Optional[Dict[str, str]],
    timeout: int,
) -> Optional[Decimal]:
    price_urls = [
        ("Binance", "https://api.binance.com/api/v3/ticker/price?symbol=TRXUSDT"),
        ("CoinGecko", "https://api.coingecko.com/api/v3/simple/price?ids=tron&vs_currencies=usd"),
    ]

    for source, url in price_urls:
        try:
            with create_httpx_client(proxy_dict, timeout=timeout) as client:
                response = client.get(url, headers={"accept": "application/json"})
                response.raise_for_status()
                data = response.json()

            if source == "Binance":
                price = _decimal(data.get("price"))
            else:
                price = _decimal(data.get("tron", {}).get("usd"))

            if price > 0:
                return price
        except Exception as e:
            warning_log(f"TRX price fallback {source} ошибка: {str(e)[:120]}")

    return None


def _fetch_trongrid_fallback(
    address_hex: str,
    proxy_dict: Optional[Dict[str, str]],
    timeout: int,
    collect_tokens: bool,
    min_token_value: float,
) -> Dict[str, any]:
    account = _trongrid_post("/wallet/getaccount", {"address": address_hex}, proxy_dict, timeout)
    if account is None:
        return _empty_result("TRONGRID_ERROR")

    parameter = address_hex[2:].rjust(64, "0")
    usdt_data = _trongrid_post(
        "/wallet/triggerconstantcontract",
        {
            "owner_address": address_hex,
            "contract_address": TRON_USDT_CONTRACT_HEX,
            "function_selector": "balanceOf(address)",
            "parameter": parameter,
        },
        proxy_dict,
        timeout,
    )
    constant_result = (usdt_data or {}).get("constant_result") or []
    if not constant_result:
        return _empty_result("TRONGRID_ERROR")

    trx_price = _get_trx_usd_price(proxy_dict, timeout)
    if trx_price is None:
        return _empty_result("TRX_PRICE_ERROR")

    trx_amount = _decimal(account.get("balance")) / Decimal(1_000_000)
    usdt_amount = Decimal(int(constant_result[0], 16)) / Decimal(1_000_000)
    trx_balance = trx_amount * trx_price
    usdt_balance = usdt_amount
    total_balance = trx_balance + usdt_balance

    tokens_data = None
    if collect_tokens:
        tokens_data = {}
        min_value = Decimal(str(min_token_value))
        other_bucket = Decimal("0")

        for symbol, value in [("TRX", trx_balance), ("USDT", usdt_balance)]:
            if value <= 0:
                continue
            if value >= min_value:
                tokens_data[symbol] = float(value)
            else:
                other_bucket += value

        if other_bucket > 0:
            tokens_data["Other"] = float(other_bucket)
        tokens_data["error"] = None

    return {
        "trx_balance": float(trx_balance),
        "usdt_balance": float(usdt_balance),
        "other_tokens_balance": 0.0,
        "total_balance": float(total_balance),
        "tokens": tokens_data,
        "source": "trongrid",
        "error": None,
    }


def get_trx_balance(
    address: str,
    proxy_dict: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    wallet_info: Optional[str] = None,
    collect_tokens: bool = False,
    min_token_value: float = 1.0,
) -> Dict[str, any]:
    """
    Получить баланс TRON кошелька.

    Возвращает USD-стоимость TRX, canonical TRC20 USDT и остальных проверенных TRC20.
    Primary source: TronLink assetList. Fallback: TronGrid raw balances + public TRX price.
    """
    try:
        address_hex = _address_to_hex(address)
    except Exception:
        if wallet_info:
            error_log(f"{wallet_info} → Ошибка: INVALID_ADDRESS")
        return _empty_result("INVALID_ADDRESS")

    try:
        data = _fetch_tronlink_assets(address_hex, proxy_dict, timeout)
        if data is not None:
            result = _process_tronlink_data(data, collect_tokens, min_token_value)
        else:
            result = _fetch_trongrid_fallback(
                address_hex,
                proxy_dict,
                timeout,
                collect_tokens,
                min_token_value,
            )

        if wallet_info:
            if result.get("error"):
                error_log(f"{wallet_info} → Ошибка: {result['error']}")
            else:
                tokens_data = result.get("tokens")
                if tokens_data and tokens_data.get("error") is None:
                    token_parts = [
                        f"{symbol}: ${value:,.2f}"
                        for symbol, value in tokens_data.items()
                        if symbol != "error" and isinstance(value, (int, float)) and value > 0
                    ]
                    if token_parts:
                        info_log(f"{wallet_info} → Токены: {', '.join(token_parts)}")

                info_log(
                    f"{wallet_info} → "
                    f"TRX: ${result.get('trx_balance', 0):,.2f} | "
                    f"USDT: ${result.get('usdt_balance', 0):,.2f} | "
                    f"Другие токены: ${result.get('other_tokens_balance', 0):,.2f} | "
                    f"Итого: ${result.get('total_balance', 0):,.2f} "
                    f"({result.get('source')})"
                )

        return result

    except httpx.TimeoutException:
        if wallet_info:
            error_log(f"{wallet_info} → Ошибка: TIMEOUT")
        return _empty_result("TIMEOUT")
    except Exception as e:
        if wallet_info:
            error_log(f"{wallet_info} → Ошибка: {str(e)[:80]}")
        return _empty_result("ERROR")
