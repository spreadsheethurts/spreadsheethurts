import pytest
from datetime import datetime
from wizard.store.database import DatabaseManager
from wizard.store.models import (
    SoftwareType,
    OutputType,
    StatusType,
    SeverityType,
    BugStatusType,
    CounterIntuitiveRecordData,
)


@pytest.fixture(scope="function")
def db() -> DatabaseManager:
    """Create a test database instance"""
    return DatabaseManager("sqlite:///:memory:")


@pytest.fixture
def sample_record_data():
    """Create sample record data for testing"""
    return CounterIntuitiveRecordData(
        software=SoftwareType.EXCEL,
        input="=1+1",
        type=OutputType.NUMBER,
        value="2",
        status=StatusType.ONGOING,
        desc="Basic addition",
        dt=datetime.now(),
    )


def test_add_record(db, sample_record_data):
    """Test adding a single record"""
    record_id = db.add_record(
        software=sample_record_data.software,
        input=sample_record_data.input,
        type=sample_record_data.type,
        value=sample_record_data.value,
        desc=sample_record_data.desc,
    )
    assert record_id > 0

    # Verify record was added correctly
    record = db.get_record(record_id)
    assert record.software == sample_record_data.software
    assert record.input == sample_record_data.input
    assert record.type == sample_record_data.type
    assert record.value == sample_record_data.value


def test_add_pair(db: DatabaseManager, sample_record_data):
    """Test adding a counter-intuitive pair"""
    # Create two records for the pair
    record2 = CounterIntuitiveRecordData(
        software=SoftwareType.CALC,
        input="=1+1",
        type=OutputType.NUMBER,
        value="3",  # Different result
        status=StatusType.ONGOING,
        desc="Different addition result",
        dt=datetime.now(),
    )

    pair_id = db.add_pair(
        pair=(sample_record_data, record2),
        desc="Addition discrepancy",
        severity=SeverityType.HIGH,
    )
    assert pair_id > 0

    # Verify pair was created correctly
    pair = db.get_pair(pair_id)
    assert pair.desc == "Addition discrepancy"
    assert pair.severity == SeverityType.HIGH
    assert len(pair.members) == 2

    record = db.find_records(software=SoftwareType.CALC)[0]
    assert record.input == "=1+1"
    assert record.value == "3"


def test_add_bug(db, sample_record_data):
    """Test adding a bug with example records"""
    bug_id = db.add_bug(
        severity=SeverityType.CRITICAL,
        link="https://bugtracker.com/123",
        bug_status=BugStatusType.REPORTED,
        bug_desc="Critical calculation error",
        examples=(sample_record_data,),
    )
    assert bug_id > 0

    # Verify bug was created correctly
    bug = db.get_bug(bug_id)
    assert bug.severity == SeverityType.CRITICAL
    assert bug.link == "https://bugtracker.com/123"
    assert bug.bug_status == BugStatusType.REPORTED
    assert len(bug.examples) == 1


def test_find_records(db, sample_record_data):
    """Test finding records with filters"""
    # Add a record first
    db.add_record(
        software=sample_record_data.software,
        input=sample_record_data.input,
        type=sample_record_data.type,
        value=sample_record_data.value,
        desc=sample_record_data.desc,
    )

    # Test finding by software
    records = db.find_records(software=SoftwareType.EXCEL)
    assert len(records) == 1
    assert records[0].software == SoftwareType.EXCEL

    # Test finding by input
    records = db.find_records(input="=1+1")
    assert len(records) == 1
    assert records[0].input == "=1+1"

    # Test finding with no matches
    records = db.find_records(software=SoftwareType.GSHEET)
    assert len(records) == 0


def test_update_inconsistencies(db: DatabaseManager, sample_record_data):
    """Test updating inconsistencies table"""
    # Add two records with same input but different outputs
    db.add_record(
        software=sample_record_data.software,
        input=sample_record_data.input,
        type=sample_record_data.type,
        value=sample_record_data.value,
    )

    db.add_record(
        software=SoftwareType.CALC,
        input=sample_record_data.input,
        type=sample_record_data.type,
        value="different_result",
    )

    # Update inconsistencies
    db.update_inconsistencies()

    # Verify inconsistency was detected
    inconsistencies = db.get_inconsistencies()
    assert len(inconsistencies) == 1
    assert inconsistencies[0].input == sample_record_data.input
    assert len(inconsistencies[0].records) == 2


def test_error_cases(db):
    """Test error handling"""
    # Test getting non-existent record
    with pytest.raises(ValueError):
        db.get_record(999)

    # Test getting non-existent pair
    with pytest.raises(ValueError):
        db.get_pair(999)

    # Test getting non-existent bug
    with pytest.raises(ValueError):
        db.get_bug(999)
