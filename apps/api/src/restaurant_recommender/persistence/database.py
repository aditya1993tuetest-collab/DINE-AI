"""Database engine and transaction construction."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker


def build_engine(
    database_url: str,
    *,
    echo: bool = False,
    pool_size: int = 10,
    max_overflow: int = 10,
    pool_timeout: float = 5.0,
    connect_timeout: int = 3,
) -> Engine:
    connect_args = (
        {"connect_timeout": connect_timeout}
        if make_url(database_url).get_backend_name() == "postgresql"
        else {}
    )
    return create_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        connect_args=connect_args,
    )


@contextmanager
def transaction(engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as session:
        yield session
