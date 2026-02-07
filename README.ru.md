> **[English version](README.md)**

### Создание и активация виртуального окружения

```bash
python3 -m venv venv
```

```bash
source venv/bin/activate
```

### Установка зависимостей

```bash
pip install -r requirements.txt
npm install
```

### Данные

Поменять данные на свои в `data.xlsx`. Неиспользуемые листы можно не удалять, просто в настройках убрать из списка ENABLED_SHEETS.

Для апи ключей бирж достаточно дать право на чтение. Также можно в поле Specific Proxy в таблице указать отдельный прокси для каждого аккаунта, либо указать "no proxy", либо оставить пустым - будут использоваться те же настройки что и для всех.

- Binance: https://www.binance.com/en/my/settings/api-management
- OKX: https://www.okx.com/account/my-api
- Bybit: https://www.bybit.com/app/user/api-management
- Backpack: https://backpack.exchange/portfolio/settings/api-keys
- KuCoin: https://www.kucoin.com/account/api
- MEXC: https://www.mexc.com/user/openapi
- Gate: https://www.gate.com/myaccount/profile/api-key/manage (тип: API v4 Key)

### Настройки

`settings.py` - все комментарии читаем и под себя настраиваем прежде чем запускать.

### Прокси

В файле `proxies.txt`

webshare.io тут можно купить 100 shared прокси за +-3$.
Если без прокси то лучше ставить больше задержки между запросами.

### Запуск

```bash
python main.py
```

### Результаты

- **Excel:** `analyses/balance_YYYY-MM-DD_HH-MM-SS.xlsx`
- **JSON:** `website/data/balance_YYYY-MM-DD_HH-MM-SS.json`
- **Web:** http://localhost:8000 (режим 2)

### Требования

- Python 3.8+
- Node.js 14+
