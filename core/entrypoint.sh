#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
while ! pg_isready -h ${DATABASE_HOST:-postgres} -p ${DATABASE_PORT:-5432} -U ${DATABASE_USER:-govos} -q; do
    sleep 1
done
echo "Database is ready!"

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Auto-seed policies if database is empty (first run only)
echo "Checking if policies need to be seeded..."
python -c "
from core.database import SessionLocal
from core.models import Policy

db = SessionLocal()
policy_count = db.query(Policy).count()
db.close()

if policy_count == 0:
    print('No policies found. Seeding policies...')
    import subprocess
    subprocess.run(['python', '-m', 'core.scripts.seed_fixtures', '--policies-only'], check=True)
    print('Policies seeded successfully!')
else:
    print(f'Found {policy_count} policies. Skipping seed.')
"

# Start the application
echo "Starting Governance OS API..."
exec uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload
