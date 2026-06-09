"""
Модуль управления прокси для Balance Checker
Читает прокси из файла и обеспечивает ротацию
"""

from pathlib import Path
from typing import Optional, Dict, List
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from modules.utils.logger import error_log, info_log, warning_log, success_log
from modules.utils.httpx_compat import create_httpx_client


class ProxyManager:
    """Класс для управления прокси"""

    def __init__(self, proxy_file: str = "proxies.txt"):
        """
        Инициализация менеджера прокси

        Args:
            proxy_file: Путь к файлу с прокси
        """
        self.proxy_file = Path(proxy_file)
        self.proxies = []
        self.current_index = 0
        self.failed_proxies = set()

    def load_proxies(self) -> bool:
        """
        Загрузить прокси из файла

        Returns:
            True если прокси успешно загружены, иначе False
        """
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
        """
        Преобразовать строку прокси в формат для httpx

        Args:
            proxy_string: Строка вида "host:port:user:pass"

        Returns:
            Словарь с прокси для httpx или None при ошибке
        """
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
        """
        Получить следующий прокси

        Args:
            random_selection: Если True, выбирать случайный прокси

        Returns:
            Словарь с прокси для httpx или None если прокси нет
        """
        if not self.proxies:
            error_log("Список прокси пуст")
            return None

        # Если все прокси провалились
        if len(self.failed_proxies) >= len(self.proxies):
            warning_log("Все прокси помечены как неработающие, сбрасываем список")
            self.failed_proxies.clear()

        # Получаем доступные прокси
        available_proxies = [p for p in self.proxies if p not in self.failed_proxies]

        if not available_proxies:
            error_log("Нет доступных прокси")
            return None

        # Выбираем прокси
        if random_selection:
            proxy_string = random.choice(available_proxies)
        else:
            # Циклическая ротация
            while self.proxies[self.current_index] in self.failed_proxies:
                self.current_index = (self.current_index + 1) % len(self.proxies)

            proxy_string = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)

        return self._parse_proxy(proxy_string)

    def mark_proxy_failed(self, proxy_dict: Dict[str, str]) -> None:
        """
        Пометить прокси как неработающий

        Args:
            proxy_dict: Словарь прокси полученный из get_proxy()
        """
        # Извлекаем исходную строку прокси из URL
        try:
            proxy_url = proxy_dict.get("http://", "")
            if not proxy_url:
                return

            # Парсим URL обратно в строку формата host:port:user:pass
            # Формат: http://user:pass@host:port
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
        """Получить количество загруженных прокси"""
        return len(self.proxies)

    def get_available_proxy_count(self) -> int:
        """Получить количество доступных (не провалившихся) прокси"""
        return len(self.proxies) - len(self.failed_proxies)

    def _check_single_proxy(self, proxy_string: str, test_url: str, timeout: int) -> bool:
        """
        Проверить один прокси (для многопоточной проверки)

        Args:
            proxy_string: Строка прокси в формате host:port:user:pass
            test_url: URL для тестирования
            timeout: Таймаут запроса

        Returns:
            True если прокси работает, иначе False
        """
        proxy_dict = self._parse_proxy(proxy_string)
        if not proxy_dict:
            return False

        try:
            with create_httpx_client(proxy_dict, timeout=timeout) as client:
                response = client.get(test_url)
                return response.status_code == 200
        except Exception:
            return False

    def verify_proxies(self, test_url: str = "https://httpbin.org/ip", timeout: int = 10, max_workers: int = 50) -> int:
        """
        Проверить работоспособность всех прокси (многопоточно)

        Args:
            test_url: URL для тестирования прокси
            timeout: Таймаут для проверки каждого прокси (секунды)
            max_workers: Максимальное количество потоков для проверки

        Returns:
            Количество рабочих прокси
        """
        if not self.proxies:
            warning_log("Список прокси пуст, нечего проверять")
            return 0

        info_log(f"Начинаем проверку {len(self.proxies)} прокси ({max_workers} потоков)...")

        working_count = 0
        checked_count = 0
        total = len(self.proxies)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Запускаем проверку всех прокси
            future_to_proxy = {
                executor.submit(self._check_single_proxy, proxy_string, test_url, timeout): proxy_string
                for proxy_string in self.proxies
            }

            # Собираем результаты
            for future in as_completed(future_to_proxy):
                proxy_string = future_to_proxy[future]
                checked_count += 1

                try:
                    is_working = future.result()
                    if is_working:
                        working_count += 1
                    else:
                        self.failed_proxies.add(proxy_string)
                except Exception:
                    self.failed_proxies.add(proxy_string)

                # Логируем прогресс каждые 10 прокси или в конце
                if checked_count % 10 == 0 or checked_count == total:
                    info_log(f"Проверено: {checked_count}/{total}, работают: {working_count}")

        info_log("")
        success_log(f"Проверка завершена: {working_count}/{total} прокси работают")

        if working_count == 0:
            error_log("Ни один прокси не работает!")

        return working_count
