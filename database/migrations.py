"""
SecureIoT-X Database Migrations & Initialisation.

Creates all tables and the default admin user on first run.
"""

import logging
import sys
from pathlib import Path

# Add project root to path for imports
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from backend.core.config import settings
from backend.core.database import Base, init_db_sync, get_sync_db
from backend.core.security import hash_password

# Force model registration
import backend.models  # noqa: F401

logger = logging.getLogger("secureiot.migrations")


def run_migrations() -> None:
    """Create all database tables and seed the default admin user."""
    print("=" * 60)
    print("SecureIoT-X Database Migration")
    print("=" * 60)

    # Create tables
    print("[1/3] Creating database tables...")
    init_db_sync()
    print("      [OK] All tables created")

    # Create default admin
    print("[2/3] Checking default admin user...")
    _ensure_admin()

    print("[3/3] Migration complete!")
    print("=" * 60)


def _ensure_admin() -> None:
    """Create the default admin user if not present."""
    from backend.models.user import User
    from sqlalchemy import select

    session = get_sync_db()
    try:
        result = session.execute(
            select(User).where(User.username == settings.default_admin_username)
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"      [OK] Admin '{settings.default_admin_username}' already exists")
            return

        admin = User(
            username=settings.default_admin_username,
            email=settings.default_admin_email,
            hashed_password=hash_password(settings.default_admin_password),
            role="ADMIN",
            is_active=True,
        )
        session.add(admin)
        session.commit()
        print(f"      [OK] Created admin user: {settings.default_admin_username}")
    except Exception as e:
        session.rollback()
        print(f"      [ERROR] Error creating admin: {e}")
        raise
    finally:
        session.close()


def reset_database() -> None:
    """Drop and recreate all tables. WARNING: Destroys all data."""
    from backend.core.database import sync_engine

    print("⚠  RESETTING DATABASE — all data will be lost!")
    Base.metadata.drop_all(bind=sync_engine)
    print("   ✓ All tables dropped")
    run_migrations()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SecureIoT-X Database Management")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables")
    args = parser.parse_args()

    if args.reset:
        reset_database()
    else:
        run_migrations()
