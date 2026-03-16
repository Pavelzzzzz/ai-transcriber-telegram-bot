#!/bin/bash
set -e

echo "Environment: POSTGRES_USER=$POSTGRES_USER, POSTGRES_DB=$POSTGRES_DB"

echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
  if PGPASSWORD=$POSTGRES_PASSWORD psql -U "$POSTGRES_USER" -d "postgres" -c '\q' 2>/dev/null; then
    echo "PostgreSQL is ready!"
    break
  fi
  echo "Attempt $i - waiting..."
  sleep 1
done

echo "Creating tables in database $POSTGRES_DB..."
PGPASSWORD=$POSTGRES_PASSWORD psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<EOF
CREATE TABLE IF NOT EXISTS user_settings (
    user_id BIGINT PRIMARY KEY,
    image_model VARCHAR(20) DEFAULT 'sd15',
    image_style VARCHAR(30),
    aspect_ratio VARCHAR(10) DEFAULT '1:1',
    num_variations INT DEFAULT 1,
    negative_prompt TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS image_generation_history (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    prompt TEXT NOT NULL,
    model VARCHAR(20) NOT NULL,
    style VARCHAR(30),
    aspect_ratio VARCHAR(10),
    file_path VARCHAR(500),
    status VARCHAR(20) DEFAULT 'success',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_image_history_user_id ON image_generation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_image_history_created_at ON image_generation_history(created_at);

CREATE TABLE IF NOT EXISTS task_queue (
    task_id VARCHAR(255) PRIMARY KEY,
    user_id BIGINT NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    priority INT DEFAULT 0,
    prompt TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_task_queue_user_id ON task_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_task_queue_status ON task_queue(status);
CREATE INDEX IF NOT EXISTS idx_task_queue_priority ON task_queue(priority DESC);
EOF

echo "Tables created successfully!"
