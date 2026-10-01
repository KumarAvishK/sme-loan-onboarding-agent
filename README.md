# SME Loan Onboarding Agent

Agentic SME loan onboarding prototype using **LangGraph, RAG, ChromaDB, banking-domain tools, deterministic policy rules, and human-in-the-loop approval**.

> **Demo only:** This repository uses synthetic application data and mock banking integrations. It is not suitable for real lending decisions without institution-approved policies, models, controls, integrations, security, and compliance review.

## Architecture

```text
SME Application
      |
      v
LangGraph Orchestrator
      |
      +--> Application Intake
      +--> KYC / KYB
      +--> Credit Bureau
      +--> GST / Tax
      +--> Banking / Cash Flow
      +--> Financial Analysis
      +--> Fraud Checks
      +--> RAG / Credit Policy Knowledge
      |
      v
Deterministic Policy Engine
      |
      v
Credit Memo Agent
      |
      v
HITL Credit Officer
      |
      v
Final Decision
```

## Repository structure

```text
sme-loan-onboarding-agent/
├── notebooks/
│   └── 01_sme_loan_agent_v1.ipynb
├── app/
│   ├── agents/
│   ├── graph/
│   ├── llm/
│   ├── policy/
│   ├── rag/
│   └── tools/
├── tests/
├── data/
├── .env.example
├── .gitignore
├── requirements.txt
├── streamlit_app.py
└── README.md
```

## Run locally

### 1. Create environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2. Optional Claude setup

Copy `.env.example` to `.env` and add your Anthropic API key.

```text
ANTHROPIC_API_KEY=your_key
CLAUDE_MODEL=claude-sonnet-4-5
```

The demo can run without the API key using deterministic fallback text generation.

### 3. Run the notebook

```powershell
jupyter notebook
```

Open `notebooks/01_sme_loan_agent_v1.ipynb` and run top-to-bottom.

### 4. Run the Streamlit prototype

```powershell
streamlit run streamlit_app.py
```

## GitHub setup

Create an **empty** GitHub repository named `sme-loan-onboarding-agent` and then:

```powershell
git init -b main
git add .
git commit -m "Initial SME loan onboarding agent"
git remote add origin https://github.com/YOUR_USERNAME/sme-loan-onboarding-agent.git
git push -u origin main
```

Before `git add .`, confirm that `.env` is not being staged:

```powershell
git status
```

Never commit API keys, credentials, customer data, or production secrets.

## Deployment path

Recommended sequence:

1. **Local notebook** — validate the graph and domain logic.
2. **GitHub** — version the project and establish a clean repository.
3. **Streamlit** — deploy the demo UI from GitHub.
4. **FastAPI** — expose the graph as a service when the workflow stabilizes.
5. **PostgreSQL checkpointer** — replace in-memory checkpointing for multi-user use.
6. **Real APIs/MCP** — replace mock KYC, bureau, GST, banking and document tools.
7. **Production controls** — authentication, authorization, secrets management, audit logging, observability, encryption, policy governance and HITL controls.

## Next engineering milestones

- Add structured Pydantic schemas for every tool response.
- Separate agent prompts from orchestration code.
- Add idempotency keys to external calls.
- Add retry / timeout / circuit-breaker behavior around external systems.
- Add deterministic policy versioning.
- Add immutable audit events.
- Add evaluation datasets for memo quality and HITL precision.
- Add chaos tests for interrupted / failed tool calls.
- Add MCP servers for bureau and credit-memo capabilities.

## V2: Stepwise bank-style workflow

The Streamlit UI now follows a bank-style onboarding journey rather than executing the entire case from one button:

1. Application intake
2. Document submission
3. KYC / KYB verification
4. Credit bureau checks
5. GST / tax verification
6. Banking / cash-flow analysis
7. Financial analysis
8. Fraud / anomaly screening
9. Deterministic policy assessment
10. Credit memo generation
11. Credit officer HITL review
12. Final decision

The demo tools remain synthetic. Replace them with institution-approved APIs and controls before production use.
