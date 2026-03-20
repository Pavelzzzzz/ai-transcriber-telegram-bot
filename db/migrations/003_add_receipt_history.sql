DO $$
BEGIN
    CREATE TABLE receipt_history (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        items JSONB NOT NULL,
        total DECIMAL(10, 2) DEFAULT 0,
        file_path VARCHAR(500),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX idx_receipt_history_user_id ON receipt_history(user_id);
    CREATE INDEX idx_receipt_history_created_at ON receipt_history(created_at DESC);
    
    INSERT INTO schema_migrations (version, description) 
    VALUES ('003', 'Add receipt_history table');
END $$;
