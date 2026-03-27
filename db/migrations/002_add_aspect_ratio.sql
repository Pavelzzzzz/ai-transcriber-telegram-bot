DO $$
BEGIN
    ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS aspect_ratio VARCHAR(10) DEFAULT '1:1';
    UPDATE user_settings SET aspect_ratio = '1:1' WHERE aspect_ratio IS NULL;
    INSERT INTO schema_migrations (version, description) 
    VALUES ('002', 'Add aspect_ratio column to user_settings')
    ON CONFLICT (version) DO NOTHING;
END $$;
