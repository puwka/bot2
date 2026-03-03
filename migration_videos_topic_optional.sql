-- Опционально: добавить в таблицу videos колонки для работы бота (категории и ссылка).
-- Выполните в Supabase SQL Editor, если в videos нет topic_id и/или url.
-- После этого «Статистика по категориям» и «Получить видео» по категориям будут работать.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'videos' AND column_name = 'topic_id'
    ) THEN
        ALTER TABLE videos ADD COLUMN topic_id UUID REFERENCES topics(id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'videos' AND column_name = 'url'
    ) THEN
        ALTER TABLE videos ADD COLUMN url TEXT;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'videos' AND column_name = 'platform'
    ) THEN
        ALTER TABLE videos ADD COLUMN platform TEXT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_videos_topic_id ON videos (topic_id);
