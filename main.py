"""
Balance Checker Combine - главный скрипт
Проверяет балансы кошельков EVM и Solana из data.xlsx
"""

import time
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import settings
from modules.utils.logger import (
    setup_logging,
    info_log,
    error_log,
    success_log,
    warning_log
)
from modules.utils.proxy_manager import ProxyManager
from modules.utils.excel_handler import ExcelHandler
from modules.utils.json_handler import JSONHandler
from modules.checkers.evm_checker import get_evm_balance
from modules.checkers.sol_checker import get_sol_balance
from modules.checkers.btc_checker import get_btc_balance
from modules.checkers.apt_checker import get_apt_balance
from modules.checkers.okx_checker import get_okx_balance
from modules.checkers.binance_checker import get_binance_balance
from modules.checkers.bybit_checker import get_bybit_balance
from modules.checkers.backpack_checker import get_backpack_balance
from modules.checkers.kucoin_checker import get_kucoin_balance
from modules.checkers.mexc_checker import get_mexc_balance
from modules.checkers.gate_checker import get_gate_balance


def display_ascii_banner():
    banner = """
┳┓  ┓         ┏┓┓    ┓       ┏┓     ┓ •    
┣┫┏┓┃┏┓┏┓┏┏┓  ┃ ┣┓┏┓┏┃┏┏┓┏┓  ┃ ┏┓┏┳┓┣┓┓┏┓┏┓
┻┛┗┻┗┗┻┛┗┗┗   ┗┛┛┗┗ ┗┛┗┗ ┛   ┗┛┗┛┛┗┗┗┛┗┛┗┗ 
                                           """
    print(banner)


def _parse_specific_proxy(specific_proxy: Optional[str]) -> Optional[Dict[str, str]]:
    """
    Парсит specific_proxy в формат proxy_dict для httpx

    Args:
        specific_proxy: Строка прокси в формате "host:port:username:password" или "no proxy" или None

    Returns:
        Dict с прокси в формате httpx, или None
    """
    if not specific_proxy:
        # Пусто - вернуть None (будет использоваться текущая механика)
        return None

    if specific_proxy.lower() == "no proxy":
        # Явно указано не использовать прокси
        return "no_proxy"  # Специальный маркер

    # Парсим формат host:port:username:password
    parts = specific_proxy.split(':')
    if len(parts) != 4:
        error_log(f"Неверный формат прокси: {specific_proxy}. Ожидается host:port:username:password")
        return None

    host, port, username, password = parts
    proxy_url = f"http://{username}:{password}@{host}:{port}"

    return {
        "http://": proxy_url,
        "https://": proxy_url
    }


def _process_single_wallet(
    wallet: Dict[str, str],
    idx: int,
    total: int,
    checker_func,
    proxy_manager: Optional[ProxyManager] = None
) -> Dict[str, any]:
    """
    Обработать один кошелек (для параллельной обработки)

    Args:
        wallet: Данные кошелька
        idx: Индекс кошелька
        total: Общее количество кошельков
        checker_func: Функция для проверки баланса
        proxy_manager: Менеджер прокси или None

    Returns:
        Словарь с балансом
    """
    address = wallet['address']
    name = wallet['name']

    # Формируем информацию о кошельке для вывода
    wallet_info_str = f"[{idx}/{total}] {name} ({address[:8]}...{address[-6:]})"

    # Определяем параметры запроса
    proxy_dict = None

    # Пытаемся получить баланс с БЕСКОНЕЧНЫМИ повторными попытками
    balance = None
    attempt = 0

    while True:
        attempt += 1

        if settings.USE_PROXY and proxy_manager:
            proxy_dict = proxy_manager.get_proxy(settings.RANDOM_PROXY_SELECTION)
            if not proxy_dict:
                error_log(f"{wallet_info_str} → Нет доступных прокси после попытки {attempt}, ждем 5 сек и пробуем снова...")
                time.sleep(5)
                continue

        # Выполняем запрос (для EVM, SOL и APT собираем токены сразу)
        if checker_func in [get_evm_balance, get_sol_balance, get_apt_balance]:
            balance = checker_func(
                address=address,
                proxy_dict=proxy_dict,
                timeout=settings.REQUEST_TIMEOUT,
                wallet_info=wallet_info_str,
                collect_tokens=True,
                min_token_value=settings.MIN_TOKEN_VALUE_TO_TRACK
            )
        else:
            balance = checker_func(
                address=address,
                proxy_dict=proxy_dict,
                timeout=settings.REQUEST_TIMEOUT,
                wallet_info=wallet_info_str
            )

        # Проверяем результат
        if balance.get('error') is None:
            # Успешно получили баланс
            # Задержка после успешного запроса с прокси (если настроена)
            if settings.USE_PROXY and proxy_manager and settings.PROXY_REQUEST_DELAY > 0:
                time.sleep(settings.PROXY_REQUEST_DELAY)
            break
        else:
            # Ошибка - пробуем другой прокси если доступны
            if settings.USE_PROXY and proxy_manager and proxy_dict:
                # НЕ помечаем прокси как failed - пусть используется для других кошельков
                # Даже если прокси мертвый, он будет fail на повторных попытках и retry сработает
                warning_log(f"{wallet_info_str} → Попытка {attempt} провалилась (ошибка: {balance.get('error')}), пробуем другой прокси...")
                time.sleep(settings.PROXY_RETRY_DELAY)
            else:
                warning_log(f"{wallet_info_str} → Попытка {attempt} провалилась, повторяем...")
                time.sleep(settings.REQUEST_DELAY)

    return balance


def _process_wallets_sequential(
    wallets: List[Dict[str, str]],
    checker_func
) -> List[Dict[str, any]]:
    """
    Последовательная обработка кошельков с адаптивной задержкой

    Args:
        wallets: Список словарей с данными кошельков
        checker_func: Функция для проверки баланса

    Returns:
        Список словарей с балансами в том же порядке
    """
    balances = []
    total_wallets = len(wallets)

    # Определяем задержку в зависимости от количества кошельков
    if total_wallets < 10:
        delay = 0.5
    else:  # 10-100
        delay = 0.2

    for idx, wallet in enumerate(wallets, 1):
        balance = _process_single_wallet(wallet, idx, len(wallets), checker_func, None)
        balances.append(balance)

        # Задержка между запросами
        if idx < len(wallets):
            time.sleep(delay)

    return balances


def _process_wallets_parallel(
    wallets: List[Dict[str, str]],
    checker_func,
    proxy_manager: ProxyManager
) -> List[Dict[str, any]]:
    """
    Параллельная обработка кошельков с использованием прокси

    Args:
        wallets: Список словарей с данными кошельков
        checker_func: Функция для проверки баланса
        proxy_manager: Менеджер прокси

    Returns:
        Список словарей с балансами в том же порядке
    """
    # Определяем количество параллельных потоков
    if settings.PROXY_MAX_WORKERS and settings.PROXY_MAX_WORKERS > 0:
        # Используем настройку из конфига (но не больше чем доступных прокси)
        max_workers = min(settings.PROXY_MAX_WORKERS, proxy_manager.get_available_proxy_count())
    else:
        # Автоматически = количеству доступных прокси
        max_workers = proxy_manager.get_available_proxy_count()

    info_log(f"Параллельная обработка: {max_workers} потоков")

    # Словарь для хранения результатов с сохранением порядка
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Запускаем задачи
        future_to_idx = {
            executor.submit(
                _process_single_wallet,
                wallet,
                idx,
                len(wallets),
                checker_func,
                proxy_manager
            ): idx
            for idx, wallet in enumerate(wallets, 1)
        }

        # Собираем результаты по мере выполнения
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                balance = future.result()
                results[idx] = balance
            except Exception as e:
                error_log(f"Ошибка обработки кошелька {idx}: {str(e)}")
                results[idx] = {"error": "ERROR"}

    # Возвращаем результаты в правильном порядке
    balances = [results[idx] for idx in sorted(results.keys())]

    return balances


def _process_wallets_parallel_no_proxy(
    wallets: List[Dict[str, str]],
    checker_func
) -> List[Dict[str, any]]:
    """
    Параллельная обработка кошельков без прокси (для > 100 кошельков)

    Args:
        wallets: Список словарей с данными кошельков
        checker_func: Функция для проверки баланса

    Returns:
        Список словарей с балансами в том же порядке
    """
    # Ограничиваем количество потоков до 10 чтобы не нагружать API
    max_workers = 10
    info_log(f"Параллельная обработка без прокси: {max_workers} потоков")

    # Словарь для хранения результатов с сохранением порядка
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Запускаем задачи
        future_to_idx = {
            executor.submit(
                _process_single_wallet,
                wallet,
                idx,
                len(wallets),
                checker_func,
                None
            ): idx
            for idx, wallet in enumerate(wallets, 1)
        }

        # Собираем результаты по мере выполнения
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                balance = future.result()
                results[idx] = balance
            except Exception as e:
                error_log(f"Ошибка обработки кошелька {idx}: {str(e)}")
                results[idx] = {"error": "ERROR"}

    # Возвращаем результаты в правильном порядке
    balances = [results[idx] for idx in sorted(results.keys())]

    return balances


def process_wallets(
    wallets: List[Dict[str, str]],
    checker_func,
    proxy_manager: Optional[ProxyManager] = None
) -> List[Dict[str, any]]:
    """
    Обработать список кошельков через чекер

    Args:
        wallets: Список словарей с данными кошельков
        checker_func: Функция для проверки баланса
        proxy_manager: Менеджер прокси или None

    Returns:
        Список словарей с балансами в том же порядке
    """
    # Если используем прокси - ВСЕГДА параллельная обработка (независимо от количества)
    if settings.USE_PROXY and proxy_manager:
        return _process_wallets_parallel(wallets, checker_func, proxy_manager)

    # Без прокси - выбираем стратегию по количеству кошельков
    total_wallets = len(wallets)
    if total_wallets > 100:
        # Больше 100 - параллельная обработка без прокси
        return _process_wallets_parallel_no_proxy(wallets, checker_func)
    else:
        # Меньше 100 - последовательная обработка с задержками
        return _process_wallets_sequential(wallets, checker_func)


def process_exchange_accounts(
    sheet_name: str,
    excel_handler: ExcelHandler,
    checker_func
) -> Optional[Dict]:
    """
    Обработать биржевые аккаунты (OKX, Binance, Bybit) - специальная обработка для API ключей

    Args:
        sheet_name: Имя листа (OKX, BINANCE, BYBIT)
        excel_handler: Обработчик Excel
        checker_func: Функция чекера для конкретной биржи

    Returns:
        Словарь с данными {"wallets": [...], "balances": [...], "stats": {...}} или None при ошибке
    """
    info_log("=" * 80)
    info_log(f"Обработка листа: {sheet_name}")
    info_log("=" * 80)

    # Читаем аккаунты
    if sheet_name == "OKX":
        accounts = excel_handler.read_okx_accounts()
    elif sheet_name == "BINANCE":
        accounts = excel_handler.read_binance_accounts()
    elif sheet_name == "BYBIT":
        accounts = excel_handler.read_bybit_accounts()
    elif sheet_name == "BACKPACK":
        accounts = excel_handler.read_backpack_accounts()
    elif sheet_name == "KUCOIN":
        accounts = excel_handler.read_kucoin_accounts()
    elif sheet_name == "MEXC":
        accounts = excel_handler.read_mexc_accounts()
    elif sheet_name == "GATE":
        accounts = excel_handler.read_gate_accounts()
    else:
        error_log(f"Неизвестный тип биржи: {sheet_name}")
        return None

    if not accounts:
        warning_log(f"Лист {sheet_name} пустой или не найден, пропускаем")
        return None

    # Определяем стратегию обработки в зависимости от количества
    balances = []
    total = len(accounts)

    # Биржевые API сильнее реагируют на частые запросы, поэтому задержка вынесена в settings.py
    delay = getattr(settings, "EXCHANGE_REQUEST_DELAY", settings.REQUEST_DELAY)

    for idx, account in enumerate(accounts, 1):
        name = account['name']

        # Формируем информацию для вывода
        wallet_info_str = f"[{idx}/{total}] {name}"

        # Обрабатываем specific_proxy
        specific_proxy_str = account.get('specific_proxy')
        specific_proxy_dict = _parse_specific_proxy(specific_proxy_str)

        # Пытаемся получить баланс с ограниченным количеством попыток
        balance = None
        attempt = 0
        max_retries = settings.MAX_EXCHANGE_RETRIES

        while attempt < max_retries:
            attempt += 1

            # Определяем proxy_dict для текущего запроса
            proxy_dict = None

            if specific_proxy_dict == "no_proxy":
                # Явно указано не использовать прокси
                proxy_dict = None
            elif specific_proxy_dict:
                # Указан конкретный прокси - используем его
                proxy_dict = specific_proxy_dict
            # Если specific_proxy_dict = None, значит поле было пустым - оставляем proxy_dict = None (текущая механика)

            # Получаем баланс в зависимости от биржи
            if sheet_name == "OKX":
                # Для OKX собираем токены
                balance = checker_func(
                    api_key=account['api_key'],
                    secret_key=account['secret_key'],
                    passphrase=account['passphrase'],
                    proxy_dict=proxy_dict,
                    timeout=30,
                    wallet_info=wallet_info_str,
                    collect_tokens=True,
                    min_token_value=settings.MIN_EXCHANGE_TOKEN_VALUE_TO_TRACK
                )
            elif sheet_name == "KUCOIN":
                # Для KuCoin собираем токены
                balance = checker_func(
                    api_key=account['api_key'],
                    secret_key=account['secret_key'],
                    passphrase=account['passphrase'],
                    proxy_dict=proxy_dict,
                    timeout=30,
                    wallet_info=wallet_info_str,
                    collect_tokens=True,
                    min_token_value=settings.MIN_EXCHANGE_TOKEN_VALUE_TO_TRACK
                )
            elif sheet_name == "BINANCE":
                # Для Binance собираем токены
                balance = checker_func(
                    api_key=account['api_key'],
                    secret_key=account['secret_key'],
                    proxy_dict=proxy_dict,
                    timeout=30,
                    wallet_info=wallet_info_str,
                    collect_tokens=True,
                    min_token_value=settings.MIN_EXCHANGE_TOKEN_VALUE_TO_TRACK
                )
            elif sheet_name == "BYBIT":
                # Для Bybit собираем токены
                balance = checker_func(
                    api_key=account['api_key'],
                    secret_key=account['secret_key'],
                    proxy_dict=proxy_dict,
                    timeout=30,
                    wallet_info=wallet_info_str,
                    collect_tokens=True,
                    min_token_value=settings.MIN_EXCHANGE_TOKEN_VALUE_TO_TRACK
                )
            elif sheet_name == "BACKPACK":
                # Для Backpack собираем токены
                balance = checker_func(
                    api_key=account['api_key'],
                    secret_key=account['secret_key'],
                    proxy_dict=proxy_dict,
                    timeout=30,
                    wallet_info=wallet_info_str,
                    collect_tokens=True,
                    min_token_value=settings.MIN_EXCHANGE_TOKEN_VALUE_TO_TRACK
                )
            elif sheet_name == "MEXC":
                # Для MEXC собираем токены
                balance = checker_func(
                    api_key=account['api_key'],
                    secret_key=account['secret_key'],
                    proxy_dict=proxy_dict,
                    timeout=30,
                    wallet_info=wallet_info_str,
                    collect_tokens=True,
                    min_token_value=settings.MIN_EXCHANGE_TOKEN_VALUE_TO_TRACK
                )
            elif sheet_name == "GATE":
                # Для Gate.io собираем токены
                balance = checker_func(
                    api_key=account['api_key'],
                    secret_key=account['secret_key'],
                    proxy_dict=proxy_dict,
                    timeout=30,
                    wallet_info=wallet_info_str,
                    collect_tokens=True,
                    min_token_value=settings.MIN_EXCHANGE_TOKEN_VALUE_TO_TRACK
                )

            # Проверяем результат
            if balance.get('error') is None:
                # Успешно получили баланс
                break
            else:
                if attempt < max_retries:
                    warning_log(f"{wallet_info_str} → Попытка {attempt}/{max_retries} провалилась (ошибка: {balance.get('error')}), повторяем...")
                    time.sleep(settings.PROXY_RETRY_DELAY)
                else:
                    error_log(f"{wallet_info_str} → Все {max_retries} попыток провалились (ошибка: {balance.get('error')}), пропускаем аккаунт")
                    # Оставляем balance с error - он попадет в результаты как failed

        balances.append(balance)

        # Задержка между запросами (если не последний и задержка > 0)
        if idx < total and delay > 0:
            time.sleep(delay)

    # Подсчитываем статистику
    total_accounts = len(accounts)
    successful = sum(1 for b in balances if b.get('error') is None)
    failed = total_accounts - successful

    # Подсчитываем суммы балансов
    sum_total = sum(b.get('total_balance', 0) for b in balances if b.get('error') is None)
    sum_stats = {"total": sum_total}

    # Выводим статистику
    info_log("")
    info_log("=" * 80)
    info_log(f"СТАТИСТИКА ПО ЛИСТУ {sheet_name}")
    info_log("=" * 80)
    success_log(f"Успешно проверено: {successful}/{total_accounts}")
    if failed > 0:
        error_log(f"Не удалось проверить: {failed}/{total_accounts}")

    # Выводим суммы балансов
    info_log("")
    info_log("СУММЫ БАЛАНСОВ:")
    success_log(f"  ИТОГО:        ${sum_total:>15,.2f}")
    info_log("=" * 80)

    return {
        "wallets": accounts,
        "balances": balances,
        "stats": {
            "total": total_accounts,
            "successful": successful,
            "failed": failed
        },
        "balance_sums": sum_stats
    }


def process_sheet(
    sheet_name: str,
    excel_handler: ExcelHandler,
    proxy_manager: Optional[ProxyManager] = None
) -> Optional[Dict]:
    """
    Обработать один лист из Excel

    Args:
        sheet_name: Имя листа
        excel_handler: Обработчик Excel
        proxy_manager: Менеджер прокси или None

    Returns:
        Словарь с данными {"wallets": [...], "balances": [...], "stats": {...}} или None при ошибке
    """
    # Биржи обрабатываются отдельно (используют API ключи вместо адресов)
    if sheet_name == "OKX":
        return process_exchange_accounts(sheet_name, excel_handler, get_okx_balance)
    elif sheet_name == "BINANCE":
        return process_exchange_accounts(sheet_name, excel_handler, get_binance_balance)
    elif sheet_name == "BYBIT":
        return process_exchange_accounts(sheet_name, excel_handler, get_bybit_balance)
    elif sheet_name == "BACKPACK":
        return process_exchange_accounts(sheet_name, excel_handler, get_backpack_balance)
    elif sheet_name == "KUCOIN":
        return process_exchange_accounts(sheet_name, excel_handler, get_kucoin_balance)
    elif sheet_name == "MEXC":
        return process_exchange_accounts(sheet_name, excel_handler, get_mexc_balance)
    elif sheet_name == "GATE":
        return process_exchange_accounts(sheet_name, excel_handler, get_gate_balance)

    info_log("=" * 80)
    info_log(f"Обработка листа: {sheet_name}")
    info_log("=" * 80)

    # Читаем кошельки
    wallets = excel_handler.read_wallets_from_sheet(sheet_name)
    if not wallets:
        warning_log(f"Лист {sheet_name} пустой или не найден, пропускаем")
        return None

    # Определяем чекер по типу листа
    if sheet_name == "EVM":
        checker_func = get_evm_balance
    elif sheet_name == "SOL":
        checker_func = get_sol_balance
    elif sheet_name == "BTC":
        checker_func = get_btc_balance
    elif sheet_name == "APT":
        checker_func = get_apt_balance
    else:
        error_log(f"Неизвестный тип листа: {sheet_name}")
        return None

    # Обрабатываем кошельки
    balances = process_wallets(wallets, checker_func, proxy_manager)

    # Подсчитываем статистику
    total_wallets = len(wallets)
    successful = sum(1 for b in balances if b.get('error') is None)
    failed = total_wallets - successful

    # Подсчитываем суммы балансов
    sum_stats = {}
    if sheet_name == "EVM":
        sum_net = sum(b.get('net_balance', 0) for b in balances if b.get('error') is None)
        sum_apps = sum(b.get('apps_balance', 0) for b in balances if b.get('error') is None)
        sum_polymarket_positions = sum(b.get('polymarket_positions_balance', 0) for b in balances if b.get('error') is None)
        sum_polymarket_total = sum(b.get('polymarket_total_balance', 0) for b in balances if b.get('error') is None)
        sum_hyperliquid = sum(b.get('hyperliquid_balance', 0) for b in balances if b.get('error') is None)
        sum_lighter = sum(b.get('lighter_balance', 0) for b in balances if b.get('error') is None)
        sum_total = sum(b.get('total_balance', 0) for b in balances if b.get('error') is None)
        sum_stats = {
            "net": sum_net,
            "apps": sum_apps,
            "polymarket_positions": sum_polymarket_positions,
            "polymarket_total": sum_polymarket_total,
            "hyperliquid": sum_hyperliquid,
            "lighter": sum_lighter,
            "total": sum_total
        }
    elif sheet_name == "SOL":
        sum_tokens = sum(b.get('tokens_balance', 0) for b in balances if b.get('error') is None)
        sum_defi = sum(b.get('defi_balance', 0) for b in balances if b.get('error') is None)
        sum_total = sum(b.get('total_balance', 0) for b in balances if b.get('error') is None)
        sum_stats = {
            "tokens": sum_tokens,
            "defi": sum_defi,
            "total": sum_total
        }
    elif sheet_name == "BTC":
        sum_btc = sum(b.get('btc_balance', 0) for b in balances if b.get('error') is None)
        sum_runes = sum(b.get('runes_balance', 0) for b in balances if b.get('error') is None)
        sum_inscriptions = sum(b.get('inscriptions_balance', 0) for b in balances if b.get('error') is None)
        sum_total = sum(b.get('total_balance', 0) for b in balances if b.get('error') is None)
        sum_stats = {
            "btc": sum_btc,
            "runes": sum_runes,
            "inscriptions": sum_inscriptions,
            "total": sum_total
        }
    elif sheet_name == "APT":
        sum_apt = sum(b.get('apt_balance', 0) for b in balances if b.get('error') is None)
        sum_other_tokens = sum(b.get('other_tokens_balance', 0) for b in balances if b.get('error') is None)
        sum_staked = sum(b.get('staked_apt_balance', 0) for b in balances if b.get('error') is None)
        sum_total = sum(b.get('total_balance', 0) for b in balances if b.get('error') is None)
        sum_stats = {
            "apt": sum_apt,
            "other_tokens": sum_other_tokens,
            "staked": sum_staked,
            "total": sum_total
        }

    # Выводим статистику по листу
    info_log("")
    info_log("=" * 80)
    info_log(f"СТАТИСТИКА ПО ЛИСТУ {sheet_name}")
    info_log("=" * 80)
    success_log(f"Успешно проверено: {successful}/{total_wallets}")
    if failed > 0:
        error_log(f"Не удалось проверить: {failed}/{total_wallets}")

    # Выводим суммы балансов
    if sum_stats:
        info_log("")
        info_log("СУММЫ БАЛАНСОВ:")
        if sheet_name == "EVM":
            info_log(f"  Сети:                 ${sum_stats['net']:>15,.2f}")
            info_log(f"  DeFi & Other:         ${sum_stats['apps']:>15,.2f}")
            info_log(f"  Polymarket Positions: ${sum_stats['polymarket_positions']:>15,.2f}")
            info_log(f"  Polymarket Total:     ${sum_stats['polymarket_total']:>15,.2f}")
            info_log(f"  Hyperliquid Total:    ${sum_stats['hyperliquid']:>15,.2f}")
            info_log(f"  Lighter:              ${sum_stats['lighter']:>15,.2f}")
            info_log(f"  {'─' * 40}")
            success_log(f"  ИТОГО:                 ${sum_stats['total']:>15,.2f}")
        elif sheet_name == "SOL":
            info_log(f"  Токены:      ${sum_stats['tokens']:>15,.2f}")
            info_log(f"  DeFi:        ${sum_stats['defi']:>15,.2f}")
            info_log(f"  {'─' * 40}")
            success_log(f"  ИТОГО:        ${sum_stats['total']:>15,.2f}")
        elif sheet_name == "BTC":
            info_log(f"  BTC:         ${sum_stats['btc']:>15,.2f}")
            if sum_stats['runes'] > 0:
                info_log(f"  Руны:        ${sum_stats['runes']:>15,.2f}")
            if sum_stats['inscriptions'] > 0:
                info_log(f"  Инскрипции:  ${sum_stats['inscriptions']:>15,.2f}")
            info_log(f"  {'─' * 40}")
            success_log(f"  ИТОГО:        ${sum_stats['total']:>15,.2f}")
        elif sheet_name == "APT":
            info_log(f"  APT:         ${sum_stats['apt']:>15,.2f}")
            if sum_stats['other_tokens'] > 0:
                info_log(f"  Другие токены: ${sum_stats['other_tokens']:>13,.2f}")
            info_log(f"  APT в стейкинге: ${sum_stats['staked']:>11,.2f}")
            info_log(f"  {'─' * 40}")
            success_log(f"  ИТОГО:        ${sum_stats['total']:>15,.2f}")

    info_log("=" * 80)

    return {
        "wallets": wallets,
        "balances": balances,
        "stats": {
            "total": total_wallets,
            "successful": successful,
            "failed": failed
        },
        "balance_sums": sum_stats
    }


def main():
    """Главная функция"""

    # Настройка логирования
    setup_logging()

    info_log(f"Файл данных: {settings.DATA_FILE}")
    info_log(f"Листы для обработки: {', '.join(settings.ENABLED_SHEETS)}")
    info_log(f"Использование прокси: {'Да' if settings.USE_PROXY else 'Нет'}")
    info_log("=" * 80)

    # Инициализируем менеджер прокси
    proxy_manager = None
    if settings.USE_PROXY:
        info_log("Инициализация менеджера прокси...")
        proxy_manager = ProxyManager(settings.PROXY_FILE)

        if not proxy_manager.load_proxies():
            error_log("Не удалось загрузить прокси, продолжаем без прокси")
            proxy_manager = None
        else:
            info_log(f"Загружено прокси: {proxy_manager.get_proxy_count()}")

            # Проверяем прокси если включена проверка
            if settings.VERIFY_PROXIES:
                info_log("")
                working_proxies = proxy_manager.verify_proxies(
                    timeout=settings.PROXY_VERIFY_TIMEOUT,
                    max_workers=settings.PROXY_VERIFY_THREADS
                )

                if working_proxies == 0:
                    error_log("Ни один прокси не работает, продолжаем без прокси")
                    proxy_manager = None
                else:
                    success_log(f"Доступно рабочих прокси: {working_proxies}")
                info_log("")
            else:
                info_log(f"Проверка прокси отключена")

    # Инициализируем обработчик Excel
    excel_handler = ExcelHandler(
        data_file=settings.DATA_FILE,
        output_dir=settings.OUTPUT_DIR
    )

    # Инициализируем обработчик JSON
    json_handler = JSONHandler(output_dir="website/data")

    # Обрабатываем каждый включенный лист и собираем результаты
    results_by_sheet = {}
    processed_sheets = []
    failed_sheets = []

    for sheet_name in settings.ENABLED_SHEETS:
        try:
            result = process_sheet(sheet_name, excel_handler, proxy_manager)
            if result:
                results_by_sheet[sheet_name] = result
                processed_sheets.append(sheet_name)

                # Если обработали EVM лист - извлекаем статистику токенов из балансов
                if sheet_name == "EVM":
                    wallets = result['wallets']
                    balances = result['balances']

                    # Извлекаем токены из балансов (они уже собраны в get_evm_balance)
                    tokens_list = [balance.get('tokens') for balance in balances]

                    # Добавляем результаты токенов в структуру (только если есть хоть один с токенами)
                    if any(tokens is not None for tokens in tokens_list):
                        info_log("")
                        info_log("=" * 80)
                        info_log("СТАТИСТИКА ТОКЕНОВ EVM СОБРАНА")
                        info_log("=" * 80)

                        results_by_sheet["EVM Tokens Stats"] = {
                            "wallets": wallets,
                            "tokens": tokens_list
                        }

                # Если обработали SOL лист - извлекаем статистику токенов из балансов
                if sheet_name == "SOL":
                    wallets = result['wallets']
                    balances = result['balances']

                    # Извлекаем токены из балансов (они уже собраны в get_sol_balance)
                    tokens_list = [balance.get('tokens') for balance in balances]

                    # Добавляем результаты токенов в структуру (только если есть хоть один с токенами)
                    if any(tokens is not None for tokens in tokens_list):
                        info_log("")
                        info_log("=" * 80)
                        info_log("СТАТИСТИКА ТОКЕНОВ SOL СОБРАНА")
                        info_log("=" * 80)

                        results_by_sheet["SOL Tokens Stats"] = {
                            "wallets": wallets,
                            "tokens": tokens_list
                        }

                # Если обработали APT лист - извлекаем статистику токенов из балансов
                if sheet_name == "APT":
                    wallets = result['wallets']
                    balances = result['balances']

                    # Извлекаем токены из балансов (они уже собраны в get_apt_balance)
                    tokens_list = [balance.get('tokens') for balance in balances]

                    # Добавляем результаты токенов в структуру (только если есть хоть один с токенами)
                    if any(tokens is not None for tokens in tokens_list):
                        info_log("")
                        info_log("=" * 80)
                        info_log("СТАТИСТИКА ТОКЕНОВ APT СОБРАНА")
                        info_log("=" * 80)

                        results_by_sheet["APT Tokens Stats"] = {
                            "wallets": wallets,
                            "tokens": tokens_list
                        }

            else:
                failed_sheets.append(sheet_name)
        except Exception as e:
            error_log(f"Критическая ошибка при обработке листа {sheet_name}: {str(e)}")
            failed_sheets.append(sheet_name)

    # Сохраняем все результаты в Excel и JSON
    output_file = None
    json_file = None
    if results_by_sheet:
        output_file = excel_handler.save_results_to_excel(results_by_sheet)

        # Сохраняем также в JSON для веб-интерфейса
        if output_file:
            # Используем то же имя файла для JSON
            json_filename = Path(output_file).stem + ".json"
            json_file = json_handler.save_results_to_json(results_by_sheet, json_filename)

    # Собираем статистику
    total_all = 0
    successful_all = 0
    failed_all = 0
    sheet_stats = {}

    for sheet_name, data in results_by_sheet.items():
        if 'stats' in data:
            stats = data['stats']
            total_all += stats['total']
            successful_all += stats['successful']
            failed_all += stats['failed']
            sheet_stats[sheet_name] = stats

    # Собираем балансы
    grand_total = 0.0
    balance_details = {}

    for sheet_name, data in results_by_sheet.items():
        if 'balance_sums' in data and data['balance_sums']:
            sums = data['balance_sums']
            balance_details[sheet_name] = sums
            grand_total += sums.get('total', 0)

    # Компактный вывод итогов
    info_log("")
    if output_file:
        success_log(f"✓ Результаты: {output_file}")
    else:
        error_log("✗ Не удалось сохранить результаты")

    info_log("")

    # Статистика по кошелькам
    if failed_all > 0:
        sheet_info = ', '.join([f"{name}: {sheet_stats[name]['successful']}/{sheet_stats[name]['total']}" for name in sheet_stats])
        warning_log(f"Проверено кошельков: {successful_all}/{total_all} успешно ({sheet_info})")
        error_log(f"Не удалось проверить: {failed_all}")
    else:
        sheet_info = ', '.join([f"{name}: {sheet_stats[name]['successful']}" for name in sheet_stats])
        success_log(f"Проверено кошельков: {successful_all}/{total_all} успешно ({sheet_info})")

    # Балансы
    if balance_details:
        info_log("")
        info_log("Балансы:")
        for sheet_name, sums in balance_details.items():
            if sheet_name == "EVM":
                info_log(f"  EVM: ${sums.get('net', 0):,.2f} (сети) + ${sums.get('apps', 0):,.2f} (DeFi & Other) + ${sums.get('polymarket_positions', 0):,.2f} (Polymarket Positions) + ${sums.get('polymarket_total', 0):,.2f} (Polymarket Total) + ${sums.get('hyperliquid', 0):,.2f} (Hyperliquid) + ${sums.get('lighter', 0):,.2f} (Lighter) = ${sums.get('total', 0):,.2f}")
            elif sheet_name == "SOL":
                info_log(f"  SOL: ${sums.get('tokens', 0):,.2f} (токены) + ${sums.get('defi', 0):,.2f} (DeFi) = ${sums.get('total', 0):,.2f}")
            elif sheet_name == "BTC":
                parts = [f"${sums.get('btc', 0):,.2f} (BTC)"]
                if sums.get('runes', 0) > 0:
                    parts.append(f"${sums.get('runes', 0):,.2f} (руны)")
                if sums.get('inscriptions', 0) > 0:
                    parts.append(f"${sums.get('inscriptions', 0):,.2f} (инскрипции)")
                info_log(f"  BTC: {' + '.join(parts)} = ${sums.get('total', 0):,.2f}")
            elif sheet_name == "APT":
                parts = [f"${sums.get('apt', 0):,.2f} (APT)"]
                if sums.get('other_tokens', 0) > 0:
                    parts.append(f"${sums.get('other_tokens', 0):,.2f} (другие токены)")
                parts.append(f"${sums.get('staked', 0):,.2f} (APT в стейкинге)")
                info_log(f"  APT: {' + '.join(parts)} = ${sums.get('total', 0):,.2f}")
            elif sheet_name == "OKX":
                info_log(f"  OKX: ${sums.get('total', 0):,.2f}")
            elif sheet_name == "BINANCE":
                info_log(f"  BINANCE: ${sums.get('total', 0):,.2f}")
            elif sheet_name == "BYBIT":
                info_log(f"  BYBIT: ${sums.get('total', 0):,.2f}")
            elif sheet_name == "BACKPACK":
                info_log(f"  BACKPACK: ${sums.get('total', 0):,.2f}")
            elif sheet_name == "KUCOIN":
                info_log(f"  KUCOIN: ${sums.get('total', 0):,.2f}")
            elif sheet_name == "MEXC":
                info_log(f"  MEXC: ${sums.get('total', 0):,.2f}")
            elif sheet_name == "GATE":
                info_log(f"  GATE: ${sums.get('total', 0):,.2f}")

        info_log(f"  {'─' * 50}")
        success_log(f"  Общий баланс: ${grand_total:,.2f}")

    # Прокси и завершение
    info_log("")
    if proxy_manager:
        proxy_msg = f"Прокси: {proxy_manager.get_available_proxy_count()}/{proxy_manager.get_proxy_count()} рабочих | Работа завершена!"
    else:
        proxy_msg = "Работа завершена!"

    success_log(proxy_msg)


def start_web_server():
    """Запуск веб-сервера для просмотра результатов"""
    import http.server
    import socketserver
    import os
    import webbrowser
    from threading import Timer

    PORT = 8000
    DIRECTORY = "website"

    # Проверяем существование папки website
    if not os.path.exists(DIRECTORY):
        print(f"\nError: Folder '{DIRECTORY}' not found!")
        input("\nPress Enter to exit...")
        return

    # Проверяем существование index.html
    if not os.path.exists(os.path.join(DIRECTORY, "index.html")):
        print(f"\nError: File 'index.html' not found in '{DIRECTORY}' folder!")
        input("\nPress Enter to exit...")
        return

    class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=DIRECTORY, **kwargs)

        def log_message(self, format, *args):
            # Отключаем логи запросов для чистоты вывода
            pass

        def do_GET(self):
            """Обработка GET запросов"""
            # API endpoint для получения списка файлов
            if self.path == '/api/files':
                self.send_api_files_list()
            else:
                # Для всех остальных запросов используем стандартную обработку
                super().do_GET()

        def send_api_files_list(self):
            """Отправить список файлов в JSON формате"""
            import json
            from pathlib import Path
            from datetime import datetime

            try:
                data_dir = Path(DIRECTORY) / 'data'
                files_list = []

                # Сканируем папку data/ и ищем все balance_*.json файлы
                if data_dir.exists():
                    for json_file in sorted(data_dir.glob('balance_*.json'), reverse=True):
                        try:
                            # Читаем метаданные из файла
                            with open(json_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)

                            metadata = data.get('metadata', {})
                            timestamp_readable = metadata.get('timestamp_readable', '')
                            total_balance = metadata.get('total_balance', 0)

                            files_list.append({
                                'filename': json_file.name,
                                'timestamp': timestamp_readable,
                                'total_balance': total_balance
                            })
                        except Exception as e:
                            # Пропускаем поврежденные файлы
                            continue

                # Формируем ответ
                response = {
                    'files': files_list,
                    'count': len(files_list),
                    'generated_at': datetime.now().isoformat()
                }

                # Отправляем JSON ответ
                response_data = json.dumps(response, ensure_ascii=False).encode('utf-8')

                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Content-length', str(len(response_data)))
                self.send_header('Access-Control-Allow-Origin', '*')  # CORS
                self.end_headers()
                self.wfile.write(response_data)

            except Exception as e:
                # В случае ошибки возвращаем пустой список
                error_response = {
                    'files': [],
                    'count': 0,
                    'error': str(e)
                }
                response_data = json.dumps(error_response).encode('utf-8')

                self.send_response(500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Content-length', str(len(response_data)))
                self.end_headers()
                self.wfile.write(response_data)

    try:
        with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
            url = f"http://localhost:{PORT}"

            print(f"\nОткройте в браузере: {url}\n")

            # Автоматически открываем браузер через 1 секунду
            Timer(1.0, lambda: webbrowser.open(url)).start()

            httpd.serve_forever()

    except OSError as e:
        if "address already in use" in str(e).lower():
            print(f"\nError: Port {PORT} is already in use!")
            print(f"Try opening: http://localhost:{PORT}")
        else:
            print(f"\nServer startup error: {str(e)}")
        input("\nPress Enter to exit...")
    except KeyboardInterrupt:
        print()


def show_menu():
    """Показать меню выбора режима работы"""
    # Отображаем ASCII заставку
    display_ascii_banner()

    print("Режим:\n")
    print("1. Получение балансов")
    print("2. Открыть веб-интерфейс\n")

    while True:
        try:
            choice = input("Введите (1, 2): ").strip()

            if choice == "1":
                return "balance"
            elif choice == "2":
                return "web"
            else:
                print()
        except KeyboardInterrupt:
            print()
            return "exit"


if __name__ == "__main__":
    try:
        mode = show_menu()

        if mode == "balance":
            main()
        elif mode == "web":
            start_web_server()
        elif mode == "exit":
            pass

    except KeyboardInterrupt:
        warning_log("\nОстановлено пользователем (Ctrl+C)")
    except Exception as e:
        error_log(f"Критическая ошибка: {str(e)}")
        import traceback
        error_log(traceback.format_exc())
