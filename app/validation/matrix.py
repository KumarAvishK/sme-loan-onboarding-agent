"""Matrix-driven validation for the EXL Bank SME lending demo.

The included registry is synthetic and for local testing only. It is not a government,
bureau, tax or banking integration. Production verification must use approved services.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import re

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "data" / "EXL_Bank_SME_Loan_Validation_Master_Matrix.xlsx"
REGISTRY_PATH = ROOT / "data" / "EXL_Bank_Mock_Government_Validation_Registry.xlsx"

MANDATORY_DOCUMENTS = [
    ("business_pan", "Business PAN Card"),
    ("director_pan", "Director / Promoter PAN Card"),
    ("gst_certificate", "GST Registration Certificate"),
    ("bank_statement", "Business Bank Statement (12–36 months)"),
    ("financial_statements", "Financial Statements (P&L + Balance Sheet)"),
    ("gstr1", "Latest GSTR-1 Filing"),
    ("itr", "Latest ITR"),
    ("business_address", "Business Registered Office Address Proof"),
]
OPTIONAL_DOCUMENTS = [
    ("receivables_payables", "Receivables and Payables Ageing"),
    ("stock_inventory", "Stock / Inventory Statement"),
    ("existing_loan_sanction", "Existing Loan Sanction"),
    ("shareholding_pattern", "Shareholding Pattern"),
]


def _norm(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


def _yes(value: Any) -> bool:
    return str(value or "").strip().upper() in {"YES", "Y", "TRUE", "1", "PASS", "VERIFIED"}


def _load_sheets():
    if pd is None or not MATRIX_PATH.exists() or not REGISTRY_PATH.exists():
        return None, None, None
    matrix = pd.read_excel(MATRIX_PATH, sheet_name="Validation_Master_Matrix").fillna("")
    applicants = pd.read_excel(REGISTRY_PATH, sheet_name="Applicant_Input").fillna("")
    business = pd.read_excel(REGISTRY_PATH, sheet_name="Mock_Business_Registry").fillna("")
    promoters = pd.read_excel(REGISTRY_PATH, sheet_name="Mock_Promoter_KYC").fillna("")
    tax = pd.read_excel(REGISTRY_PATH, sheet_name="Mock_Tax_Filing_Registry").fillna("")
    return matrix, (applicants, business, promoters, tax), None


def _lookup(application_id: str):
    if pd is None or not REGISTRY_PATH.exists():
        return None
    try:
        applicants = pd.read_excel(REGISTRY_PATH, sheet_name="Applicant_Input").fillna("")
        business = pd.read_excel(REGISTRY_PATH, sheet_name="Mock_Business_Registry").fillna("")
        promoters = pd.read_excel(REGISTRY_PATH, sheet_name="Mock_Promoter_KYC").fillna("")
        tax = pd.read_excel(REGISTRY_PATH, sheet_name="Mock_Tax_Filing_Registry").fillna("")
        a = applicants.loc[applicants["application_id"].astype(str) == str(application_id)]
        b = business.loc[business["application_id"].astype(str) == str(application_id)]
        p = promoters.loc[promoters["application_id"].astype(str) == str(application_id)]
        t = tax.loc[tax["application_id"].astype(str) == str(application_id)]
        if a.empty or b.empty or p.empty or t.empty:
            return None
        return {
            "input": a.iloc[0].to_dict(),
            "business": b.iloc[0].to_dict(),
            "promoter": p.iloc[0].to_dict(),
            "tax": t.iloc[0].to_dict(),
        }
    except Exception:
        return None


def _result(row: dict, status: str, observed: Any, feedback: str, action: str):
    return {
        "stage": str(row.get("Stage", "")),
        "category": str(row.get("Category", "")),
        "check": str(row.get("Field / Validation Check", "")),
        "severity": str(row.get("Severity", "CRITICAL")),
        "status": status,
        "observed": str(observed)[:240],
        "blocks_financial_analysis": str(row.get("Blocks Financial Analysis", "YES")).strip().upper() not in {"NO", "FALSE"},
        "feedback": feedback,
        "required_action": action,
        "pass_condition": str(row.get("Pass Condition", "")),
    }


def run_validation_matrix(
    application: dict,
    documents: dict | None = None,
    validation_inputs: dict | None = None,
    *,
    matrix_path: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> dict:
    """Run all matrix rows; return per-check status and the Financial Analysis gate.

    For the two seeded demo IDs, synthetic Applicant_Input values are used to exercise
    matching logic. For all other IDs, values must be supplied by an approved extraction
    or verification adapter. No real external verification is performed here.
    """
    import pandas as pd_local

    docs = documents or {}
    uploaded = docs.get("uploaded", {}) if isinstance(docs, dict) else {}
    inputs = dict(validation_inputs or {})
    app_id = str(application.get("application_id", ""))
    registry = _lookup(app_id) if not registry_path else _lookup_from_path(app_id, Path(registry_path))
    if registry:
        # Explicit caller values win; otherwise use synthetic test-case values.
        source_input = registry["input"]
        for target, source in {
            "business_name": "business_name_entered",
            "business_pan": "business_pan_entered",
            "gstin": "gstin_entered",
            "cin": "cin_entered",
            "registered_address": "registered_address_entered",
            "promoter_name": "promoter_name_entered",
            "promoter_pan": "promoter_pan_entered",
            "promoter_dob": "dob_entered",
            "director_role": "role_entered",
            "ownership_percent": "ownership_percent_entered",
            "gstr1_gstin": "gstr1_gstin_entered",
            "itr_pan": "itr_pan_entered",
            "verification_consent": "verification_consent",
        }.items():
            if target not in inputs or inputs[target] in (None, ""):
                inputs[target] = source_input.get(source, "")
    matrix_file = Path(matrix_path) if matrix_path else MATRIX_PATH
    if pd_local is None or not matrix_file.exists():
        return {
            "checks": [{"check": "Validation matrix availability", "severity": "CRITICAL",
                        "status": "BLOCKED", "blocks_financial_analysis": True,
                        "feedback": "Validation matrix file is missing.", "required_action": "Restore the matrix workbook."}],
            "can_proceed": False, "summary": {"pass": 0, "review": 0, "blocked": 1, "total": 1},
            "source_mode": "unavailable",
        }

    rows = pd_local.read_excel(matrix_file, sheet_name="Validation_Master_Matrix").fillna("").to_dict("records")
    business = registry["business"] if registry else {}
    promoter = registry["promoter"] if registry else {}
    tax = registry["tax"] if registry else {}
    checks = []

    def compare(field: str, supplied: Any, expected: Any, feedback: str, action: str, severity="CRITICAL", matrix_row=None):
        row = matrix_row or next((r for r in rows if str(r.get("Field / Validation Check", "")).lower() == field.lower()), {})
        if not supplied or not expected:
            return _result(row, "REVIEW", supplied or "not provided",
                           "Verification evidence is not available in this demo. " + feedback,
                           action)
        if _norm(supplied) == _norm(expected):
            return _result(row, "PASS", supplied, "Matched against the synthetic test registry.", "Continue")
        return _result(row, "BLOCKED" if severity == "CRITICAL" else "REVIEW", supplied, feedback, action)

    def by_contains(term: str, occurrence: int = 0):
        found = [r for r in rows if term.lower() in str(r.get("Field / Validation Check", "")).lower()]
        return found[occurrence] if len(found) > occurrence else {}

    # Ordered checks correspond to the matrix's 33 rows.
    for i, row in enumerate(rows):
        field = str(row.get("Field / Validation Check", ""))
        category = str(row.get("Category", ""))
        supplied = ""
        expected = ""
        status = "REVIEW"
        feedback = "Required evidence is not yet verified."
        action = str(row.get("Required Action", "Provide evidence or route to an authorized reviewer."))
        observed = "not evaluated"

        if "Consent to verification" in field:
            supplied = inputs.get("verification_consent", "")
            status = "PASS" if _yes(supplied) else "BLOCKED"
            feedback = "Consent recorded." if status == "PASS" else "Record applicant consent before verification."
            action = "Continue" if status == "PASS" else "Capture consent"
            observed = supplied or "not recorded"
        elif field == "Business PAN number":
            supplied, expected = inputs.get("business_pan", ""), business.get("business_pan_test", "")
            c = compare(field, supplied, expected, "Business PAN does not match the registered record.", "Correct PAN / re-upload Business PAN", matrix_row=row)
            checks.append(c); continue
        elif field == "Legal business name":
            supplied, expected = application.get("applicant_name", "") or inputs.get("business_name", ""), business.get("legal_business_name", "")
            # Safe normalized exact match; close-but-not-exact names are sent to review.
            if supplied and expected and _norm(supplied) == _norm(expected):
                status, feedback, action = "PASS", "Legal name matched.", "Continue"
            elif supplied and expected:
                status, feedback, action = "REVIEW", "Legal name differs from the reference; provide supporting evidence or officer resolution.", "Correct name or request officer review"
            observed = supplied or "not provided"
        elif field == "Entity type":
            supplied, expected = application.get("entity_type", ""), business.get("business_type", "")
            status = "PASS" if supplied and expected and _norm(supplied) == _norm(expected) else ("REVIEW" if not expected else "BLOCKED")
            feedback = "Entity type matched." if status == "PASS" else "Entity type does not match the reference record."
            action = "Continue" if status == "PASS" else "Correct entity type / review"
            observed = supplied or "not provided"
        elif field == "Company / LLP registration number":
            supplied, expected = inputs.get("cin", ""), business.get("cin_llpin_test", "")
            c = compare(field, supplied, expected, "Company/LLP registration identifier does not match.", "Correct registration number", matrix_row=row)
            checks.append(c); continue
        elif field == "Company / LLP active status":
            supplied = business.get("mca_status", "")
            status = "PASS" if str(supplied).upper() == "ACTIVE" else ("REVIEW" if not supplied else "BLOCKED")
            feedback = "Mock registry status is active." if status == "PASS" else "Entity status requires review."
            action = "Continue" if status == "PASS" else "Route to officer"
            observed = supplied or "not available"
        elif field == "GST registration number":
            supplied, expected = inputs.get("gstin", ""), business.get("gstin_test", "")
            c = compare(field, supplied, expected, "GSTIN mismatch or inactive registration. Correct the GSTIN and re-upload the certificate.", "Correct GSTIN / re-upload GST certificate", matrix_row=row)
            if c["status"] == "PASS" and str(business.get("gst_status", "")).upper() != "ACTIVE":
                c.update(status="BLOCKED", feedback="GST registration is not active.", required_action="Route to officer")
            checks.append(c); continue
        elif field == "Legal name on GST record":
            supplied, expected = application.get("applicant_name", "") or inputs.get("business_name", ""), business.get("legal_business_name", "")
            c = compare(field, supplied, expected, "GST legal name does not reconcile with the business identity.", "Correct details / officer review", severity="REVIEW", matrix_row=row)
            checks.append(c); continue
        elif field == "Latest GSTR-1 filing status and period":
            supplied = tax.get("gstr1_filing_status", "")
            status = "PASS" if str(supplied).upper() == "FILED" and bool(tax.get("latest_gstr1_period")) else ("REVIEW" if not supplied else "BLOCKED")
            feedback = "Latest GSTR-1 filing is present in the synthetic registry." if status == "PASS" else "Latest GSTR-1 filing evidence is missing or not filed."
            action = "Continue" if status == "PASS" else "Provide latest GSTR-1 filing / officer review"
            observed = supplied or "not available"
        elif field == "PAN shown on ITR":
            supplied, expected = inputs.get("itr_pan", ""), business.get("business_pan_test", "")
            c = compare(field, supplied, expected, "PAN on ITR does not match the business PAN.", "Correct ITR evidence / officer review", matrix_row=row)
            checks.append(c); continue
        elif field == "Latest ITR filing status and year":
            supplied = tax.get("itr_filing_status", "")
            status = "PASS" if str(supplied).upper() == "FILED" and bool(tax.get("assessment_year")) else ("REVIEW" if not supplied else "BLOCKED")
            feedback = "Latest ITR filing is present in the synthetic registry." if status == "PASS" else "Latest ITR filing status/year needs evidence."
            action = "Continue" if status == "PASS" else "Provide latest ITR / officer review"
            observed = supplied or "not available"
        elif field == "Director/promoter PAN":
            supplied, expected = inputs.get("promoter_pan", ""), promoter.get("promoter_pan_test", "")
            c = compare(field, supplied, expected, "Promoter PAN does not match the reference.", "Correct promoter PAN / re-upload document", matrix_row=row)
            checks.append(c); continue
        elif field == "Promoter full legal name":
            supplied, expected = inputs.get("promoter_name", ""), promoter.get("promoter_full_name", "")
            c = compare(field, supplied, expected, "Promoter name mismatch; supporting evidence or officer resolution is required.", "Correct promoter details", severity="REVIEW", matrix_row=row)
            checks.append(c); continue
        elif field == "Promoter DOB":
            supplied, expected = inputs.get("promoter_dob", ""), promoter.get("dob", "")
            c = compare(field, supplied, expected, "Promoter DOB mismatch; verify source and route ambiguity to an officer.", "Correct DOB / officer review", severity="REVIEW", matrix_row=row)
            checks.append(c); continue
        elif field == "Identity verification result":
            supplied = promoter.get("identity_status", "")
            status = "PASS" if str(supplied).upper() == "VERIFIED" else ("REVIEW" if not supplied else "BLOCKED")
            feedback = "Synthetic identity verification status is verified." if status == "PASS" else "Identity verification is not confirmed."
            action = "Continue" if status == "PASS" else "Use approved identity verification / officer review"
            observed = supplied or "not available"
        elif field == "Director / authorized signatory status":
            supplied = promoter.get("director_match_status", "")
            status = "PASS" if str(supplied).upper() == "MATCH" else ("REVIEW" if not supplied else "BLOCKED")
            feedback = "Director role matched in the synthetic registry." if status == "PASS" else "Director / signatory authority is not confirmed."
            action = "Continue" if status == "PASS" else "Provide authority evidence / officer review"
            observed = supplied or "not available"
        elif field == "Shareholding / beneficial ownership":
            supplied = inputs.get("ownership_percent", "")
            expected = promoter.get("ownership_percent", "")
            c = compare(field, supplied, expected, "Ownership percentage differs from the registry; officer review required.", "Provide ownership evidence / officer review", severity="REVIEW", matrix_row=row)
            checks.append(c); continue
        elif field == "Business registered-office address":
            supplied, expected = inputs.get("registered_address", ""), business.get("registered_address", "")
            if supplied and expected and (_norm(supplied) == _norm(expected) or _norm(expected) in _norm(supplied) or _norm(supplied) in _norm(expected)):
                status, feedback, action = "PASS", "Address matched after safe normalization.", "Continue"
            elif supplied and expected:
                status, feedback, action = "REVIEW", "Address differs from reference; confirm pincode and provide supporting evidence.", "Correct address / officer review"
            observed = supplied or "not provided"
        elif category in {
            "Business PAN document", "Promoter PAN document", "GST certificate",
            "Bank statement", "Financial statements", "GSTR-1 document",
            "ITR document", "Address proof",
        }:
            # Matrix document rows map to the eight mandatory uploads.
            doc_map = {
                "Business PAN document": 0, "Promoter PAN document": 1,
                "GST certificate": 2, "Bank statement": 3,
                "Financial statements": 4, "GSTR-1 document": 5,
                "ITR document": 6, "Address proof": 7,
            }
            doc_key, doc_label = MANDATORY_DOCUMENTS[doc_map[category]]
            file_meta = uploaded.get(doc_key)
            synthetic_uploaded = str(registry["input"].get({
                "business_pan":"business_pan_doc_uploaded",
                "director_pan":"promoter_pan_doc_uploaded",
                "gst_certificate":"gst_certificate_uploaded",
                "business_address":"address_proof_uploaded",
                "gstr1":"gstr1_uploaded",
                "itr":"itr_uploaded",
            }.get(doc_key, ""), "")).upper() if registry else ""
            present = bool(file_meta and file_meta.get("name") and int(file_meta.get("size", 0) or 0) > 0)
            # For the demo only, uploads are required from the current session; registry flags
            # describe the synthetic fixture but never substitute for an actual uploaded file.
            readability_confirmed = bool(docs.get("readability_confirmed"))
            status = "BLOCKED" if not present else ("PASS" if readability_confirmed else "REVIEW")
            observed = f"{doc_label}: {'uploaded' if present else 'missing'}; readability attestation={'yes' if readability_confirmed else 'no'}"
            feedback = (f"{doc_label} is uploaded and the applicant has confirmed legibility (demo attestation only)." if status == "PASS"
                        else (f"Upload the mandatory document: {doc_label}." if not present
                              else f"Confirm the file is complete and legible. OCR/authenticity is not automated in this demo: {doc_label}."))
            action = "Continue" if status == "PASS" else (f"Upload {doc_label}" if not present else "Confirm readability or route for document review")
        elif field == "Entity identity consistency":
            status = "PASS" if registry and _norm(inputs.get("business_name")) == _norm(business.get("legal_business_name")) and _norm(inputs.get("business_pan")) == _norm(business.get("business_pan_test")) else ("REVIEW" if not registry else "BLOCKED")
            observed = "business name + PAN cross-check"
            feedback = "Business identity is consistent." if status == "PASS" else "Business identity fields do not reconcile."
            action = "Continue" if status == "PASS" else "Correct fields / officer review"
        elif category == "GST ↔ GSTR-1":
            supplied = inputs.get("gstr1_gstin", "")
            expected = tax.get("gstin_test", "")
            status = "PASS" if supplied and expected and _norm(supplied) == _norm(expected) else ("REVIEW" if not registry else "BLOCKED")
            observed = supplied or "not provided"
            feedback = "GSTR-1 GSTIN reconciles." if status == "PASS" else "GSTIN on GSTR-1 does not reconcile with the registered GSTIN."
            action = "Continue" if status == "PASS" else "Correct filing evidence"
        elif category == "ITR ↔ entity PAN":
            status = "PASS" if inputs.get("itr_pan") and _norm(inputs.get("itr_pan")) == _norm(business.get("business_pan_test")) else ("REVIEW" if not registry else "BLOCKED")
            observed = inputs.get("itr_pan", "not provided")
            feedback = "ITR entity mapping reconciles." if status == "PASS" else "ITR entity mapping does not reconcile."
            action = "Continue" if status == "PASS" else "Correct ITR evidence"
        elif category == "Name/address reconciliation":
            # This is an exception/ambiguity check, not a silent auto-rejection.
            status = "PASS" if registry and _norm(inputs.get("gstin")) == _norm(business.get("gstin_test")) and _norm(inputs.get("promoter_pan")) == _norm(promoter.get("promoter_pan_test")) else ("REVIEW" if not registry else "REVIEW")
            observed = "GSTIN / promoter PAN reconciliation"
            feedback = "Material identity fields reconcile." if status == "PASS" else "One or more fields conflict; officer review or corrected evidence is required."
            action = "Continue" if status == "PASS" else "Correct evidence / officer review"
        elif field == "All 8 mandatory documents":
            missing = [label for key, label in MANDATORY_DOCUMENTS if not uploaded.get(key)]
            status = "PASS" if not missing else "BLOCKED"
            observed = "all present" if not missing else "; ".join(missing)
            feedback = "All eight mandatory documents are present." if not missing else "Missing mandatory documents: " + ", ".join(missing)
            action = "Continue" if not missing else "Upload missing mandatory documents"
        elif field == "Pre-financial validation gate":
            status = "PASS" if all(c.get("status") == "PASS" for c in checks if c.get("blocks_financial_analysis")) else "BLOCKED"
            observed = "critical checks evaluated"
            feedback = "All blocking validations passed." if status == "PASS" else "Financial Analysis remains locked until all blocking checks pass."
            action = "Continue" if status == "PASS" else "Resolve failed/review checks"
        elif category == "Retry / re-upload loop":
            status = "PASS" if all(c.get("status") == "PASS" or not c.get("blocks_financial_analysis") for c in checks) else "BLOCKED"
            observed = "current validation run"
            feedback = "Current version has no unresolved blocking checks." if status == "PASS" else "Re-run validation after corrections; unresolved checks still block Financial Analysis."
            action = "Continue" if status == "PASS" else "Correct evidence and revalidate"
        else:
            # Unknown matrix row: fail closed instead of silently allowing the workflow.
            status = "REVIEW"
            observed = "not mapped to an executable rule"
            feedback = "This matrix check needs a configured verification adapter or authorized officer resolution."
            action = "Configure adapter / officer review"

        checks.append(_result(row, status, observed, feedback, action))

    # Gate uses only blocking checks; REVIEW counts as unresolved when blocking is true.
    blocking = [c for c in checks if c.get("blocks_financial_analysis") and c.get("status") != "PASS"]
    summary = {
        "pass": sum(c["status"] == "PASS" for c in checks),
        "review": sum(c["status"] == "REVIEW" for c in checks),
        "blocked": sum(c["status"] == "BLOCKED" for c in checks),
        "total": len(checks),
        "blocking": len(blocking),
    }
    return {
        "application_id": app_id,
        "checks": checks,
        "can_proceed": not blocking,
        "summary": summary,
        "source_mode": "synthetic_mock_registry" if registry else "manual_unverified",
        "notice": "Synthetic local test data only. No government, tax, identity, bureau or bank portal was queried.",
    }


def _lookup_from_path(application_id: str, path: Path):
    """Lookup variant for tests/custom registry path."""
    if pd is None or not path.exists():
        return None
    try:
        def find(sheet, col="application_id"):
            df = pd.read_excel(path, sheet_name=sheet).fillna("")
            hit = df.loc[df[col].astype(str) == str(application_id)]
            return hit.iloc[0].to_dict() if not hit.empty else {}
        a, b, p, t = (find(s) for s in ("Applicant_Input", "Mock_Business_Registry", "Mock_Promoter_KYC", "Mock_Tax_Filing_Registry"))
        if not a or not b or not p or not t:
            return None
        return {"input": a, "business": b, "promoter": p, "tax": t}
    except Exception:
        return None


def get_document_requirements():
    help_text = {
        "business_pan": "PAN of the borrowing business / entity.",
        "director_pan": "PAN of relevant director / promoter.",
        "gst_certificate": "GST registration certificate, where applicable.",
        "bank_statement": "Business bank statement covering the product-required period (12–36 months).",
        "financial_statements": "Latest Profit & Loss statement and Balance Sheet.",
        "gstr1": "Latest available GSTR-1 filing evidence.",
        "itr": "Latest applicable Income Tax Return filing evidence.",
        "business_address": "Registered office / business address proof.",
        "receivables_payables": "Optional supporting ageing schedules.",
        "stock_inventory": "Optional stock / inventory statement.",
        "existing_loan_sanction": "Optional existing loan sanction / repayment documents.",
        "shareholding_pattern": "Optional supporting ownership statement; ownership checks may still require evidence.",
    }
    rows = [{"id": key, "name": label, "category": "Mandatory documents",
             "required": True, "help": help_text.get(key, "")} for key, label in MANDATORY_DOCUMENTS]
    rows += [{"id": key, "name": label, "category": "Optional supporting documents",
              "required": False, "help": help_text.get(key, "")} for key, label in OPTIONAL_DOCUMENTS]
    return rows
