from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.types import TypeDecorator
from datetime import timezone
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class UTCDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


class Base(DeclarativeBase):
    pass


class RunStatus(StrEnum):
    QUEUED = "QUEUED"
    COLLECTING = "COLLECTING"
    NORMALIZING = "NORMALIZING"
    CLASSIFYING = "CLASSIFYING"
    ASSESSING = "ASSESSING"
    GENERATING_REPORT = "GENERATING_REPORT"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class RunModel(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    records_retrieved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_normalized: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_classified: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    normalization_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    previous_baseline_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)

    report: Mapped["ReportModel | None"] = relationship(back_populates="run", uselist=False)
    report_records: Mapped[list["ReportRecordModel"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class ReportModel(Base):
    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    pdf_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    run: Mapped[RunModel] = relationship(back_populates="report")


class CompromiseHistoryModel(Base):
    __tablename__ = "compromise_history"
    __table_args__ = (UniqueConstraint("provider", "compromise_identity", name="uq_history_provider_identity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    compromise_identity: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_record_id: Mapped[str | None] = mapped_column(String(255))
    first_local_seen: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_local_seen: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    first_provider_seen: Mapped[datetime | None] = mapped_column(UTCDateTime())
    last_provider_seen: Mapped[datetime | None] = mapped_column(UTCDateTime())
    last_classification: Mapped[str] = mapped_column(String(32), nullable=False)
    last_observation_fingerprint: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class ProviderRecordModel(Base):
    __tablename__ = "provider_records"
    __table_args__ = (UniqueConstraint("provider", "provider_record_id", name="uq_provider_record"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_record_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class ObservationModel(Base):
    __tablename__ = "observations"
    __table_args__ = (UniqueConstraint("provider", "compromise_identity", "observation_fingerprint", name="uq_observation"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    compromise_identity: Mapped[str] = mapped_column(String(128), nullable=False)
    observation_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class ReportRecordModel(Base):
    __tablename__ = "report_records"
    __table_args__ = (UniqueConstraint("run_id", "provider", "compromise_identity", name="uq_run_record"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    compromise_identity: Mapped[str] = mapped_column(String(128), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    observation_fingerprint: Mapped[str | None] = mapped_column(String(64))
    canonical_json: Mapped[str] = mapped_column(Text, nullable=False)
    run: Mapped[RunModel] = relationship(back_populates="report_records")


class AssessmentModel(Base):
    __tablename__ = "assessments"

    assessment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), unique=True, nullable=False)
    activity_level: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), nullable=False)
    facts_json: Mapped[str] = mapped_column(Text, nullable=False)
    observations_json: Mapped[str] = mapped_column(Text, nullable=False)
    assessment: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_attention_json: Mapped[str] = mapped_column(Text, nullable=False)
    basis_json: Mapped[str] = mapped_column(Text, nullable=False)


class DataQualityModel(Base):
    __tablename__ = "data_quality"

    data_quality_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), unique=True, nullable=False)
    normalization_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    schema_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warnings_json: Mapped[str] = mapped_column(Text, nullable=False)
