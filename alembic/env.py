from __future__ import annotations

from datetime import datetime, timezone
from logging.config import fileConfig
import os

from alembic import context
from azure.identity import WorkloadIdentityCredential
from sqlalchemy import engine_from_config, pool

from storage.database import Base
from storage.database import EntraAccessToken, ProactiveEntraTokenProvider, create_postgres_entra_engine
import storage.identity_models  # noqa: F401
import storage.operation_models  # noqa: F401
import storage.roadmap_models  # noqa: F401
import storage.learning_models  # noqa: F401
import storage.progress_models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def migration_engine():
    database_url = os.environ.get("DATABASE_URL")
    federated_token_file = os.environ.get("AZURE_FEDERATED_TOKEN_FILE")
    if database_url and federated_token_file:
        client_id = os.environ.get("AZURE_CLIENT_ID")
        tenant_id = os.environ.get("AZURE_TENANT_ID")
        if not client_id or not tenant_id:
            raise RuntimeError("Migration Workload Identity environment is incomplete")
        credential = WorkloadIdentityCredential(
            client_id=client_id,
            tenant_id=tenant_id,
            token_file_path=federated_token_file,
        )

        def acquire() -> EntraAccessToken:
            token = credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
            return EntraAccessToken(
                token=token.token,
                expires_at=datetime.fromtimestamp(token.expires_on, timezone.utc),
            )

        return create_postgres_entra_engine(database_url, ProactiveEntraTokenProvider(acquire))
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)
    return engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = migration_engine()
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
