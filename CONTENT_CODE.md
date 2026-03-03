# Код контента (маркировка роликов)

Формат: **исполнитель (A) + порядковый номер (#)**; при выдаче дистрибьюторам в код добавляется **дистрибьютор (D)**. Код генерируется при загрузке в бота, имя файла на диске меняется на код.

---

## 1. Формат кода

**При загрузке:** `A3#0042`  
**После выдачи дистрибьютора:** `A3#0042D7`

| Сегмент | Смысл | Лимит | Пример |
|---------|--------|--------|--------|
| **A** | Исполнитель (кто делал ролик) | 1–99 | A3 = исполнитель 3 |
| **#** | Порядковый номер ролика от этого исполнителя | 1–9999 | #0042 = 42-й ролик |
| **D** | Дистрибьютор (добавляется при выдаче) | 0–99 | D7 = дистрибьютор 7 |

- Код **генерируется автоматически** при загрузке видео в бота (загрузчик = исполнитель, номер = следующий по счёту).
- Файл на Яндекс.Диске сохраняется под именем кода, например `A3#0042.mp4`.
- При выдаче задачи дистрибьюторам в `content_code` добавляется сегмент **D** (код дистрибьютора из профиля пользователя).

---

## 2. БД

**Таблица `videos`:**
- `content_code` (text, nullable) — код контента, при выдаче обновляется (добавляется D).
- `performer_code` (int, nullable) — код исполнителя (1–99).
- `performer_sequence` (int, nullable) — порядковый номер ролика у этого пользователя.
- `uploaded_by_user_id` (uuid, nullable) — id пользователя-загрузчика; счётчик номера ролика привязан к нему.

**Таблица `users`:**
- `performer_code` (int, nullable) — код исполнителя для загрузчиков (1–99). Если не задан, при загрузке используется 1.
- `distributor_code` (int, nullable) — код дистрибьютора для дистрибьюторов (0–99). Подставляется в код при выдаче видео.

**Миграция в Supabase (SQL):**
```sql
ALTER TABLE videos ADD COLUMN IF NOT EXISTS content_code text;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS performer_code int;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS performer_sequence int;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS uploaded_by_user_id uuid REFERENCES users(id);
ALTER TABLE users ADD COLUMN IF NOT EXISTS performer_code int;
ALTER TABLE users ADD COLUMN IF NOT EXISTS distributor_code int;
```

---

## 3. Логика в боте

1. **Загрузка видео (uploader):** берётся `performer_code` пользователя (или 1), считается следующий `performer_sequence` для этого исполнителя, собирается код `A{performer}#{sequence}`, файл загружается на Диск с именем `A3#0042.mp4`, в БД создаётся запись с `content_code`, `performer_code`, `performer_sequence`.
2. **Выдача дистрибьюторам:** при создании выдачи (distribution) к текущему `content_code` видео добавляется сегмент D с `distributor_code` пользователя (например `A3#0042` → `A3#0042D7`), запись в `videos` обновляется.

---

## 4. Утилиты (app/utils/content_code.py)

- `build_performer_code(performer, sequence)` — собрать код при загрузке, например `A3#0042`.
- `append_distributor(content_code, distributor_code)` — добавить сегмент дистрибьютора к коду.
- `parse(content_code)` — разобрать код в словарь `{performer, sequence, distributor}`.
- `filename_for_code(content_code, ext)` — имя файла по коду, например `A3#0042.mp4`.
- `parse_from_filename(filename)` — извлечь код из имени файла (при синхронизации с диска).

---

## 5. Назначение кодов пользователям

- **performer_code** — задаётся загрузчикам (вручную в БД или через админку), чтобы ролики разных исполнителей имели разные коды A.
- **distributor_code** — задаётся дистрибьюторам (вручную в БД или через админку), чтобы в коде было видно, какому дистрибьютору выдали ролик.

После выдачи в коде будет полная цепочка: исполнитель → номер ролика → дистрибьютор (например `A3#0042D7`).
