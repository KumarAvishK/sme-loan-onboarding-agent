from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

from app.agents.nodes import (
    intake_node, kyb_node, bureau_node, gst_node, cashflow_node,
    financial_node, fraud_node, rag_node, policy_node,
    credit_memo_node, human_review_node, final_decision_node,
)
from app.models import LoanState
from app.sample_data import APPLICATION


def build_graph():
    builder = StateGraph(LoanState)
    nodes = {
        "intake": intake_node, "kyb": kyb_node, "bureau": bureau_node,
        "gst": gst_node, "cashflow": cashflow_node, "financial": financial_node,
        "fraud": fraud_node, "rag": rag_node, "policy": policy_node,
        "credit_memo": credit_memo_node, "human_review": human_review_node,
        "final_decision": final_decision_node,
    }
    for name, node in nodes.items():
        builder.add_node(name, node)

    builder.add_edge(START, "intake")
    for name in ["kyb", "bureau", "gst", "cashflow", "financial", "fraud", "rag"]:
        builder.add_edge("intake", name)
        builder.add_edge(name, "policy")
    builder.add_edge("policy", "credit_memo")
    builder.add_edge("credit_memo", "human_review")
    builder.add_edge("human_review", "final_decision")
    builder.add_edge("final_decision", END)
    return builder.compile(checkpointer=MemorySaver())


def run_demo_application():
    graph = build_graph()
    config = {"configurable": {"thread_id": APPLICATION["application_id"]}}
    initial_state = {
        "application": APPLICATION,
        "request": "Assess this SME working-capital loan application.",
        "audit": [],
    }
    graph.invoke(initial_state, config)
    # Demo HITL action; production UI should collect this from an authorized reviewer.
    # Resume the graph after the demo HITL interrupt. In production, this
    # payload should come from an authenticated/authorized credit officer.
    graph.invoke(Command(resume={
        "action": "approve",
        "comment": "Demo credit officer reviewed the evidence.",
        "reviewer": "demo_credit_officer",
    }), config)
    state = graph.get_state(config).values
    return {
        "application_id": APPLICATION["application_id"],
        "policy_outcome": state["policy_result"]["outcome"],
        "final_status": state.get("final_status"),
        "bureau_score": state["bureau"]["bureau_score"],
        "credit_memo": state["credit_memo"],
        "audit": state.get("audit", []),
        "llm_used": bool(__import__("os").getenv("ANTHROPIC_API_KEY")),
    }
