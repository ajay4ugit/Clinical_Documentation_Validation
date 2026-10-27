"""
API Routers for Clinical Documentation System.
Covers: documents, patients, doctors, dashboard stats.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.models.database import (
    get_db, ClinicalDocument, Patient, Doctor,
    ValidationIssue, DocumentStatus
)
from app.services.ai_validator import validate_document

router = APIRouter()


# ── Pydantic Schemas ──────────────────────────────────────────────────────────
class DocumentCreate(BaseModel):
    patient_id:  int
    doctor_id:   int
    doc_type:    str
    title:       str
    content:     str
    diagnosis:   str
    icd_codes:   str
    medications: str


class DocumentUpdate(BaseModel):
    title:       Optional[str] = None
    content:     Optional[str] = None
    diagnosis:   Optional[str] = None
    icd_codes:   Optional[str] = None
    medications: Optional[str] = None
    status:      Optional[str] = None


# ── Helper: serialize document ────────────────────────────────────────────────
def _doc_out(doc: ClinicalDocument) -> dict:
    return {
        "id":          doc.id,
        "doc_id":      doc.doc_id,
        "patient_id":  doc.patient_id,
        "doctor_id":   doc.doctor_id,
        "patient_name":doc.patient.name if doc.patient else "",
        "doctor_name": doc.doctor.name  if doc.doctor  else "",
        "doc_type":    doc.doc_type,
        "title":       doc.title,
        "content":     doc.content,
        "diagnosis":   doc.diagnosis,
        "icd_codes":   doc.icd_codes,
        "medications": doc.medications,
        "status":      doc.status,
        "ai_score":    doc.ai_score,
        "ai_summary":  doc.ai_summary,
        "department":  doc.patient.department if doc.patient else "",
        "created_at":  doc.created_at.isoformat() if doc.created_at else None,
        "updated_at":  doc.updated_at.isoformat() if doc.updated_at else None,
        "issues":      [
            {
                "id":          i.id,
                "issue_type":  i.issue_type,
                "severity":    i.severity,
                "description": i.description,
                "field_name":  i.field_name,
                "resolved":    i.resolved,
            }
            for i in (doc.issues or [])
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD STATS
# ═══════════════════════════════════════════════════════════════════════════════
@router.get("/api/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Returns aggregate statistics for the dashboard."""
    # Document counts by status
    status_q = await db.execute(
        select(ClinicalDocument.status, func.count().label("cnt"))
        .group_by(ClinicalDocument.status)
    )
    status_map = {row.status: row.cnt for row in status_q}

    # Total counts
    total_patients = (await db.execute(select(func.count()).select_from(Patient))).scalar()
    total_doctors  = (await db.execute(select(func.count()).select_from(Doctor))).scalar()
    total_docs     = (await db.execute(select(func.count()).select_from(ClinicalDocument))).scalar()
    total_issues   = (await db.execute(
        select(func.count()).select_from(ValidationIssue).where(ValidationIssue.resolved == False)
    )).scalar()

    # Average AI score
    avg_score_q = await db.execute(
        select(func.avg(ClinicalDocument.ai_score))
        .where(ClinicalDocument.ai_score.isnot(None))
    )
    avg_score = round(float(avg_score_q.scalar() or 0), 1)

    # Documents by department
    dept_q = await db.execute(
        select(Patient.department, func.count(ClinicalDocument.id).label("cnt"))
        .join(ClinicalDocument, ClinicalDocument.patient_id == Patient.id)
        .group_by(Patient.department)
        .order_by(desc("cnt"))
    )
    by_dept = [{"department": r.department, "count": r.cnt} for r in dept_q]

    # Documents by type
    type_q = await db.execute(
        select(ClinicalDocument.doc_type, func.count().label("cnt"))
        .group_by(ClinicalDocument.doc_type)
    )
    by_type = [{"type": r.doc_type, "count": r.cnt} for r in type_q]

    # Score distribution buckets
    score_q = await db.execute(
        select(ClinicalDocument.ai_score)
        .where(ClinicalDocument.ai_score.isnot(None))
    )
    scores = [row[0] for row in score_q]
    buckets = {"90-100": 0, "75-89": 0, "50-74": 0, "Below 50": 0}
    for s in scores:
        if s >= 90:   buckets["90-100"] += 1
        elif s >= 75: buckets["75-89"]  += 1
        elif s >= 50: buckets["50-74"]  += 1
        else:          buckets["Below 50"] += 1

    # Recent issues severity breakdown
    sev_q = await db.execute(
        select(ValidationIssue.severity, func.count().label("cnt"))
        .where(ValidationIssue.resolved == False)
        .group_by(ValidationIssue.severity)
    )
    by_severity = {r.severity: r.cnt for r in sev_q}

    return {
        "totals": {
            "patients":  total_patients,
            "doctors":   total_doctors,
            "documents": total_docs,
            "issues":    total_issues,
        },
        "status": {
            "validated": status_map.get("validated", 0),
            "pending":   status_map.get("pending",   0),
            "rejected":  status_map.get("rejected",  0),
            "review":    status_map.get("review",    0),
        },
        "avg_score":    avg_score,
        "by_dept":      by_dept,
        "by_type":      by_type,
        "score_dist":   buckets,
        "by_severity":  by_severity,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  DOCUMENTS
# ═══════════════════════════════════════════════════════════════════════════════
@router.get("/api/documents")
async def list_documents(
    page:       int = Query(1, ge=1),
    per_page:   int = Query(10, ge=1, le=100),
    status:     Optional[str] = None,
    department: Optional[str] = None,
    doc_type:   Optional[str] = None,
    search:     Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(ClinicalDocument)
        .options(
            selectinload(ClinicalDocument.patient),
            selectinload(ClinicalDocument.doctor),
            selectinload(ClinicalDocument.issues),
        )
        .order_by(desc(ClinicalDocument.created_at))
    )
    if status:
        q = q.where(ClinicalDocument.status == status)
    if doc_type:
        q = q.where(ClinicalDocument.doc_type == doc_type)
    if department:
        q = q.join(Patient, ClinicalDocument.patient_id == Patient.id)\
             .where(Patient.department == department)
    if search:
        q = q.join(Patient, ClinicalDocument.patient_id == Patient.id, isouter=True)\
             .where(or_(
                 ClinicalDocument.title.ilike(f"%{search}%"),
                 ClinicalDocument.diagnosis.ilike(f"%{search}%"),
                 Patient.name.ilike(f"%{search}%"),
             ))

    total_q = await db.execute(select(func.count()).select_from(q.subquery()))
    total   = total_q.scalar()

    q  = q.offset((page - 1) * per_page).limit(per_page)
    rs = await db.execute(q)
    docs = rs.scalars().all()

    return {
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    (total + per_page - 1) // per_page,
        "data":     [_doc_out(d) for d in docs],
    }


@router.get("/api/documents/{doc_id}")
async def get_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    q = await db.execute(
        select(ClinicalDocument)
        .options(
            selectinload(ClinicalDocument.patient),
            selectinload(ClinicalDocument.doctor),
            selectinload(ClinicalDocument.issues),
        )
        .where(ClinicalDocument.id == doc_id)
    )
    doc = q.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_out(doc)


@router.post("/api/documents")
async def create_document(data: DocumentCreate, db: AsyncSession = Depends(get_db)):
    # Validate patient and doctor exist
    patient = (await db.execute(select(Patient).where(Patient.id == data.patient_id))).scalar_one_or_none()
    doctor  = (await db.execute(select(Doctor).where(Doctor.id == data.doctor_id))).scalar_one_or_none()
    if not patient:
        raise HTTPException(400, "Patient not found")
    if not doctor:
        raise HTTPException(400, "Doctor not found")

    # Generate doc_id
    count = (await db.execute(select(func.count()).select_from(ClinicalDocument))).scalar()
    doc_id = f"DOC{(count + 1):05d}"

    doc = ClinicalDocument(
        doc_id     = doc_id,
        patient_id = data.patient_id,
        doctor_id  = data.doctor_id,
        doc_type   = data.doc_type,
        title      = data.title,
        content    = data.content,
        diagnosis  = data.diagnosis,
        icd_codes  = data.icd_codes,
        medications= data.medications,
        status     = "pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Reload with relationships
    q   = await db.execute(
        select(ClinicalDocument)
        .options(selectinload(ClinicalDocument.patient), selectinload(ClinicalDocument.doctor), selectinload(ClinicalDocument.issues))
        .where(ClinicalDocument.id == doc.id)
    )
    doc = q.scalar_one()
    return _doc_out(doc)


@router.post("/api/documents/{doc_id}/validate")
async def run_validation(doc_id: int, db: AsyncSession = Depends(get_db)):
    """Runs AI validation on a document and stores results."""
    q = await db.execute(
        select(ClinicalDocument)
        .options(selectinload(ClinicalDocument.patient), selectinload(ClinicalDocument.doctor), selectinload(ClinicalDocument.issues))
        .where(ClinicalDocument.id == doc_id)
    )
    doc = q.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Run AI/rule-based validation
    result = await validate_document({
        "doc_type":   doc.doc_type,
        "title":      doc.title,
        "content":    doc.content,
        "diagnosis":  doc.diagnosis,
        "icd_codes":  doc.icd_codes,
        "medications":doc.medications,
    })

    # Persist results
    doc.ai_score   = result["score"]
    doc.ai_summary = result["summary"]
    doc.status     = result["status"]
    doc.updated_at = datetime.utcnow()

    # Clear old issues and write new ones
    for old in doc.issues:
        await db.delete(old)
    await db.flush()

    for issue in result["issues"]:
        db.add(ValidationIssue(
            document_id = doc.id,
            issue_type  = issue["type"],
            severity    = issue["severity"],
            description = issue["description"],
            field_name  = issue["field"],
            resolved    = False,
        ))

    await db.commit()

    # Reload
    q   = await db.execute(
        select(ClinicalDocument)
        .options(selectinload(ClinicalDocument.patient), selectinload(ClinicalDocument.doctor), selectinload(ClinicalDocument.issues))
        .where(ClinicalDocument.id == doc.id)
    )
    doc = q.scalar_one()
    return {**_doc_out(doc), "engine": result.get("engine", "rule-based")}


@router.patch("/api/documents/{doc_id}")
async def update_document(doc_id: int, data: DocumentUpdate, db: AsyncSession = Depends(get_db)):
    q = await db.execute(
        select(ClinicalDocument)
        .options(selectinload(ClinicalDocument.patient), selectinload(ClinicalDocument.doctor), selectinload(ClinicalDocument.issues))
        .where(ClinicalDocument.id == doc_id)
    )
    doc = q.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(doc, field, val)
    doc.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(doc)
    q   = await db.execute(
        select(ClinicalDocument)
        .options(selectinload(ClinicalDocument.patient), selectinload(ClinicalDocument.doctor), selectinload(ClinicalDocument.issues))
        .where(ClinicalDocument.id == doc.id)
    )
    doc = q.scalar_one()
    return _doc_out(doc)


@router.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    q   = await db.execute(select(ClinicalDocument).where(ClinicalDocument.id == doc_id))
    doc = q.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    await db.delete(doc)
    await db.commit()
    return {"message": "Document deleted successfully"}


# ═══════════════════════════════════════════════════════════════════════════════
#  PATIENTS
# ═══════════════════════════════════════════════════════════════════════════════
@router.get("/api/patients")
async def list_patients(
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    q = select(Patient).order_by(Patient.name)
    if search:
        q = q.where(or_(
            Patient.name.ilike(f"%{search}%"),
            Patient.patient_id.ilike(f"%{search}%"),
        ))
    rs = await db.execute(q)
    patients = rs.scalars().all()
    return [
        {
            "id":           p.id,
            "patient_id":   p.patient_id,
            "name":         p.name,
            "age":          p.age,
            "gender":       p.gender,
            "blood_type":   p.blood_type,
            "department":   p.department,
            "admission_date": p.admission_date.isoformat() if p.admission_date else None,
        }
        for p in patients
    ]


@router.get("/api/patients/{patient_id}")
async def get_patient(patient_id: int, db: AsyncSession = Depends(get_db)):
    """Full patient profile: demographics + all documents + aggregate stats."""
    # Load patient — use load_options to eagerly fetch both doctor and issues
    # in one pass (avoid duplicate selectinload on the same relationship).
    from sqlalchemy.orm import selectinload as sil
    q = await db.execute(
        select(Patient)
        .options(
            sil(Patient.documents).options(
                sil(ClinicalDocument.doctor),
                sil(ClinicalDocument.issues),
            )
        )
        .where(Patient.id == patient_id)
    )
    p = q.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Patient not found")

    # Aggregate doc stats
    docs = p.documents or []
    statuses   = [d.status for d in docs]
    ai_scores  = [d.ai_score for d in docs if d.ai_score is not None]
    open_issues = sum(
        1 for d in docs for i in d.issues if not i.resolved
    )
    critical_issues = sum(
        1 for d in docs for i in d.issues
        if not i.resolved and i.severity == "critical"
    )

    doc_list = sorted(docs, key=lambda d: d.created_at, reverse=True)

    return {
        "id":             p.id,
        "patient_id":     p.patient_id,
        "name":           p.name,
        "age":            p.age,
        "gender":         p.gender,
        "blood_type":     p.blood_type,
        "department":     p.department,
        "admission_date": p.admission_date.isoformat() if p.admission_date else None,
        "created_at":     p.created_at.isoformat() if p.created_at else None,
        "stats": {
            "total_docs":      len(docs),
            "validated":       statuses.count("validated"),
            "pending":         statuses.count("pending"),
            "rejected":        statuses.count("rejected"),
            "review":          statuses.count("review"),
            "avg_score":       round(sum(ai_scores) / len(ai_scores), 1) if ai_scores else None,
            "open_issues":     open_issues,
            "critical_issues": critical_issues,
        },
        "documents": [
            {
                "id":          d.id,
                "doc_id":      d.doc_id,
                "doc_type":    d.doc_type,
                "title":       d.title,
                "diagnosis":   d.diagnosis,
                "icd_codes":   d.icd_codes,
                "medications": d.medications,
                "status":      d.status,
                "ai_score":    d.ai_score,
                "doctor_name": d.doctor.name if d.doctor else "—",
                "created_at":  d.created_at.isoformat() if d.created_at else None,
                "issue_count": sum(1 for i in d.issues if not i.resolved),
                "critical":    any(i.severity == "critical" and not i.resolved for i in d.issues),
            }
            for d in doc_list
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  DOCTORS
# ═══════════════════════════════════════════════════════════════════════════════
@router.get("/api/doctors")
async def list_doctors(db: AsyncSession = Depends(get_db)):
    rs = await db.execute(select(Doctor).order_by(Doctor.name))
    return [
        {
            "id":             d.id,
            "doctor_id":      d.doctor_id,
            "name":           d.name,
            "specialization": d.specialization,
            "department":     d.department,
            "email":          d.email,
        }
        for d in rs.scalars().all()
    ]


# ═══════════════════════════════════════════════════════════════════════════════
#  ISSUES
# ═══════════════════════════════════════════════════════════════════════════════
@router.get("/api/issues")
async def list_issues(
    resolved:   Optional[bool] = None,
    severity:   Optional[str]  = None,
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(ValidationIssue)
        .options(selectinload(ValidationIssue.document).selectinload(ClinicalDocument.patient))
        .order_by(desc(ValidationIssue.created_at))
        .limit(200)
    )
    if resolved is not None:
        q = q.where(ValidationIssue.resolved == resolved)
    if severity:
        q = q.where(ValidationIssue.severity == severity)
    rs = await db.execute(q)
    issues = rs.scalars().all()
    return [
        {
            "id":          i.id,
            "document_id": i.document_id,
            "doc_id":      i.document.doc_id if i.document else "",
            "patient_name":i.document.patient.name if i.document and i.document.patient else "",
            "issue_type":  i.issue_type,
            "severity":    i.severity,
            "description": i.description,
            "field_name":  i.field_name,
            "resolved":    i.resolved,
            "created_at":  i.created_at.isoformat() if i.created_at else None,
        }
        for i in issues
    ]


@router.patch("/api/issues/{issue_id}/resolve")
async def resolve_issue(issue_id: int, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(ValidationIssue).where(ValidationIssue.id == issue_id))
    issue = q.scalar_one_or_none()
    if not issue:
        raise HTTPException(404, "Issue not found")
    issue.resolved = True
    await db.commit()
    return {"message": "Issue resolved", "id": issue_id}
