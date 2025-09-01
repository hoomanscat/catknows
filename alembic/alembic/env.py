# REPLACE FILE: alembic/env.py
from __future__ import annotations
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# >>> SkoolHUD: hol die Base/Engine direkt aus unserem Paket
from skoolhud.db import engine as skool_engine
from skoolhud.models import Base as skool_base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = skool_base.metadata

def run_migrations_offline():
    # Fallback: URL aus ini, falls jemand offline laufen lässt
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    # >>> SkoolHUD: nutze die bestehende Engine des Projekts
    connectable = skool_engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
