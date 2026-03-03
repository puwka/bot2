# Trendwatch Telegram Bot

Telegram-бот для платформы мониторинга коротких видео.

## Стек

- Python 3.11 + aiogram 3.x
- Supabase (подключение только через SUPABASE_URL + SERVICE_ROLE_KEY, без прямого URL БД)
- Webhook или polling + aiohttp

## Требования

Нужен **уже установленный** Python 3.11 или 3.12 (ничего дополнительно качать не нужно, если они есть).

**Windows — один скрипт создаёт venv из Python 3.12/3.11 и сам ставит зависимости (важно: иначе может использоваться 3.14 и понадобится Rust):**
```powershell
.\setup.ps1
.\.venv\Scripts\Activate.ps1
python -m app.main
```

Если скрипт пишет «Python 3.11 or 3.12 not found» — установите один из них (Microsoft Store или python.org) и снова запустите `.\setup.ps1`.

## Быстрый старт

### 1. Подготовка базы данных

Откройте **Supabase SQL Editor** и выполните содержимое файла `migration.sql`.
Это создаст все необходимые таблицы, индексы и триггеры.

> Таблицы `topics`, `sources`, `videos` должны уже существовать.

### 2. Настройка окружения

```bash
cp .env.example .env
```

Заполните `.env`:

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен Telegram бота от @BotFather |
| `WEBHOOK_HOST` | Публичный URL сервера (с HTTPS) |
| `WEBHOOK_PATH` | Путь webhook (по умолчанию `/webhook`) |
| `SUPABASE_URL` | URL проекта Supabase (https://PROJECT.supabase.co) |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (НЕ anon key!) — доступ к БД через API |

### 3. Запуск локально или на сервере

После `setup.ps1`, активации venv и `pip install -r requirements.txt`:

```bash
python -m app.main
```

Бот будет слушать webhook на `WEBHOOK_HOST` + `WEBHOOK_PATH` (порт из переменной `PORT` или `WEBAPP_PORT`, по умолчанию 8080).

**Развёртывание на бесплатный хост (Render, Fly.io, Railway):** см. [DEPLOY.md](DEPLOY.md).

### 4. Создание первого администратора

Вставьте в Supabase SQL Editor:

```sql
INSERT INTO users (telegram_id, role) VALUES (YOUR_TELEGRAM_ID, 'ADMIN');
```

После этого отправьте боту `/start`.

### Загрузка видео аплоадером (файлом)

Аплоадер может отправлять видеофайл или ссылку. Для загрузки файлов в Supabase Storage:

1. В Supabase: **Storage** → **New bucket** → имя `videos`, включите **Public bucket** (чтобы ссылки на видео были доступны).
2. В `.env` при необходимости задайте другой бакет: `STORAGE_BUCKET=videos` (по умолчанию уже `videos`).

### Ошибка «pydantic-core» / Rust при `pip install`

Значит в venv попал Python 3.14. Запустите заново `.\setup.ps1` — он пересоздаст `.venv` из 3.11 или 3.12, если они установлены.

### Ошибка «Supabase connection failed»

Проверьте **SUPABASE_URL** и **SUPABASE_SERVICE_ROLE_KEY** в `.env` и доступ в интернет к Supabase API.

## Архитектура

```
/app
  config.py              — Конфигурация (SUPABASE_URL, SERVICE_ROLE_KEY, без DATABASE_URL)
  db.py                  — Проверка подключения к Supabase
  supabase_client.py     — Supabase client (service role, обход RLS)
  dto.py                 — DTO для ответов API
  main.py                — Точка входа, webhook/polling

  /repositories          — Доступ к данным через Supabase API (async через to_thread)
  /services              — Бизнес-логика
  /handlers              — aiogram роутеры + FSM
  /middlewares           — Role check, Rate limit
  /keyboards             — Inline-клавиатуры
  /utils                 — Утилиты (детекция платформ)
  /models                — Старые SQLAlchemy модели (для справки по схеме)
```

## Роли

| Роль | Возможности |
|---|---|
| **ADMIN** | Создание категорий, пользователей, назначение ролей/категорий, просмотр статистики |
| **UPLOADER** | Загрузка видео: выбор категории → ссылка → описание |
| **DISTRIBUTOR** | Получение видео для обработки, отправка ссылок-результатов |

## Бизнес-правила

- Дистрибьютор никогда не получает одно и то же видео дважды
- Дубликаты ссылок-результатов запрещены глобально
- Незавершённые задачи видны администратору
- Администратор может переназначить задачу
- Все действия логируются в `action_logs`
- Rate limiting на уровне middleware
