import streamlit as st

from app.workflow import build_stepwise_graph, run_stage, resume_human_review
from app.sample_data import APPLICATION

st.set_page_config(page_title="EXL Bank | SME Lending", page_icon="🏦", layout="wide", initial_sidebar_state="expanded")

# --- Enterprise banking visual system ---
st.markdown("""
<style>
:root { --orange:#FF5B35; --orange2:#E94825; --navy:#17324D; --navy2:#234D6B; --teal:#2E667F; --mint:#EEF5F7; --ink:#172B3A; --muted:#64788A; --line:#DCE5EC; --bg:#F6F8FA; --white:#FFFFFF; --amber:#C47D19; }
.stApp { background:var(--bg); color:var(--ink); }
[data-testid="stHeader"] { background:rgba(245,248,250,.94); }
[data-testid="stSidebar"] { background:#17324D; }
[data-testid="stSidebar"] * { color:#F4F7F9 !important; }
[data-testid="stSidebar"] .stButton button { background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.16); color:#fff !important; }
.block-container { padding-top:1.1rem; max-width:1420px; }
.bank-topbar { background:#fff; border:1px solid var(--line); border-radius:14px; padding:13px 20px; display:flex; align-items:center; justify-content:space-between; box-shadow:0 2px 10px rgba(11,42,74,.05); margin-bottom:20px; }
.bank-topbar img { height:54px; }
.bank-security { color:#64788A; font-size:13px; font-weight:600; }
.bank-security span { color:var(--orange); }
.hero { background:linear-gradient(115deg,#17324D 0%,#234D6B 68%,#2D647C 100%); color:white; border-radius:18px; padding:28px 32px; margin-bottom:22px; box-shadow:0 10px 30px rgba(11,42,74,.14); }
.hero h1 { color:white !important; margin:0 0 5px 0; font-size:30px; }
.hero p { color:#D7E5EF; margin:0; font-size:15px; }
.section-card { background:white; border:1px solid var(--line); border-radius:14px; padding:22px 24px; margin:12px 0; box-shadow:0 2px 8px rgba(11,42,74,.04); }
.step-pill { display:inline-block; background:#FFF0EC; color:#C83E22; border-radius:999px; padding:5px 11px; font-size:12px; font-weight:700; margin-bottom:8px; }
.stButton > button { border-radius:9px; min-height:42px; font-weight:650; }
.stButton > button[kind="primary"] { background:#17324D; border-color:#0B2A4A; }
.stButton > button[kind="primary"]:hover { background:#E94825; border-color:#E94825; }
[data-testid="stMetric"] { background:white; border:1px solid var(--line); border-radius:12px; padding:13px 15px; }
[data-testid="stFileUploader"] { background:#FBFCFD; border:1px dashed #B8C8D4; border-radius:10px; padding:4px; }
.stProgress > div > div > div > div { background:#FF5B35; }
hr { border-color:var(--line); }
.small-muted { color:#66798A; font-size:13px; }
.status-good { color:#167052; font-weight:700; }
</style>
""", unsafe_allow_html=True)


STAGES = [
    ("application", "Application"),
    ("documents", "Documents"),
    ("kyb", "KYC / KYB"),
    ("bureau", "Credit Bureau"),
    ("gst", "GST / Tax"),
    ("cashflow", "Banking / Cash Flow"),
    ("financials", "Financial Analysis"),
    ("fraud", "Fraud / Anomaly"),
    ("policy", "Policy Assessment"),
    ("memo", "Credit Memo"),
    ("review", "Credit Officer"),
    ("complete", "Final Decision"),
]

if "graph" not in st.session_state:
    st.session_state.graph = build_stepwise_graph()
if "case" not in st.session_state:
    st.session_state.case = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "documents" not in st.session_state:
    st.session_state.documents = {"files": [], "document_count": 0, "uploaded": {}, "requirements": []}


def config():
    return {"configurable": {"thread_id": st.session_state.thread_id}}


def current_stage():
    return (st.session_state.case or {}).get("stage", "application")


def save_case_state(update):
    if st.session_state.case is None:
        st.session_state.case = {}
    st.session_state.case.update(update)


def execute_stage(stage, extra=None):
    state = dict(st.session_state.case or {})
    state["stage"] = stage
    if extra:
        state.update(extra)
    result = run_stage(st.session_state.graph, config(), state)
    # The one-stage graph returns the updated state directly.
    save_case_state(dict(result))
    return result


def reset_case():
    for key in ["case", "thread_id", "documents"]:
        st.session_state.pop(key, None)
    st.rerun()


def fmt_inr(value):
    return f"₹{value:,.0f}"

def get_document_requirements(app):
    """Build an entity- and loan-purpose-specific document checklist.

    This is a demo requirement engine; production rules must be configured
    against the bank\'s approved KYC/KYB, credit and legal policy.
    """
    entity = app.get("entity_type", "Private Limited")
    purpose = app.get("purpose", "Working Capital")
    gst = app.get("gst_registered", True)
    itr = app.get("itr_applicable", True)
    audited = app.get("audited_financials", False)

    docs = [
        {"id":"business_pan", "name":"Business PAN card", "category":"Legal identity", "required":True, "help":"PAN of the borrowing entity / proprietor."},
    ]

    if entity == "Private Limited":
        docs += [
            {"id":"incorporation", "name":"Certificate of Incorporation", "category":"Legal identity", "required":True, "help":"MCA certificate establishing the company."},
            {"id":"moa", "name":"Memorandum of Association (MOA)", "category":"Legal identity", "required":True, "help":"Latest MOA and amendments, where applicable."},
            {"id":"aoa", "name":"Articles of Association (AOA)", "category":"Legal identity", "required":True, "help":"Latest AOA and amendments, where applicable."},
            {"id":"shareholding", "name":"Latest shareholding pattern", "category":"Ownership & authority", "required":True, "help":"Current ownership / shareholding statement."},
            {"id":"board_resolution", "name":"Board resolution / borrowing authority", "category":"Ownership & authority", "required":True, "help":"Authority to borrow and identify authorised signatory."},
            {"id":"director_pan", "name":"Director PAN card(s)", "category":"Promoter / director KYC", "required":True, "help":"PAN for relevant directors / authorised persons."},
            {"id":"director_ovd", "name":"Director KYC — Aadhaar / other OVD", "category":"Promoter / director KYC", "required":True, "help":"Aadhaar or another accepted Officially Valid Document; exact requirements follow the bank KYC policy."},
            {"id":"ubo_declaration", "name":"Beneficial ownership / UBO declaration", "category":"Ownership & authority", "required":True, "help":"Identify and verify applicable beneficial owners."},
        ]
    elif entity == "LLP":
        docs += [
            {"id":"incorporation", "name":"LLP incorporation certificate", "category":"Legal identity", "required":True, "help":"MCA LLP incorporation document."},
            {"id":"llp_agreement", "name":"LLP Agreement", "category":"Legal identity", "required":True, "help":"Latest executed LLP agreement and amendments."},
            {"id":"partners", "name":"Partner / designated partner details", "category":"Ownership & authority", "required":True, "help":"Current partner list and ownership / contribution details."},
            {"id":"partner_pan", "name":"Partner PAN card(s)", "category":"Promoter / partner KYC", "required":True, "help":"PAN for relevant partners / authorised persons."},
            {"id":"partner_ovd", "name":"Partner KYC — Aadhaar / other OVD", "category":"Promoter / partner KYC", "required":True, "help":"Aadhaar or another accepted OVD as applicable under the bank KYC policy."},
            {"id":"ubo_declaration", "name":"Beneficial ownership declaration", "category":"Ownership & authority", "required":True, "help":"Applicable beneficial owners / controlling persons."},
        ]
    elif entity == "Partnership":
        docs += [
            {"id":"partnership_deed", "name":"Partnership Deed", "category":"Legal identity", "required":True, "help":"Latest executed partnership deed and amendments."},
            {"id":"partner_authority", "name":"Partner authorisation / borrowing authority", "category":"Ownership & authority", "required":True, "help":"Authority for borrowing and authorised signatory."},
            {"id":"partner_pan", "name":"Partner PAN card(s)", "category":"Promoter / partner KYC", "required":True, "help":"PAN for relevant partners / authorised persons."},
            {"id":"partner_ovd", "name":"Partner KYC — Aadhaar / other OVD", "category":"Promoter / partner KYC", "required":True, "help":"Aadhaar or another accepted OVD as applicable under the bank KYC policy."},
            {"id":"ubo_declaration", "name":"Beneficial ownership declaration", "category":"Ownership & authority", "required":True, "help":"Applicable beneficial owners / controlling persons."},
        ]
    else:  # Proprietorship
        docs += [
            {"id":"proprietor_pan", "name":"Proprietor PAN card", "category":"Promoter KYC", "required":True, "help":"PAN of the proprietor."},
            {"id":"proprietor_ovd", "name":"Proprietor KYC — Aadhaar / other OVD", "category":"Promoter KYC", "required":True, "help":"Aadhaar or another accepted OVD; not universally Aadhaar-only."},
        ]

    docs += [
        {"id":"business_address", "name":"Business / registered-office address proof", "category":"Address", "required":True, "help":"For example property tax receipt, municipal khata, electricity bill, valid lease/rent agreement, consent letter or applicable government document."},
        {"id":"authorised_signatory", "name":"Authorised signatory KYC & authority", "category":"Ownership & authority", "required":True, "help":"Identity/KYC plus appointment/authorisation evidence where applicable."},
    ]

    if gst:
        docs += [
            {"id":"gst_certificate", "name":"GST Registration Certificate / GSTIN proof", "category":"Tax", "required":True, "help":"GST registration details where the business is GST-registered."},
            {"id":"gstr1", "name":"Latest GSTR-1 filing(s)", "category":"Tax", "required":True, "help":"Latest available filing(s), subject to the bank's lookback policy."},
            {"id":"gstr3b", "name":"Latest GSTR-3B filing(s)", "category":"Tax", "required":True, "help":"Latest available filing(s), subject to the bank's lookback policy."},
        ]

    if itr:
        docs.append({"id":"itr", "name":"Latest ITR / income-tax filing", "category":"Tax", "required":True, "help":"Latest applicable ITR and computation / acknowledgement."})

    docs += [
        {"id":"bank_statements", "name":"Business bank statements — last 12 months", "category":"Banking", "required":True, "help":"Primary operating account(s); production should use consented Account Aggregator / bank feeds where available."},
        {"id":"existing_loans", "name":"Existing loan sanction letters / repayment schedules", "category":"Banking", "required":True, "help":"All material existing borrowing and repayment obligations."},
    ]

    if audited:
        docs.append({"id":"audited_financials", "name":"Latest audited financial statements", "category":"Financials", "required":True, "help":"Balance Sheet, P&L and Cash Flow, with notes / audit report as applicable."})
    else:
        docs.append({"id":"financials", "name":"Latest financial statements / computation", "category":"Financials", "required":True, "help":"Latest Balance Sheet and P&L or applicable financial statements."})

    if purpose in ["Working Capital"]:
        docs += [
            {"id":"receivables_payables", "name":"Receivables & payables ageing", "category":"Loan purpose", "required":True, "help":"Latest ageing supporting working-capital assessment."},
            {"id":"stock_statement", "name":"Latest stock / inventory statement", "category":"Loan purpose", "required":True, "help":"Required where relevant to the working-capital facility."},
        ]
    elif purpose in ["Term Loan", "Equipment / Capex"]:
        docs += [
            {"id":"vendor_quote", "name":"Vendor quotation / pro-forma invoice", "category":"Loan purpose", "required":True, "help":"For the asset / equipment / capex being financed."},
            {"id":"project_cost", "name":"Project cost / capex estimate", "category":"Loan purpose", "required":True, "help":"Cost, funding mix and implementation details."},
        ]
    elif purpose == "Business Expansion":
        docs += [
            {"id":"project_report", "name":"Business expansion / project report", "category":"Loan purpose", "required":True, "help":"Expansion plan, investment and projected economics."},
            {"id":"projected_financials", "name":"Projected financial statements", "category":"Loan purpose", "required":True, "help":"Projections supporting the requested facility."},
        ]

    return docs



st.markdown(f"""
<div class="bank-topbar">
  <img src="data:image/svg+xml;utf8,{__import__('urllib.parse').parse.quote(open('assets/exl-bankmark.svg', encoding='utf-8').read())}" />
  <div class="bank-security">🔒 Secure SME Lending Workspace &nbsp; <span>● Systems operational</span></div>
</div>
<div class="hero">
  <div class="step-pill">EXL BANK • SME LENDING</div>
  <h1>Business Loan Onboarding</h1>
  <p>Digital SME lending workflow with structured onboarding, evidence validation and credit decision support.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='text-align:right;color:#7B8995;font-size:11px;margin-top:-10px;margin-bottom:8px;'>Concept demonstration • Not an actual EXL banking product</div>", unsafe_allow_html=True)

stage = current_stage()
idx = next((i for i, (key, _) in enumerate(STAGES) if key == stage), 0)

with st.sidebar:
    st.image("assets/exl-wordmark.svg", use_container_width=True)
    st.markdown("<div style='font-size:12px;opacity:.75;margin:-8px 0 16px 4px;'>SME CREDIT ORIGINATION</div>", unsafe_allow_html=True)
    st.header("Application journey")
    for i, (key, label) in enumerate(STAGES):
        if i < idx:
            st.success(f"✓ {label}")
        elif i == idx:
            st.info(f"● {label}")
        else:
            st.write(f"○ {label}")
    st.divider()
    if st.session_state.case:
        st.caption(f"Application: {st.session_state.case['application']['application_id']}")
        if st.button("Start new application", use_container_width=True):
            reset_case()

if st.session_state.case is None:
    st.progress(0)
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.header("1. Start a new SME loan application")
    st.write("Capture the information a relationship manager or applicant would provide. External credit, tax and banking data will be retrieved later by specialist agents.")

    with st.form("application_form"):
        c1, c2 = st.columns(2)
        with c1:
            application_id = st.text_input("Application ID", value=APPLICATION["application_id"])
            applicant_name = st.text_input("Legal business name", value="")
            entity_type = st.selectbox("Entity type", ["Private Limited", "LLP", "Partnership", "Proprietorship"])
            industry = st.text_input("Industry", value="")
            gst_registered = st.checkbox("GST registered", value=True)
            itr_applicable = st.checkbox("ITR applicable", value=True)
            audited_financials = st.checkbox("Audited financial statements available", value=False)
            vintage = st.number_input("Business vintage (years)", min_value=0, max_value=100, value=3)
        with c2:
            requested_amount = st.number_input("Requested facility (₹)", min_value=100000, value=2500000, step=100000)
            tenure = st.number_input("Tenure (months)", min_value=3, max_value=120, value=36)
            purpose = st.selectbox("Loan purpose", ["Working Capital", "Term Loan", "Equipment / Capex", "Business Expansion"])
            turnover = st.number_input("Annual turnover (₹)", min_value=0, value=48000000, step=100000)
            ebitda = st.number_input("Annual EBITDA (₹)", min_value=0, value=4200000, step=100000)
            existing_debt = st.number_input("Existing debt (₹)", min_value=0, value=12000000, step=100000)

        st.subheader("Additional financial information")
        c3, c4, c5 = st.columns(3)
        with c3:
            current_assets = st.number_input("Current assets (₹)", min_value=0, value=14500000, step=100000)
            current_liabilities = st.number_input("Current liabilities (₹)", min_value=0, value=8500000, step=100000)
        with c4:
            annual_interest = st.number_input("Existing annual interest (₹)", min_value=0, value=1200000, step=100000)
            annual_principal = st.number_input("Existing annual principal (₹)", min_value=0, value=2400000, step=100000)
        with c5:
            inflows = st.number_input("Avg monthly business inflows (₹)", min_value=0, value=3820000, step=10000)
            outflows = st.number_input("Avg monthly business outflows (₹)", min_value=0, value=3140000, step=10000)

        submitted = st.form_submit_button("Submit Application", type="primary", use_container_width=True)

    if submitted:
        if not applicant_name.strip() or not industry.strip():
            st.error("Please enter the legal business name and industry before submitting.")
        else:
            app = {
                **APPLICATION,
                "application_id": application_id.strip(),
                "applicant_name": applicant_name.strip(),
                "entity_type": entity_type,
                "industry": industry.strip(),
                "business_vintage_years": vintage,
                "requested_amount": requested_amount,
                "tenure_months": tenure,
                "purpose": purpose,
                "annual_turnover": turnover,
                "annual_ebitda": ebitda,
                "existing_debt": existing_debt,
                "gst_registered": gst_registered,
                "itr_applicable": itr_applicable,
                "audited_financials": audited_financials,
                "current_assets": current_assets,
                "current_liabilities": current_liabilities,
                "annual_interest": annual_interest,
                "annual_principal": annual_principal,
                "avg_monthly_business_inflows": inflows,
                "avg_monthly_business_outflows": outflows,
            }
            st.session_state.thread_id = app["application_id"]
            st.session_state.case = {"application": app, "request": "Assess this SME working-capital loan application.", "audit": [], "stage": "application"}
            execute_stage("application")
            st.rerun()
    st.info("Demo note: bureau, GST and banking information are simulated in this prototype and will be retrieved by agents in later stages.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

case = st.session_state.case
stage = current_stage()
idx = next((i for i, (key, _) in enumerate(STAGES) if key == stage), 0)
st.progress(idx / (len(STAGES) - 1))
st.markdown(f"<div class='step-pill'>STEP {idx + 1} OF {len(STAGES)}</div>", unsafe_allow_html=True)
st.header(STAGES[idx][1])

app = case["application"]

# Common applicant header
c1, c2, c3, c4 = st.columns(4)
c1.metric("Business", app["applicant_name"])
c2.metric("Facility", fmt_inr(app["requested_amount"]))
c3.metric("Purpose", app["purpose"])
c4.metric("Application", app["application_id"])

if stage == "documents":
    st.subheader("Document submission")
    st.write("The checklist below is generated from the entity type, tax applicability and loan purpose. Upload each required document against its specific requirement.")

    requirements = get_document_requirements(app)
    existing = st.session_state.documents.get("uploaded", {})
    uploaded = dict(existing)

    # Group the checklist so the applicant sees a bank-style document request.
    categories = []
    for d in requirements:
        if d["category"] not in categories:
            categories.append(d["category"])

    for category in categories:
        st.markdown(f"### {category}")
        for d in [x for x in requirements if x["category"] == category]:
            label = f"{d['name']}" + ("  **(Mandatory)**" if d["required"] else "  *(Optional)*")
            st.markdown(label)
            st.caption(d["help"])
            f = st.file_uploader(
                "Upload document",
                type=["pdf", "png", "jpg", "jpeg"],
                key=f"doc_{d['id']}",
                label_visibility="collapsed",
            )
            if f is not None:
                uploaded[d["id"]] = {"name": f.name, "size": f.size, "type": f.type}
            elif d["id"] not in uploaded:
                uploaded[d["id"]] = None

    st.session_state.documents["uploaded"] = uploaded
    st.session_state.documents["requirements"] = requirements

    mandatory = [d for d in requirements if d["required"]]
    missing = [d["name"] for d in mandatory if not uploaded.get(d["id"])]

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Mandatory documents", len(mandatory))
    with col2:
        st.metric("Missing mandatory documents", len(missing))

    if missing:
        st.warning("Please upload all mandatory documents before continuing. Missing: " + "; ".join(missing))
    else:
        st.success("All mandatory documents have been uploaded. Document Intelligence can now classify, extract and validate them.")

    if st.button("Submit Documents & Continue to KYC / KYB", type="primary", use_container_width=True, disabled=bool(missing)):
        execute_stage("documents", {
            "documents": {
                "files": [v["name"] for v in uploaded.values() if v],
                "document_count": sum(1 for v in uploaded.values() if v),
                "mandatory_document_count": len(mandatory),
                "missing_mandatory": missing,
                "checklist": requirements,
            }
        })
        st.rerun()

elif stage == "kyb":
    st.subheader("KYC / KYB verification")
    st.write("The KYB agent validates business identity and onboarding checks before credit data is retrieved.")
    if st.button("Run KYC / KYB Verification", type="primary", use_container_width=True):
        execute_stage("kyb")
        st.rerun()

elif stage == "bureau":
    st.subheader("Credit bureau retrieval")
    st.write("The bureau agent retrieves business/promoter credit behaviour and existing exposure. No score is manually entered here.")
    if st.button("Pull Credit Bureau", type="primary", use_container_width=True):
        execute_stage("bureau")
        st.rerun()

elif stage == "gst":
    st.subheader("GST / tax verification")
    st.write("The tax agent retrieves filing status and reconciles reported turnover with the application.")
    if st.button("Run GST Verification", type="primary", use_container_width=True):
        execute_stage("gst")
        st.rerun()

elif stage == "cashflow":
    st.subheader("Banking / cash-flow analysis")
    st.write("The banking agent summarizes consented business account activity and repayment cash capacity.")
    if st.button("Analyze Banking & Cash Flow", type="primary", use_container_width=True):
        execute_stage("cashflow")
        st.rerun()

elif stage == "financials":
    st.subheader("Financial analysis")
    st.write("Financial ratios and repayment capacity are calculated deterministically from the submitted financial data.")
    if st.button("Calculate Financial Metrics", type="primary", use_container_width=True):
        execute_stage("financials")
        st.rerun()

elif stage == "fraud":
    st.subheader("Fraud / anomaly screening")
    st.write("The fraud agent performs deterministic demo checks and surfaces exceptions for review.")
    if st.button("Run Fraud & Anomaly Checks", type="primary", use_container_width=True):
        execute_stage("fraud")
        st.rerun()

elif stage == "policy":
    st.subheader("Credit policy assessment")
    st.write("The deterministic policy engine evaluates the configured demo rules. The LLM does not make the policy decision.")
    if st.button("Evaluate Credit Policy", type="primary", use_container_width=True):
        execute_stage("policy")
        st.rerun()

elif stage == "memo":
    st.subheader("Credit memo generation")
    st.write("The Credit Memo Agent combines validated evidence with retrieved policy context. Claude is optional; the prototype has a deterministic fallback.")
    if st.button("Generate Evidence-Grounded Credit Memo", type="primary", use_container_width=True):
        execute_stage("memo")
        st.rerun()

elif stage == "review":
    st.subheader("Credit officer review")
    st.warning("Human approval required. This is the only commitment/decision point in the workflow.")
    policy = case.get("policy_result", {})
    c1, c2 = st.columns(2)
    c1.metric("Policy outcome", policy.get("outcome", "-"))
    c2.metric("Bureau score", case.get("bureau", {}).get("bureau_score", "-"))
    if policy.get("failed_rules"):
        st.error("Policy exceptions / failed rules")
        for rule in policy["failed_rules"]:
            st.write(f"• {rule['rule']} — value: {rule['value']}")
    st.subheader("Credit memo")
    st.text(case.get("credit_memo", ""))
    st.divider()
    if "hitl_opened" not in st.session_state or not st.session_state.hitl_opened:
        if st.button("Open Credit Officer Decision", type="primary", use_container_width=True):
            result = run_stage(st.session_state.graph, config(), dict(case))
            if "__interrupt__" in result:
                st.session_state.hitl_opened = True
            st.rerun()
    else:
        st.info("Review the evidence above, then record the authorized credit decision.")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Approve", type="primary", use_container_width=True):
                resume_human_review(st.session_state.graph, config(), {"action": "approve", "reviewer": "credit_officer_demo", "comment": "Approved after human review."})
                st.session_state.case = dict(st.session_state.graph.get_state(config()).values)
                st.session_state.pop("hitl_opened", None)
                st.rerun()
        with c2:
            if st.button("Request Information", use_container_width=True):
                resume_human_review(st.session_state.graph, config(), {"action": "request_info", "reviewer": "credit_officer_demo", "comment": "Additional information required."})
                st.session_state.case = dict(st.session_state.graph.get_state(config()).values)
                st.session_state.pop("hitl_opened", None)
                st.rerun()
        with c3:
            if st.button("Reject", use_container_width=True):
                resume_human_review(st.session_state.graph, config(), {"action": "reject", "reviewer": "credit_officer_demo", "comment": "Rejected after human review."})
                st.session_state.case = dict(st.session_state.graph.get_state(config()).values)
                st.session_state.pop("hitl_opened", None)
                st.rerun()

elif stage == "complete":
    st.success(f"Final decision: {case.get('final_status', '-')}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Policy outcome", case.get("policy_result", {}).get("outcome", "-"))
    c2.metric("Final status", case.get("final_status", "-"))
    c3.metric("Bureau score", case.get("bureau", {}).get("bureau_score", "-"))
    st.subheader("Credit memo")
    st.text(case.get("credit_memo", ""))
    st.subheader("Decision record")
    st.json(case.get("hitl_decision", {}))
    st.subheader("Audit trail")
    st.json(case.get("audit", []))
    if st.button("Start another application", type="primary"):
        reset_case()

# Evidence panels for completed stages
if stage in {"kyb", "bureau", "gst", "cashflow", "financials", "fraud", "policy", "memo", "review", "complete"}:
    st.divider()
    st.subheader("Latest agent output")
    output_map = {
        "kyb": case.get("kyb"), "bureau": case.get("bureau"), "gst": case.get("gst"),
        "cashflow": case.get("cashflow"), "financials": case.get("financials"),
        "fraud": case.get("fraud"), "policy": case.get("policy_result"),
    }
    if stage in output_map and output_map[stage] is not None:
        st.json(output_map[stage])

with st.expander("Technical audit trail"):
    st.json(case.get("audit", []))
