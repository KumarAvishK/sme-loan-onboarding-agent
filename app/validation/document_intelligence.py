"""Synthetic document extraction and validation for EXL Bank demo.
Extracts embedded PDF text with pypdf; OCR for scanned images requires optional Tesseract.
All records are fictional and this module does not contact external portals.
"""
from __future__ import annotations
import re, io, os
from pathlib import Path
from typing import Any

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None
try:
    import pandas as pd
except Exception:
    pd = None

ROOT = Path(__file__).resolve().parents[2]
DB_XLSX = ROOT / "data" / "EXL_Bank_Synthetic_Customer_Database.xlsx"

DOC_IDS = {
    "business_pan": ("Business PAN Card", True),
    "director_pan": ("Director / Promoter PAN Card", True),
    "gst_certificate": ("GST Registration Certificate", True),
    "bank_statement": ("Business Bank Statement (12–36 months)", True),
    "financial_statements": ("Financial Statements (P&L + Balance Sheet)", True),
    "gstr1": ("Latest GSTR-1 Filing", True),
    "itr": ("Latest ITR", True),
    "business_address": ("Business Registered Office Address Proof", True),
    "promoter_ovd": ("Promoter identity proof (Aadhaar masked / accepted OVD)", False),
    "receivables_payables": ("Receivables and Payables Ageing", False),
    "stock_inventory": ("Stock / Inventory Statement", False),
    "existing_loan_sanction": ("Existing Loan Sanction", False),
    "shareholding_pattern": ("Shareholding Pattern", False),
}
def norm(v: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(v or "").strip().lower())
def extract_pdf_text(file_bytes: bytes) -> str:
    if not PdfReader:
        raise RuntimeError("pypdf is not installed. Add pypdf to requirements.txt.")
    reader = PdfReader(io.BytesIO(file_bytes))
    return "\n".join((p.extract_text() or "") for p in reader.pages).strip()
def _field(text, labels):
    for label in labels:
        m = re.search(r"(?im)^\s*" + re.escape(label) + r"\s*[:\-]?\s*\n?\s*([^\n]+)", text)
        if m:
            val=m.group(1).strip().strip(":")
            if val and val.lower() not in {"value","field"}: return val
    return ""
def parse_document(doc_id: str, text: str) -> dict:
    # Text labels in the supplied synthetic PDFs are deliberately supported.
    out={"document_id":doc_id,"document_name":DOC_IDS.get(doc_id,(doc_id,False))[0],"text":text}
    out["business_name"] = _field(text,["Entity","Legal Name","Business Name"])
    out["promoter_name"] = _field(text,["Promoter","Director","Applicant"])
    out["business_pan"] = _field(text,["PAN"])
    out["promoter_pan"] = _field(text,["Promoter PAN","Director PAN"]) or (_field(text,["PAN"]) if doc_id=="director_pan" else "")
    out["gstin"] = _field(text,["GSTIN"])
    out["cin"] = _field(text,["CIN","Company Registration Number","Registration Number"])
    out["address"] = _field(text,["Address","Registered Address"])
    out["status"] = _field(text,["Status","Filing Status"])
    out["tax_period"] = _field(text,["Tax Period","Period","FY","AY"])
    out["turnover"] = _field(text,["Turnover","Annualized Credits","Revenue"])
    out["ebitda"] = _field(text,["EBITDA"])
    out["net_worth"] = _field(text,["Net Worth"])
    out["debt"] = _field(text,["Debt"])
    out["dscr"] = _field(text,["DSCR"])
    out["business_income"] = _field(text,["Business Income"])
    out["dpd_bounces"] = _field(text,["DPD / Bounces","DPD","Bounces"])
    out["aadhaar_last4"] = _field(text,["Aadhaar last 4","Aadhaar last four","Identity last 4"])
    out["ownership"] = _field(text,["Ownership","Ownership %"])
    # Preserve raw values; downstream validation normalizes only for comparison.
    return out
def load_database(path=None):
    if pd is None: raise RuntimeError("pandas/openpyxl are required to load the synthetic database.")
    path=Path(path or DB_XLSX)
    return {s:pd.read_excel(path,sheet_name=s).fillna("").to_dict("records") for s in
            ["Application_Form","Synthetic_Business_DB","Synthetic_Promoter_DB","Synthetic_Tax_DB","Synthetic_Credit_DB","Loan_Policy"]}
def _one(rows, app_id):
    return next((r for r in rows if str(r.get("application_id",""))==str(app_id)),None)
def validate_uploaded_documents(application: dict, documents: dict, consent: bool, db_path=None) -> dict:
    """Extract text from uploaded bytes, reconcile with seeded DB, and apply conservative gate."""
    db=load_database(db_path); supplied_app_id=str(application.get("application_id","")).strip()
    # Support IDs printed on the supplied synthetic PDFs as aliases to seeded demo records.
    aliases = {
        "SME-10001": "DEMO-APP-1001",
        "SME-APP-10001": "DEMO-APP-1001",
        "DEMO-APP-1001": "DEMO-APP-1001",
        "SME-20002": "DEMO-APP-2002",
        "SME-APP-20002": "DEMO-APP-2002",
        "DEMO-APP-2002": "DEMO-APP-2002",
    }
    app_id=aliases.get(supplied_app_id.upper(), supplied_app_id)
    approw=_one(db["Application_Form"],app_id)
    business=_one(db["Synthetic_Business_DB"],app_id)
    promoter=_one(db["Synthetic_Promoter_DB"],app_id)
    tax=_one(db["Synthetic_Tax_DB"],app_id)
    credit=_one(db["Synthetic_Credit_DB"],app_id)
    results=[]; parsed={}; reupload=[]
    def add(stage,check,status,observed,feedback,action,critical=True):
        results.append({"stage":stage,"check":check,"severity":"CRITICAL" if critical else "MAJOR","status":status,
                        "observed":str(observed or "")[:160],"feedback":feedback,"required_action":action,
                        "blocks_financial_analysis":bool(critical and status!="PASS")})
        if status in {"BLOCKED","REVIEW"} and action.lower().startswith(("re-upload","upload corrected","provide corrected")):
            reupload.append({"check":check,"action":action,"feedback":feedback})
    if not approw or not business or not promoter or not tax:
        add("Pre-check","Application exists in synthetic database","BLOCKED",app_id,
            "Application ID is not in the synthetic test database.","Select a seeded DEMO application ID.")
        return {"checks":results,"documents":parsed,"can_proceed":False,"reupload":reupload,
                "summary":{"total":len(results),"pass":0,"review":0,"blocked":1},"eligibility":{}}
    add("Pre-check","Consent to verification","PASS" if consent else "BLOCKED","recorded" if consent else "not recorded",
        "Demo consent recorded." if consent else "Consent is required before mock verification.",
        "Continue" if consent else "Record consent before running validation.")
    uploaded=documents.get("uploaded",{}) if isinstance(documents,dict) else {}
    # Documents are stored as {name,size,type,content_bytes}; never trust filename alone.
    for doc_id,(label,required) in DOC_IDS.items():
        item=uploaded.get(doc_id)
        if not item:
            if required: add("Documents",label,"BLOCKED","missing",f"{label} is mandatory and has not been uploaded.",f"Upload the {label}.")
            continue
        raw=item.get("content_bytes")
        if not raw:
            add("Documents",label,"BLOCKED","file bytes unavailable",f"The file {item.get('name','')} was recorded by name only; its contents were not available for inspection.",f"Re-upload the {label}.")
            continue
        try:
            text=extract_pdf_text(raw)
        except Exception as e:
            add("Documents",label,"REVIEW",item.get("name"),f"Could not extract text ({type(e).__name__}). If this is a scan, OCR or a clearer PDF is required.",f"Re-upload a text-searchable {label} or route for manual review.")
            continue
        if not text.strip():
            add("Documents",label,"REVIEW",item.get("name"),"No selectable text was found. Scanned-page OCR is required before validation.",f"Re-upload a text-searchable {label} or route for manual review.")
            continue
        fields=parse_document(doc_id,text); parsed[doc_id]=fields
        # Document must contain the intended type / key field.
        expected_hint = {
          "business_pan":("business_pan","PAN"),"director_pan":("promoter_pan","PAN"),
          "gst_certificate":("gstin","GSTIN"),"bank_statement":("dpd_bounces","Period"),
          "financial_statements":("revenue","Revenue"),"gstr1":("gstin","GSTIN"),
          "itr":("business_pan","PAN"),"business_address":("business_name","Entity")
        }.get(doc_id)
        if not expected_hint:
            add("Documents",label,"PASS",item.get("name"),"Text extracted from uploaded optional document; field-level rules depend on document content.","Continue",False)
        else:
            # Ensure correct document type via basic keywords and a nonempty extracted text.
            keys={"business_pan":["Business PAN"],"director_pan":["Director Promoter PAN","Director PAN"],"gst_certificate":["GST Registration"],"bank_statement":["Bank Statement"],"financial_statements":["Financial Statements"],"gstr1":["GSTR-1"],"itr":["Latest ITR","ITR"],"business_address":["Address Proof"]}[doc_id]
            if not any(k.lower() in text.lower() for k in keys):
                add("Documents",label,"BLOCKED",item.get("name"),"Uploaded file does not appear to be the requested document type.",f"Re-upload the correct {label}.")
            else:
                add("Documents",label,"PASS","text extracted",f"Readable text extracted from {label}; content checks follow.","Continue",False)
    # Reconcile extracted document facts to synthetic DB.
    def compare(doc_id,field,expected,check,stage="Cross-document",required=True,normal=True):
        got=parsed.get(doc_id,{}).get(field,"")
        if not got:
            if required: add(stage,check,"BLOCKED","field not found",f"{check}: the required field was not extractable from the uploaded document.",f"Re-upload a corrected {DOC_IDS[doc_id][0]} with the field visible.")
            return
        if norm(got)==norm(expected):
            add(stage,check,"PASS",got,"Extracted value matches the synthetic database.","Continue")
        else:
            add(stage,check,"BLOCKED",got,f"Extracted value does not match the synthetic record (expected test value: {expected}).",f"Re-upload corrected {DOC_IDS[doc_id][0]} or correct the application details.")
    compare("business_pan","business_pan",business["business_pan_test"],"Business PAN matches mock registry","Business identity")
    compare("business_pan","business_name",business["legal_business_name"],"Legal business name on PAN")
    compare("director_pan","promoter_name",promoter["promoter_full_name"],"Promoter name matches mock registry","Promoter identity")
    compare("director_pan","business_pan",promoter["promoter_pan_test"],"Promoter PAN matches mock registry","Promoter identity")
    compare("gst_certificate","gstin",business["gstin_test"],"GSTIN matches mock registry","Tax identity")
    compare("gst_certificate","business_name",business["legal_business_name"],"GST legal name matches mock registry","Tax identity")
    compare("gstr1","gstin",tax["gstin_test"],"GSTR-1 GSTIN matches GST certificate","Tax reconciliation")
    compare("itr","business_pan",tax["itr_pan_test"],"PAN on ITR matches business PAN","Tax reconciliation")
    compare("business_address","business_name",business["legal_business_name"],"Address proof entity matches business","Address verification")
    # Compare first-page captured identity fields to the synthetic database.
    for key, expected, label in [
        ("business_pan",business.get("business_pan_test",""),"First-page Business PAN matches registry"),
        ("gstin",business.get("gstin_test",""),"First-page GSTIN matches registry"),
        ("cin",business.get("cin_llpin_test",""),"First-page CIN/LLPIN matches registry"),
        ("promoter_name",promoter.get("promoter_full_name",""),"First-page promoter name matches registry"),
        ("promoter_pan",promoter.get("promoter_pan_test",""),"First-page promoter PAN matches registry"),
        ("promoter_dob",promoter.get("dob",""),"First-page promoter DOB matches registry"),
    ]:
        supplied=application.get(key,"")
        if supplied:
            if norm(supplied)==norm(expected):
                add("Application",label,"PASS",supplied,"First-page value matches synthetic database.","Continue")
            else:
                add("Application",label,"BLOCKED",supplied,"First-page value differs from the synthetic customer record.",f"Correct {key.replace('_',' ')} and re-upload the supporting document.")
    aadhaar4=application.get("aadhaar_last4","")
    if aadhaar4:
        expected4=str(promoter.get("aadhaar_last4_test",""))
        if norm(aadhaar4)==norm(expected4):
            add("Promoter identity","First-page masked identity reference matches registry","PASS","masked reference matched","Masked test reference matches.","Continue")
        else:
            add("Promoter identity","First-page masked identity reference matches registry","REVIEW","masked reference mismatch","Masked identity reference does not match; verify the accepted identity proof.","Re-upload accepted identity proof or route to authorized officer.")
    # Compare business name supplied on first page to DB.
    appname=application.get("applicant_name","")
    if norm(appname)==norm(business["legal_business_name"]):
        add("Application","First-page business name matches registry","PASS",appname,"Application name matches the mock registry.","Continue")
    else:
        add("Application","First-page business name matches registry","BLOCKED",appname,"The first-page legal business name differs from the synthetic record.", "Correct the legal name and re-upload supporting documents.")
    # Aadhaar/OVD is checked if uploaded; no raw Aadhaar numbers stored/displayed.
    if "promoter_ovd" in parsed:
        a4=parsed["promoter_ovd"].get("aadhaar_last4","")
        exp=str(promoter.get("aadhaar_last4_test",""))
        if a4 and norm(a4)==norm(exp):
            add("Promoter identity","Masked identity last-four match","PASS","last four matched","Masked identity reference matched.","Continue")
        else:
            add("Promoter identity","Masked identity last-four match","REVIEW","not found or mismatch","Identity proof did not match the synthetic masked reference; route for re-upload/manual review.","Re-upload accepted identity proof or route to authorized officer.")
    # Document-level business PAN / promoter PAN mismatches trigger re-upload; never auto-pass from filenames.
    # Calculate indicative loan eligibility with conservative DSCR-based policy.
    try:
        requested=float(application.get("requested_amount",0) or 0)
        annual_ebitda=float(re.sub(r"[^0-9.]", "", parsed.get("financial_statements",{}).get("ebitda","0")) or 0)
        # Supplied demo statement values use lakh units; convert to INR.
        if annual_ebitda < 1000000: annual_ebitda *= 100000
        existing_debt=float(credit.get("existing_annual_debt_service_inr",0) or 0)
        annual_rate=float(credit.get("assumed_interest_rate_pct",13.5) or 13.5)/100
        tenure=int(application.get("tenure_months",36) or 36)
        # Interest coverage/DSCR proxy: max annual new debt service = EBITDA / minimum DSCR - existing annual debt service.
        min_dscr=float(credit.get("minimum_dscr",1.25) or 1.25)
        available=max(0,annual_ebitda/min_dscr-existing_debt)
        r=annual_rate/12; n=max(1,tenure)
        factor=(r*(1+r)**n)/(((1+r)**n)-1) if r else 1/n
        eligible=available/(12*factor) if factor else 0
        eligible=min(eligible,float(credit.get("product_cap_inr",10000000) or 10000000))
        reason=[]
        if requested>eligible: reason.append(f"Requested ₹{requested:,.0f} exceeds indicative repayment-capacity eligibility ₹{eligible:,.0f} by ₹{requested-eligible:,.0f}.")
        if annual_ebitda<=0: reason.append("EBITDA could not be reliably extracted; eligibility is not calculable.")
        eligibility={"requested_amount_inr":requested,"indicative_eligible_amount_inr":round(eligible,0),
          "excess_amount_inr":round(max(0,requested-eligible),0),"minimum_dscr":min_dscr,
          "assumed_interest_rate_pct":annual_rate*100,"tenure_months":tenure,"annual_ebitda_inr":annual_ebitda,
          "existing_annual_debt_service_inr":existing_debt,"available_annual_service_inr":available,
          "reasoning":reason,"route_to_credit_officer":bool(reason)}
    except Exception as e:
        eligibility={"reasoning":[f"Eligibility calculation requires review: {type(e).__name__}"],"route_to_credit_officer":True}
    summary={"total":len(results),"pass":sum(x["status"]=="PASS" for x in results),
             "review":sum(x["status"]=="REVIEW" for x in results),"blocked":sum(x["status"]=="BLOCKED" for x in results)}
    can=summary["blocked"]==0 and summary["review"]==0
    return {"checks":results,"documents":parsed,"can_proceed":can,"reupload_requests":reupload,
            "summary":summary,"eligibility":eligibility,
            "notice":"Synthetic local database only. No government, tax, identity, bureau or bank portal was queried."}
