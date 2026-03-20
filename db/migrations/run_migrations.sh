#!/bin/bash
set -e

MIGRATIONS_DIR="/docker-entrypoint-initdb.d/migrations"

echo "Running database migrations..."

for migration in "$MIGRATIONS_DIR"/*.sql; do
    if [ -f "$migration" ]; then
        filename=$(basename "$migration")
        version="${filename:0:3}"

        applied=$(PGPASSWORD=$POSTGRES_PASSWORD psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT EXISTS(SELECT 1 FROM schema_migrations WHERE version='$version')")

        if [ "$applied" = "t" ]; then
            echo "Skipping $filename (already applied)"
            continue
        fi

        echo "Applying $filename..."

        if PGPASSWORD=$POSTGRES_PASSWORD psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$migration"; then
            echo "✓ $filename applied successfully"
        else
            echo "✗ ERROR: Migration $filename failed"
            exit 1
        fi
    fi
done

echo "All migrations completed."
