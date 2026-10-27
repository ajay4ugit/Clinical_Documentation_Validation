"""
Seed the database with synthetic (fake) but realistic clinical data.
Safe to run multiple times -- skips if data already exists.
"""
import sys, io
# Ensure stdout can handle unicode on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf_8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import asyncio
import random
from datetime import datetime, timedelta
from app.models.database import (
    AsyncSessionLocal, init_db,
    Patient, Doctor, ClinicalDocument, ValidationIssue
)

# ── Synthetic Data Pools ──────────────────────────────────────────────────────
FIRST_NAMES = ["James", "Maria", "Robert", "Linda", "Michael", "Barbara",
               "William", "Patricia", "David", "Jennifer", "Richard", "Sarah",
               "Priya", "Arjun", "Mei", "Carlos", "Fatima", "Kwame", "Sofia", "Ali"]

LAST_NAMES  = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
               "Miller", "Davis", "Martinez", "Wilson", "Patel", "Chen",
               "Nguyen", "Taylor", "Anderson", "Thomas", "Jackson", "White"]

BLOOD_TYPES   = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
DEPARTMENTS   = ["Cardiology", "Neurology", "Orthopedics", "Oncology",
                 "Emergency", "Pediatrics", "Radiology", "General Medicine"]

DOCTOR_SPECS  = {
    "Cardiology":      ["Cardiologist", "Interventional Cardiologist"],
    "Neurology":       ["Neurologist", "Epileptologist"],
    "Orthopedics":     ["Orthopedic Surgeon", "Sports Medicine"],
    "Oncology":        ["Medical Oncologist", "Radiation Oncologist"],
    "Emergency":       ["Emergency Physician", "Trauma Surgeon"],
    "Pediatrics":      ["Pediatrician", "Neonatologist"],
    "Radiology":       ["Radiologist", "Interventional Radiologist"],
    "General Medicine":["General Physician", "Internal Medicine Specialist"],
}

DOC_TYPES = ["Discharge Summary", "Prescription", "Lab Report",
             "Radiology Report", "Surgical Note", "Progress Note"]

DIAGNOSES = [
    ("Acute Myocardial Infarction", "I21.9", "Aspirin 81mg, Metoprolol 25mg, Atorvastatin 40mg"),
    ("Type 2 Diabetes Mellitus", "E11.9", "Metformin 500mg, Glipizide 5mg"),
    ("Hypertensive Heart Disease", "I11.9", "Lisinopril 10mg, Amlodipine 5mg"),
    ("Community-Acquired Pneumonia", "J18.9", "Amoxicillin 500mg, Azithromycin 250mg"),
    ("Lumbar Disc Herniation", "M51.1", "Ibuprofen 400mg, Cyclobenzaprine 5mg"),
    ("Migraine Without Aura", "G43.0", "Sumatriptan 50mg, Topiramate 25mg"),
    ("Breast Cancer Stage II", "C50.9", "Tamoxifen 20mg, Letrozole 2.5mg"),
    ("Acute Appendicitis", "K37", "Ceftriaxone 1g IV, Metronidazole 500mg"),
    ("Chronic Kidney Disease Stage 3", "N18.3", "Furosemide 40mg, Sodium Bicarbonate 650mg"),
    ("Major Depressive Disorder", "F32.1", "Sertraline 50mg, Lorazepam 0.5mg"),
    ("Asthma Moderate Persistent", "J45.1", "Salbutamol inhaler, Budesonide 200mcg"),
    ("Atrial Fibrillation", "I48.91", "Warfarin 5mg, Digoxin 0.125mg"),
]

ISSUE_TEMPLATES = [
    ("missing_field",     "medium", "diagnosis",    "Diagnosis field is incomplete or missing ICD code"),
    ("icd_mismatch",      "high",   "icd_codes",    "ICD-10 code does not match stated diagnosis"),
    ("drug_interaction",  "critical","medications", "Potential drug interaction detected between medications"),
    ("missing_field",     "low",    "medications",  "Medication dosage not specified"),
    ("incomplete_note",   "medium", "content",      "Progress note lacks required sections (assessment/plan)"),
    ("date_error",        "low",    "created_at",   "Document date is in the future"),
    ("missing_signature", "high",   "doctor_id",    "Document missing physician signature or attestation"),
    ("allergy_check",     "critical","medications", "Prescribed medication conflicts with patient allergy flag"),
]

def rand_date(days_back=180):
    return datetime.utcnow() - timedelta(days=random.randint(0, days_back))

async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        # Check if already seeded
        from sqlalchemy import select, func
        result = await db.execute(select(func.count()).select_from(Patient))
        if result.scalar() > 0:
            print("[OK]  Database already seeded -- skipping.")
            return

        print("[INFO]  Seeding synthetic clinical data...")

        # ── Doctors (16 across departments) ──────────────────────────────────
        doctors = []
        for i, dept in enumerate(DEPARTMENTS):
            for j, spec in enumerate(DOCTOR_SPECS[dept]):
                fn = random.choice(FIRST_NAMES)
                ln = random.choice(LAST_NAMES)
                doc = Doctor(
                    doctor_id   = f"DR{(i*2+j+1):04d}",
                    name        = f"Dr. {fn} {ln}",
                    specialization = spec,
                    department  = dept,
                    email       = f"{fn.lower()}.{ln.lower()}@hospital.com",
                )
                db.add(doc)
                doctors.append(doc)

        await db.flush()

        # ── Patients (60 synthetic patients) ─────────────────────────────────
        patients = []
        for i in range(60):
            fn  = random.choice(FIRST_NAMES)
            ln  = random.choice(LAST_NAMES)
            dept = random.choice(DEPARTMENTS)
            p = Patient(
                patient_id     = f"PT{(i+1):05d}",
                name           = f"{fn} {ln}",
                age            = random.randint(18, 85),
                gender         = random.choice(["Male", "Female"]),
                blood_type     = random.choice(BLOOD_TYPES),
                department     = dept,
                admission_date = rand_date(90),
            )
            db.add(p)
            patients.append(p)

        await db.flush()

        # ── Clinical Documents (120 documents) ───────────────────────────────
        statuses = ["pending", "validated", "rejected", "review"]
        status_weights = [0.35, 0.40, 0.10, 0.15]

        documents = []
        for i in range(120):
            patient  = random.choice(patients)
            # Pick a doctor from the same or related department
            dept_docs = [d for d in doctors if d.department == patient.department]
            doctor   = random.choice(dept_docs) if dept_docs else random.choice(doctors)
            diag     = random.choice(DIAGNOSES)
            doc_type = random.choice(DOC_TYPES)
            status   = random.choices(statuses, weights=status_weights)[0]
            ai_score = round(random.uniform(55, 99), 1) if status != "pending" else None

            content = (
                f"Patient {patient.name}, {patient.age}y {patient.gender}, "
                f"admitted to {patient.department} on "
                f"{patient.admission_date.strftime('%Y-%m-%d')}.\n\n"
                f"Chief Complaint: Presenting with symptoms consistent with {diag[0]}.\n\n"
                f"Assessment: {diag[0]} confirmed based on clinical evaluation and investigations.\n\n"
                f"Plan: Initiate {diag[2]}. Follow-up in 2 weeks. "
                f"Patient educated on medication adherence and lifestyle modifications."
            )

            doc = ClinicalDocument(
                doc_id     = f"DOC{(i+1):05d}",
                patient_id = patient.id,
                doctor_id  = doctor.id,
                doc_type   = doc_type,
                title      = f"{doc_type} — {diag[0]}",
                content    = content,
                diagnosis  = diag[0],
                icd_codes  = diag[1],
                medications= diag[2],
                status     = status,
                ai_score   = ai_score,
                ai_summary = (
                    f"AI Analysis: Document quality score {ai_score}/100. "
                    f"Diagnosis '{diag[0]}' aligns with ICD-10 code {diag[1]}. "
                    f"Medications are appropriate for stated diagnosis."
                ) if ai_score else None,
                created_at = rand_date(180),
            )
            db.add(doc)
            documents.append(doc)

        await db.flush()

        # ── Validation Issues (for pending + review docs) ─────────────────────
        issue_count = 0
        for doc in documents:
            if doc.status in ("pending", "review", "rejected"):
                num_issues = random.randint(1, 3)
                chosen = random.sample(ISSUE_TEMPLATES, min(num_issues, len(ISSUE_TEMPLATES)))
                for tmpl in chosen:
                    issue = ValidationIssue(
                        document_id = doc.id,
                        issue_type  = tmpl[0],
                        severity    = tmpl[1],
                        description = tmpl[3],
                        field_name  = tmpl[2],
                        resolved    = random.choice([True, False]) if doc.status == "review" else False,
                    )
                    db.add(issue)
                    issue_count += 1

        await db.commit()
        print(f"[OK]  Seeded: {len(doctors)} doctors, {len(patients)} patients, "
              f"{len(documents)} documents, {issue_count} validation issues.")


if __name__ == "__main__":
    asyncio.run(seed())
