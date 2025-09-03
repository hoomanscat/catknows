import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context  # type: ignore

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- App metadata laden ---
from skoolhud.models import Base
target_metadata = Base.metadata

# --- DB-URL auflösen: ENV > ini ---
db_url_env = os.getenv("DATABASE_URL", "").strip()
if db_url_env:
    config.set_main_option("sqlalchemy.url", db_url_env)

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )
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
