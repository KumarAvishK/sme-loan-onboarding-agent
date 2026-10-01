from typing import Any, Dict
import json

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt

from app.models import LoanState
from app.policy.engine import run_policy_engine
from app.rag.retriever import retrieve_credit_policy
from app.llm.client import get_llm, llm_text


def _audit(event: str, details: Dict[str, Any] | None = None):
    return [{"event": event, "details": details or {}}]


def application_node(state: LoanState):
    app = state["application"]
    return {
        "stage": "documents",
        "audit": _audit("application_submitted", {"application_id": app["application_id"]}),
    }


def documents_node(state: LoanState):
    docs = state.get("documents", {})
    return {
        "stage": "kyb",
        "audit": _audit("documents_received", docs),
    }


def kyb_node(state: LoanState):
    app = state["application"]
    result = {
        "kyb_status": "PASS",
        "pan_verified": True,
        "gstin_verified": True,
        "entity_verified": bool(app.get("applicant_name") and app.get("entity_type")),
        "ownership_check": "PASS",
        "screening": "CLEAR",
    }
    return {"kyb": result, "stage": "bureau", "audit": _audit("kyb_completed", result)}


def bureau_node(state: LoanState):
    app = state["application"]
    result = {
        "bureau_score": int(app.get("bureau_score", 748)),
        "business_dpd": int(app.get("business_dpd", 0)),
        "promoter_dpd": int(app.get("promoter_dpd", 0)),
        "recent_enquiries": int(app.get("recent_bureau_enquiries", 2)),
        "outstanding_exposure": float(app.get("existing_debt", 0)),
    }
    return {"bureau": result, "stage": "gst", "audit": _audit("bureau_completed", result)}


def gst_node(state: LoanState):
    app = state["application"]
    turnover = float(app.get("annual_turnover", 0))
    gst_turnover = float(app.get("gst_turnover", turnover))
    variance = (gst_turnover - turnover) / turnover if turnover else 0
    result = {
        "gst_turnover": gst_turnover,
        "filings_current": bool(app.get("gst_filings_current", True)),
        "turnover_variance_pct": round(variance, 4),
    }
    return {"gst": result, "stage": "cashflow", "audit": _audit("gst_completed", result)}


def cashflow_node(state: LoanState):
    app = state["application"]
    inflows = float(app.get("avg_monthly_business_inflows", 0))
    outflows = float(app.get("avg_monthly_business_outflows", 0))
    result = {
        "avg_monthly_inflows": inflows,
        "avg_monthly_outflows": outflows,
        "cashflow_volatility": float(app.get("cashflow_volatility", 0.12)),
        "monthly_surplus": inflows - outflows,
    }
    return {"cashflow": result, "stage": "financials", "audit": _audit("cashflow_completed", result)}


def financials_node(state: LoanState):
    app = state["application"]
    current_ratio = float(app.get("current_assets", 0)) / max(float(app.get("current_liabilities", 1)), 1)
    debt_to_ebitda = float(app.get("existing_debt", 0)) / max(float(app.get("annual_ebitda", 1)), 1)
    proposed_debt_service = float(app.get("requested_amount", 0)) / max(float(app.get("tenure_months", 12)) / 12, 1)
    dscr = float(app.get("annual_ebitda", 0)) / max(
        float(app.get("annual_interest", 0)) + float(app.get("annual_principal", 0)) + proposed_debt_service, 1
    )
    result = {
        "current_ratio": round(current_ratio, 2),
        "debt_to_ebitda": round(debt_to_ebitda, 2),
        "annual_ebitda": float(app.get("annual_ebitda", 0)),
        "dscr_demo": round(dscr, 2),
    }
    return {"financials": result, "stage": "fraud", "audit": _audit("financial_analysis_completed", result)}


def fraud_node(state: LoanState):
    flags = state["application"].get("fraud_flags", [])
    result = {"fraud_risk": "HIGH" if flags else "LOW", "flags": flags}
    return {"fraud": result, "stage": "policy", "audit": _audit("fraud_completed", result)}


def policy_node(state: LoanState):
    r = run_policy_engine(
        state["application"], state["kyb"], state["bureau"], state["gst"], state["financials"], state["fraud"]
    )
    return {
        "policy_result": r,
        "stage": "memo",
        "audit": _audit("policy_completed", {"outcome": r["outcome"], "failed_rules": r["failed_rules"]}),
    }


def memo_node(state: LoanState):
    app = state["application"]
    evidence = {
        "application": app,
        "documents": state.get("documents", {}),
        "kyb": state["kyb"], "bureau": state["bureau"], "gst": state["gst"],
        "cashflow": state["cashflow"], "financials": state["financials"],
        "fraud": state["fraud"], "policy": state["policy_result"],
    }
    rag_context = retrieve_credit_policy.invoke({
        "query": "SME loan credit policy KYC bureau GST cash flow DSCR human approval",
        "top_k": 4,
    })
    llm = get_llm()
    if llm is not None:
        memo = llm_text(
            "You are a banking credit memo analyst. Use only supplied evidence. Do not invent numbers.",
            "Prepare a concise credit memo covering profile, facility, financials, bureau, cash flow, strengths, concerns, policy outcome, conditions and next step.\nRAG:\n"
            + rag_context + "\nEvidence:\n" + json.dumps(evidence, indent=2),
        )
    else:
        p = state["policy_result"]
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
            f"DSCR: {state['financials']['dscr_demo']}\n"
            f"Policy outcome: {p['outcome']}\n"
            f"Failed rules: {p['failed_rules']}\n"
            "Next step: credit officer review."
        )
    return {
        "credit_memo": memo.strip(),
        "rag_context": rag_context,
        "stage": "review",
        "audit": _audit("credit_memo_generated", {"llm_used": llm is not None}),
    }


def review_node(state: LoanState):
    decision = interrupt({
        "stage": "review",
        "title": "Credit officer review",
        "message": "Review the complete case and select Approve, Reject or Request Information.",
        "allowed_actions": ["approve", "reject", "request_info"],
    })
    action = decision.get("action", "request_info") if isinstance(decision, dict) else "request_info"
    status = {
        "approve": "APPROVED",
        "reject": "REJECTED",
        "request_info": "MORE_INFORMATION_REQUIRED",
    }.get(action, "MORE_INFORMATION_REQUIRED")
    return {
        "hitl_decision": decision,
        "final_status": status,
        "stage": "complete",
        "audit": _audit("human_review_completed", {**(decision if isinstance(decision, dict) else {}), "status": status}),
    }


def route_stage(state: LoanState):
    return state.get("stage", "application")


def build_stepwise_graph():
    """One-stage-at-a-time LangGraph.

    Streamlit owns navigation. LangGraph executes exactly one stage per invocation.
    The only LangGraph interrupt is the genuine credit-officer HITL checkpoint.
    """
    builder = StateGraph(LoanState)
    nodes = {
        "application": application_node,
        "documents": documents_node,
        "kyb": kyb_node,
        "bureau": bureau_node,
        "gst": gst_node,
        "cashflow": cashflow_node,
        "financials": financials_node,
        "fraud": fraud_node,
        "policy": policy_node,
        "memo": memo_node,
        "review": review_node,
    }
    for name, fn in nodes.items():
        builder.add_node(name, fn)

    builder.add_conditional_edges(START, route_stage, {name: name for name in nodes})
    for name in nodes:
        builder.add_edge(name, END)
    return builder.compile(checkpointer=MemorySaver())


def run_stage(graph, config, state):
    return graph.invoke(state, config)


def resume_human_review(graph, config, payload):
    return graph.invoke(Command(resume=payload), config)
