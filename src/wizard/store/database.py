from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from wizard.store.models import (
    Base,
    SoftwareType,
    OutputType,
    StatusType,
    SeverityType,
    BugStatusType,
)
from wizard.store.models import (
    CounterIntuitiveRecord,
    WorkingRecord,
    Inconsistency,
    CounterIntuitivePair,
    PairMember,
    ConfirmedBug,
    BugMember,
    CounterIntuitiveRecordData,
    BugData,
    PairData,
    InconsistencyData,
)
from typing import List, Optional, Iterable
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_url: str = "sqlite:///behavior_records.db"):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.url = db_url

    def add_counter_example(
        self,
        software: SoftwareType,
        input: str,
        desc: str = "",
        status: StatusType = StatusType.ONGOING,
        type: Optional[OutputType] = None,
        value: Optional[str] = None,
    ) -> int:
        """Add a new counter example record to the database working space, for experiment working purpose."""
        with self.Session() as session:
            data = CounterIntuitiveRecordData(
                software=software.value,
                input=input,
                type=type,
                value=value,
                status=status.value,
                desc=desc,
                dt=datetime.now(),
            )
            record = WorkingRecord.from_data(data)
            session.add(record)
            session.commit()
            session.refresh(record)

            return record.id

    def add_record(
        self,
        software: SoftwareType,
        input: str,
        type: OutputType,
        value: str,
        desc: str = "",
        status: StatusType = StatusType.ONGOING,
    ) -> int:
        """Add a new counter-intuitive record to the database.

        Args:
            software: The software type (Excel, Calc, Gsheet) for this record
            input: The input formula or expression
            type: The output type (Number, DateTime, etc)
            value: The actual output value
            desc: Optional description of the counter-intuitive behavior
            status: Status of the record, defaults to ONGOING

        Returns:
            int: The ID of the newly created record

        Raises:
            ValueError: If a record with the same software and input already exists
        """
        with self.Session() as session:
            record = CounterIntuitiveRecord(
                software=software.value,
                input=input,
                type=type.value,
                value=value,
                status=status.value,
                desc=desc,
                dt=datetime.now(),
            )
            session.add(record)
            session.commit()
            session.refresh(record)

            return record.id

    def add_pair(
        self,
        pair: Iterable[CounterIntuitiveRecordData],
        desc: str = "",
        severity: SeverityType = SeverityType.MEDIUM,
    ) -> int:
        """Add a new counter-intuitive pair.

        Args:
            pair: A tuple of CounterIntuitiveRecordData objects representing the records to pair
            desc: Optional description of the counter-intuitive behavior
            severity: Severity level of the counter-intuitive behavior, defaults to MEDIUM

        Returns:
            int: The ID of the newly created pair
        """
        with self.Session() as session:
            # Check if all records are from the same software
            is_identical = len(set(r.software for r in pair)) == 1
            # Process each record
            record_ids = []
            for data in pair:
                # Check if record already exists
                existing = (
                    session.query(CounterIntuitiveRecord)
                    .filter_by(software=data.software.value, input=data.input)
                    .first()
                )

                if existing:
                    # Update existing record
                    existing.status = data.status.value
                    existing.desc = data.desc
                    record_ids.append(existing.id)
                else:
                    # Create new record
                    record = CounterIntuitiveRecord.from_data(data)
                    session.add(record)
                    session.flush()  # Get new record ID
                    record_ids.append(record.id)

            # Create counter-intuitive pair
            pair_obj = CounterIntuitivePair(
                desc=desc, is_identical_software=is_identical, severity=severity.value
            )
            session.add(pair_obj)
            session.flush()  # Get pair ID

            # Create pair member relationships
            for record_id in record_ids:
                member = PairMember(
                    pair_id=pair_obj.id,
                    record_id=record_id,
                )
                session.add(member)
            session.commit()
            return pair_obj.id

    def add_to_pair(self, pair_id: int, data: CounterIntuitiveRecordData) -> int:
        """Add a record to an existing counter-intuitive pair.

        Args:
            pair_id: ID of the counter-intuitive pair to add the record to
            data: Record data to add as a new pair member

        Returns:
            int: ID of the newly created pair member

        Raises:
            ValueError: If the specified pair_id does not exist
        """
        with self.Session() as session:
            pair = session.get(CounterIntuitivePair, pair_id)
            if not pair:
                raise ValueError(f"Pair {pair_id} do not exist at all.")

            existing = (
                session.query(CounterIntuitiveRecord)
                .filter_by(software=data.software.value, input=data.input)
                .first()
            )
            if existing:
                existing.status = data.status.value
                existing.desc = data.desc
            else:
                record = CounterIntuitiveRecord.from_data(data)
                session.add(record)
                session.flush()  # Get new record ID

            member = (
                session.query(PairMember)
                .filter_by(pair_id=pair_id, record_id=record.id)
                .first()
            )
            if not member:
                member = PairMember(
                    pair_id=pair_id,
                    record_id=record.id,
                )
                session.add(member)
                session.commit()

            return member.id

    def add_bug(
        self,
        severity: SeverityType,
        link: str,
        bug_status: BugStatusType,
        bug_desc: str,
        examples: Iterable[CounterIntuitiveRecordData],
    ) -> int:
        """Add a bug with associated example records.

        Args:
            severity: Severity level of the bug
            link: Link to bug report/ticket
            bug_status: Current status of the bug
            bug_desc: Description of the bug
            examples: Tuple of record data to associate with this bug

        Returns:
            int: ID of the newly created bug

        Raises:
            ValueError: If any validation fails
        """
        with self.Session() as session:
            # Create the bug first
            bug = ConfirmedBug(
                severity=severity.value,
                link=link,
                bug_desc=bug_desc,
                bug_status=bug_status.value,
            )
            session.add(bug)
            session.flush()  # Get the new bug ID

            # Process each example record
            for data in examples:
                # Check if record already exists
                existing = (
                    session.query(CounterIntuitiveRecord)
                    .filter_by(software=data.software.value, input=data.input)
                    .first()
                )

                if existing:
                    record_id = existing.id
                    # Update existing record
                    existing.status = data.status.value
                    existing.desc = data.desc
                else:
                    # Create new record
                    record = CounterIntuitiveRecord.from_data(data)
                    session.add(record)
                    session.flush()
                    record_id = record.id

                # Create bug membership
                bug_member = BugMember(
                    bug_id=bug.id,
                    record_id=record_id,
                )
                session.add(bug_member)

            session.commit()
            return bug.id

    def update_inconsistencies(self):
        """Automatically update the inconsistency table"""
        with self.Session() as session:
            inconsistent_inputs = (
                session.query(CounterIntuitiveRecord.input)
                .group_by(CounterIntuitiveRecord.input)
                .having(func.count(func.distinct(CounterIntuitiveRecord.value)) > 1)
                .all()
            )

            for input_tuple in inconsistent_inputs:
                input = input_tuple[0]
                # Check if record already exists
                existing = session.query(Inconsistency).filter_by(input=input).first()
                if not existing:
                    # Get all related records to generate description
                    records = (
                        session.query(CounterIntuitiveRecord)
                        .filter_by(input=input)
                        .all()
                    )
                    desc = f"Different software handle input '{input}' differently: "
                    desc += "\n\n".join(
                        f"{r.software} outputs {r.type} '{r.value}'"
                        for r in sorted(records, key=lambda x: x.software)
                    )
                    softwares = {r.software.lower(): True for r in records}

                    # Create new inconsistency record
                    inconsistency = Inconsistency(
                        input=input,
                        desc=desc,
                        **softwares,
                    )
                    session.add(inconsistency)
            session.commit()

    def get_inconsistencies(self) -> list[InconsistencyData]:
        """Get all inconsistencies with their related records.

        Returns:
            List of InconsistencyData objects containing inconsistency details and related records
        """
        with self.Session() as session:
            inconsistencies = session.query(Inconsistency).all()
            result = []

            for inconsistency in inconsistencies:
                # Get all records with this input
                records = (
                    session.query(CounterIntuitiveRecord)
                    .filter_by(input=inconsistency.input)
                    .all()
                )

                result.append(
                    InconsistencyData(
                        input=inconsistency.input,
                        records=[r.to_data() for r in records],
                    )
                )

            return result

    def get_bug(self, id: int) -> BugData:
        """Get bug data by ID.

        Args:
            id: The ID of the bug to retrieve

        Returns:
            BugData object containing the bug details and example records
        """
        with self.Session() as session:
            bug = session.get(ConfirmedBug, id)
            if not bug:
                raise ValueError(f"Bug with ID {id} not found")

            # Get all bug members first
            bug_members = session.query(BugMember).filter(BugMember.bug_id == id).all()

            # Then query records by their IDs
            record_ids = [member.record_id for member in bug_members]
            records = (
                session.query(CounterIntuitiveRecord)
                .filter(CounterIntuitiveRecord.id.in_(record_ids))
                .all()
            )

            return BugData(
                severity=SeverityType(bug.severity),
                link=bug.link,
                bug_desc=bug.bug_desc,
                bug_status=BugStatusType(bug.bug_status),
                examples=[r.to_data() for r in records],
            )

    def get_record(self, id: int) -> CounterIntuitiveRecordData:
        """Get record data by ID.

        Args:
            id: The ID of the record to retrieve

        Returns:
            CounterIntuitiveRecordData object containing the record details

        Raises:
            ValueError: If record with given ID is not found
        """
        with self.Session() as session:
            record = session.get(CounterIntuitiveRecord, id)
            if not record:
                raise ValueError(f"Record with ID {id} not found")
            return record.to_data()

    def get_pair(self, id: int) -> PairData:
        """Get pair data by ID.

        Args:
            id: The ID of the pair to retrieve

        Returns:
            PairData object containing the pair details and member records

        Raises:
            ValueError: If pair with given ID is not found
        """
        with self.Session() as session:
            pair = session.get(CounterIntuitivePair, id)
            if not pair:
                raise ValueError(f"Pair with ID {id} not found")

            # Get all pair members first
            pair_members = (
                session.query(PairMember).filter(PairMember.pair_id == id).all()
            )

            # Then query records by their IDs
            record_ids = [member.record_id for member in pair_members]
            records = (
                session.query(CounterIntuitiveRecord)
                .filter(CounterIntuitiveRecord.id.in_(record_ids))
                .all()
            )

            return PairData(
                desc=pair.desc,
                severity=SeverityType(pair.severity),
                is_identical_software=pair.is_identical_software,
                members=[r.to_data() for r in records],
            )

    def get_pairs(self) -> list[PairData]:
        """Get all counter-intuitive pairs.

        Returns:
            List of PairData objects containing pair details and member records
        """
        with self.Session() as session:
            pairs = session.query(CounterIntuitivePair).all()
            result = []

            for pair in pairs:
                # Get all pair members
                pair_members = (
                    session.query(PairMember)
                    .filter(PairMember.pair_id == pair.id)
                    .all()
                )

                # Get records for each member
                record_ids = [member.record_id for member in pair_members]
                records = (
                    session.query(CounterIntuitiveRecord)
                    .filter(CounterIntuitiveRecord.id.in_(record_ids))
                    .all()
                )

                result.append(
                    PairData(
                        desc=pair.desc,
                        severity=SeverityType(pair.severity),
                        is_identical_software=pair.is_identical_software,
                        members=[r.to_data() for r in records],
                    )
                )

            return result

    def get_bugs(self) -> list[BugData]:
        """Get all confirmed bugs.

        Returns:
            List of BugData objects containing bug details and example records
        """
        with self.Session() as session:
            bugs = session.query(ConfirmedBug).all()
            result = []

            for bug in bugs:
                # Get all bug members
                bug_members = (
                    session.query(BugMember).filter(BugMember.bug_id == bug.id).all()
                )

                # Get records for each member
                record_ids = [member.record_id for member in bug_members]
                records = (
                    session.query(CounterIntuitiveRecord)
                    .filter(CounterIntuitiveRecord.id.in_(record_ids))
                    .all()
                )

                result.append(
                    BugData(
                        severity=SeverityType(bug.severity),
                        link=bug.link,
                        bug_desc=bug.bug_desc,
                        bug_status=BugStatusType(bug.bug_status),
                        examples=[r.to_data() for r in records],
                    )
                )

            return result

    def find_records(
        self,
        software: Optional[SoftwareType] = None,
        input: Optional[str] = None,
        type: Optional[OutputType] = None,
    ) -> List[CounterIntuitiveRecordData]:
        with self.Session() as session:
            query = session.query(CounterIntuitiveRecord)
            if software:
                query = query.filter(CounterIntuitiveRecord.software == software.value)
            if input:
                query = query.filter(CounterIntuitiveRecord.input == input)
            if type:
                query = query.filter(CounterIntuitiveRecord.type == type.value)
            return [record.to_data() for record in query.all()]
