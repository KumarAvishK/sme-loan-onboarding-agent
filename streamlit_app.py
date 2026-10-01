import json
import streamlit as st

from app.workflow import build_stepwise_graph, start_or_resume
from app.sample_data import APPLICATION

st.set_page_config(page_title="SME Loan Onboarding Agent", page_icon="🏦", layout="wide")

STAGES = [
    ("application", "Application"),
    ("documents", "Documents"),
    ("kyb", "KYC / KYB"),
    ("bureau", "Bureau"),
    ("gst", "GST / Tax"),
    ("cashflow", "Banking / Cash Flow"),
    ("financials", "Financial Analysis"),
    ("fraud", "Fraud / Anomaly"),
    ("policy", "Policy Assessment"),
    ("memo", "Credit Memo"),
    ("review", "Credit Officer"),
    ("complete", "Decision"),
]

if "graph" not in st.session_state:
    st.session_state.graph = build_stepwise_graph()
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "started" not in st.session_state:
    st.session_state.started = False
if "paused" not in st.session_state:
    st.session_state.paused = None


def get_state():
    if not st.session_state.thread_id:
        return {}
    cfg = {"configurable": {"thread_id": st.session_state.thread_id}}
    return st.session_state.graph.get_state(cfg).values


def run_start():
    app = st.session_state.application
    st.session_state.thread_id = app["application_id"]
    st.session_state.started = True
    cfg = {"configurable": {"thread_id": st.session_state.thread_id}}
    initial = {"application": app, "request": "Assess this SME working-capital loan application.", "audit": []}
    result = start_or_resume(st.session_state.graph, cfg, state=initial)
    st.session_state.paused = result.get("__interrupt__")


def resume(payload):
    cfg = {"configurable": {"thread_id": st.session_state.thread_id}}
    result = start_or_resume(st.session_state.graph, cfg, resume=payload)
    st.session_state.paused = result.get("__interrupt__")


st.title("SME Loan Onboarding Agent")
st.caption("Bank-style stepwise onboarding • LangGraph • RAG • deterministic credit policy • human approval")

with st.sidebar:
    st.header("Application journey")
    current_state = get_state()
    current_stage = current_state.get("stage", "application")
    current_index = next((i for i, (key, _) in enumerate(STAGES) if key == current_stage), 0)
    for i, (_, label) in enumerate(STAGES):
        if i < current_index:
            st.success(f"✓ {label}")
        elif i == current_index:
            st.info(f"● {label}")
        else:
            st.write(f"○ {label}")
    if st.session_state.started:
        if st.button("Start new application", use_container_width=True):
            for key in ["thread_id", "paused", "started"]:
                st.session_state.pop(key, None)
            st.rerun()

if not st.session_state.started:
    st.header("1. Start a new SME loan application")
    st.write("Enter the applicant information below. The bank workflow will then move through verification, data retrieval, credit assessment and human approval one stage at a time.")

    with st.form("application_form"):
        c1, c2 = st.columns(2)
        with c1:
            application_id = st.text_input("Application ID", value=APPLICATION["application_id"])
            applicant_name = st.text_input("Legal business name", value=APPLICATION["applicant_name"])
            entity_type = st.selectbox("Entity type", ["Private Limited", "LLP", "Partnership", "Proprietorship"], index=0)
            industry = st.text_input("Industry", value=APPLICATION["industry"])
            vintage = st.number_input("Business vintage (years)", min_value=0, max_value=100, value=APPLICATION["business_vintage_years"])
            purpose = st.selectbox("Loan purpose", ["Working Capital", "Term Loan", "Equipment / Capex", "Business Expansion"], index=0)
        with c2:
            requested_amount = st.number_input("Requested facility (₹)", min_value=100000, value=APPLICATION["requested_amount"], step=100000)
            tenure = st.number_input("Tenure (months)", min_value=3, max_value=120, value=APPLICATION["tenure_months"])
            turnover = st.number_input("Annual turnover (₹)", min_value=0, value=APPLICATION["annual_turnover"], step=100000)
            ebitda = st.number_input("Annual EBITDA (₹)", min_value=0, value=APPLICATION["annual_ebitda"], step=100000)
            existing_debt = st.number_input("Existing debt (₹)", min_value=0, value=APPLICATION["existing_debt"], step=100000)

        st.subheader("Credit and financial information")
        c3, c4, c5 = st.columns(3)
        with c3:
            bureau_score = st.number_input("Business bureau score", min_value=0, max_value=900, value=APPLICATION["bureau_score"])
            business_dpd = st.number_input("Business DPD", min_value=0, value=APPLICATION["business_dpd"])
        with c4:
            gst_turnover = st.number_input("GST turnover (₹)", min_value=0, value=APPLICATION["gst_turnover"], step=100000)
            gst_current = st.checkbox("GST filings current", value=APPLICATION["gst_filings_current"])
        with c5:
            inflows = st.number_input("Avg monthly inflows (₹)", min_value=0, value=APPLICATION["avg_monthly_business_inflows"], step=10000)
            outflows = st.number_input("Avg monthly outflows (₹)", min_value=0, value=APPLICATION["avg_monthly_business_outflows"], step=10000)

        submitted = st.form_submit_button("Submit Application", type="primary", use_container_width=True)

    if submitted:
        st.session_state.application = {
            **APPLICATION,
            "application_id": application_id,
            "applicant_name": applicant_name,
            "entity_type": entity_type,
            "industry": industry,
            "business_vintage_years": vintage,
            "purpose": purpose,
            "requested_amount": requested_amount,
            "tenure_months": tenure,
            "annual_turnover": turnover,
            "annual_ebitda": ebitda,
            "existing_debt": existing_debt,
            "bureau_score": bureau_score,
            "business_dpd": business_dpd,
            "gst_turnover": gst_turnover,
            "gst_filings_current": gst_current,
            "avg_monthly_business_inflows": inflows,
            "avg_monthly_business_outflows": outflows,
        }
        run_start()
        st.rerun()

else:
    state = get_state()
    current_stage = state.get("stage", "application")
    idx = next((i for i, (key, _) in enumerate(STAGES) if key == current_stage), 0)
    label = STAGES[idx][1]

    st.progress(idx / (len(STAGES) - 1))
    st.header(f"Stage {idx + 1} of {len(STAGES)} — {label}")

    app = state.get("application", {})
    if current_stage == "documents":
        st.subheader("Document collection")
        st.write("In a production bank, these documents would come from the applicant portal, RM upload or document vault.")
        files = st.file_uploader("Upload supporting documents", accept_multiple_files=True, type=["pdf", "png", "jpg", "jpeg", "xlsx", "csv"])
        st.caption("Demo: file contents are not sent to an external system; only filenames are recorded.")
        if st.button("Complete document submission", type="primary"):
            payload = {"files": [f.name for f in files], "document_count": len(files)}
            resume(payload)
            st.rerun()

    elif current_stage == "review":
        st.subheader("Credit officer review")
        st.warning("This is the human decision point. The system does not automatically approve the case.")
        st.write("**Policy outcome:**", state.get("policy_result", {}).get("outcome"))
        failed = state.get("policy_result", {}).get("failed_rules", [])
        if failed:
            st.error("Policy exceptions / failed rules")
            for rule in failed:
                st.write(f"• {rule['rule']} — value: {rule['value']}")
        st.subheader("Credit memo")
        st.text(state.get("credit_memo", ""))
        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Approve", type="primary", use_container_width=True):
                resume({"action": "approve", "reviewer": "demo_credit_officer", "comment": "Approved after human review."})
                st.rerun()
        with c2:
            if st.button("Request Information", use_container_width=True):
                resume({"action": "request_info", "reviewer": "demo_credit_officer", "comment": "Additional information required."})
                st.rerun()
        with c3:
            if st.button("Reject", use_container_width=True):
                resume({"action": "reject", "reviewer": "demo_credit_officer", "comment": "Rejected after human review."})
                st.rerun()

    elif current_stage == "complete":
        st.success(f"Final decision: {state.get('final_status')}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Policy outcome", state.get("policy_result", {}).get("outcome", "-"))
        c2.metric("Final status", state.get("final_status", "-"))
        c3.metric("Bureau score", state.get("bureau", {}).get("bureau_score", "-"))
        st.subheader("Credit memo")
        st.text(state.get("credit_memo", ""))
        st.subheader("Audit trail")
        st.json(state.get("audit", []))

    else:
        # Show the output produced by the current agent/stage.
        st.subheader("Applicant")
        c1, c2, c3 = st.columns(3)
        c1.metric("Business", app.get("applicant_name", "-"))
        c2.metric("Requested facility", f"₹{app.get('requested_amount', 0):,.0f}")
        c3.metric("Purpose", app.get("purpose", "-"))

        output_map = {
            "application": None,
            "kyb": state.get("kyb"),
            "bureau": state.get("bureau"),
            "gst": state.get("gst"),
            "cashflow": state.get("cashflow"),
            "financials": state.get("financials"),
            "fraud": state.get("fraud"),
            "policy": state.get("policy_result"),
            "memo": None,
        }
        output = output_map.get(current_stage)
        if current_stage == "memo":
            st.subheader("Credit memo")
            st.text(state.get("credit_memo", ""))
        elif output:
            st.subheader("Agent output")
            st.json(output)

        # The interrupt has already completed this stage; the user explicitly moves to the next stage.
        if current_stage == "application":
            action_label = "Continue to Documents"
        elif current_stage == "kyb":
            action_label = "Continue to Credit Bureau"
        elif current_stage == "bureau":
            action_label = "Continue to GST / Tax"
        elif current_stage == "gst":
            action_label = "Continue to Banking / Cash Flow"
        elif current_stage == "cashflow":
            action_label = "Continue to Financial Analysis"
        elif current_stage == "financials":
            action_label = "Continue to Fraud / Anomaly"
        elif current_stage == "fraud":
            action_label = "Continue to Policy Assessment"
        elif current_stage == "policy":
            action_label = "Generate Credit Memo"
        elif current_stage == "memo":
            action_label = "Send to Credit Officer"
        else:
            action_label = "Continue"

        if st.button(action_label, type="primary", use_container_width=True):
            resume(True)
            st.rerun()

    with st.expander("Technical audit trail"):
        st.json(state.get("audit", []))
