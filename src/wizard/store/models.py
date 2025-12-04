from datetime import datetime
from typing import Self, Optional
from enum import Enum
from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Text,
    Boolean,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from wizard.base import Serializable
from pydantic import Field

Base = declarative_base()


class SoftwareType(Enum):
    EXCEL = "Excel"
    CALC = "Calc"
    GSHEET = "Gsheet"


class OutputType(Enum):
    NUMBER = "Number"
    DATE = "Date"
    TIME = "Time"
    DATETIME = "DateTime"
    TEXT = "Text"
    BOOLEAN = "Boolean"
    ERROR = "Error"


class StatusType(Enum):
    ONGOING = "Ongoing"
    DONE = "Done"


class SeverityType(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class BugStatusType(Enum):
    REPORTED = "Reported"
    CONFIRMED = "Confirmed"
    FIXED = "Fixed"
    WONTFIX = "WontFix"


class CounterIntuitiveRecordData(Serializable):
    software: SoftwareType
    input: str
    desc: str
    status: StatusType
    type: Optional[OutputType] = None
    value: Optional[str] = None
    dt: datetime = Field(default=datetime.now())


class WorkingRecord(Base):
    __tablename__ = "working_records"
    __table_args__ = (UniqueConstraint("software", "input", name="uq_software_input"),)

    id = Column(Integer, primary_key=True)
    software = Column(Text, nullable=False)
    input = Column(Text, nullable=False)
    type = Column(Text, nullable=True)
    value = Column(Text, nullable=True)
    status = Column(Text, default=StatusType.ONGOING.value)
    desc = Column(Text, nullable=False)
    dt = Column(DateTime, default=datetime.now)

    @classmethod
    def from_data(cls, data: CounterIntuitiveRecordData) -> Self:
        return cls(
            software=data.software.value,
            input=data.input,
            type=data.type.value if data.type else None,
            value=data.value,
            status=data.status.value,
            desc=data.desc,
            dt=data.dt,
        )

    def to_data(self) -> CounterIntuitiveRecordData:
        return CounterIntuitiveRecordData(
            software=SoftwareType(self.software),
            input=self.input,
            type=OutputType(self.type) if self.type else None,
            value=self.value,
            status=StatusType(self.status),
            desc=self.desc,
            dt=self.dt,
        )


class CounterIntuitiveRecord(Base):
    __tablename__ = "counter_intuitive_records"
    __table_args__ = (UniqueConstraint("software", "input", name="uq_software_input"),)

    id = Column(Integer, primary_key=True)
    software = Column(Text, nullable=False)
    input = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    value = Column(Text, nullable=False)
    status = Column(Text, default=StatusType.ONGOING.value)
    desc = Column(Text)
    dt = Column(DateTime, default=datetime.now)

    pair_memberships = relationship("PairMember", back_populates="record")
    bug_memberships = relationship("BugMember", back_populates="record")

    @hybrid_property
    def software_enum(self):
        return SoftwareType(self.software)

    @software_enum.setter
    def software_enum(self, value):
        self.software = value.value

    @classmethod
    def from_data(cls, data: CounterIntuitiveRecordData) -> Self:
        return cls(
            software=data.software.value,
            input=data.input,
            type=data.type.value,
            value=data.value,
            status=data.status.value,
            desc=data.desc,
            dt=data.dt,
        )

    def to_data(self) -> CounterIntuitiveRecordData:
        return CounterIntuitiveRecordData(
            software=SoftwareType(self.software),
            input=self.input,
            type=OutputType(self.type),
            value=self.value,
            status=StatusType(self.status),
            desc=self.desc,
            dt=self.dt,
        )


class InconsistencyData(Serializable):
    input: str
    records: list[CounterIntuitiveRecordData]


class Inconsistency(Base):
    __tablename__ = "inconsistencies"

    id = Column(Integer, primary_key=True)
    input = Column(Text, unique=True, nullable=False)
    excel = Column(Boolean, default=False)
    calc = Column(Boolean, default=False)
    gsheet = Column(Boolean, default=False)
    desc = Column(Text)


class PairData(Serializable):
    desc: str
    severity: SeverityType
    is_identical_software: bool
    members: list[CounterIntuitiveRecordData]


class CounterIntuitivePair(Base):
    __tablename__ = "counter_intuitive_pairs"

    id = Column(Integer, primary_key=True)
    desc = Column(Text)
    severity = Column(Text, default=SeverityType.MEDIUM.value)
    is_identical_software = Column(Boolean, default=True)

    members = relationship("PairMember", back_populates="pair")


class PairMember(Base):
    __tablename__ = "pair_members"
    __table_args__ = (
        UniqueConstraint("pair_id", "record_id", name="uq_pair_member_pair_record"),
    )

    id = Column(Integer, primary_key=True)
    pair_id = Column(
        Integer, ForeignKey("counter_intuitive_pairs.id"), nullable=False, index=True
    )
    record_id = Column(
        Integer, ForeignKey("counter_intuitive_records.id"), nullable=False
    )

    pair = relationship("CounterIntuitivePair", back_populates="members")
    record = relationship(
        "CounterIntuitiveRecord",
        back_populates="pair_memberships",
    )


class BugData(Serializable):
    severity: SeverityType
    link: str
    bug_desc: str
    bug_status: BugStatusType
    examples: list[CounterIntuitiveRecordData]


class ConfirmedBug(Base):
    __tablename__ = "confirmed_bugs"

    id = Column(Integer, primary_key=True)
    severity = Column(Text, default=SeverityType.MEDIUM.value)
    link = Column(Text)
    bug_desc = Column(Text, nullable=False)
    bug_status = Column(Text, default=BugStatusType.REPORTED.value)

    members = relationship("BugMember", back_populates="bug")


class BugMember(Base):
    __tablename__ = "bug_members"
    __table_args__ = (
        UniqueConstraint("bug_id", "record_id", name="uq_bug_member_bug_record"),
    )

    id = Column(Integer, primary_key=True)
    bug_id = Column(Integer, ForeignKey("confirmed_bugs.id"), nullable=False)
    record_id = Column(
        Integer, ForeignKey("counter_intuitive_records.id"), nullable=False
    )

    bug = relationship("ConfirmedBug", back_populates="members")
    record = relationship(
        "CounterIntuitiveRecord",
        back_populates="bug_memberships",
    )
