import pytest
from src.database.models import Om, OmStatus
from src.database.database import AsyncDatabase

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def db():
    # Use in-memory SQLite database for testing
    db = AsyncDatabase(":memory:")
    await db.initialize()
    yield db
    # Cleanup
    await db.engine.dispose()


@pytest.fixture
async def session(db):
    async with db.session() as session:
        yield session
        await session.rollback()


async def test_om_create(session):
    # Test creating a new Om
    om = await Om.create(
        user_id="test-user-id", storage_object_id="test-storage-object-id", session=session
    )

    assert om.id is not None
    assert om.user_id == "test-user-id"
    assert om.storage_object_id == "test-storage-object-id"
    assert om.status == OmStatus.UPLOADED
    assert om.created_at is not None
    assert om.updated_at is not None


async def test_om_read(session):
    # Create an Om first
    om = await Om.create(
        user_id="test-user-id", storage_object_id="test-storage-object-id", session=session
    )

    # Test reading the Om
    read_om = await Om.read(om.id, session)
    assert read_om is not None
    assert read_om.id == om.id
    assert read_om.user_id == "test-user-id"
    assert read_om.storage_object_id == "test-storage-object-id"


async def test_om_update(session):
    # Create an Om first
    om = await Om.create(
        user_id="test-user-id", storage_object_id="test-storage-object-id", session=session
    )

    # Test updating the Om
    update_data = {
        "status": OmStatus.PROCESSED,
        "title": "Test Title",
        "description": "Test Description",
        "summary": "Test Summary",
        "address": "Test Address",
        "property_type": "Test Property Type",
        "square_feet": 1000,
        "total_units": 10,
    }

    updated_om = await Om.update(om.id, update_data, session)
    assert updated_om.status == OmStatus.PROCESSED
    assert updated_om.title == "Test Title"
    assert updated_om.description == "Test Description"
    assert updated_om.summary == "Test Summary"
    assert updated_om.address == "Test Address"
    assert updated_om.property_type == "Test Property Type"
    assert updated_om.square_feet == 1000
    assert updated_om.total_units == 10


async def test_read_by_user_id(session):
    # Create multiple Oms for the same user
    user_id = "test-user-id"
    await Om.create(user_id=user_id, storage_object_id="storage-object-1", session=session)
    await Om.create(user_id=user_id, storage_object_id="storage-object-2", session=session)

    # Test reading all Oms for the user
    oms = await Om.read_by_user_id(user_id, session, span=None)
    assert len(oms) == 2
    assert all(om.user_id == user_id for om in oms)


async def test_om_update_nonexistent(session):
    # Test updating a non-existent Om
    with pytest.raises(ValueError, match="Om with id fake-id not found"):
        await Om.update("fake-id", {"status": OmStatus.PROCESSED}, session)
