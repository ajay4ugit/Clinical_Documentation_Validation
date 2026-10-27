"""
Database models and connection setup for Clinical Documentation System.
Uses SQLAlchemy async with SQLite for simple, local storage.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Float, Integer, Boolean, DateTime, ForeignKey, Enum
from datetime import datetime
from typing import Optional, List
import enum
import os

# ── Database URL ──────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./clinical_docs.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


# ── Enums ─────────────────────────────────────────────────────────────────────
class DocumentStatus(str, enum.Enum):
    PENDING   = "pending"
    VALIDATED = "validated"
    REJECTED  = "rejected"
    REVIEW    = "review"


class Severity(str, enum.Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class Department(str, enum.Enum):
    CARDIOLOGY     = "Cardiology"
    NEUROLOGY      = "Neurology"
    ORTHOPEDICS    = "Orthopedics"
    ONCOLOGY       = "Oncology"
    EMERGENCY      = "Emergency"
    PEDIATRICS     = "Pediatrics"
    RADIOLOGY      = "Radiology"
    GENERAL        = "General Medicine"


# ── ORM Models ────────────────────────────────────────────────────────────────
class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int]            = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[str]    = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str]          = mapped_column(String(100))
    age: Mapped[int]           = mapped_column(Integer)
    gender: Mapped[str]        = mapped_column(String(10))
    blood_type: Mapped[str]    = mapped_column(String(5))
    department: Mapped[str]    = mapped_column(String(50))
    admission_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime]     = mapped_column(DateTime, default=datetime.utcnow)

    documents: Mapped[List["ClinicalDocument"]] = relationship("ClinicalDocument", back_populates="patient")


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int]          = mapped_column(Integer, primary_key=True, index=True)
    doctor_id: Mapped[str]   = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str]        = mapped_column(String(100))
    specialization: Mapped[str] = mapped_column(String(100))
    department: Mapped[str]  = mapped_column(String(50))
    email: Mapped[str]       = mapped_column(String(100))

    documents: Mapped[List["ClinicalDocument"]] = relationship("ClinicalDocument", back_populates="doctor")


class ClinicalDocument(Base):
    __tablename__ = "clinical_documents"

    id: Mapped[int]              = mapped_column(Integer, primary_key=True, index=True)
    doc_id: Mapped[str]          = mapped_column(String(20), unique=True, index=True)
    patient_id: Mapped[int]      = mapped_column(ForeignKey("patients.id"))
    doctor_id: Mapped[int]       = mapped_column(ForeignKey("doctors.id"))
    doc_type: Mapped[str]        = mapped_column(String(50))        # discharge, prescription, lab, etc.
    title: Mapped[str]           = mapped_column(String(200))
    content: Mapped[str]         = mapped_column(Text)
    diagnosis: Mapped[str]       = mapped_column(String(300))
    icd_codes: Mapped[str]       = mapped_column(String(200))       # comma-separated ICD-10 codes
    medications: Mapped[str]     = mapped_column(Text)
    status: Mapped[str]          = mapped_column(String(20), default=DocumentStatus.PENDING)
    ai_score: Mapped[Optional[float]]   = mapped_column(Float, nullable=True)
    ai_summary: Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]        = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime]        = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient: Mapped["Patient"] = relationship("Patient", back_populates="documents")
    doctor: Mapped["Doctor"]   = relationship("Doctor", back_populates="documents")
    issues: Mapped[List["ValidationIssue"]] = relationship("ValidationIssue", back_populates="document", cascade="all, delete-orphan")


class ValidationIssue(Base):
    __tablename__ = "validation_issues"

    id: Mapped[int]          = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("clinical_documents.id"))
    issue_type: Mapped[str]  = mapped_column(String(50))   # missing_field, icd_mismatch, drug_interaction, etc.
    severity: Mapped[str]    = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)
    field_name: Mapped[str]  = mapped_column(String(100))
    resolved: Mapped[bool]   = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    document: Mapped["ClinicalDocument"] = relationship("ClinicalDocument", back_populates="issues")


# ── DB Helpers ────────────────────────────────────────────────────────────────
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
