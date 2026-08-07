"""
Модуль для сохранения результатов анализа в JSON формат
Генерирует JSON файлы для веб-интерфейса
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from modules.utils.logger import info_log, success_log, error_log


class JSONHandler:
    """Класс для сохранения результатов в JSON"""

    def __init__(self, output_dir: str = "website/data"):
        """
        Инициализация обработчика JSON

        Args:
            output_dir: Папка для сохранения JSON файлов
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_results_to_json(
        self,
        results_by_sheet: Dict[str, Dict],
        output_filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Сохранить результаты анализа в JSON файл

        Args:
            results_by_sheet: Словарь {sheet_name: {"wallets": [...], "balances": [...]}}
            output_filename: Имя выходного файла (опционально)

        Returns:
            Путь к созданному файлу или None при ошибке
        """
        try:
            # Генерируем имя файла с timestamp
            if output_filename is None:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                output_filename = f"balance_{timestamp}.json"

            output_file = self.output_dir / output_filename

            # Формируем структуру JSON
            json_data = self._create_json_structure(results_by_sheet)

            # Сохраняем в файл с красивым форматированием
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)

            # Также сохраняем как latest.json для автоматической загрузки на сайте
            latest_file = self.output_dir / "latest.json"
            with open(latest_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)

            success_log(f"JSON сохранен: {output_file}")
            info_log(f"Latest JSON обновлен: {latest_file}")

            # Обновляем список файлов
            self._update_files_list()

            return str(output_file)

        except Exception as e:
            error_log(f"Ошибка сохранения JSON: {str(e)}")
            return None

    def _create_json_structure(self, results_by_sheet: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Создать структуру JSON из results_by_sheet

        Args:
            results_by_sheet: Словарь с данными по каждому листу

        Returns:
            Словарь для сохранения в JSON
        """
        # Метаданные
        timestamp = datetime.now().isoformat()
        timestamp_readable = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Собираем общий баланс
        total_balance = 0
        for sheet_name, data in results_by_sheet.items():
            # Пропускаем листы "Tokens Stats"
            if sheet_name.endswith("Tokens Stats"):
                continue
            balances = data.get('balances', [])
            for balance in balances:
                if balance.get('error') is None:
                    total_balance += balance.get('total_balance', 0)

        # Собираем категории
        categories = {}
        tokens_stats = {}

        for sheet_name, data in results_by_sheet.items():
            if sheet_name.endswith("Tokens Stats"):
                # Пропускаем APT Tokens Stats (больше не создаем)
                if sheet_name == "APT Tokens Stats":
                    continue
                # Обработка листов с токенами (только EVM и SOL)
                category_name = sheet_name.replace(" Tokens Stats", "")
                tokens_stats[category_name] = self._process_tokens_stats(data)
            else:
                # Обработка основных листов
                categories[sheet_name] = self._process_category(sheet_name, data)

        # Собираем данные для Total Stats (как в Excel)
        total_stats = self._create_total_stats(results_by_sheet)

        return {
            "metadata": {
                "timestamp": timestamp,
                "timestamp_readable": timestamp_readable,
                "total_balance": round(total_balance, 2)
            },
            "total_stats": total_stats,
            "categories": categories,
            "tokens_stats": tokens_stats
        }

    def _process_category(self, sheet_name: str, data: Dict) -> Dict[str, Any]:
        """
        Обработать данные одной категории (EVM, SOL, BTC, APT, биржи)

        Args:
            sheet_name: Имя листа
            data: Данные листа

        Returns:
            Словарь с обработанными данными категории
        """
        wallets = data.get('wallets', [])
        balances = data.get('balances', [])

        # Собираем данные по кошелькам/аккаунтам
        items = []
        for wallet, balance in zip(wallets, balances):
            item = {
                "name": wallet.get('name', ''),
                "group": wallet.get('group', '')
            }

            # Для кошельков добавляем адрес
            if 'address' in wallet:
                item['address'] = wallet['address']

            # Для бирж добавляем API ключи (только последние 4 символа для безопасности)
            if 'api_key' in wallet:
                api_key = wallet.get('api_key', '')
                item['api_key_last4'] = api_key[-4:] if len(api_key) >= 4 else api_key

            # Добавляем балансы
            if balance.get('error') is None:
                # Детальные балансы в зависимости от типа
                if sheet_name == "EVM":
                    item['balances'] = {
                        "chains": round(balance.get('net_balance', 0), 2),
                        "defi_other": round(balance.get('apps_balance', 0), 2),
                        "polymarket_positions": round(balance.get('polymarket_positions_balance', 0), 2),
                        "polymarket_total": round(balance.get('polymarket_total_balance', 0), 2),
                        "hyperliquid": round(balance.get('hyperliquid_balance', 0), 2),
                        "lighter": round(balance.get('lighter_balance', 0), 2),
                        "total": round(balance.get('total_balance', 0), 2)
                    }
                elif sheet_name == "SOL":
                    item['balances'] = {
                        "tokens": round(balance.get('tokens_balance', 0), 2),
                        "defi": round(balance.get('defi_balance', 0), 2),
                        "total": round(balance.get('total_balance', 0), 2)
                    }
                elif sheet_name == "BTC":
                    item['balances'] = {
                        "btc": round(balance.get('btc_balance', 0), 2),
                        "runes": round(balance.get('runes_balance', 0), 2),
                        "inscriptions": round(balance.get('inscriptions_balance', 0), 2),
                        "total": round(balance.get('total_balance', 0), 2)
                    }
                elif sheet_name == "APT":
                    item['balances'] = {
                        "apt": round(balance.get('apt_balance', 0), 2),
                        "other_tokens": round(balance.get('other_tokens_balance', 0), 2),
                        "staked_apt": round(balance.get('staked_apt_balance', 0), 2),
                        "total": round(balance.get('total_balance', 0), 2)
                    }
                elif sheet_name == "TRX":
                    item['balances'] = {
                        "trx": round(balance.get('trx_balance', 0), 2),
                        "usdt": round(balance.get('usdt_balance', 0), 2),
                        "other_tokens": round(balance.get('other_tokens_balance', 0), 2),
                        "total": round(balance.get('total_balance', 0), 2)
                    }
                else:
                    # Для бирж и неизвестных типов
                    item['balances'] = {
                        "total": round(balance.get('total_balance', 0), 2)
                    }

                # Добавляем токены если есть
                tokens = balance.get('tokens')
                if tokens and tokens.get('error') is None:
                    item['tokens'] = {k: round(v, 2) for k, v in tokens.items() if k != 'error' and isinstance(v, (int, float))}
            else:
                item['error'] = balance['error']

            items.append(item)

        # Собираем статистику категории
        balance_sums = data.get('balance_sums', {})
        category_stats = {}

        if sheet_name == "EVM":
            category_stats = {
                "chains": round(balance_sums.get('net', 0), 2),
                "defi_other": round(balance_sums.get('apps', 0), 2),
                "polymarket_positions": round(balance_sums.get('polymarket_positions', 0), 2),
                "polymarket_total": round(balance_sums.get('polymarket_total', 0), 2),
                "hyperliquid": round(balance_sums.get('hyperliquid', 0), 2),
                "lighter": round(balance_sums.get('lighter', 0), 2),
                "total": round(balance_sums.get('total', 0), 2)
            }
        elif sheet_name == "SOL":
            category_stats = {
                "tokens": round(balance_sums.get('tokens', 0), 2),
                "defi": round(balance_sums.get('defi', 0), 2),
                "total": round(balance_sums.get('total', 0), 2)
            }
        elif sheet_name == "BTC":
            category_stats = {
                "btc": round(balance_sums.get('btc', 0), 2),
                "runes": round(balance_sums.get('runes', 0), 2),
                "inscriptions": round(balance_sums.get('inscriptions', 0), 2),
                "total": round(balance_sums.get('total', 0), 2)
            }
        elif sheet_name == "APT":
            category_stats = {
                "apt": round(balance_sums.get('apt', 0), 2),
                "other_tokens": round(balance_sums.get('other_tokens', 0), 2),
                "staked_apt": round(balance_sums.get('staked', 0), 2),
                "total": round(balance_sums.get('total', 0), 2)
            }
        elif sheet_name == "TRX":
            category_stats = {
                "trx": round(balance_sums.get('trx', 0), 2),
                "usdt": round(balance_sums.get('usdt', 0), 2),
                "other_tokens": round(balance_sums.get('other_tokens', 0), 2),
                "total": round(balance_sums.get('total', 0), 2)
            }
        else:
            category_stats = {
                "total": round(balance_sums.get('total', 0), 2)
            }

        return {
            "items": items,
            "stats": category_stats
        }

    def _process_tokens_stats(self, data: Dict) -> Dict[str, Any]:
        """
        Обработать данные листа с токенами (EVM/SOL/APT Tokens Stats)

        Args:
            data: Данные листа токенов

        Returns:
            Словарь с данными токенов
        """
        wallets = data.get('wallets', [])
        tokens_list = data.get('tokens', [])

        items = []
        for wallet, tokens in zip(wallets, tokens_list):
            item = {
                "name": wallet.get('name', ''),
                "group": wallet.get('group', '')
            }

            # Добавляем адрес если это кошелек
            if 'address' in wallet:
                item['address'] = wallet['address']

            # Добавляем токены
            if tokens and tokens.get('error') is None:
                item['tokens'] = {k: round(v, 2) for k, v in tokens.items() if k != 'error' and isinstance(v, (int, float))}
            else:
                item['error'] = tokens.get('error', 'ERROR') if tokens else 'ERROR'

            items.append(item)

        # Собираем общую статистику по токенам
        all_tokens = {}
        for tokens in tokens_list:
            if tokens and tokens.get('error') is None:
                for token_symbol, value in tokens.items():
                    if token_symbol != 'error' and isinstance(value, (int, float)):
                        all_tokens[token_symbol] = all_tokens.get(token_symbol, 0) + value

        # Сортируем токены по убыванию стоимости
        sorted_tokens = {k: round(v, 2) for k, v in sorted(all_tokens.items(), key=lambda x: x[1], reverse=True)}

        return {
            "items": items,
            "totals": sorted_tokens
        }

    def _create_total_stats(self, results_by_sheet: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Создать данные для Total Stats (аналог листа Total Stats в Excel)

        Args:
            results_by_sheet: Словарь с данными по каждому листу

        Returns:
            Словарь с общей статистикой
        """
        # Собираем категории
        categories = {}

        # EVM
        if "EVM" in results_by_sheet:
            balances = results_by_sheet["EVM"].get('balances', [])
            evm_data = {
                "total": 0,
                "chains": 0,
                "defi_other": 0,
                "polymarket_positions": 0,
                "polymarket_total": 0,
                "hyperliquid": 0,
                "lighter": 0
            }
            for b in balances:
                if b.get('error') is None:
                    evm_data["total"] += b.get('total_balance', 0)
                    evm_data["chains"] += b.get('net_balance', 0)
                    evm_data["defi_other"] += b.get('apps_balance', 0)
                    evm_data["polymarket_positions"] += b.get('polymarket_positions_balance', 0)
                    evm_data["polymarket_total"] += b.get('polymarket_total_balance', 0)
                    evm_data["hyperliquid"] += b.get('hyperliquid_balance', 0)
                    evm_data["lighter"] += b.get('lighter_balance', 0)

            categories["EVM"] = {k: round(v, 2) for k, v in evm_data.items()}

        # SOL
        if "SOL" in results_by_sheet:
            balances = results_by_sheet["SOL"].get('balances', [])
            sol_data = {"total": 0, "tokens": 0, "defi": 0}
            for b in balances:
                if b.get('error') is None:
                    sol_data["total"] += b.get('total_balance', 0)
                    sol_data["tokens"] += b.get('tokens_balance', 0)
                    sol_data["defi"] += b.get('defi_balance', 0)

            categories["SOL"] = {k: round(v, 2) for k, v in sol_data.items()}

        # BTC
        if "BTC" in results_by_sheet:
            balances = results_by_sheet["BTC"].get('balances', [])
            btc_data = {"total": 0, "btc": 0, "runes": 0, "inscriptions": 0}
            for b in balances:
                if b.get('error') is None:
                    btc_data["total"] += b.get('total_balance', 0)
                    btc_data["btc"] += b.get('btc_balance', 0)
                    btc_data["runes"] += b.get('runes_balance', 0)
                    btc_data["inscriptions"] += b.get('inscriptions_balance', 0)

            categories["BTC"] = {k: round(v, 2) for k, v in btc_data.items()}

        # APT
        if "APT" in results_by_sheet:
            balances = results_by_sheet["APT"].get('balances', [])
            apt_data = {"total": 0, "apt": 0, "other_tokens": 0, "staked_apt": 0}
            for b in balances:
                if b.get('error') is None:
                    apt_data["total"] += b.get('total_balance', 0)
                    apt_data["apt"] += b.get('apt_balance', 0)
                    apt_data["other_tokens"] += b.get('other_tokens_balance', 0)
                    apt_data["staked_apt"] += b.get('staked_apt_balance', 0)

            categories["APT"] = {k: round(v, 2) for k, v in apt_data.items()}

        # TRX
        if "TRX" in results_by_sheet:
            balances = results_by_sheet["TRX"].get('balances', [])
            trx_data = {"total": 0, "trx": 0, "usdt": 0, "other_tokens": 0}
            for b in balances:
                if b.get('error') is None:
                    trx_data["total"] += b.get('total_balance', 0)
                    trx_data["trx"] += b.get('trx_balance', 0)
                    trx_data["usdt"] += b.get('usdt_balance', 0)
                    trx_data["other_tokens"] += b.get('other_tokens_balance', 0)

            categories["TRX"] = {k: round(v, 2) for k, v in trx_data.items()}

        # Биржи
        exchanges = ["OKX", "BINANCE", "BYBIT", "BACKPACK", "KUCOIN", "MEXC", "GATE"]
        for exchange in exchanges:
            if exchange in results_by_sheet:
                balances = results_by_sheet[exchange].get('balances', [])
                exchange_total = 0
                for b in balances:
                    if b.get('error') is None:
                        exchange_total += b.get('total_balance', 0)
                categories[exchange] = {"total": round(exchange_total, 2)}

        # Собираем все токены
        all_tokens = {}
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
                                # Убираем метки категорий для бирж
                                clean_symbol = token_symbol
                                for category in exchange_categories:
                                    category_pattern = f" ({category})"
                                    if category_pattern in token_symbol:
                                        clean_symbol = token_symbol.replace(category_pattern, '')
                                        break

                                all_tokens[clean_symbol] = all_tokens.get(clean_symbol, 0) + value

        # Сортируем токены по убыванию стоимости
        sorted_tokens = {k: round(v, 2) for k, v in sorted(all_tokens.items(), key=lambda x: x[1], reverse=True)}
        sorted_tokens['Other'] = round(total_other, 2)

        return {
            "categories": categories,
            "tokens": sorted_tokens
        }

    def _update_files_list(self) -> None:
        """
        Обновить файл files_list.json со списком всех доступных анализов
        """
        try:
            # Находим все JSON файлы (кроме latest.json и files_list.json)
            json_files = sorted(
                [f for f in self.output_dir.glob("balance_*.json")],
                key=lambda x: x.stem,
                reverse=True  # Новые файлы первыми
            )

            # Формируем список файлов
            files = []
            for json_file in json_files:
                try:
                    # Читаем метаданные из файла
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    metadata = data.get('metadata', {})
                    timestamp_readable = metadata.get('timestamp_readable', json_file.stem.replace('balance_', '').replace('_', ' '))
                    total_balance = metadata.get('total_balance', 0)

                    files.append({
                        "filename": json_file.name,
                        "timestamp": timestamp_readable,
                        "total_balance": total_balance
                    })
                except:
                    pass  # Пропускаем файлы с ошибками

            # Сохраняем список
            files_list_path = self.output_dir / "files_list.json"
            with open(files_list_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "files": files,
                    "count": len(files),
                    "generated_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)

            info_log(f"Обновлен files_list.json ({len(files)} файлов)")

        except Exception as e:
            error_log(f"Не удалось обновить files_list.json: {str(e)}")
