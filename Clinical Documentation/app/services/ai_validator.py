"""
AI Validation Service — uses IBM Granite via watsonx.ai REST API.
Falls back to a rule-based engine when no API key is configured.
Students: replace the env vars with your real IBM watsonx credentials.
"""

import os, re, httpx, json
from typing import Dict, Any, List

IBM_API_KEY   = os.getenv("IBM_GRANITE_API_KEY", "")
IBM_URL       = os.getenv("IBM_GRANITE_URL", "https://us-south.ml.cloud.ibm.com")
MODEL_ID      = os.getenv("IBM_GRANITE_MODEL_ID", "ibm/granite-3-8b-instruct")
PROJECT_ID    = os.getenv("IBM_PROJECT_ID", "")

REQUIRED_ICD = {
    "Acute Myocardial Infarction":         ["I21"],
    "Type 2 Diabetes Mellitus":            ["E11"],
    "Hypertensive Heart Disease":          ["I11"],
    "Community-Acquired Pneumonia":        ["J18"],
    "Lumbar Disc Herniation":              ["M51"],
    "Migraine Without Aura":               ["G43"],
    "Breast Cancer Stage II":              ["C50"],
    "Acute Appendicitis":                  ["K37", "K35"],
    "Chronic Kidney Disease Stage 3":      ["N18"],
    "Major Depressive Disorder":           ["F32"],
    "Asthma Moderate Persistent":          ["J45"],
    "Atrial Fibrillation":                 ["I48"],
}

DRUG_INTERACTIONS = [
    ({"warfarin", "aspirin"},          "Warfarin + Aspirin: High bleeding risk"),
    ({"metformin", "furosemide"},      "Metformin + Furosemide: Risk of lactic acidosis"),
    ({"sertraline", "lorazepam"},      "Sertraline + Lorazepam: CNS depression risk"),
    ({"digoxin", "amiodarone"},        "Digoxin + Amiodarone: Digoxin toxicity risk"),
    ({"sumatriptan", "sertraline"},    "Sumatriptan + Sertraline: Serotonin syndrome risk"),
]


# ── IBM Granite Token Helper ──────────────────────────────────────────────────
async def _get_ibm_token() -> str | None:
    if not IBM_API_KEY or IBM_API_KEY == "your_ibm_api_key_here":
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://iam.cloud.ibm.com/identity/token",
                data={"apikey": IBM_API_KEY, "grant_type": "urn:ibm:params:oauth:grant-type:apikey"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            return r.json().get("access_token")
    except Exception:
        return None


async def _call_granite(prompt: str) -> str | None:
    token = await _get_ibm_token()
    if not token:
        return None
    payload = {
        "model_id": MODEL_ID,
        "project_id": PROJECT_ID,
        "input": prompt,
        "parameters": {"decoding_method": "greedy", "max_new_tokens": 400, "temperature": 0.3},
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{IBM_URL}/ml/v1/text/generation?version=2023-05-29",
                json=payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            results = r.json().get("results", [])
            return results[0]["generated_text"].strip() if results else None
    except Exception:
        return None


# ── Rule-Based Fallback Validator ─────────────────────────────────────────────
def _rule_based_validate(doc: Dict[str, Any]) -> Dict[str, Any]:
    issues   = []
    score    = 100.0
    content  = (doc.get("content") or "").lower()
    diag     = doc.get("diagnosis", "")
    icd      = doc.get("icd_codes", "")
    meds_raw = (doc.get("medications") or "").lower()

    # 1. Check required fields
    for field in ["title", "content", "diagnosis", "icd_codes", "medications"]:
        if not doc.get(field):
            issues.append({"type": "missing_field", "severity": "high",
                           "field": field, "description": f"Required field '{field}' is missing."})
            score -= 15

    # 2. ICD code match
    expected_prefixes = REQUIRED_ICD.get(diag, [])
    if expected_prefixes and icd:
        if not any(icd.startswith(p) for p in expected_prefixes):
            issues.append({"type": "icd_mismatch", "severity": "high",
                           "field": "icd_codes",
                           "description": f"ICD code '{icd}' may not match diagnosis '{diag}'. Expected prefix(es): {expected_prefixes}"})
            score -= 20

    # 3. Drug interaction check
    meds_set = {m.strip().split()[0].lower() for m in meds_raw.split(",")}
    for pair, msg in DRUG_INTERACTIONS:
        if pair.issubset(meds_set):
            issues.append({"type": "drug_interaction", "severity": "critical",
                           "field": "medications", "description": msg})
            score -= 25

    # 4. Content completeness
    required_sections = ["assessment", "plan"]
    for sec in required_sections:
        if sec not in content:
            issues.append({"type": "incomplete_note", "severity": "medium",
                           "field": "content",
                           "description": f"Document is missing the '{sec.title()}' section."})
            score -= 10

    # 5. Medications have dosage?
    if meds_raw and not re.search(r"\d+\s?(mg|mcg|ml|g|iu)", meds_raw):
        issues.append({"type": "missing_field", "severity": "low",
                       "field": "medications",
                       "description": "Medication entries appear to be missing dosage information."})
        score -= 5

    score = max(0.0, round(score, 1))
    status = "validated" if score >= 75 and not any(i["severity"] == "critical" for i in issues) else \
             "review"    if score >= 50 else "rejected"

    summary = (
        f"Rule-based Analysis: Score {score}/100. "
        f"Found {len(issues)} issue(s). "
        + (f"Critical: {sum(1 for i in issues if i['severity']=='critical')} | " if issues else "")
        + (f"High: {sum(1 for i in issues if i['severity']=='high')} | " if issues else "")
        + ("Document meets quality standards." if score >= 75 else "Document requires review before approval.")
    )

    return {"score": score, "status": status, "issues": issues, "summary": summary, "engine": "rule-based"}


# ── Main Validation Entry Point ───────────────────────────────────────────────
async def validate_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates a clinical document.
    Tries IBM Granite first; falls back to rule-based engine.
    Returns: {score, status, issues, summary, engine}
    """
    # Always run rules first (fast & reliable)
    rule_result = _rule_based_validate(doc)

    # Try to enrich summary with IBM Granite
    prompt = f"""You are a clinical documentation quality expert.
Review the following clinical document and provide a concise quality assessment.

Document Type: {doc.get('doc_type', 'Unknown')}
Diagnosis: {doc.get('diagnosis', 'N/A')}
ICD Codes: {doc.get('icd_codes', 'N/A')}
Medications: {doc.get('medications', 'N/A')}
Content Summary: {str(doc.get('content', ''))[:500]}

Existing Issues Found: {json.dumps(rule_result['issues'], indent=2)}
Quality Score: {rule_result['score']}/100

Provide a 2-3 sentence clinical assessment explaining the score and key improvements needed.
Be specific, professional, and helpful for medical staff."""

    granite_summary = await _call_granite(prompt)

    if granite_summary:
        rule_result["summary"] = granite_summary
        rule_result["engine"]  = "IBM Granite (watsonx.ai)"

    return rule_result


# ── Batch Stats Helper ────────────────────────────────────────────────────────
def compute_stats(documents: List[Dict]) -> Dict[str, Any]:
    if not documents:
        return {}
    scores    = [d["ai_score"] for d in documents if d.get("ai_score")]
    statuses  = [d["status"] for d in documents]
    return {
        "total":        len(documents),
        "validated":    statuses.count("validated"),
        "pending":      statuses.count("pending"),
        "rejected":     statuses.count("rejected"),
        "review":       statuses.count("review"),
        "avg_score":    round(sum(scores) / len(scores), 1) if scores else 0,
        "high_quality": sum(1 for s in scores if s >= 85),
    }
