import httpx
from typing import Optional, Dict
from modules.utils.logger import error_log, info_log, debug_log, success_log, warning_log

MEMPOOL_API_BASE = "https://mempool.space/api"
XVERSE_API_BASE = "https://api-3.xverse.app"

XVERSE_HEADERS = {
    "accept": "application/json",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def _is_taproot_address(address: str) -> bool:
    return address.startswith("bc1p")

def _get_btc_balance(
    address: str,
    proxy_dict: Optional[Dict[str, str]],
    timeout: int
) -> Optional[float]:
    try:
        with httpx.Client(proxies=proxy_dict, timeout=timeout) as client:
            addr_response = client.get(f"{MEMPOOL_API_BASE}/address/{address}")
            addr_response.raise_for_status()
            addr_data = addr_response.json()

            balance_sats = (
                addr_data['chain_stats']['funded_txo_sum'] -
                addr_data['chain_stats']['spent_txo_sum']
            )
            balance_btc = balance_sats / 100_000_000

            price_response = client.get(f"{MEMPOOL_API_BASE}/v1/prices")
            price_response.raise_for_status()
            btc_price = price_response.json()['USD']

            balance_usd = balance_btc * btc_price
            return round(balance_usd, 2)

    except httpx.HTTPStatusError as e:
        error_log(f"HTTP ошибка {e.response.status_code} от mempool.space")
        return None
    except Exception as e:
        error_log(f"Ошибка получения BTC баланса: {str(e)}")
        return None

def _get_runes_balance(
    address: str,
    proxy_dict: Optional[Dict[str, str]],
    timeout: int
) -> Optional[float]:
    try:
        with httpx.Client(proxies=proxy_dict, timeout=timeout) as client:
            response = client.get(
                f"{XVERSE_API_BASE}/v2/address/{address}/rune-balance",
                params={"includeUnconfirmed": "true"},
                headers=XVERSE_HEADERS
            )
            response.raise_for_status()
            runes = response.json()

            if not runes:
                return 0.0

            rune_ids = [rune.get('id') for rune in runes if rune.get('id')]

            headers = {
                **XVERSE_HEADERS,
                "content-type": "application/json"
            }

            fiat_response = client.post(
                f"{XVERSE_API_BASE}/v2/runes/fiat-rates",
                json={"currency": "USD", "runeIds": rune_ids},
                headers=headers
            )
            fiat_response.raise_for_status()
            fiat_rates = fiat_response.json()

            total_value = 0.0
            for rune in runes:
                rune_id = rune.get('id', '')
                amount = rune.get('amount', 0)
                divisibility = rune.get('divisibility', 0)

                usd_price = 0.0
                if rune_id in fiat_rates and 'USD' in fiat_rates[rune_id]:
                    usd_price = fiat_rates[rune_id]['USD']

                balance = amount / (10 ** divisibility)
                value = balance * usd_price
                total_value += value

            return round(total_value, 2)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return 0.0
        error_log(f"HTTP ошибка {e.response.status_code} от XVerse (runes)")
        return None
    except Exception as e:
        error_log(f"Ошибка получения баланса рун: {str(e)}")
        return None

def _get_inscriptions_balance(
    address: str,
    proxy_dict: Optional[Dict[str, str]],
    timeout: int
) -> Optional[float]:
    try:
        body = {
            "limit": 30,
            "offset": 0,
            "filters": {
                "hiddenCollectibleIds": []
            }
        }

        headers = {
            **XVERSE_HEADERS,
            "content-type": "application/json"
        }

        with httpx.Client(proxies=proxy_dict, timeout=timeout) as client:
            response = client.post(
                f"{XVERSE_API_BASE}/v2/address/{address}/ordinals/collections",
                json=body,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            total_value = 0.0
            collections = data.get('results', [])

            debug_log(f"Найдено {len(collections)} коллекций инскрипций")

            for collection in collections:
                collection_name = collection.get('collection_name', 'Unknown')
                total_inscriptions = collection.get('total_inscriptions', 0)
                floor_price_usd = collection.get('inscription_floor_price_usd', 0)

                value = total_inscriptions * floor_price_usd
                total_value += value

                debug_log(
                    f"  {collection_name}: {total_inscriptions} шт × "
                    f"${floor_price_usd:.2f} = ${value:.2f}"
                )

            return round(total_value, 2)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return 0.0
        error_log(f"HTTP ошибка {e.response.status_code} от XVerse (inscriptions)")
        return None
    except Exception as e:
        error_log(f"Ошибка получения баланса инскрипций: {str(e)}")
        return None

def get_btc_balance(
    address: str,
    proxy_dict: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    wallet_info: Optional[str] = None
) -> Dict[str, any]:
    try:
        btc_balance = _get_btc_balance(address, proxy_dict, timeout)
        if btc_balance is None:
            return {
                "btc_balance": 0.0,
                "runes_balance": 0.0,
                "inscriptions_balance": 0.0,
                "total_balance": 0.0,
                "error": "API_ERROR"
            }

        runes_balance = 0.0
        inscriptions_balance = 0.0

        if _is_taproot_address(address):
            runes_result = _get_runes_balance(address, proxy_dict, timeout)
            if runes_result is not None:
                runes_balance = runes_result
            else:
                return {
                    "btc_balance": 0.0,
                    "runes_balance": 0.0,
                    "inscriptions_balance": 0.0,
                    "total_balance": 0.0,
                    "error": "API_ERROR"
                }

            inscriptions_result = _get_inscriptions_balance(address, proxy_dict, timeout)
            if inscriptions_result is not None:
                inscriptions_balance = inscriptions_result
            else:
                return {
                    "btc_balance": 0.0,
                    "runes_balance": 0.0,
                    "inscriptions_balance": 0.0,
                    "total_balance": 0.0,
                    "error": "API_ERROR"
                }

        total_balance = btc_balance + runes_balance + inscriptions_balance

        if wallet_info:
            parts = [f"BTC: ${btc_balance:,.2f}"]
            if runes_balance > 0:
                parts.append(f"Руны: ${runes_balance:,.2f}")
            if inscriptions_balance > 0:
                parts.append(f"Инскрипции: ${inscriptions_balance:,.2f}")
            parts.append(f"Итого: ${total_balance:,.2f}")

            info_log(f"{wallet_info} → {' | '.join(parts)}")

        return {
            "btc_balance": round(btc_balance, 2),
            "runes_balance": round(runes_balance, 2),
            "inscriptions_balance": round(inscriptions_balance, 2),
            "total_balance": round(total_balance, 2),
            "error": None
        }

    except httpx.TimeoutException:
        if wallet_info:
            error_log(f"{wallet_info} → Ошибка: TIMEOUT")
        return {
            "btc_balance": 0.0,
            "runes_balance": 0.0,
            "inscriptions_balance": 0.0,
            "total_balance": 0.0,
            "error": "TIMEOUT"
        }
    except Exception as e:
        if wallet_info:
            error_log(f"{wallet_info} → Ошибка: {str(e)[:50]}")
        return {
            "btc_balance": 0.0,
            "runes_balance": 0.0,
            "inscriptions_balance": 0.0,
            "total_balance": 0.0,
            "error": "ERROR"
        }
