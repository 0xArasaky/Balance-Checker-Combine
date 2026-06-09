"""
Совместимость с разными версиями HTTPX для прокси.
"""

from typing import Any, Dict, Optional, Union

import httpx


ProxyConfig = Optional[Union[str, Dict[str, str]]]


def create_httpx_client(proxy_dict: ProxyConfig = None, **kwargs: Any) -> httpx.Client:
    """
    Создать HTTPX client с прокси в формате проекта.

    HTTPX 0.28 удалил аргумент ``proxies``. Проект хранит прокси как
    {"http://": url, "https://": url}, поэтому здесь конвертируем его в
    актуальный API ``proxy`` или ``mounts``.
    """
    if not proxy_dict:
        return httpx.Client(**kwargs)

    if isinstance(proxy_dict, str):
        return httpx.Client(proxy=proxy_dict, **kwargs)

    http_proxy = proxy_dict.get("http://") or proxy_dict.get("http")
    https_proxy = proxy_dict.get("https://") or proxy_dict.get("https")

    if http_proxy and https_proxy and http_proxy != https_proxy:
        mounts = {
            "http://": httpx.HTTPTransport(proxy=http_proxy),
            "https://": httpx.HTTPTransport(proxy=https_proxy),
        }
        return httpx.Client(mounts=mounts, **kwargs)

    proxy_url = https_proxy or http_proxy
    if proxy_url:
        return httpx.Client(proxy=proxy_url, **kwargs)

    return httpx.Client(**kwargs)
