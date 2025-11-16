from pathlib import Path
from typing import Optional, Dict, List
import random
import httpx
from modules.utils.logger import error_log, info_log, warning_log, success_log


class ProxyManager:

    def __init__(self, proxy_file: str = "proxies.txt"):
        self.proxy_file = Path(proxy_file)
        self.proxies = []
        self.current_index = 0
        self.failed_proxies = set()

    def load_proxies(self) -> bool:
        try:
            if not self.proxy_file.exists():
                error_log(f"Файл прокси не найден: {self.proxy_file}")
                return False

            with open(self.proxy_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            self.proxies = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    self.proxies.append(line)

            if not self.proxies:
                error_log("Файл прокси пустой")
                return False

            info_log(f"Загружено {len(self.proxies)} прокси")
            return True

        except Exception as e:
            error_log(f"Ошибка загрузки прокси: {str(e)}")
            return False

    def _parse_proxy(self, proxy_string: str) -> Optional[Dict[str, str]]:
        try:
            parts = proxy_string.split(':')
            if len(parts) != 4:
                warning_log(f"Неверный формат прокси: {proxy_string}")
                return None

            host, port, user, password = parts
            proxy_url = f"http://{user}:{password}@{host}:{port}"

            return {
                "http://": proxy_url,
                "https://": proxy_url
            }

        except Exception as e:
            error_log(f"Ошибка парсинга прокси: {str(e)}")
            return None

    def get_proxy(self, random_selection: bool = False) -> Optional[Dict[str, str]]:
        if not self.proxies:
            error_log("Список прокси пуст")
            return None

        if len(self.failed_proxies) >= len(self.proxies):
            warning_log("Все прокси помечены как неработающие, сбрасываем список")
            self.failed_proxies.clear()

        available_proxies = [p for p in self.proxies if p not in self.failed_proxies]

        if not available_proxies:
            error_log("Нет доступных прокси")
            return None

        if random_selection:
            proxy_string = random.choice(available_proxies)
        else:
            while self.proxies[self.current_index] in self.failed_proxies:
                self.current_index = (self.current_index + 1) % len(self.proxies)

            proxy_string = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)

        return self._parse_proxy(proxy_string)

    def mark_proxy_failed(self, proxy_dict: Dict[str, str]) -> None:
        try:
            proxy_url = proxy_dict.get("http://", "")
            if not proxy_url:
                return

            if "@" in proxy_url:
                auth_part, server_part = proxy_url.split("@")
                user_pass = auth_part.replace("http://", "")
                user, password = user_pass.split(":")
                host, port = server_part.rsplit(":", 1)

                proxy_string = f"{host}:{port}:{user}:{password}"

                if proxy_string in self.proxies:
                    self.failed_proxies.add(proxy_string)
                    warning_log(f"Прокси помечен как неработающий: {host}:{port}")

        except Exception as e:
            error_log(f"Ошибка при пометке прокси как неработающего: {str(e)}")

    def get_proxy_count(self) -> int:
        return len(self.proxies)

    def get_available_proxy_count(self) -> int:
        return len(self.proxies) - len(self.failed_proxies)
