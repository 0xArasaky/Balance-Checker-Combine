"""
Модуль работы с Excel файлами для Balance Checker
Читает кошельки из data.xlsx и сохраняет результаты
"""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, Border, Fill
from openpyxl.utils import get_column_letter
from loguru import logger
from modules.utils.logger import error_log, info_log, success_log, warning_log


class ExcelHandler:
    """Класс для работы с Excel файлами"""

    def __init__(self, data_file: str = "data.xlsx", output_dir: str = "analyses"):
        """
        Инициализация обработчика Excel

        Args:
            data_file: Путь к файлу с данными
            output_dir: Папка для сохранения результатов
        """
        self.data_file = Path(data_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def read_bybit_accounts(self) -> List[Dict[str, str]]:
        """
        Прочитать аккаунты Bybit из листа BYBIT

        Returns:
            Список словарей с данными Bybit аккаунтов
        """
        try:
            if not self.data_file.exists():
                error_log(f"Файл данных не найден: {self.data_file}")
                return []

            # Читаем лист BYBIT
            df = pd.read_excel(self.data_file, sheet_name="BYBIT")

            # Проверяем наличие необходимых столбцов
            required_columns = ['Name', 'Group', 'API Key', 'Secret Key']
            if not all(col in df.columns for col in required_columns):
                error_log(f"Лист BYBIT: отсутствуют необходимые столбцы ({', '.join(required_columns)})")
                return []

            # Фильтруем пустые строки (без API Key)
            df = df.dropna(subset=['API Key'])
            df = df[df['API Key'].str.strip() != '']

            # Преобразуем в список словарей
            accounts = []
            for _, row in df.iterrows():
                # Читаем Specific Proxy если столбец существует
                specific_proxy = None
                if 'Specific Proxy' in df.columns and pd.notna(row['Specific Proxy']):
                    proxy_value = str(row['Specific Proxy']).strip()
                    if proxy_value:
                        specific_proxy = proxy_value

                accounts.append({
                    'name': str(row['Name']) if pd.notna(row['Name']) else '',
                    'group': str(row['Group']) if pd.notna(row['Group']) else '',
                    'api_key': str(row['API Key']).strip(),
                    'secret_key': str(row['Secret Key']).strip(),
                    'specific_proxy': specific_proxy
                })

            info_log(f"Лист BYBIT: прочитано {len(accounts)} аккаунтов")
            return accounts

        except ValueError as e:
            if "Worksheet" in str(e):
                warning_log("Лист BYBIT не найден в файле")
            else:
                error_log(f"Ошибка чтения листа BYBIT: {str(e)}")
            return []
        except Exception as e:
            error_log(f"Ошибка чтения листа BYBIT: {str(e)}")
            return []

    def read_binance_accounts(self) -> List[Dict[str, str]]:
        """
        Прочитать аккаунты Binance из листа BINANCE

        Returns:
            Список словарей с данными Binance аккаунтов
        """
        try:
            if not self.data_file.exists():
                error_log(f"Файл данных не найден: {self.data_file}")
                return []

            # Читаем лист BINANCE
            df = pd.read_excel(self.data_file, sheet_name="BINANCE")

            # Проверяем наличие необходимых столбцов
            required_columns = ['Name', 'Group', 'API Key', 'Secret Key']
            if not all(col in df.columns for col in required_columns):
                error_log(f"Лист BINANCE: отсутствуют необходимые столбцы ({', '.join(required_columns)})")
                return []

            # Фильтруем пустые строки (без API Key)
            df = df.dropna(subset=['API Key'])
            df = df[df['API Key'].str.strip() != '']

            # Преобразуем в список словарей
            accounts = []
            for _, row in df.iterrows():
                # Читаем Specific Proxy если столбец существует
                specific_proxy = None
                if 'Specific Proxy' in df.columns and pd.notna(row['Specific Proxy']):
                    proxy_value = str(row['Specific Proxy']).strip()
                    if proxy_value:
                        specific_proxy = proxy_value

                accounts.append({
                    'name': str(row['Name']) if pd.notna(row['Name']) else '',
                    'group': str(row['Group']) if pd.notna(row['Group']) else '',
                    'api_key': str(row['API Key']).strip(),
                    'secret_key': str(row['Secret Key']).strip(),
                    'specific_proxy': specific_proxy
                })

            info_log(f"Лист BINANCE: прочитано {len(accounts)} аккаунтов")
            return accounts

        except ValueError as e:
            if "Worksheet" in str(e):
                warning_log("Лист BINANCE не найден в файле")
            else:
                error_log(f"Ошибка чтения листа BINANCE: {str(e)}")
            return []
        except Exception as e:
            error_log(f"Ошибка чтения листа BINANCE: {str(e)}")
            return []

    def read_backpack_accounts(self) -> List[Dict[str, str]]:
        """
        Прочитать аккаунты Backpack из листа BACKPACK

        Returns:
            Список словарей с данными Backpack аккаунтов
        """
        try:
            if not self.data_file.exists():
                error_log(f"Файл данных не найден: {self.data_file}")
                return []

            # Читаем лист BACKPACK
            df = pd.read_excel(self.data_file, sheet_name="BACKPACK")

            # Проверяем наличие необходимых столбцов
            required_columns = ['Name', 'Group', 'API Key', 'Secret Key']
            if not all(col in df.columns for col in required_columns):
                error_log(f"Лист BACKPACK: отсутствуют необходимые столбцы ({', '.join(required_columns)})")
                return []

            # Фильтруем пустые строки (без API Key)
            df = df.dropna(subset=['API Key'])
            df = df[df['API Key'].str.strip() != '']

            # Преобразуем в список словарей
            accounts = []
            for _, row in df.iterrows():
                # Читаем Specific Proxy если столбец существует
                specific_proxy = None
                if 'Specific Proxy' in df.columns and pd.notna(row['Specific Proxy']):
                    proxy_value = str(row['Specific Proxy']).strip()
                    if proxy_value:
                        specific_proxy = proxy_value

                accounts.append({
                    'name': str(row['Name']) if pd.notna(row['Name']) else '',
                    'group': str(row['Group']) if pd.notna(row['Group']) else '',
                    'api_key': str(row['API Key']).strip(),
                    'secret_key': str(row['Secret Key']).strip(),
                    'specific_proxy': specific_proxy
                })

            info_log(f"Лист BACKPACK: прочитано {len(accounts)} аккаунтов")
            return accounts

        except ValueError as e:
            if "Worksheet" in str(e):
                warning_log("Лист BACKPACK не найден в файле")
            else:
                error_log(f"Ошибка чтения листа BACKPACK: {str(e)}")
            return []
        except Exception as e:
            error_log(f"Ошибка чтения листа BACKPACK: {str(e)}")
            return []

    def read_okx_accounts(self) -> List[Dict[str, str]]:
        """
        Прочитать аккаунты OKX из листа OKX

        Returns:
            Список словарей с данными OKX аккаунтов
        """
        try:
            if not self.data_file.exists():
                error_log(f"Файл данных не найден: {self.data_file}")
                return []

            # Читаем лист OKX
            df = pd.read_excel(self.data_file, sheet_name="OKX")

            # Проверяем наличие необходимых столбцов
            required_columns = ['Name', 'Group', 'API Key', 'Secret Key', 'Passphrase']
            if not all(col in df.columns for col in required_columns):
                error_log(f"Лист OKX: отсутствуют необходимые столбцы ({', '.join(required_columns)})")
                return []

            # Фильтруем пустые строки (без API Key)
            df = df.dropna(subset=['API Key'])
            df = df[df['API Key'].str.strip() != '']

            # Преобразуем в список словарей
            accounts = []
            for _, row in df.iterrows():
                # Читаем Specific Proxy если столбец существует
                specific_proxy = None
                if 'Specific Proxy' in df.columns and pd.notna(row['Specific Proxy']):
                    proxy_value = str(row['Specific Proxy']).strip()
                    if proxy_value:
                        specific_proxy = proxy_value

                accounts.append({
                    'name': str(row['Name']) if pd.notna(row['Name']) else '',
                    'group': str(row['Group']) if pd.notna(row['Group']) else '',
                    'api_key': str(row['API Key']).strip(),
                    'secret_key': str(row['Secret Key']).strip(),
                    'passphrase': str(row['Passphrase']).strip(),
                    'specific_proxy': specific_proxy
                })

            info_log(f"Лист OKX: прочитано {len(accounts)} аккаунтов")
            return accounts

        except ValueError as e:
            if "Worksheet" in str(e):
                warning_log("Лист OKX не найден в файле")
            else:
                error_log(f"Ошибка чтения листа OKX: {str(e)}")
            return []
        except Exception as e:
            error_log(f"Ошибка чтения листа OKX: {str(e)}")
            return []

    def read_kucoin_accounts(self) -> List[Dict[str, str]]:
        """
        Прочитать аккаунты KuCoin из листа KUCOIN

        Returns:
            Список словарей с данными KuCoin аккаунтов
        """
        try:
            if not self.data_file.exists():
                error_log(f"Файл данных не найден: {self.data_file}")
                return []

            # Читаем лист KUCOIN
            df = pd.read_excel(self.data_file, sheet_name="KUCOIN")

            # Проверяем наличие необходимых столбцов
            required_columns = ['Name', 'Group', 'API Key', 'Secret Key', 'Passphrase']
            if not all(col in df.columns for col in required_columns):
                error_log(f"Лист KUCOIN: отсутствуют необходимые столбцы ({', '.join(required_columns)})")
                return []

            # Фильтруем пустые строки (без API Key)
            df = df.dropna(subset=['API Key'])
            df = df[df['API Key'].str.strip() != '']

            # Преобразуем в список словарей
            accounts = []
            for _, row in df.iterrows():
                # Читаем Specific Proxy если столбец существует
                specific_proxy = None
                if 'Specific Proxy' in df.columns and pd.notna(row['Specific Proxy']):
                    proxy_value = str(row['Specific Proxy']).strip()
                    if proxy_value:
                        specific_proxy = proxy_value

                accounts.append({
                    'name': str(row['Name']) if pd.notna(row['Name']) else '',
                    'group': str(row['Group']) if pd.notna(row['Group']) else '',
                    'api_key': str(row['API Key']).strip(),
                    'secret_key': str(row['Secret Key']).strip(),
                    'passphrase': str(row['Passphrase']).strip(),
                    'specific_proxy': specific_proxy
                })

            info_log(f"Лист KUCOIN: прочитано {len(accounts)} аккаунтов")
            return accounts

        except ValueError as e:
            if "Worksheet" in str(e):
                warning_log("Лист KUCOIN не найден в файле")
            else:
                error_log(f"Ошибка чтения листа KUCOIN: {str(e)}")
            return []
        except Exception as e:
            error_log(f"Ошибка чтения листа KUCOIN: {str(e)}")
            return []

    def read_mexc_accounts(self) -> List[Dict[str, str]]:
        """
        Прочитать аккаунты MEXC из листа MEXC

        Returns:
            Список словарей с данными MEXC аккаунтов
        """
        try:
            if not self.data_file.exists():
                error_log(f"Файл данных не найден: {self.data_file}")
                return []

            # Читаем лист MEXC
            df = pd.read_excel(self.data_file, sheet_name="MEXC")

            # Проверяем наличие необходимых столбцов
            required_columns = ['Name', 'Group', 'API Key', 'Secret Key']
            if not all(col in df.columns for col in required_columns):
                error_log(f"Лист MEXC: отсутствуют необходимые столбцы ({', '.join(required_columns)})")
                return []

            # Фильтруем пустые строки (без API Key)
            df = df.dropna(subset=['API Key'])
            df = df[df['API Key'].str.strip() != '']

            # Преобразуем в список словарей
            accounts = []
            for _, row in df.iterrows():
                # Читаем Specific Proxy если столбец существует
                specific_proxy = None
                if 'Specific Proxy' in df.columns and pd.notna(row['Specific Proxy']):
                    proxy_value = str(row['Specific Proxy']).strip()
                    if proxy_value:
                        specific_proxy = proxy_value

                accounts.append({
                    'name': str(row['Name']) if pd.notna(row['Name']) else '',
                    'group': str(row['Group']) if pd.notna(row['Group']) else '',
                    'api_key': str(row['API Key']).strip(),
                    'secret_key': str(row['Secret Key']).strip(),
                    'specific_proxy': specific_proxy
                })

            info_log(f"Лист MEXC: прочитано {len(accounts)} аккаунтов")
            return accounts

        except ValueError as e:
            if "Worksheet" in str(e):
                warning_log("Лист MEXC не найден в файле")
            else:
                error_log(f"Ошибка чтения листа MEXC: {str(e)}")
            return []
        except Exception as e:
            error_log(f"Ошибка чтения листа MEXC: {str(e)}")
            return []

    def read_gate_accounts(self) -> List[Dict[str, str]]:
        """
        Прочитать аккаунты Gate.io из листа GATE

        Returns:
            Список словарей с данными Gate.io аккаунтов
        """
        try:
            if not self.data_file.exists():
                error_log(f"Файл данных не найден: {self.data_file}")
                return []

            # Читаем лист GATE
            df = pd.read_excel(self.data_file, sheet_name="GATE")

            # Проверяем наличие необходимых столбцов
            required_columns = ['Name', 'Group', 'API Key', 'Secret Key']
            if not all(col in df.columns for col in required_columns):
                error_log(f"Лист GATE: отсутствуют необходимые столбцы ({', '.join(required_columns)})")
                return []

            # Фильтруем пустые строки (без API Key)
            df = df.dropna(subset=['API Key'])
            df = df[df['API Key'].str.strip() != '']

            # Преобразуем в список словарей
            accounts = []
            for _, row in df.iterrows():
                # Читаем Specific Proxy если столбец существует
                specific_proxy = None
                if 'Specific Proxy' in df.columns and pd.notna(row['Specific Proxy']):
                    proxy_value = str(row['Specific Proxy']).strip()
                    if proxy_value:
                        specific_proxy = proxy_value

                accounts.append({
                    'name': str(row['Name']) if pd.notna(row['Name']) else '',
                    'group': str(row['Group']) if pd.notna(row['Group']) else '',
                    'api_key': str(row['API Key']).strip(),
                    'secret_key': str(row['Secret Key']).strip(),
                    'specific_proxy': specific_proxy
                })

            info_log(f"Лист GATE: прочитано {len(accounts)} аккаунтов")
            return accounts

        except ValueError as e:
            if "Worksheet" in str(e):
                warning_log("Лист GATE не найден в файле")
            else:
                error_log(f"Ошибка чтения листа GATE: {str(e)}")
            return []
        except Exception as e:
            error_log(f"Ошибка чтения листа GATE: {str(e)}")
            return []

    def read_wallets_from_sheet(self, sheet_name: str) -> List[Dict[str, str]]:
        """
        Прочитать кошельки из указанного листа

        Args:
            sheet_name: Имя листа (EVM, SOL, BTC, и т.д.)

        Returns:
            Список словарей с данными кошельков
        """
        try:
            if not self.data_file.exists():
                error_log(f"Файл данных не найден: {self.data_file}")
                return []

            # Читаем лист
            df = pd.read_excel(self.data_file, sheet_name=sheet_name)

            # Проверяем наличие необходимых столбцов
            required_columns = ['Name', 'Group', 'Address']
            if not all(col in df.columns for col in required_columns):
                error_log(f"Лист {sheet_name}: отсутствуют необходимые столбцы")
                return []

            # Фильтруем пустые строки (без адреса)
            df = df.dropna(subset=['Address'])
            df = df[df['Address'].str.strip() != '']

            # Преобразуем в список словарей
            wallets = []
            for _, row in df.iterrows():
                wallets.append({
                    'name': str(row['Name']) if pd.notna(row['Name']) else '',
                    'group': str(row['Group']) if pd.notna(row['Group']) else '',
                    'address': str(row['Address']).strip()
                })

            info_log(f"Лист {sheet_name}: прочитано {len(wallets)} кошельков")
            return wallets

        except ValueError as e:
            if "Worksheet" in str(e):
                warning_log(f"Лист {sheet_name} не найден в файле")
            else:
                error_log(f"Ошибка чтения листа {sheet_name}: {str(e)}")
            return []
        except Exception as e:
            error_log(f"Ошибка чтения листа {sheet_name}: {str(e)}")
            return []

    def save_results_to_excel(
        self,
        results_by_sheet: Dict[str, Dict],
        output_filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Сохранить результаты всех листов в один Excel файл

        Args:
            results_by_sheet: Словарь {sheet_name: {"wallets": [...], "balances": [...]}}
            output_filename: Имя выходного файла (опционально, по умолчанию генерируется автоматически)

        Returns:
            Путь к созданному файлу или None при ошибке
        """
        try:
            # Генерируем имя файла с timestamp
            if output_filename is None:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                output_filename = f"balance_{timestamp}.xlsx"

            output_file = self.output_dir / output_filename

            # Создаем Excel writer
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # СНАЧАЛА создаем лист "Total Stats" (он будет первым)
                total_stats_df = self._create_total_stats_sheet(results_by_sheet)
                total_stats_df.to_excel(writer, sheet_name="Total Stats", index=False)

                # ЗАТЕМ создаем остальные листы
                for sheet_name, data in results_by_sheet.items():
                    # Пропускаем APT Tokens Stats (больше не создаем этот лист)
                    if sheet_name == "APT Tokens Stats":
                        continue

                    wallets = data['wallets']

                    # Для листов "Tokens Stats" используем токены вместо балансов
                    if sheet_name.endswith("Tokens Stats"):
                        tokens = data.get('tokens', [])
                        df = self._create_dataframe(sheet_name, wallets, [], tokens)
                    else:
                        balances = data['balances']
                        df = self._create_dataframe(sheet_name, wallets, balances)

                    # Сохраняем лист
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

            # Применяем стили (передаем исходные данные для расчета ширины)
            self._apply_styles(output_file, results_by_sheet)

            return str(output_file)

        except Exception as e:
            error_log(f"Ошибка сохранения результатов: {str(e)}")
            return None

    @staticmethod
    def _round_balance(value: any) -> any:
        """
        Округлить значение баланса до 2 знаков после запятой

        Args:
            value: Значение (число или строка с кодом ошибки)

        Returns:
            Округленное число или исходная строка
        """
        if isinstance(value, (int, float)):
            return round(value, 2)
        return value

    def _create_dataframe(
        self,
        sheet_name: str,
        wallets: List[Dict[str, str]],
        balances: List[Dict[str, any]],
        tokens: Optional[List[Dict[str, any]]] = None
    ) -> pd.DataFrame:
        """
        Создать DataFrame с правильными колонками для каждого типа листа
        С группировкой по полю "Group" если групп > 1

        Args:
            sheet_name: Имя листа (EVM, SOL, BTC, OKX и т.д.)
            wallets: Список кошельков или аккаунтов
            balances: Список балансов (словари)
            tokens: Список токенов (только для "EVM Tokens Stats")

        Returns:
            DataFrame с правильными колонками и группировкой
        """
        # Специальная обработка для листов "Tokens Stats"
        if sheet_name.endswith("Tokens Stats"):
            # Пропускаем APT Tokens Stats (больше не создаем этот лист)
            if sheet_name == "APT Tokens Stats":
                return pd.DataFrame()
            return self._create_tokens_dataframe(wallets, tokens)

        # Для APT используем новую логику с динамическими колонками токенов
        if sheet_name == "APT":
            # Извлекаем токены из балансов
            tokens_list = [balance.get('tokens') for balance in balances]
            # Определяем уникальные группы
            seen_groups = []
            for w in wallets:
                group = w.get('group', '')
                if group and group not in seen_groups:
                    seen_groups.append(group)

            # Если групп > 1 - создаем с группировкой
            if len(seen_groups) > 1:
                return self._create_apt_with_tokens_grouped(sheet_name, wallets, balances, tokens_list, seen_groups)
            else:
                return self._create_apt_with_tokens_simple(sheet_name, wallets, balances, tokens_list)

        # Для бирж проверяем есть ли токены в балансах
        if sheet_name in ["OKX", "BINANCE", "BYBIT", "BACKPACK", "KUCOIN", "MEXC", "GATE"]:
            # Извлекаем токены из балансов
            tokens_list = [balance.get('tokens') for balance in balances]
            # Если есть хоть один баланс с токенами - используем логику токенов + Total Balance
            if any(tokens is not None and tokens.get('error') is None for tokens in tokens_list):
                # Определяем уникальные группы
                seen_groups = []
                for w in wallets:
                    group = w.get('group', '')
                    if group and group not in seen_groups:
                        seen_groups.append(group)

                # Если групп > 1 - создаем с группировкой
                if len(seen_groups) > 1:
                    return self._create_exchange_with_tokens_grouped(sheet_name, wallets, balances, tokens_list, seen_groups)
                else:
                    return self._create_exchange_with_tokens_simple(sheet_name, wallets, balances, tokens_list)

        # Определяем уникальные группы в порядке появления
        seen_groups = []
        for w in wallets:
            group = w.get('group', '')
            if group and group not in seen_groups:
                seen_groups.append(group)

        # Если групп > 1, создаем DataFrame с группировкой
        if len(seen_groups) > 1:
            return self._create_grouped_dataframe(sheet_name, wallets, balances, seen_groups)
        else:
            # Если группа одна или нет групп - создаем как раньше
            return self._create_simple_dataframe(sheet_name, wallets, balances)

    def _create_exchange_with_tokens_simple(
        self,
        sheet_name: str,
        wallets: List[Dict[str, str]],
        balances: List[Dict[str, any]],
        tokens_list: List[Dict[str, any]]
    ) -> pd.DataFrame:
        """
        Создать DataFrame для бирж с токенами (без группировки)

        Args:
            sheet_name: Имя листа биржи (OKX, BINANCE, etc.)
            wallets: Список аккаунтов
            balances: Список балансов
            tokens_list: Список токенов из балансов

        Returns:
            DataFrame с динамическими колонками токенов + Total Balance
        """
        # Собираем все уникальные токены и их общую стоимость (исключая "error" и "Other")
        token_totals = {}
        for tokens in tokens_list:
            if tokens and tokens.get('error') is None:
                for token_symbol, value in tokens.items():
                    if token_symbol not in ["error", "Other"] and isinstance(value, (int, float)):
                        token_totals[token_symbol] = token_totals.get(token_symbol, 0) + value

        # Сортируем токены по убыванию общей стоимости
        sorted_tokens = sorted(token_totals.keys(), key=lambda x: token_totals[x], reverse=True)

        # Базовые колонки в зависимости от биржи
        base_data = {
            'Name': [w['name'] for w in wallets],
            'Group': [w['group'] for w in wallets]
        }

        # Добавляем API Key и Secret Key
        base_data['API Key'] = [w.get('api_key', '') for w in wallets]
        base_data['Secret Key'] = [w.get('secret_key', '') for w in wallets]

        # Для OKX и KUCOIN добавляем Passphrase
        if sheet_name in ["OKX", "KUCOIN"]:
            base_data['Passphrase'] = [w.get('passphrase', '') for w in wallets]

        # Добавляем колонки для каждого токена
        for token_symbol in sorted_tokens:
            token_values = []
            for tokens in tokens_list:
                if tokens and tokens.get('error') is None:
                    token_values.append(self._round_balance(tokens.get(token_symbol, 0)))
                else:
                    token_values.append(tokens.get('error', 'ERROR') if tokens else 'ERROR')
            base_data[f'{token_symbol}, $'] = token_values

        # Добавляем колонку "Other"
        other_values = []
        for tokens in tokens_list:
            if tokens and tokens.get('error') is None:
                other_values.append(self._round_balance(tokens.get('Other', 0)))
            else:
                other_values.append(tokens.get('error', 'ERROR') if tokens else 'ERROR')
        base_data['Other, $'] = other_values

        # Добавляем колонку "Total Balance" (из балансов, не из токенов!)
        total_values = []
        for balance in balances:
            if balance.get('error') is None:
                total_values.append(self._round_balance(balance.get('total_balance', 0)))
            else:
                total_values.append(balance['error'])
        base_data['Total Balance, $'] = total_values

        return pd.DataFrame(base_data)

    def _create_exchange_with_tokens_grouped(
        self,
        sheet_name: str,
        wallets: List[Dict[str, str]],
        balances: List[Dict[str, any]],
        tokens_list: List[Dict[str, any]],
        groups: List[str]
    ) -> pd.DataFrame:
        """
        Создать DataFrame для бирж с токенами (с группировкой)

        Args:
            sheet_name: Имя листа биржи
            wallets: Список аккаунтов
            balances: Список балансов
            tokens_list: Список токенов из балансов
            groups: Список уникальных групп

        Returns:
            DataFrame с группировкой и токенами
        """
        # Собираем все уникальные токены (кроме "APT", "Other", "error") и сортируем
        # "APT" исключаем, т.к. у него отдельная колонка "APT, $"
        token_totals = {}
        for tokens in tokens_list:
            if tokens and tokens.get('error') is None:
                for token_symbol, value in tokens.items():
                    if token_symbol not in ["error", "APT", "Other"] and isinstance(value, (int, float)):
                        token_totals[token_symbol] = token_totals.get(token_symbol, 0) + value

        sorted_tokens = sorted(token_totals.keys(), key=lambda x: token_totals[x], reverse=True)

        rows = []

        # Для каждой группы
        for group in groups:
            # Находим индексы аккаунтов этой группы
            group_indices = [i for i, w in enumerate(wallets) if w.get('group', '') == group]

            # Добавляем аккаунты этой группы
            for idx in group_indices:
                row = {
                    'Name': wallets[idx]['name'],
                    'Group': wallets[idx]['group'],
                    'API Key': wallets[idx].get('api_key', ''),
                    'Secret Key': wallets[idx].get('secret_key', '')
                }

                # Для OKX и KUCOIN добавляем Passphrase
                if sheet_name in ["OKX", "KUCOIN"]:
                    row['Passphrase'] = wallets[idx].get('passphrase', '')

                tokens = tokens_list[idx]
                balance = balances[idx]

                if tokens and tokens.get('error') is None:
                    # Добавляем каждый токен
                    for token_symbol in sorted_tokens:
                        row[f'{token_symbol}, $'] = self._round_balance(tokens.get(token_symbol, 0))

                    # Other
                    row['Other, $'] = self._round_balance(tokens.get('Other', 0))

                    # Total Balance (из баланса)
                    row['Total Balance, $'] = self._round_balance(balance.get('total_balance', 0))
                else:
                    # Ошибка - заполняем все колонки кодом ошибки
                    error = tokens.get('error', 'ERROR') if tokens else 'ERROR'
                    for token_symbol in sorted_tokens:
                        row[f'{token_symbol}, $'] = error
                    row['Other, $'] = error
                    row['Total Balance, $'] = error

                rows.append(row)

            # Добавляем строку статистики группы
            stats_row = self._create_exchange_group_stats_row(sheet_name, group, sorted_tokens)
            rows.append(stats_row)

            # Добавляем пустую строку
            empty_row = self._create_exchange_empty_row(sheet_name, sorted_tokens)
            rows.append(empty_row)

        # Добавляем строку Total
        total_row = self._create_exchange_total_row(sheet_name, sorted_tokens)
        rows.append(total_row)

        return pd.DataFrame(rows)

    def _create_exchange_group_stats_row(
        self,
        sheet_name: str,
        group_name: str,
        sorted_tokens: List[str]
    ) -> Dict[str, any]:
        """
        Создать строку статистики группы для биржи с токенами
        """
        row = {
            'Name': f'{group_name} Group Stats:',
            'Group': '',
            'API Key': '',
            'Secret Key': ''
        }

        if sheet_name in ["OKX", "KUCOIN"]:
            row['Passphrase'] = ''

        # Пустые значения для токенов (формулы добавятся позже)
        for token_symbol in sorted_tokens:
            row[f'{token_symbol}, $'] = ''

        row['Other, $'] = ''
        row['Total Balance, $'] = ''

        return row

    def _create_exchange_empty_row(
        self,
        sheet_name: str,
        sorted_tokens: List[str]
    ) -> Dict[str, any]:
        """
        Создать пустую строку для биржи с токенами
        """
        row = self._create_exchange_group_stats_row(sheet_name, '', sorted_tokens)
        row['Name'] = ''
        return row

    def _create_exchange_total_row(
        self,
        sheet_name: str,
        sorted_tokens: List[str]
    ) -> Dict[str, any]:
        """
        Создать строку Total для биржи с токенами
        """
        row = self._create_exchange_group_stats_row(sheet_name, '', sorted_tokens)
        row['Name'] = 'Total:'
        return row

    def _create_apt_with_tokens_simple(
        self,
        sheet_name: str,
        wallets: List[Dict[str, str]],
        balances: List[Dict[str, any]],
        tokens_list: List[Dict[str, any]]
    ) -> pd.DataFrame:
        """
        Создать DataFrame для APT с токенами (без группировки)

        Args:
            sheet_name: Имя листа (APT)
            wallets: Список кошельков
            balances: Список балансов
            tokens_list: Список токенов из балансов

        Returns:
            DataFrame с динамическими колонками токенов
        """
        # Собираем все уникальные токены (кроме "APT", "Other", "error") и их общую стоимость
        # "APT" исключаем, т.к. у него отдельная колонка "APT, $"
        token_totals = {}
        for tokens in tokens_list:
            if tokens and tokens.get('error') is None:
                for token_symbol, value in tokens.items():
                    if token_symbol not in ["error", "APT", "Other"] and isinstance(value, (int, float)):
                        token_totals[token_symbol] = token_totals.get(token_symbol, 0) + value

        # Сортируем токены по убыванию общей стоимости
        sorted_tokens = sorted(token_totals.keys(), key=lambda x: token_totals[x], reverse=True)

        # Базовые колонки
        base_data = {
            'Name': [w['name'] for w in wallets],
            'Group': [w['group'] for w in wallets],
            'Address': [w['address'] for w in wallets]
        }

        # Добавляем колонку APT
        apt_values = []
        for balance in balances:
            if balance.get('error') is None:
                apt_values.append(self._round_balance(balance.get('apt_balance', 0)))
            else:
                apt_values.append(balance['error'])
        base_data['APT, $'] = apt_values

        # Добавляем колонку Staked APT
        staked_values = []
        for balance in balances:
            if balance.get('error') is None:
                staked_values.append(self._round_balance(balance.get('staked_apt_balance', 0)))
            else:
                staked_values.append(balance['error'])
        base_data['Staked APT, $'] = staked_values

        # Добавляем колонки для каждого токена
        for token_symbol in sorted_tokens:
            token_values = []
            for tokens in tokens_list:
                if tokens and tokens.get('error') is None:
                    token_values.append(self._round_balance(tokens.get(token_symbol, 0)))
                else:
                    token_values.append(tokens.get('error', 'ERROR') if tokens else 'ERROR')
            base_data[f'{token_symbol}, $'] = token_values

        # Добавляем колонку "Other"
        other_values = []
        for tokens in tokens_list:
            if tokens and tokens.get('error') is None:
                other_values.append(self._round_balance(tokens.get('Other', 0)))
            else:
                other_values.append(tokens.get('error', 'ERROR') if tokens else 'ERROR')
        base_data['Other, $'] = other_values

        # Добавляем колонку "Total Balance"
        total_values = []
        for balance in balances:
            if balance.get('error') is None:
                total_values.append(self._round_balance(balance.get('total_balance', 0)))
            else:
                total_values.append(balance['error'])
        base_data['Total Balance, $'] = total_values

        return pd.DataFrame(base_data)

    def _create_apt_with_tokens_grouped(
        self,
        sheet_name: str,
        wallets: List[Dict[str, str]],
        balances: List[Dict[str, any]],
        tokens_list: List[Dict[str, any]],
        groups: List[str]
    ) -> pd.DataFrame:
        """
        Создать DataFrame для APT с токенами (с группировкой)

        Args:
            sheet_name: Имя листа (APT)
            wallets: Список кошельков
            balances: Список балансов
            tokens_list: Список токенов из балансов
            groups: Список уникальных групп

        Returns:
            DataFrame с группировкой и токенами
        """
        # Собираем все уникальные токены (кроме "APT", "Other", "error") и сортируем
        # "APT" исключаем, т.к. у него отдельная колонка "APT, $"
        token_totals = {}
        for tokens in tokens_list:
            if tokens and tokens.get('error') is None:
                for token_symbol, value in tokens.items():
                    if token_symbol not in ["error", "APT", "Other"] and isinstance(value, (int, float)):
                        token_totals[token_symbol] = token_totals.get(token_symbol, 0) + value

        sorted_tokens = sorted(token_totals.keys(), key=lambda x: token_totals[x], reverse=True)

        rows = []

        # Для каждой группы
        for group in groups:
            # Находим индексы кошельков этой группы
            group_indices = [i for i, w in enumerate(wallets) if w.get('group', '') == group]

            # Добавляем кошельки этой группы
            for idx in group_indices:
                row = {
                    'Name': wallets[idx]['name'],
                    'Group': wallets[idx]['group'],
                    'Address': wallets[idx]['address']
                }

                balance = balances[idx]
                tokens = tokens_list[idx]

                if balance.get('error') is None:
                    # APT и Staked APT
                    row['APT, $'] = self._round_balance(balance.get('apt_balance', 0))
                    row['Staked APT, $'] = self._round_balance(balance.get('staked_apt_balance', 0))

                    # Токены
                    if tokens and tokens.get('error') is None:
                        for token_symbol in sorted_tokens:
                            row[f'{token_symbol}, $'] = self._round_balance(tokens.get(token_symbol, 0))
                        row['Other, $'] = self._round_balance(tokens.get('Other', 0))
                    else:
                        error = tokens.get('error', 'ERROR') if tokens else 'ERROR'
                        for token_symbol in sorted_tokens:
                            row[f'{token_symbol}, $'] = error
                        row['Other, $'] = error

                    # Total Balance
                    row['Total Balance, $'] = self._round_balance(balance.get('total_balance', 0))
                else:
                    # Ошибка - заполняем все колонки кодом ошибки
                    error = balance['error']
                    row['APT, $'] = error
                    row['Staked APT, $'] = error
                    for token_symbol in sorted_tokens:
                        row[f'{token_symbol}, $'] = error
                    row['Other, $'] = error
                    row['Total Balance, $'] = error

                rows.append(row)

            # Добавляем строку статистики группы
            stats_row = self._create_apt_group_stats_row(group, sorted_tokens)
            rows.append(stats_row)

            # Добавляем пустую строку
            empty_row = self._create_apt_empty_row(sorted_tokens)
            rows.append(empty_row)

        # Добавляем строку Total
        total_row = self._create_apt_total_row(sorted_tokens)
        rows.append(total_row)

        return pd.DataFrame(rows)

    def _create_apt_group_stats_row(
        self,
        group_name: str,
        sorted_tokens: List[str]
    ) -> Dict[str, any]:
        """
        Создать строку статистики группы для APT с токенами
        """
        row = {
            'Name': f'{group_name} Group Stats:',
            'Group': '',
            'Address': '',
            'APT, $': '',
            'Staked APT, $': ''
        }

        # Пустые значения для токенов (формулы добавятся позже)
        for token_symbol in sorted_tokens:
            row[f'{token_symbol}, $'] = ''

        row['Other, $'] = ''
        row['Total Balance, $'] = ''

        return row

    def _create_apt_empty_row(
        self,
        sorted_tokens: List[str]
    ) -> Dict[str, any]:
        """
        Создать пустую строку для APT с токенами
        """
        row = self._create_apt_group_stats_row('', sorted_tokens)
        row['Name'] = ''
        return row

    def _create_apt_total_row(
        self,
        sorted_tokens: List[str]
    ) -> Dict[str, any]:
        """
        Создать строку Total для APT с токенами
        """
        row = self._create_apt_group_stats_row('', sorted_tokens)
        row['Name'] = 'Total:'
        return row

    def _create_tokens_dataframe(
        self,
        wallets: List[Dict[str, str]],
        tokens_list: List[Dict[str, any]]
    ) -> pd.DataFrame:
        """
        Создать DataFrame для листов "Tokens Stats" с динамическими колонками токенов

        Args:
            wallets: Список кошельков
            tokens_list: Список словарей с токенами для каждого кошелька

        Returns:
            DataFrame с токенами
        """
        # Собираем все уникальные токены и их общую стоимость (исключая "error" и "Other")
        token_totals = {}
        for tokens in tokens_list:
            if tokens and tokens.get('error') is None:
                for token_symbol, value in tokens.items():
                    if token_symbol not in ["error", "Other"] and isinstance(value, (int, float)):
                        token_totals[token_symbol] = token_totals.get(token_symbol, 0) + value

        # Сортируем токены по убыванию общей стоимости
        sorted_tokens = sorted(token_totals.keys(), key=lambda x: token_totals[x], reverse=True)

        # Определяем уникальные группы
        seen_groups = []
        for w in wallets:
            group = w.get('group', '')
            if group and group not in seen_groups:
                seen_groups.append(group)

        # Если групп > 1 - создаем с группировкой
        if len(seen_groups) > 1:
            return self._create_tokens_grouped_dataframe(wallets, tokens_list, sorted_tokens, seen_groups)
        else:
            return self._create_tokens_simple_dataframe(wallets, tokens_list, sorted_tokens)

    def _create_tokens_simple_dataframe(
        self,
        wallets: List[Dict[str, str]],
        tokens_list: List[Dict[str, any]],
        sorted_tokens: List[str]
    ) -> pd.DataFrame:
        """
        Создать простой DataFrame для токенов без группировки

        Args:
            wallets: Список кошельков
            tokens_list: Список словарей с токенами
            sorted_tokens: Отсортированный список уникальных токенов

        Returns:
            DataFrame
        """
        # Базовые колонки
        base_data = {
            'Name': [w['name'] for w in wallets],
            'Group': [w['group'] for w in wallets]
        }

        # Добавляем Address только если это кошельки (не биржи)
        if wallets and 'address' in wallets[0]:
            base_data['Address'] = [w['address'] for w in wallets]

        # Добавляем колонки для каждого токена
        for token_symbol in sorted_tokens:
            token_values = []
            for tokens in tokens_list:
                if tokens and tokens.get('error') is None:
                    token_values.append(self._round_balance(tokens.get(token_symbol, 0)))
                else:
                    token_values.append(tokens.get('error', 'ERROR') if tokens else 'ERROR')
            base_data[f'{token_symbol}, $'] = token_values

        # Добавляем колонку "Other"
        other_values = []
        for tokens in tokens_list:
            if tokens and tokens.get('error') is None:
                other_values.append(self._round_balance(tokens.get('Other', 0)))
            else:
                other_values.append(tokens.get('error', 'ERROR') if tokens else 'ERROR')
        base_data['Other, $'] = other_values

        # Добавляем колонку "Total Tokens"
        total_values = []
        for tokens in tokens_list:
            if tokens and tokens.get('error') is None:
                # Суммируем все токены (включая Other)
                total = sum(v for k, v in tokens.items() if k != 'error' and isinstance(v, (int, float)))
                total_values.append(self._round_balance(total))
            else:
                total_values.append(tokens.get('error', 'ERROR') if tokens else 'ERROR')
        base_data['Total Tokens, $'] = total_values

        return pd.DataFrame(base_data)

    def _create_tokens_grouped_dataframe(
        self,
        wallets: List[Dict[str, str]],
        tokens_list: List[Dict[str, any]],
        sorted_tokens: List[str],
        groups: List[str]
    ) -> pd.DataFrame:
        """
        Создать DataFrame для токенов с группировкой

        Args:
            wallets: Список кошельков
            tokens_list: Список словарей с токенами
            sorted_tokens: Отсортированный список уникальных токенов
            groups: Список уникальных групп

        Returns:
            DataFrame с группировкой
        """
        rows = []

        # Для каждой группы
        for group in groups:
            # Находим индексы кошельков этой группы
            group_indices = [i for i, w in enumerate(wallets) if w.get('group', '') == group]

            # Добавляем кошельки этой группы
            for idx in group_indices:
                row = {
                    'Name': wallets[idx]['name'],
                    'Group': wallets[idx]['group']
                }

                # Добавляем Address только если это кошельки (не биржи)
                if 'address' in wallets[idx]:
                    row['Address'] = wallets[idx]['address']

                tokens = tokens_list[idx]
                if tokens and tokens.get('error') is None:
                    # Добавляем каждый токен
                    for token_symbol in sorted_tokens:
                        row[f'{token_symbol}, $'] = self._round_balance(tokens.get(token_symbol, 0))

                    # Other
                    row['Other, $'] = self._round_balance(tokens.get('Other', 0))

                    # Total
                    total = sum(v for k, v in tokens.items() if k != 'error' and isinstance(v, (int, float)))
                    row['Total Tokens, $'] = self._round_balance(total)
                else:
                    error = tokens.get('error', 'ERROR') if tokens else 'ERROR'
                    for token_symbol in sorted_tokens:
                        row[f'{token_symbol}, $'] = error
                    row['Other, $'] = error
                    row['Total Tokens, $'] = error

                rows.append(row)

            # Добавляем строку статистики группы
            stats_row = {
                'Name': f'{group} Group Stats:',
                'Group': '',
                'Address': ''
            }
            for token_symbol in sorted_tokens:
                stats_row[f'{token_symbol}, $'] = ''
            stats_row['Other, $'] = ''
            stats_row['Total Tokens, $'] = ''
            rows.append(stats_row)

            # Пустая строка
            empty_row = stats_row.copy()
            empty_row['Name'] = ''
            rows.append(empty_row)

        # Добавляем строку Total
        total_row = {
            'Name': 'Total:',
            'Group': '',
            'Address': ''
        }
        for token_symbol in sorted_tokens:
            total_row[f'{token_symbol}, $'] = ''
        total_row['Other, $'] = ''
        total_row['Total Tokens, $'] = ''
        rows.append(total_row)

        return pd.DataFrame(rows)

    def _create_total_stats_sheet(
        self,
        results_by_sheet: Dict[str, Dict]
    ) -> pd.DataFrame:
        """
        Создать лист "Total Stats" с общей статистикой по всем категориям и токенам

        Args:
            results_by_sheet: Словарь с данными по каждому листу

        Returns:
            DataFrame для листа Total Stats
        """
        rows = []

        # 1. TOTAL BALANCE
        total_balance = 0
        for sheet_name, data in results_by_sheet.items():
            # Пропускаем листы "Tokens Stats"
            if sheet_name.endswith("Tokens Stats"):
                continue
            balances = data.get('balances', [])
            for balance in balances:
                if balance.get('error') is None:
                    total_balance += balance.get('total_balance', 0)

        rows.append({
            'Section': '',
            'Category': 'TOTAL BALANCE',
            'Amount ($)': self._round_balance(total_balance)
        })

        # Пустая строка
        rows.append({'Section': '', 'Category': '', 'Amount ($)': ''})

        # 2. CATEGORIES секция
        rows.append({'Section': 'Categories', 'Category': '', 'Amount ($)': ''})

        # Собираем данные по категориям
        categories_data = {}

        # EVM
        if "EVM" in results_by_sheet:
            balances = results_by_sheet["EVM"].get('balances', [])
            evm_total = 0
            evm_chains = 0
            evm_defi = 0
            evm_poly_pos = 0
            evm_poly_total = 0
            evm_hyper = 0
            evm_lighter = 0

            for b in balances:
                if b.get('error') is None:
                    evm_total += b.get('total_balance', 0)
                    evm_chains += b.get('net_balance', 0)
                    evm_defi += b.get('apps_balance', 0)
                    evm_poly_pos += b.get('polymarket_positions_balance', 0)
                    evm_poly_total += b.get('polymarket_total_balance', 0)
                    evm_hyper += b.get('hyperliquid_balance', 0)
                    evm_lighter += b.get('lighter_balance', 0)

            categories_data['EVM'] = {
                'total': evm_total,
                'subcategories': [
                    ('  Chains', evm_chains),
                    ('  DeFi & Other', evm_defi),
                    ('  Polymarket Positions', evm_poly_pos),
                    ('  Polymarket Total', evm_poly_total),
                    ('  Hyperliquid Total', evm_hyper),
                    ('  Lighter', evm_lighter)
                ]
            }

        # SOL
        if "SOL" in results_by_sheet:
            balances = results_by_sheet["SOL"].get('balances', [])
            sol_total = 0
            sol_tokens = 0
            sol_defi = 0

            for b in balances:
                if b.get('error') is None:
                    sol_total += b.get('total_balance', 0)
                    sol_tokens += b.get('tokens_balance', 0)
                    sol_defi += b.get('defi_balance', 0)

            categories_data['SOL'] = {
                'total': sol_total,
                'subcategories': [
                    ('  Tokens', sol_tokens),
                    ('  DeFi', sol_defi)
                ]
            }

        # BTC
        if "BTC" in results_by_sheet:
            balances = results_by_sheet["BTC"].get('balances', [])
            btc_total = 0
            btc_amount = 0
            btc_runes = 0
            btc_inscriptions = 0

            for b in balances:
                if b.get('error') is None:
                    btc_total += b.get('total_balance', 0)
                    btc_amount += b.get('btc_balance', 0)
                    btc_runes += b.get('runes_balance', 0)
                    btc_inscriptions += b.get('inscriptions_balance', 0)

            categories_data['BTC'] = {
                'total': btc_total,
                'subcategories': [
                    ('  BTC Amount', btc_amount),
                    ('  Runes', btc_runes),
                    ('  Inscriptions', btc_inscriptions)
                ]
            }

        # APT
        if "APT" in results_by_sheet:
            balances = results_by_sheet["APT"].get('balances', [])
            apt_total = 0
            apt_amount = 0
            apt_other = 0
            apt_staked = 0

            for b in balances:
                if b.get('error') is None:
                    apt_total += b.get('total_balance', 0)
                    apt_amount += b.get('apt_balance', 0)
                    apt_other += b.get('other_tokens_balance', 0)
                    apt_staked += b.get('staked_apt_balance', 0)

            categories_data['APT'] = {
                'total': apt_total,
                'subcategories': [
                    ('  APT', apt_amount),
                    ('  Other Tokens', apt_other),
                    ('  Staked APT', apt_staked)
                ]
            }

        # TRX
        if "TRX" in results_by_sheet:
            balances = results_by_sheet["TRX"].get('balances', [])
            trx_total = 0
            trx_amount = 0
            trx_usdt = 0
            trx_other = 0

            for b in balances:
                if b.get('error') is None:
                    trx_total += b.get('total_balance', 0)
                    trx_amount += b.get('trx_balance', 0)
                    trx_usdt += b.get('usdt_balance', 0)
                    trx_other += b.get('other_tokens_balance', 0)

            categories_data['TRX'] = {
                'total': trx_total,
                'subcategories': [
                    ('  TRX', trx_amount),
                    ('  USDT', trx_usdt),
                    ('  Other Tokens', trx_other)
                ]
            }

        # Exchanges (биржи)
        exchanges = ["OKX", "BINANCE", "BYBIT", "BACKPACK", "KUCOIN", "MEXC", "GATE"]
        for exchange in exchanges:
            if exchange in results_by_sheet:
                balances = results_by_sheet[exchange].get('balances', [])
                exchange_total = 0
                for b in balances:
                    if b.get('error') is None:
                        exchange_total += b.get('total_balance', 0)
                categories_data[exchange] = {
                    'total': exchange_total,
                    'subcategories': []
                }

        # Записываем категории в строки
        for category_name, category_info in categories_data.items():
            # Основная строка категории
            rows.append({
                'Section': '',
                'Category': category_name,
                'Amount ($)': self._round_balance(category_info['total'])
            })
            # Подкатегории (с отступами)
            for subcat_name, subcat_value in category_info['subcategories']:
                rows.append({
                    'Section': '',
                    'Category': subcat_name,
                    'Amount ($)': self._round_balance(subcat_value)
                })

        # Пустая строка перед Tokens
        rows.append({'Section': '', 'Category': '', 'Amount ($)': ''})

        # 3. TOKENS секция
        rows.append({'Section': 'Tokens', 'Category': '', 'Amount ($)': ''})

        # Собираем все токены
        all_tokens = {}  # {token_symbol: total_value}
        total_other = 0

        # Список категорий бирж для удаления из названий токенов
        exchange_categories = [
            'Spot', 'Futures USDT', 'Futures BTC', 'Margin',
            'Cross Margin', 'Isolated Margin', 'Trading', 'Funding'
        ]

        for sheet_name, data in results_by_sheet.items():
            # Обрабатываем листы "Tokens Stats" (для кошельков)
            if sheet_name.endswith("Tokens Stats"):
                tokens_list = data.get('tokens', [])
                for tokens in tokens_list:
                    if tokens and tokens.get('error') is None:
                        for token_symbol, value in tokens.items():
                            if token_symbol == 'error':
                                continue
                            elif token_symbol == 'Other':
                                total_other += value
                            elif isinstance(value, (int, float)):
                                # Для кошельков оставляем токен как есть (с метками типа "RAP (Raydium Alpha)")
                                all_tokens[token_symbol] = all_tokens.get(token_symbol, 0) + value

            # Обрабатываем биржи
            elif sheet_name in exchanges:
                balances = data.get('balances', [])
                for balance in balances:
                    tokens = balance.get('tokens')
                    if tokens and tokens.get('error') is None:
                        for token_symbol, value in tokens.items():
                            if token_symbol == 'error':
                                continue
                            elif token_symbol == 'Other':
                                total_other += value
                            elif isinstance(value, (int, float)):
                                # Убираем метки категорий для бирж (например "BTC (Spot)" -> "BTC")
                                clean_symbol = token_symbol
                                for category in exchange_categories:
                                    category_pattern = f" ({category})"
                                    if category_pattern in token_symbol:
                                        clean_symbol = token_symbol.replace(category_pattern, '')
                                        break

                                all_tokens[clean_symbol] = all_tokens.get(clean_symbol, 0) + value

        # Сортируем токены по убыванию стоимости
        sorted_tokens = sorted(all_tokens.items(), key=lambda x: x[1], reverse=True)

        # Записываем токены
        for token_symbol, token_value in sorted_tokens:
            rows.append({
                'Section': '',
                'Category': token_symbol,
                'Amount ($)': self._round_balance(token_value)
            })

        # Other
        rows.append({
            'Section': '',
            'Category': 'Other',
            'Amount ($)': self._round_balance(total_other)
        })

        return pd.DataFrame(rows)

    def _create_simple_dataframe(
        self,
        sheet_name: str,
        wallets: List[Dict[str, str]],
        balances: List[Dict[str, any]]
    ) -> pd.DataFrame:
        """
        Создать простой DataFrame без группировки (как раньше)

        Args:
            sheet_name: Имя листа
            wallets: Список кошельков/аккаунтов
            balances: Список балансов

        Returns:
            DataFrame без группировки
        """
        # Базовые колонки для бирж (API ключи вместо адресов)
        if sheet_name in ["OKX", "KUCOIN"]:
            base_data = {
                'Name': [w['name'] for w in wallets],
                'Group': [w['group'] for w in wallets],
                'API Key': [w.get('api_key', '') for w in wallets],
                'Secret Key': [w.get('secret_key', '') for w in wallets],
                'Passphrase': [w.get('passphrase', '') for w in wallets]
            }
        elif sheet_name in ["BINANCE", "BYBIT", "BACKPACK", "MEXC", "GATE"]:
            base_data = {
                'Name': [w['name'] for w in wallets],
                'Group': [w['group'] for w in wallets],
                'API Key': [w.get('api_key', '') for w in wallets],
                'Secret Key': [w.get('secret_key', '') for w in wallets]
            }
        else:
            # Базовые колонки для обычных кошельков
            base_data = {
                'Name': [w['name'] for w in wallets],
                'Group': [w['group'] for w in wallets],
                'Address': [w['address'] for w in wallets]
            }

        # Добавляем колонки с балансами в зависимости от типа листа
        if sheet_name == "EVM":
            # Для EVM: Chains, DeFi etc, Polymarket Positions, Polymarket Total, Hyperliquid Total, Lighter, Total Balance
            chains_values = []
            defi_values = []
            polymarket_positions_values = []
            polymarket_total_values = []
            hyperliquid_values = []
            lighter_values = []
            total_values = []

            for b in balances:
                if b.get('error') is None:
                    chains_values.append(self._round_balance(b.get('net_balance', 0)))
                    defi_values.append(self._round_balance(b.get('apps_balance', 0)))
                    polymarket_positions_values.append(self._round_balance(b.get('polymarket_positions_balance', 0)))
                    polymarket_total_values.append(self._round_balance(b.get('polymarket_total_balance', 0)))
                    hyperliquid_values.append(self._round_balance(b.get('hyperliquid_balance', 0)))
                    lighter_values.append(self._round_balance(b.get('lighter_balance', 0)))
                    total_values.append(self._round_balance(b.get('total_balance', 0)))
                else:
                    chains_values.append(b['error'])
                    defi_values.append(b['error'])
                    polymarket_positions_values.append(b['error'])
                    polymarket_total_values.append(b['error'])
                    hyperliquid_values.append(b['error'])
                    lighter_values.append(b['error'])
                    total_values.append(b['error'])

            base_data['Chains, $'] = chains_values
            base_data['DeFi & Other, $'] = defi_values
            base_data['Polymarket Positions, $'] = polymarket_positions_values
            base_data['Polymarket Total, $'] = polymarket_total_values
            base_data['Hyperliquid Total, $'] = hyperliquid_values
            base_data['Lighter, $'] = lighter_values
            base_data['Total Balance, $'] = total_values

        elif sheet_name == "SOL":
            # Для SOL: Tokens, DeFi, Total Balance
            tokens_values = []
            defi_values = []
            total_values = []

            for b in balances:
                if b.get('error') is None:
                    tokens_values.append(self._round_balance(b.get('tokens_balance', 0)))
                    defi_values.append(self._round_balance(b.get('defi_balance', 0)))
                    total_values.append(self._round_balance(b.get('total_balance', 0)))
                else:
                    tokens_values.append(b['error'])
                    defi_values.append(b['error'])
                    total_values.append(b['error'])

            base_data['Tokens, $'] = tokens_values
            base_data['DeFi, $'] = defi_values
            base_data['Total Balance, $'] = total_values

        elif sheet_name == "BTC":
            # Для BTC: BTC Amount, Runes, Inscriptions, Total Balance
            btc_values = []
            runes_values = []
            inscriptions_values = []
            total_values = []

            for b in balances:
                if b.get('error') is None:
                    btc_values.append(self._round_balance(b.get('btc_balance', 0)))
                    runes_values.append(self._round_balance(b.get('runes_balance', 0)))
                    inscriptions_values.append(self._round_balance(b.get('inscriptions_balance', 0)))
                    total_values.append(self._round_balance(b.get('total_balance', 0)))
                else:
                    btc_values.append(b['error'])
                    runes_values.append(b['error'])
                    inscriptions_values.append(b['error'])
                    total_values.append(b['error'])

            base_data['BTC Amount, $'] = btc_values
            base_data['Runes, $'] = runes_values
            base_data['Inscriptions, $'] = inscriptions_values
            base_data['Total Balance, $'] = total_values

        elif sheet_name == "TRX":
            # Для TRX: TRX, USDT, Other Tokens, Total Balance
            trx_values = []
            usdt_values = []
            other_values = []
            total_values = []

            for b in balances:
                if b.get('error') is None:
                    trx_values.append(self._round_balance(b.get('trx_balance', 0)))
                    usdt_values.append(self._round_balance(b.get('usdt_balance', 0)))
                    other_values.append(self._round_balance(b.get('other_tokens_balance', 0)))
                    total_values.append(self._round_balance(b.get('total_balance', 0)))
                else:
                    trx_values.append(b['error'])
                    usdt_values.append(b['error'])
                    other_values.append(b['error'])
                    total_values.append(b['error'])

            base_data['TRX, $'] = trx_values
            base_data['USDT, $'] = usdt_values
            base_data['Other Tokens, $'] = other_values
            base_data['Total Balance, $'] = total_values

        elif sheet_name in ["OKX", "BINANCE", "BYBIT", "BACKPACK", "KUCOIN", "MEXC", "GATE"]:
            # Для бирж: только общий баланс
            total_values = []

            for b in balances:
                if b.get('error') is None:
                    total_values.append(self._round_balance(b.get('total_balance', 0)))
                else:
                    total_values.append(b['error'])

            base_data['Total Balance, $'] = total_values

        else:
            # Для неизвестных типов листов - только общий баланс
            balance_values = []
            for b in balances:
                if b.get('error') is None:
                    balance_values.append(self._round_balance(b.get('total_balance', 0)))
                else:
                    balance_values.append(b['error'])

            base_data['Balance, $'] = balance_values

        return pd.DataFrame(base_data)

    def _create_grouped_dataframe(
        self,
        sheet_name: str,
        wallets: List[Dict[str, str]],
        balances: List[Dict[str, any]],
        groups: List[str]
    ) -> pd.DataFrame:
        """
        Создать DataFrame с группировкой по полю "Group"

        Args:
            sheet_name: Имя листа
            wallets: Список кошельков/аккаунтов
            balances: Список балансов
            groups: Список уникальных групп в порядке появления

        Returns:
            DataFrame с группировкой и строками статистики
        """
        # Создаем список всех строк (кошельки + строки статистики)
        rows = []

        # Для каждой группы
        for group in groups:
            # Находим индексы кошельков этой группы
            group_indices = [i for i, w in enumerate(wallets) if w.get('group', '') == group]

            # Добавляем кошельки этой группы
            for idx in group_indices:
                row = self._create_row_dict(sheet_name, wallets[idx], balances[idx])
                rows.append(row)

            # Добавляем строку статистики группы
            stats_row = self._create_group_stats_row(sheet_name, group, wallets)
            rows.append(stats_row)

            # Добавляем пустую строку
            empty_row = self._create_empty_row(sheet_name, wallets)
            rows.append(empty_row)

        # Добавляем строку Total в конце
        total_row = self._create_total_row(sheet_name, wallets)
        rows.append(total_row)

        return pd.DataFrame(rows)

    def _create_row_dict(
        self,
        sheet_name: str,
        wallet: Dict[str, str],
        balance: Dict[str, any]
    ) -> Dict[str, any]:
        """
        Создать словарь для одной строки данных (кошелек/аккаунт)

        Args:
            sheet_name: Имя листа
            wallet: Данные кошелька/аккаунта
            balance: Данные баланса

        Returns:
            Словарь с данными строки
        """
        # Базовые колонки
        if sheet_name in ["OKX", "KUCOIN"]:
            row = {
                'Name': wallet['name'],
                'Group': wallet['group'],
                'API Key': wallet.get('api_key', ''),
                'Secret Key': wallet.get('secret_key', ''),
                'Passphrase': wallet.get('passphrase', '')
            }
        elif sheet_name in ["BINANCE", "BYBIT", "BACKPACK", "MEXC", "GATE"]:
            row = {
                'Name': wallet['name'],
                'Group': wallet['group'],
                'API Key': wallet.get('api_key', ''),
                'Secret Key': wallet.get('secret_key', '')
            }
        else:
            row = {
                'Name': wallet['name'],
                'Group': wallet['group'],
                'Address': wallet['address']
            }

        # Добавляем колонки с балансами
        if balance.get('error') is None:
            if sheet_name == "EVM":
                row['Chains, $'] = self._round_balance(balance.get('net_balance', 0))
                row['DeFi & Other, $'] = self._round_balance(balance.get('apps_balance', 0))
                row['Polymarket Positions, $'] = self._round_balance(balance.get('polymarket_positions_balance', 0))
                row['Polymarket Total, $'] = self._round_balance(balance.get('polymarket_total_balance', 0))
                row['Hyperliquid Total, $'] = self._round_balance(balance.get('hyperliquid_balance', 0))
                row['Lighter, $'] = self._round_balance(balance.get('lighter_balance', 0))
                row['Total Balance, $'] = self._round_balance(balance.get('total_balance', 0))
            elif sheet_name == "SOL":
                row['Tokens, $'] = self._round_balance(balance.get('tokens_balance', 0))
                row['DeFi, $'] = self._round_balance(balance.get('defi_balance', 0))
                row['Total Balance, $'] = self._round_balance(balance.get('total_balance', 0))
            elif sheet_name == "BTC":
                row['BTC Amount, $'] = self._round_balance(balance.get('btc_balance', 0))
                row['Runes, $'] = self._round_balance(balance.get('runes_balance', 0))
                row['Inscriptions, $'] = self._round_balance(balance.get('inscriptions_balance', 0))
                row['Total Balance, $'] = self._round_balance(balance.get('total_balance', 0))
            elif sheet_name == "TRX":
                row['TRX, $'] = self._round_balance(balance.get('trx_balance', 0))
                row['USDT, $'] = self._round_balance(balance.get('usdt_balance', 0))
                row['Other Tokens, $'] = self._round_balance(balance.get('other_tokens_balance', 0))
                row['Total Balance, $'] = self._round_balance(balance.get('total_balance', 0))
            elif sheet_name in ["OKX", "BINANCE", "BYBIT", "BACKPACK", "KUCOIN", "MEXC", "GATE"]:
                row['Total Balance, $'] = self._round_balance(balance.get('total_balance', 0))
            else:
                row['Balance, $'] = self._round_balance(balance.get('total_balance', 0))
        else:
            # Если ошибка - записываем код ошибки во все колонки балансов
            error = balance['error']
            if sheet_name == "EVM":
                row['Chains, $'] = error
                row['DeFi & Other, $'] = error
                row['Polymarket Positions, $'] = error
                row['Polymarket Total, $'] = error
                row['Hyperliquid Total, $'] = error
                row['Lighter, $'] = error
                row['Total Balance, $'] = error
            elif sheet_name == "SOL":
                row['Tokens, $'] = error
                row['DeFi, $'] = error
                row['Total Balance, $'] = error
            elif sheet_name == "BTC":
                row['BTC Amount, $'] = error
                row['Runes, $'] = error
                row['Inscriptions, $'] = error
                row['Total Balance, $'] = error
            elif sheet_name == "TRX":
                row['TRX, $'] = error
                row['USDT, $'] = error
                row['Other Tokens, $'] = error
                row['Total Balance, $'] = error
            elif sheet_name in ["OKX", "BINANCE", "BYBIT", "BACKPACK", "KUCOIN", "MEXC", "GATE"]:
                row['Total Balance, $'] = error
            else:
                row['Balance, $'] = error

        return row

    def _create_group_stats_row(
        self,
        sheet_name: str,
        group_name: str,
        wallets: List[Dict[str, str]]
    ) -> Dict[str, any]:
        """
        Создать строку статистики группы "[Group Name] Group Stats:"
        Формулы будут добавлены позже в _apply_styles

        Args:
            sheet_name: Имя листа
            group_name: Название группы
            wallets: Список всех кошельков (для определения структуры)

        Returns:
            Словарь с данными строки статистики
        """
        # Определяем структуру базовых колонок
        if sheet_name in ["OKX", "KUCOIN"]:
            row = {
                'Name': f'{group_name} Group Stats:',
                'Group': '',
                'API Key': '',
                'Secret Key': '',
                'Passphrase': ''
            }
        elif sheet_name in ["BINANCE", "BYBIT", "BACKPACK", "MEXC", "GATE"]:
            row = {
                'Name': f'{group_name} Group Stats:',
                'Group': '',
                'API Key': '',
                'Secret Key': ''
            }
        else:
            row = {
                'Name': f'{group_name} Group Stats:',
                'Group': '',
                'Address': ''
            }

        # Добавляем пустые значения для колонок балансов (формулы добавятся в _apply_styles)
        if sheet_name == "EVM":
            row['Chains, $'] = ''
            row['DeFi & Other, $'] = ''
            row['Polymarket Positions, $'] = ''
            row['Polymarket Total, $'] = ''
            row['Hyperliquid Total, $'] = ''
            row['Lighter, $'] = ''
            row['Total Balance, $'] = ''
        elif sheet_name == "SOL":
            row['Tokens, $'] = ''
            row['DeFi, $'] = ''
            row['Total Balance, $'] = ''
        elif sheet_name == "BTC":
            row['BTC Amount, $'] = ''
            row['Runes, $'] = ''
            row['Inscriptions, $'] = ''
            row['Total Balance, $'] = ''
        elif sheet_name == "TRX":
            row['TRX, $'] = ''
            row['USDT, $'] = ''
            row['Other Tokens, $'] = ''
            row['Total Balance, $'] = ''
        elif sheet_name in ["OKX", "BINANCE", "BYBIT", "BACKPACK", "KUCOIN", "MEXC", "GATE"]:
            row['Total Balance, $'] = ''
        else:
            row['Balance, $'] = ''

        return row

    def _create_empty_row(
        self,
        sheet_name: str,
        wallets: List[Dict[str, str]]
    ) -> Dict[str, any]:
        """
        Создать пустую строку

        Args:
            sheet_name: Имя листа
            wallets: Список всех кошельков (для определения структуры)

        Returns:
            Словарь с пустыми значениями
        """
        # Такая же структура как у group stats, но Name тоже пустой
        row = self._create_group_stats_row(sheet_name, '', wallets)
        row['Name'] = ''
        return row

    def _create_total_row(
        self,
        sheet_name: str,
        wallets: List[Dict[str, str]]
    ) -> Dict[str, any]:
        """
        Создать строку "Total:" с общими суммами

        Args:
            sheet_name: Имя листа
            wallets: Список всех кошельков (для определения структуры)

        Returns:
            Словарь с данными строки Total
        """
        row = self._create_group_stats_row(sheet_name, '', wallets)
        row['Name'] = 'Total:'
        return row

    def _apply_styles(self, file_path: Path, results_by_sheet: Dict[str, Dict]) -> None:
        """
        Применить стили к заголовкам, автоподбор ширины столбцов и добавить формулы для групп и итогов

        Args:
            file_path: Путь к файлу
            results_by_sheet: Словарь с данными по каждому листу
        """
        try:
            wb = load_workbook(file_path)

            # Применяем стили для листа "Total Stats"
            if "Total Stats" in wb.sheetnames:
                ws = wb["Total Stats"]
                # Применяем жирный шрифт для заголовков
                for col in range(1, ws.max_column + 1):
                    ws.cell(1, col).font = Font(bold=True)

                # Применяем стили для строк
                for row in range(1, ws.max_row + 1):
                    category_value = ws.cell(row, 2).value  # Колонка Category

                    # Жирный шрифт для строк с "TOTAL BALANCE", "Categories", "Tokens"
                    if category_value in ["TOTAL BALANCE", "Categories", "Tokens"]:
                        ws.cell(row, 2).font = Font(bold=True)
                        ws.cell(row, 3).font = Font(bold=True)
                    # Серый цвет для подкатегорий (начинаются с "  ")
                    elif category_value and isinstance(category_value, str) and category_value.startswith('  '):
                        # Серый цвет (50% от черного = 808080)
                        ws.cell(row, 2).font = Font(color="808080")
                        ws.cell(row, 3).font = Font(color="808080")

                # Автоподбор ширины столбцов
                ws.column_dimensions['A'].width = 15  # Section
                ws.column_dimensions['B'].width = 30  # Category
                ws.column_dimensions['C'].width = 15  # Amount ($)

            # Список имен колонок с балансами для разных типов листов
            balance_columns = [
                'Balance, $',                # Для неизвестных типов
                'Chains, $',                 # EVM
                'DeFi & Other, $',           # EVM
                'Polymarket Positions, $',   # EVM
                'Polymarket Total, $',       # EVM
                'Hyperliquid Total, $',      # EVM
                'Lighter, $',                # EVM
                'Total Balance, $',          # Все типы
                'Tokens, $',                 # SOL
                'DeFi, $',                   # SOL
                'BTC Amount, $',             # BTC
                'Runes, $',                  # BTC
                'Inscriptions, $',           # BTC
                'TRX, $',                    # TRX
                'USDT, $',                   # TRX
                'Other Tokens, $'            # TRX
                # APT теперь использует динамические колонки токенов
            ]

            for sheet_name, data in results_by_sheet.items():
                if sheet_name not in wb.sheetnames:
                    continue

                ws = wb[sheet_name]
                wallets = data['wallets']

                # Для листов "Tokens Stats" используем токены, для остальных - балансы
                if sheet_name.endswith("Tokens Stats"):
                    tokens = data.get('tokens', [])
                    balances = None
                else:
                    balances = data['balances']
                    tokens = None

                # Проверяем наличие группировки (ищем строки "Group Stats:")
                has_grouping = False
                for row in range(2, ws.max_row + 1):
                    name_value = ws.cell(row, 1).value
                    if name_value and 'Group Stats:' in str(name_value):
                        has_grouping = True
                        break

                # Собираем колонки балансов для этого листа
                if sheet_name.endswith("Tokens Stats"):
                    # Для токенов - берем все колонки кроме Name, Group, Address
                    sheet_balance_columns = [ws.cell(1, col).value for col in range(1, ws.max_column + 1)
                                            if ws.cell(1, col).value not in ['Name', 'Group', 'Address']
                                            and ws.cell(1, col).value]
                else:
                    # Для остальных - используем базовый список
                    sheet_balance_columns = balance_columns

                if has_grouping:
                    # Применяем стили для группированных данных
                    self._apply_grouped_styles(ws, sheet_balance_columns)
                else:
                    # Применяем стили для негруппированных данных (как раньше)
                    self._apply_simple_styles(ws, sheet_balance_columns)

                # Автоподбор ширины столбцов на основе исходных данных
                if sheet_name.endswith("Tokens Stats"):
                    self._apply_column_widths_tokens(ws, wallets, tokens)
                else:
                    self._apply_column_widths(ws, sheet_name, wallets, balances)

            wb.save(file_path)

        except Exception as e:
            warning_log(f"Не удалось применить стили: {str(e)}")

    def _apply_column_widths(
        self,
        ws,
        sheet_name: str,
        wallets: List[Dict[str, str]],
        balances: List[Dict[str, any]]
    ) -> None:
        """
        Применить автоподбор ширины столбцов на основе исходных данных от API

        Args:
            ws: Worksheet openpyxl
            sheet_name: Имя листа
            wallets: Список кошельков/аккаунтов
            balances: Список балансов
        """
        # Получаем все названия колонок из заголовка
        column_names = [ws.cell(1, col).value for col in range(1, ws.max_column + 1)]

        for col_idx, col_name in enumerate(column_names, start=1):
            if col_name is None:
                continue

            # Длина заголовка
            header_length = len(str(col_name))
            max_data_length = 0

            # Базовые колонки
            if col_name == 'Name':
                max_data_length = max((len(str(w.get('name', ''))) for w in wallets), default=0)
            elif col_name == 'Group':
                max_data_length = max((len(str(w.get('group', ''))) for w in wallets), default=0)
            elif col_name == 'Address':
                max_data_length = max((len(str(w.get('address', ''))) for w in wallets), default=0)
            elif col_name == 'API Key':
                max_data_length = max((len(str(w.get('api_key', ''))) for w in wallets), default=0)
            elif col_name == 'Secret Key':
                max_data_length = max((len(str(w.get('secret_key', ''))) for w in wallets), default=0)
            elif col_name == 'Passphrase':
                max_data_length = max((len(str(w.get('passphrase', ''))) for w in wallets), default=0)
            # Колонки с балансами
            elif col_name == 'Chains, $':
                max_data_length = max((len(str(self._round_balance(b.get('net_balance', 0)))) for b in balances if b.get('error') is None), default=0)
            elif col_name == 'DeFi & Other, $':
                max_data_length = max((len(str(self._round_balance(b.get('apps_balance', 0)))) for b in balances if b.get('error') is None), default=0)
            elif col_name == 'Polymarket Positions, $':
                max_data_length = max((len(str(self._round_balance(b.get('polymarket_positions_balance', 0)))) for b in balances if b.get('error') is None), default=0)
            elif col_name == 'Polymarket Total, $':
                max_data_length = max((len(str(self._round_balance(b.get('polymarket_total_balance', 0)))) for b in balances if b.get('error') is None), default=0)
            elif col_name == 'Hyperliquid Total, $':
                max_data_length = max((len(str(self._round_balance(b.get('hyperliquid_balance', 0)))) for b in balances if b.get('error') is None), default=0)
            elif col_name == 'Lighter, $':
                max_data_length = max((len(str(self._round_balance(b.get('lighter_balance', 0)))) for b in balances if b.get('error') is None), default=0)
            elif col_name == 'Tokens, $':
                max_data_length = max((len(str(self._round_balance(b.get('tokens_balance', 0)))) for b in balances if b.get('error') is None), default=0)
            elif col_name == 'DeFi, $':
                max_data_length = max((len(str(self._round_balance(b.get('defi_balance', 0)))) for b in balances if b.get('error') is None), default=0)
            elif col_name == 'BTC Amount, $':
                max_data_length = max((len(str(self._round_balance(b.get('btc_balance', 0)))) for b in balances if b.get('error') is None), default=0)
            elif col_name == 'Runes, $':
                max_data_length = max((len(str(self._round_balance(b.get('runes_balance', 0)))) for b in balances if b.get('error') is None), default=0)
            elif col_name == 'Inscriptions, $':
                max_data_length = max((len(str(self._round_balance(b.get('inscriptions_balance', 0)))) for b in balances if b.get('error') is None), default=0)
            elif col_name == 'TRX, $':
                max_data_length = max((len(str(self._round_balance(b.get('trx_balance', 0)))) for b in balances if b.get('error') is None), default=0)
            elif col_name == 'USDT, $':
                max_data_length = max((len(str(self._round_balance(b.get('usdt_balance', 0)))) for b in balances if b.get('error') is None), default=0)
            elif col_name == 'Other Tokens, $':
                max_data_length = max((len(str(self._round_balance(b.get('other_tokens_balance', 0)))) for b in balances if b.get('error') is None), default=0)
            elif col_name == 'Total Balance, $' or col_name == 'Balance, $':
                max_data_length = max((len(str(self._round_balance(b.get('total_balance', 0)))) for b in balances if b.get('error') is None), default=0)

            # Определяем отступ в зависимости от типа колонки
            # Для длинных данных (адреса, ключи) - больший отступ
            long_data_columns = ['Address', 'API Key', 'Secret Key', 'Passphrase']
            padding = 10 if col_name in long_data_columns else 3

            # Устанавливаем ширину: максимум из заголовка и данных + отступ
            column_width = max(header_length, max_data_length) + padding
            ws.column_dimensions[get_column_letter(col_idx)].width = column_width

    def _apply_column_widths_tokens(
        self,
        ws,
        wallets: List[Dict[str, str]],
        tokens_list: List[Dict[str, any]]
    ) -> None:
        """
        Применить автоподбор ширины столбцов для листа токенов

        Args:
            ws: Worksheet openpyxl
            wallets: Список кошельков
            tokens_list: Список токенов
        """
        # Получаем все названия колонок из заголовка
        column_names = [ws.cell(1, col).value for col in range(1, ws.max_column + 1)]

        for col_idx, col_name in enumerate(column_names, start=1):
            if col_name is None:
                continue

            # Длина заголовка
            header_length = len(str(col_name))
            max_data_length = 0

            # Базовые колонки
            if col_name == 'Name':
                max_data_length = max((len(str(w.get('name', ''))) for w in wallets), default=0)
            elif col_name == 'Group':
                max_data_length = max((len(str(w.get('group', ''))) for w in wallets), default=0)
            elif col_name == 'Address':
                # Проверяем что address есть в wallets (для кошельков, не бирж)
                if wallets and 'address' in wallets[0]:
                    max_data_length = max((len(str(w.get('address', ''))) for w in wallets), default=0)
                else:
                    max_data_length = 0
            # Колонки с токенами
            else:
                # Убираем ", $" из названия колонки чтобы получить символ токена
                token_symbol = col_name.replace(', $', '')
                for tokens in tokens_list:
                    if tokens and tokens.get('error') is None:
                        value = tokens.get(token_symbol, 0)
                        if isinstance(value, (int, float)):
                            value_str = str(self._round_balance(value))
                            max_data_length = max(max_data_length, len(value_str))

            # Определяем отступ
            long_data_columns = ['Address']
            padding = 10 if col_name in long_data_columns else 3

            # Устанавливаем ширину
            column_width = max(header_length, max_data_length) + padding
            ws.column_dimensions[get_column_letter(col_idx)].width = column_width

    def _apply_simple_styles(self, ws, balance_columns):
        """
        Применить стили для негруппированных данных (как раньше)

        Args:
            ws: Worksheet openpyxl
            balance_columns: Список колонок с балансами
        """
        last_data_row = ws.max_row
        total_row = last_data_row + 1  # Новая строка для итогов

        # Добавляем формулы SUMIF в новую строку итогов
        for col in range(1, ws.max_column + 1):
            col_name = ws.cell(1, col).value
            if col_name in balance_columns:
                col_letter = get_column_letter(col)
                formula = f"=SUMIF({col_letter}2:{col_letter}{last_data_row},\">0\")"
                ws.cell(total_row, col, formula)
                # Применяем жирный шрифт
                ws.cell(total_row, col).font = Font(bold=True)

    def _apply_grouped_styles(self, ws, balance_columns):
        """
        Применить стили для группированных данных

        Args:
            ws: Worksheet openpyxl
            balance_columns: Список колонок с балансами
        """
        # Находим все строки с "Group Stats:" и "Total:"
        stats_rows = []
        total_row = None
        group_start = 2  # Начало первой группы (после заголовка)

        # Определяем индекс колонки Group (обычно колонка B = 2)
        group_col_index = None
        for col in range(1, ws.max_column + 1):
            if ws.cell(1, col).value == 'Group':
                group_col_index = col
                break

        for row in range(2, ws.max_row + 1):
            name_value = ws.cell(row, 1).value
            if name_value:
                if 'Group Stats:' in str(name_value):
                    # Нашли строку статистики группы
                    stats_rows.append((group_start, row))
                    group_start = row + 2  # След группа начнется через 2 строки (stats + empty)
                elif str(name_value) == 'Total:':
                    total_row = row

        # Добавляем формулы для каждой строки "Group Stats:"
        for group_start_row, stats_row in stats_rows:
            # Применяем жирный шрифт к колонке Name
            ws.cell(stats_row, 1).font = Font(bold=True)

            for col in range(1, ws.max_column + 1):
                col_name = ws.cell(1, col).value
                if col_name in balance_columns:
                    col_letter = get_column_letter(col)
                    # Формула SUMIF для диапазона группы (исключая саму строку статистики)
                    formula = f"=SUMIF({col_letter}{group_start_row}:{col_letter}{stats_row - 1},\">0\")"
                    ws.cell(stats_row, col, formula)
                    # Применяем жирный шрифт
                    ws.cell(stats_row, col).font = Font(bold=True)

        # Добавляем формулы для строки "Total:"
        if total_row and group_col_index:
            # Применяем жирный шрифт к колонке Name
            ws.cell(total_row, 1).font = Font(bold=True)

            for col in range(1, ws.max_column + 1):
                col_name = ws.cell(1, col).value
                if col_name in balance_columns:
                    col_letter = get_column_letter(col)
                    group_col_letter = get_column_letter(group_col_index)

                    # Формула SUMIFS: суммируем только строки где Group НЕ пустой
                    # Это исключит строки "Group Stats:", "Total:" и пустые строки
                    formula = f'=SUMIFS({col_letter}:{col_letter},{group_col_letter}:{group_col_letter},"<>")'
                    ws.cell(total_row, col, formula)
                    # Применяем жирный шрифт
                    ws.cell(total_row, col).font = Font(bold=True)

    def get_available_sheets(self) -> List[str]:
        """
        Получить список доступных листов в файле данных

        Returns:
            Список имен листов
        """
        try:
            if not self.data_file.exists():
                error_log(f"Файл данных не найден: {self.data_file}")
                return []

            xl_file = pd.ExcelFile(self.data_file)
            sheets = xl_file.sheet_names
            info_log(f"Найдено {len(sheets)} листов: {', '.join(sheets)}")
            return sheets

        except Exception as e:
            error_log(f"Ошибка чтения списка листов: {str(e)}")
            return []
