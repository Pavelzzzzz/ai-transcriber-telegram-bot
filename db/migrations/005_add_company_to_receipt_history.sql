DO $$
BEGIN
    ALTER TABLE receipt_history ADD COLUMN IF NOT EXISTS company VARCHAR(100);
    
    INSERT INTO schema_migrations (version, description) 
    VALUES ('005', 'Add company column to receipt_history')
    ON CONFLICT (version) DO NOTHING;
END $$;
