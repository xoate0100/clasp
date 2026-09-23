"""
Template Migration System
Handles migrations between template versions.
"""

from .migration_1_0_0 import MIGRATIONS as MIGRATIONS_1_0_0
from .migration_1_6_0 import MIGRATIONS as MIGRATIONS_1_6_0
from .migration_1_7_0 import MIGRATIONS as MIGRATIONS_1_7_0
from .migration_2_0_0 import migrate_to_2_0_0
from .migration_2_1_0 import MIGRATIONS as MIGRATIONS_2_1_0
from .migration_2_2_0 import MIGRATIONS as MIGRATIONS_2_2_0
from .migration_3_0_0 import MIGRATIONS as MIGRATIONS_3_0_0

# Combine all migrations
ALL_MIGRATIONS = {}
ALL_MIGRATIONS.update(MIGRATIONS_1_0_0)
ALL_MIGRATIONS.update(MIGRATIONS_1_6_0)
ALL_MIGRATIONS.update(MIGRATIONS_1_7_0)
ALL_MIGRATIONS["2.0.0"] = migrate_to_2_0_0
ALL_MIGRATIONS.update(MIGRATIONS_2_1_0)
ALL_MIGRATIONS.update(MIGRATIONS_2_2_0)
ALL_MIGRATIONS.update(MIGRATIONS_3_0_0)


def get_migration(version: str):
    """Get migration function for a version."""
    return ALL_MIGRATIONS.get(version)


def list_available_migrations() -> list[str]:
    """List all available migration versions."""
    return sorted(ALL_MIGRATIONS.keys(), key=lambda v: tuple(int(p) for p in v.split(".")))


__all__ = ["get_migration", "list_available_migrations", "ALL_MIGRATIONS"]
