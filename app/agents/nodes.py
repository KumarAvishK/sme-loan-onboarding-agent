import json
from typing import Any
from langgraph.types import interrupt
from app.llm.client import get_llm, llm_text
from app.policy.engine import run_policy_engine
from app.rag.retriever import retrieve_credit_policy
from app.tools.banking_tools import (
    verify_kyb,
    get_credit_bureau,
    get_gst_data,
    get_bank_cashflow,
    calculate_financial_metrics,
    run_fraud_checks,
)


def audit_event(state, event, details=None):
    """Return one audit event for LangGraph's append-only reducer.

    Several specialist nodes run in parallel. The LoanState.audit field uses
    an operator.add reducer, so each node must return only its own event;
    LangGraph will merge concurrent events safely.
    """
    return [{"event": event, "details": details or {}}]


def intake_node(state):
    app = state["application"]
    return {
        "agent_findings": {
            "intake": {
                "applicant": app["applicant_name"],
                "requested_amount": app["requested_amount"],
                "purpose": app["purpose"],
            }
        },
        "audit": audit_event(state, "intake_completed"),
    }


def kyb_node(state):
    r = verify_kyb.invoke({"application_id": state["application"]["application_id"]})
    return {"kyb": r, "audit": audit_event(state, "kyb_completed", r)}


def bureau_node(state):
    r = get_credit_bureau.invoke({"application_id": state["application"]["application_id"]})
    return {"bureau": r, "audit": audit_event(state, "bureau_completed", r)}


def gst_node(state):
    r = get_gst_data.invoke({"application_id": state["application"]["application_id"]})
    return {"gst": r, "audit": audit_event(state, "gst_completed", r)}


def cashflow_node(state):
    r = get_bank_cashflow.invoke({"application_id": state["application"]["application_id"]})
    return {"cashflow": r, "audit": audit_event(state, "cashflow_completed", r)}


def financial_node(state):
    r = calculate_financial_metrics.invoke({"application_id": state["application"]["application_id"]})
    return {"financials": r, "audit": audit_event(state, "financial_analysis_completed", r)}


def fraud_node(state):
    r = run_fraud_checks.invoke({"application_id": state["application"]["application_id"]})
    return {"fraud": r, "audit": audit_event(state, "fraud_completed", r)}


def rag_node(state):
    c = retrieve_credit_policy.invoke({
        "query": "SME loan approval requirements KYC DSCR exceptions human approval",
        "top_k": 4,
    })
    return {"rag_context": c, "audit": audit_event(state, "rag_retrieval_completed")}


def policy_node(state):
    r = run_policy_engine(
        state["application"], state["kyb"], state["bureau"],
        state["gst"], state["financials"], state["fraud"]
    )
    return {
        "policy_result": r,
        "audit": audit_event(state, "policy_completed", {"outcome": r["outcome"], "failed_rules": r["failed_rules"]}),
    }


def credit_memo_node(state):
    app = state["application"]
    policy = state["policy_result"]
    evidence = {
        "application": app, "kyb": state["kyb"], "bureau": state["bureau"],
        "gst": state["gst"], "cashflow": state["cashflow"],
        "financials": state["financials"], "fraud": state["fraud"], "policy": policy,
    }
    llm = get_llm()
    if llm is not None:
        memo = llm_text(
            "You are a banking credit-memo analyst. Use only supplied evidence. Do not invent numbers.",
            "Create a concise credit memo with profile, facility, financials, bureau, cash flow, strengths, concerns, policy outcome and next step. RAG context:\n"
            + state["rag_context"] + "\nEvidence:\n" + json.dumps(evidence, indent=2),
        )
    else:
        memo = (
            f"SME CREDIT MEMO — {app['application_id']}\n"
            f"Applicant: {app['applicant_name']}\n"
            f"Requested facility: ₹{app['requested_amount']:,.0f}\n"
            f"Purpose: {app['purpose']}\n"
            f"Turnover: ₹{app['annual_turnover']:,.0f}\n"
            f"EBITDA: ₹{app['annual_ebitda']:,.0f}\n"
            f"Bureau score: {state['bureau']['bureau_score']}\n"
            f"Business DPD: {state['bureau']['business_dpd']}\n"
            f"Monthly cash surplus: ₹{state['cashflow']['monthly_surplus']:,.0f}\n"
            f"Current ratio: {state['financials']['current_ratio']}\n"
            f"Debt/EBITDA: {state['financials']['debt_to_ebitda']}\n"
            f"Demo DSCR: {state['financials']['dscr_demo']}\n"
            f"Policy outcome: {policy['outcome']}\n"
            f"Failed rules: {policy['failed_rules']}\n"
            "Next step: apply the configured credit-officer/HITL workflow."
        )
    return {"credit_memo": memo.strip(), "audit": audit_event(state, "credit_memo_generated", {"llm_used": llm is not None})}


def human_review_node(state):
    decision = interrupt({
        "type": "credit_officer_review",
        "application_id": state["application"]["application_id"],
        "policy_outcome": state["policy_result"]["outcome"],
        "failed_rules": state["policy_result"]["failed_rules"],
        "credit_memo": state["credit_memo"],
        "allowed_actions": ["approve", "request_info", "reject"],
    })
    return {"hitl_decision": decision, "audit": audit_event(state, "human_review_completed", decision)}


def final_decision_node(state):
    action = state.get("hitl_decision", {}).get("action", "request_info")
    status = {
        "approve": "APPROVED",
        "reject": "REJECTED",
        "request_info": "MORE_INFORMATION_REQUIRED",
    }.get(action, "MORE_INFORMATION_REQUIRED")
    return {"final_status": status, "audit": audit_event(state, "final_decision", {"status": status})}
