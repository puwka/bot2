-- Добавить значение 'uploaded' в enum platform_enum (для загрузки видео файлом).
-- Выполните в Supabase SQL Editor, если при загрузке видео появляется ошибка:
--   invalid input value for enum platform_enum: "uploaded"
-- или 400 Bad Request при запросе к sources/platform=uploaded.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum e
        JOIN pg_type t ON e.enumtypid = t.oid
        WHERE t.typname = 'platform_enum' AND e.enumlabel = 'uploaded'
    ) THEN
        ALTER TYPE platform_enum ADD VALUE 'uploaded';
    END IF;
END
$$;
