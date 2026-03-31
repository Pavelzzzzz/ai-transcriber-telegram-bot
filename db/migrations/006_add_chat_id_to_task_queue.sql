DO $$
BEGIN
    ALTER TABLE task_queue ADD COLUMN IF NOT EXISTS chat_id BIGINT;
    CREATE INDEX IF NOT EXISTS idx_task_queue_chat_id ON task_queue(chat_id);
    
    INSERT INTO schema_migrations (version, description) 
    VALUES ('006', 'Add chat_id column to task_queue')
    ON CONFLICT (version) DO NOTHING;
END $$;