# Развёртывание бота на бесплатный хост

Бот работает в режиме **webhook**: Telegram шлёт обновления на ваш URL. Ниже — варианты бесплатного хостинга.

---

## Вариант 1: Render (рекомендуется)

**Плюсы:** бесплатно, не нужна карта для Web Service, есть HTTPS.  
**Минусы:** сервис «засыпает» после ~15 мин без запросов; первый ответ после сна может быть 30–60 сек (Telegram повторяет запросы).

### Шаги

1. **Аккаунт:** зарегистрируйтесь на [render.com](https://render.com).

2. **Репозиторий:** залейте проект в **GitHub** (или GitLab). В корне должны быть `requirements.txt`, `app/`, `.env.example`.

3. **В корне репозитория** должен быть файл **`.python-version`** с содержимым `3.12` (или `3.11`) — иначе Render может взять Python 3.14 и сборка `pydantic-core` упадёт. В этом проекте файл уже есть.

4. **Новый Web Service:**
   - Render → **New** → **Web Service**.
   - Подключите репозиторий.
   - **Settings:**
     - **Runtime:** Python 3
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `python -m app.main`
   - **Environment** — добавьте переменные (при желании можно задать **PYTHON_VERSION** = `3.12.5`, если Render проигнорирует `.python-version`) (значения из вашего `.env`):

   | Key | Value |
   |-----|--------|
   | `BOT_TOKEN` | Токен от @BotFather |
   | `USE_POLLING` | `false` |
   | `WEBHOOK_HOST` | `https://ВАШ-SERVICE-НА-RENDER.onrender.com` (без слэша в конце) |
   | `WEBHOOK_PATH` | `/webhook` |
   | `SUPABASE_URL` | `https://ВАШ_PROJECT.supabase.co` |
   | `SUPABASE_SERVICE_ROLE_KEY` | ваш service role key |
   | `YANDEX_DISK_TOKEN` | OAuth-токен Яндекс.Диска |
   | `YANDEX_DISK_ROOT_PATH` | `/bot_videos` (или свой путь) |

   Переменную **PORT** Render подставляет сам, в коде она уже учитывается.

5. **Deploy:** нажмите **Create Web Service**. После первого деплоя возьмите URL сервиса (например `https://your-bot.onrender.com`) и в **Environment** задайте:
   - `WEBHOOK_HOST` = `https://your-bot.onrender.com`

   При необходимости перезапустите сервис (Redeploy), чтобы webhook обновился.

6. **Проверка:** отправьте боту в Telegram команду `/start`. Если бот «спал», первый ответ может прийти с задержкой.

---

## Вариант 2: Fly.io

**Плюсы:** бесплатный тариф, сервис не засыпает, быстрый отклик.  
**Минусы:** нужна установка `flyctl` и привязка карты (списаний нет в рамках free tier).

### Шаги

1. Установите [flyctl](https://fly.io/docs/hands-on/install-flyctl/) и выполните `fly auth login`.

2. В корне проекта создайте `Dockerfile`:

   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   ENV WEBAPP_HOST=0.0.0.0
   ENV PORT=8080
   EXPOSE 8080
   CMD ["python", "-m", "app.main"]
   ```

3. Создайте приложение и задайте секреты:

   ```bash
   fly launch --no-deploy
   fly secrets set BOT_TOKEN=ваш_токен
   fly secrets set USE_POLLING=false
   fly secrets set WEBHOOK_HOST=https://ВАШ_APP.fly.dev
   fly secrets set SUPABASE_URL=https://ВАШ_PROJECT.supabase.co
   fly secrets set SUPABASE_SERVICE_ROLE_KEY=ваш_ключ
   fly secrets set YANDEX_DISK_TOKEN=ваш_токен
   ```

   После первого `fly launch` в консоли будет URL приложения (например `https://your-bot.fly.dev`). Подставьте его в `WEBHOOK_HOST` и снова выполните `fly secrets set WEBHOOK_HOST=...`.

4. Откройте порт и задеплойте:

   ```bash
   fly scale count 1
   fly deploy
   ```

---

## Вариант 3: Railway

**Плюсы:** простой деплой из GitHub, сервис не засыпает.  
**Минусы:** бесплатно только в рамках ежемесячного кредита (~$5), дальше платно.

1. [railway.app](https://railway.app) → **Start a New Project** → **Deploy from GitHub** → выберите репозиторий.

2. **Variables** — добавьте те же переменные, что и для Render (без `PORT` — Railway подставит сам).

3. **Settings** → **Deploy**:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python -m app.main`

4. **Settings** → **Networking** → **Generate Domain**. Скопируйте URL (например `https://your-bot.up.railway.app`) и в переменных задайте `WEBHOOK_HOST` = этот URL. Перезапустите деплой.

---

## Общее для всех вариантов

- **Режим:** на хосте всегда `USE_POLLING=false` и задан `WEBHOOK_HOST` с вашим HTTPS-URL.
- **Порт:** на Render и Railway хост сам задаёт `PORT`; в коде используется он (если есть) или `WEBAPP_PORT` из настроек.
- **Секреты:** `BOT_TOKEN`, `SUPABASE_SERVICE_ROLE_KEY`, `YANDEX_DISK_TOKEN` не коммитьте в репозиторий — только в переменных окружения хоста.
- **Миграции:** таблицы и колонки создайте в Supabase по инструкциям из README и CONTENT_CODE.md.

После деплоя отправьте боту `/start` и проверьте ответ. Если что-то не работает — проверьте логи на панели хоста и что `WEBHOOK_HOST` совпадает с реальным URL сервиса.
