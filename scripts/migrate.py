"""
RevPilot AI — Database Migration CLI Wrapper (Rail 5 / Track 1)
CLI entrypoint to execute Alembic migrations cleanly from root repository.
Usage:
    python scripts/migrate.py upgrade head
    python scripts/migrate.py downgrade -1
    python scripts/migrate.py current
    python scripts/migrate.py history
"""
import os
import sys
from pathlib import Path

from alembic.config import Config
from alembic import command

REPO_ROOT = Path(__file__).resolve().parent.parent
ALEMBIC_INI = REPO_ROOT / "packages" / "backend" / "alembic.ini"
ALEMBIC_DIR = REPO_ROOT / "packages" / "backend" / "alembic"


def get_alembic_config() -> Config:
    """Build Alembic configuration pointing to packages/backend/alembic.ini."""
    if not ALEMBIC_INI.exists():
        raise FileNotFoundError(f"Alembic configuration not found at {ALEMBIC_INI}")

    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))

    # Allow overriding via DATABASE_URL
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        cfg.set_main_option("sqlalchemy.url", db_url)

    return cfg


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("Usage: python scripts/migrate.py [upgrade|downgrade|current|history|heads] [target]")
        return 1

    action = args[0]
    target = args[1] if len(args) > 1 else "head"
    cfg = get_alembic_config()

    try:
        if action == "upgrade":
            print(f"Applying migrations up to target: {target}...")
            command.upgrade(cfg, target)
            print("Upgrade complete.")
        elif action == "downgrade":
            print(f"Rolling back migrations to target: {target}...")
            command.downgrade(cfg, target)
            print("Downgrade complete.")
        elif action == "current":
            command.current(cfg)
        elif action == "history":
            command.history(cfg)
        elif action == "heads":
            command.heads(cfg)
        else:
            print(f"Unknown action: {action}")
            return 1
        return 0
    except Exception as exc:
        print(f"Migration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
