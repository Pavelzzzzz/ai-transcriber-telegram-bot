DO $$
BEGIN
    ALTER TABLE user_settings ADD COLUMN noise_reduction BOOLEAN DEFAULT TRUE;
    UPDATE user_settings SET noise_reduction = TRUE WHERE noise_reduction IS NULL;
    INSERT INTO schema_migrations (version, description) 
    VALUES ('001', 'Add noise_reduction column to user_settings');
END $$;
