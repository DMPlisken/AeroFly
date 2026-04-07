"""Shared database utilities."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def get_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True)


def get_session_factory(database_url: str):
    engine = get_engine(database_url)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
