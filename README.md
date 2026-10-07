# EXL Bank SME Loan Onboarding — V7 3-Layer UI

A digital-lending style UI inspired by the low-friction application experience of modern SME lenders, while retaining the project's banking-agent functionality.

## Three layers
- Customer Portal: eligibility, business details, dynamic document checklist/upload, assessment and status.
- Agent Control Tower: specialist-agent trace, evidence, typed tools, deterministic engines and checkpoint/audit state.
- Credit Officer: evidence pack, recommendation, HITL decision, credit memo and audit trail.

## Run
pip install -r requirements.txt
streamlit run streamlit_app.py

All external integrations are demo/mock adapters. Connect authorized production APIs/MCP servers separately.
