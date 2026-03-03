-- Google Drive: папка на категорию, файл на видео (для удаления после результата).
-- Выполните в Supabase SQL Editor.

-- topics: папка на Drive для категории
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'topics' AND column_name = 'drive_folder_id'
    ) THEN
        ALTER TABLE topics ADD COLUMN drive_folder_id TEXT;
    END IF;
END $$;

-- videos: ID файла на Drive (для удаления после отправки ссылки)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'videos' AND column_name = 'drive_file_id'
    ) THEN
        ALTER TABLE videos ADD COLUMN drive_file_id TEXT;
    END IF;
END $$;
