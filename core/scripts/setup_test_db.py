"""
Setup test database for pytest.

Creates a separate test database to avoid polluting production data.
"""

import sys
from sqlalchemy import create_engine, text

# Production database (admin connection)
ADMIN_DATABASE_URL = "postgresql://govos:local_dev_password@localhost:5432/postgres"

# Test database to create
TEST_DB_NAME = "governance_os_test"


def setup_test_database():
    """Create test database if it doesn't exist."""
    print("=" * 60)
    print("Setting up test database...")
    print("=" * 60)

    # Connect to postgres database
    engine = create_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")

    try:
        with engine.connect() as conn:
            # Check if test database exists
            result = conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{TEST_DB_NAME}'")
            )

            if result.fetchone():
                print(f"✓ Test database '{TEST_DB_NAME}' already exists")

                # Ask if user wants to recreate
                print("\nOptions:")
                print("  1. Keep existing (recommended for fast tests)")
                print("  2. Drop and recreate (clean slate)")
                choice = input("\nChoice (1 or 2): ").strip()

                if choice == "2":
                    print(f"\nDropping existing database '{TEST_DB_NAME}'...")
                    conn.execute(text(f"DROP DATABASE {TEST_DB_NAME}"))
                    print("✓ Dropped")

                    print(f"Creating database '{TEST_DB_NAME}'...")
                    conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
                    print("✓ Created")
            else:
                print(f"Creating test database '{TEST_DB_NAME}'...")
                conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
                print(f"✓ Test database '{TEST_DB_NAME}' created successfully")

        print("\n" + "=" * 60)
        print("Test database ready!")
        print(f"Database: {TEST_DB_NAME}")
        print("Run tests with: make test")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nMake sure PostgreSQL is running:")
        print("  make up")
        sys.exit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    setup_test_database()
