import pytest
from sqlalchemy.orm import Session

from agriworldmodel.db.session import engine

@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()

    session = Session(bind=connection, expire_on_commit=False)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()