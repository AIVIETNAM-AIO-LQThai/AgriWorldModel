import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from agriworldmodel.db.models.knowledge_chunk import KnowledgeChunk
from agriworldmodel.db.session import engine

@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()

    session = Session(bind=connection, expire_on_commit=False)

    try:
        # Unit tests must not depend on persistent retrieval
        # corpus data already present in the development DB.
        #
        # This DELETE occurs inside the outer test transaction.
        # The final rollback restores every pre-existing chunk.
        session.execute(delete(KnowledgeChunk))
        session.flush()

        yield session

    finally:
        session.close()
        transaction.rollback()
        connection.close()