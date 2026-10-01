from typing import Any, Dict
import json
import os

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt

from app.models import LoanState
from app.policy.engine import run_policy_engine
from app.rag.retriever import retrieve_credit_policy
from app.llm.client import get_llm, llm_text


def _audit(event: str, details: Dict[str, Any] | None = None):
    return [{"event": event, "details": details or {}}]


def _pause(stage: str, title: str, message: str):
    return interrupt({"stage": stage, "title": title, "message": message})


def intake_stage(state: LoanState):
    app = state["application"]
    _pause("application", "Application received", "Application captured. Review the applicant information and continue to document submission.")
    return {
        "stage": "documents",
        "audit": _audit("application_submitted", {"application_id": app["application_id"]}),
    }


def documents_stage(state: LoanState):
    payload = _pause("documents", "Documents", "Upload the required documents, then continue.")
    docs = payload if isinstance(payload, dict) else {}
    return {
        "documents": docs,
        "stage": "kyb",
        "audit": _audit("documents_received", docs),
    }


def kyb_stage(state: LoanState):
    app = state["application"]
    # Mock KYB: derived from supplied application fields.
    result = {
        "kyb_status": "PASS",
        "pan_verified": True,
        "gstin_verified": True,
        "entity_verified": bool(app.get("applicant_name") and app.get("entity_type")),
        "ownership_check": "PASS",
        "screening": "CLEAR",
    }
    _pause("kyb", "KYC / KYB verification", "Business identity and onboarding checks have completed. Review the result before continuing to bureau checks.")
    return {"kyb": result, "stage": "bureau", "audit": _audit("kyb_completed", result)}


def bureau_stage(state: LoanState):
    app = state["application"]
    result = {
        "bureau_score": int(app.get("bureau_score", 0)),
        "business_dpd": int(app.get("business_dpd", 0)),
        "promoter_dpd": int(app.get("promoter_dpd", 0)),
        "recent_enquiries": int(app.get("recent_bureau_enquiries", 0)),
        "outstanding_exposure": float(app.get("existing_debt", 0)),
    }
    _pause("bureau", "Credit bureau", "Business and promoter bureau information has been retrieved. Review score, DPD and exposure.")
    return {"bureau": result, "stage": "gst", "audit": _audit("bureau_completed", result)}


def gst_stage(state: LoanState):
    app = state["application"]
    turnover = float(app.get("annual_turnover", 0))
    gst_turnover = float(app.get("gst_turnover", turnover))
    variance = (gst_turnover - turnover) / turnover if turnover else 0
    result = {
        "gst_turnover": gst_turnover,
        "filings_current": bool(app.get("gst_filings_current", False)),
        "turnover_variance_pct": round(variance, 4),
    }
    _pause("gst", "GST / tax verification", "GST turnover and filing status have been checked. Review the reconciliation before continuing.")
    return {"gst": result, "stage": "cashflow", "audit": _audit("gst_completed", result)}


def cashflow_stage(state: LoanState):
    app = state["application"]
    inflows = float(app.get("avg_monthly_business_inflows", 0))
    outflows = float(app.get("avg_monthly_business_outflows", 0))
    result = {
        "avg_monthly_inflows": inflows,
        "avg_monthly_outflows": outflows,
        "cashflow_volatility": float(app.get("cashflow_volatility", 0)),
        "monthly_surplus": inflows - outflows,
    }
    _pause("cashflow", "Banking / cash-flow analysis", "Consent-based banking data has been summarized. Review inflows, outflows and surplus.")
    return {"cashflow": result, "stage": "financials", "audit": _audit("cashflow_completed", result)}


def financials_stage(state: LoanState):
    app = state["application"]
    current_ratio = float(app.get("current_assets", 0)) / max(float(app.get("current_liabilities", 1)), 1)
    debt_to_ebitda = float(app.get("existing_debt", 0)) / max(float(app.get("annual_ebitda", 1)), 1)
    proposed_debt_service = float(app.get("requested_amount", 0)) / max(float(app.get("tenure_months", 12)) / 12, 1)
    dscr = float(app.get("annual_ebitda", 0)) / max(float(app.get("annual_interest", 0)) + float(app.get("annual_principal", 0)) + proposed_debt_service, 1)
    result = {
        "current_ratio": round(current_ratio, 2),
        "debt_to_ebitda": round(debt_to_ebitda, 2),
        "annual_ebitda": float(app.get("annual_ebitda", 0)),
        "dscr_demo": round(dscr, 2),
    }
    _pause("financials", "Financial analysis", "Financial ratios and repayment-capacity metrics have been calculated deterministically.")
    return {"financials": result, "stage": "fraud", "audit": _audit("financial_analysis_completed", result)}


def fraud_stage(state: LoanState):
    flags = state["application"].get("fraud_flags", [])
    result = {"fraud_risk": "HIGH" if flags else "LOW", "flags": flags}
    _pause("fraud", "Fraud / anomaly screening", "Initial fraud and anomaly checks have completed. Review any flags before policy evaluation.")
    return {"fraud": result, "stage": "policy", "audit": _audit("fraud_completed", result)}


def policy_stage(state: LoanState):
    r = run_policy_engine(
        state["application"], state["kyb"], state["bureau"], state["gst"], state["financials"], state["fraud"]
    )
    _pause("policy", "Policy assessment", "Deterministic credit policy rules have been evaluated. Review passed and failed rules before memo generation.")
    return {"policy_result": r, "stage": "memo", "audit": _audit("policy_completed", {"outcome": r["outcome"], "failed_rules": r["failed_rules"]})}


def memo_stage(state: LoanState):
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
    _pause("memo", "Credit memo", "The evidence-grounded credit memo is ready. Review it before making the credit decision.")
    return {"credit_memo": memo.strip(), "rag_context": rag_context, "stage": "review", "audit": _audit("credit_memo_generated", {"llm_used": llm is not None})}


def review_stage(state: LoanState):
    decision = interrupt({
        "stage": "review",
        "title": "Credit officer review",
        "message": "Review the complete case and select Approve, Reject or Request Information in the UI.",
        "allowed_actions": ["approve", "reject", "request_info"],
    })
    return {"hitl_decision": decision, "stage": "decision", "audit": _audit("human_review_completed", decision)}


def final_stage(state: LoanState):
    action = state.get("hitl_decision", {}).get("action", "request_info")
    status = {"approve": "APPROVED", "reject": "REJECTED", "request_info": "MORE_INFORMATION_REQUIRED"}.get(action, "MORE_INFORMATION_REQUIRED")
    return {"final_status": status, "stage": "complete", "audit": _audit("final_decision", {"status": status})}


def build_stepwise_graph():
    builder = StateGraph(LoanState)
    stages = [
        ("application", intake_stage), ("documents", documents_stage), ("kyb", kyb_stage),
        ("bureau", bureau_stage), ("gst", gst_stage), ("cashflow", cashflow_stage),
        ("financials", financials_stage), ("fraud", fraud_stage), ("policy", policy_stage),
        ("memo", memo_stage), ("review", review_stage), ("decision", final_stage),
    ]
    for name, fn in stages:
        builder.add_node(name, fn)
    builder.add_edge(START, "application")
    for current, nxt in zip([x[0] for x in stages], [x[0] for x in stages][1:]):
        builder.add_edge(current, nxt)
    builder.add_edge("decision", END)
    return builder.compile(checkpointer=MemorySaver())


def start_or_resume(graph, config, state=None, resume=None):
    if resume is None:
        return graph.invoke(state, config)
    return graph.invoke(Command(resume=resume), config)
