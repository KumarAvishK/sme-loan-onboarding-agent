import streamlit as st

from app.workflow import build_stepwise_graph, run_stage, resume_human_review
from app.sample_data import APPLICATION

st.set_page_config(page_title="SME Loan Onboarding Agent", page_icon="🏦", layout="wide")

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
    st.session_state.documents = {"files": [], "document_count": 0}


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

st.title("SME Loan Onboarding Agent")
st.caption("Bank-style stepwise onboarding • LangGraph orchestration • RAG • deterministic credit policy • human approval")

stage = current_stage()
idx = next((i for i, (key, _) in enumerate(STAGES) if key == stage), 0)

with st.sidebar:
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
    st.header("1. Start a new SME loan application")
    st.write("Capture the information a relationship manager or applicant would provide. External credit, tax and banking data will be retrieved later by specialist agents.")

    with st.form("application_form"):
        c1, c2 = st.columns(2)
        with c1:
            application_id = st.text_input("Application ID", value=APPLICATION["application_id"])
            applicant_name = st.text_input("Legal business name", value="")
            entity_type = st.selectbox("Entity type", ["Private Limited", "LLP", "Partnership", "Proprietorship"])
            industry = st.text_input("Industry", value="")
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
    st.stop()

case = st.session_state.case
stage = current_stage()
idx = next((i for i, (key, _) in enumerate(STAGES) if key == stage), 0)
st.progress(idx / (len(STAGES) - 1))
st.header(f"Stage {idx + 1} of {len(STAGES)} — {STAGES[idx][1]}")

app = case["application"]

# Common applicant header
c1, c2, c3, c4 = st.columns(4)
c1.metric("Business", app["applicant_name"])
c2.metric("Facility", fmt_inr(app["requested_amount"]))
c3.metric("Purpose", app["purpose"])
c4.metric("Application", app["application_id"])

if stage == "documents":
    st.subheader("Document submission")
    st.write("Upload the documents normally requested during SME loan onboarding. The prototype records the files; production will route them to Document Intelligence/OCR.")
    files = st.file_uploader(
        "Supporting documents",
        accept_multiple_files=True,
        type=["pdf", "png", "jpg", "jpeg", "xlsx", "csv"],
        key="documents_uploader",
    )
    if files:
        st.write("Selected documents:")
        for f in files:
            st.write(f"• {f.name}")
    if st.button("Submit Documents & Continue to KYC / KYB", type="primary", use_container_width=True):
        docs = {"files": [f.name for f in files], "document_count": len(files)}
        execute_stage("documents", {"documents": docs})
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
