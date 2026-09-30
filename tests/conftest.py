import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.database import Base
from database.models import StudentProfile, Subject, SyllabusTopic

from rag.vector_store import get_vector_store

@pytest.fixture(autouse=True)
def clean_vector_store_for_tests():
    """Ensures vector store is isolated during test runs."""
    v_store = get_vector_store()
    original_meta = list(v_store.metadata)
    original_vectors = v_store.vectors.copy() if v_store.vectors is not None else None
    v_store.clear()
    yield
    # Restore original index after test
    v_store.metadata = original_meta
    v_store.vectors = original_vectors
    v_store.save()


@pytest.fixture(scope="function")
def db_session():
    """Creates a fresh in-memory SQLite database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
    db = TestingSessionLocal()
    
    try:
        yield db
        db.commit()
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
