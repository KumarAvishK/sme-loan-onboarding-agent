from typing import Any, Dict, List, TypedDict, Annotated
import operator


class LoanState(TypedDict, total=False):
    application: Dict[str, Any]
    request: str
    stage: str
    documents: Dict[str, Any]
    kyb: Dict[str, Any]
    bureau: Dict[str, Any]
    gst: Dict[str, Any]
    cashflow: Dict[str, Any]
    financials: Dict[str, Any]
    fraud: Dict[str, Any]
    rag_context: str
    agent_findings: Dict[str, Any]
    policy_result: Dict[str, Any]
    credit_memo: str
    hitl_decision: Dict[str, Any]
    final_status: str
    audit: Annotated[List[Dict[str, Any]], operator.add]
