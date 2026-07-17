"""Database engine, ORM records, and bootstrap helpers."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator
from collections.abc import Callable
import time

from sqlalchemy import DateTime, Integer, JSON, String, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.engine import make_url
import psycopg


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class PersistenceUnavailable(RuntimeError):
    code = "PERSISTENCE_UNAVAILABLE"


@dataclass(slots=True)
class PostgresEntraConnectionFactory:
    """Acquire a fresh Entra token for each new physical PostgreSQL connection."""

    acquire_token: Callable[[], str]
    connect: Callable[[str], Any]
    sleep: Callable[[float], None] = time.sleep
    retry_delays: tuple[float, ...] = (0.25, 1.0)

    def __call__(self) -> Any:
        last_error: Exception | None = None
        for attempt in range(len(self.retry_delays) + 1):
            try:
                token = self.acquire_token()
                if not token:
                    raise RuntimeError("empty access token")
                return self.connect(token)
            except Exception as error:
                last_error = error
                if attempt < len(self.retry_delays):
                    self.sleep(self.retry_delays[attempt])
        raise PersistenceUnavailable("PERSISTENCE_UNAVAILABLE") from last_error


@dataclass(slots=True)
class EntraAccessToken:
    token: str
    expires_at: datetime


@dataclass(slots=True)
class ProactiveEntraTokenProvider:
    acquire: Callable[[], EntraAccessToken]
    now: Callable[[], datetime] = utcnow
    refresh_margin: timedelta = timedelta(minutes=5)
    _cached: EntraAccessToken | None = None

    def __call__(self) -> str:
        current = self.now()
        if self._cached is None or self._cached.expires_at <= current + self.refresh_margin:
            token = self.acquire()
            if not token.token or token.expires_at <= current:
                raise PersistenceUnavailable("PERSISTENCE_UNAVAILABLE")
            self._cached = token
        return self._cached.token

    def invalidate(self) -> None:
        self._cached = None


def create_postgres_entra_engine(database_url: str, token_provider: ProactiveEntraTokenProvider) -> Engine:
    url = make_url(database_url)
    if not url.drivername.startswith("postgresql") or not url.host or not url.database or not url.username:
        raise ValueError("A PostgreSQL URL with host, database, and Entra username is required")

    def connect(token: str):
        return psycopg.connect(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=token, sslmode="require")

    factory = PostgresEntraConnectionFactory(token_provider, connect)
    return create_engine("postgresql+psycopg://", creator=factory, pool_pre_ping=True, pool_recycle=300, future=True)


class EmployeeProfileRecord(Base):
    __tablename__ = "employee_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RoadmapRecord(Base):
    __tablename__ = "roadmaps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    employee_profile_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ProgressCheckInRecord(Base):
    __tablename__ = "progress_check_ins"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    employee_profile_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    roadmap_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


def create_engine_for_url(database_url: str) -> Engine:
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(database_url, future=True, pool_pre_ping=True, connect_args=connect_args)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def bootstrap_database(engine: Engine) -> None:
    # Import model modules before metadata creation; imports are local to avoid
    # circular initialization while Base is being defined.
    from storage import identity_models, lab_models, learning_models, operation_models, progress_models, roadmap_models  # noqa: F401

    Base.metadata.create_all(bind=engine)


@dataclass(slots=True)
class DatabaseManager:
    engine: Engine
    session_factory: sessionmaker[Session]

    @classmethod
    def create(cls, database_url: str) -> "DatabaseManager":
        engine = create_engine_for_url(database_url)
        bootstrap_database(engine)
        return cls(engine=engine, session_factory=create_session_factory(engine))

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def readiness_canary(self) -> bool:
        from sqlalchemy import text

        try:
            with self.session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
