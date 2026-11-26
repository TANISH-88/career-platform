from collections.abc import Generator

from fastapi import Request
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.engine import create_db_engine


def create_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    bound_engine = engine or create_db_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=bound_engine)


def get_db(request: Request) -> Generator[Session, None, None]:
    session_factory = getattr(request.app.state, "db_session_factory", None)
    if session_factory is None:
        session_factory = create_session_factory()
        request.app.state.db_session_factory = session_factory

    db = session_factory()
    try:
        yield db
    finally:
        db.close()
