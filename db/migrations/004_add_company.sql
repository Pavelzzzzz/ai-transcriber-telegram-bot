DO $$
BEGIN
    ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS company VARCHAR(100);
    
    INSERT INTO schema_migrations (version, description) 
    VALUES ('004', 'Add company column to user_settings')
    ON CONFLICT (version) DO NOTHING;
END $$;
