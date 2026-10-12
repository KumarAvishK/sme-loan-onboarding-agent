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

## V3 workflow architecture

V3 separates user navigation from LangGraph execution. Streamlit controls the applicant/credit-officer journey, while each LangGraph invocation executes exactly one specialist stage. The only LangGraph interrupt is the genuine credit-officer HITL checkpoint.

Flow: Application → Documents → KYC/KYB → Bureau → GST → Cash Flow → Financials → Fraud → Policy → Credit Memo → Credit Officer → Decision.

## V4: Specific document requirement engine

The Documents stage now generates a tailored checklist from the application profile instead of asking for a generic set of files. It covers entity-specific legal documents, promoter/director/partner KYC, address proof, ownership/authority, GST and tax filings, financials, banking records, and loan-purpose documents.

Examples:
- Private Limited: PAN, Certificate of Incorporation, MOA, AOA, shareholding pattern, board borrowing authority, director PAN/KYC, UBO declaration.
- LLP: incorporation certificate, LLP Agreement, partner details/PAN/KYC, UBO declaration.
- Partnership: Partnership Deed, partner authority, partner PAN/KYC, UBO declaration.
- Proprietorship: business/proprietor PAN and proprietor KYC.
- Address: registered/business premises proof with acceptable alternatives.
- Tax: GST Registration Certificate/GSTIN proof, GSTR-1, GSTR-3B and applicable ITR.
- Banking: 12-month business bank statements and existing borrowing documents.
- Purpose-specific: receivables/payables and stock for working capital; vendor quotation/project cost for capex; project report/projected financials for expansion.

The Continue button remains disabled until every mandatory requirement has an uploaded file. Production should replace this demo ruleset with the bank's approved document policy and add OCR/classification, document authenticity checks, expiry checks, cross-document reconciliation and exception/HITL handling.


## V6 validation matrix integration

The backend now loads `data/EXL_Bank_SME_Loan_Validation_Master_Matrix.xlsx` and returns 33 row-level checks. Financial Analysis is fail-closed: any unresolved blocking CRITICAL/REVIEW check prevents the financial node from running.

### Mandatory document checklist (8)

1. Business PAN Card
2. Director / Promoter PAN Card
3. GST Registration Certificate
4. Business Bank Statement (12–36 months, as configured)
5. Financial Statements (P&L + Balance Sheet)
6. Latest GSTR-1 Filing
7. Latest ITR
8. Business Registered Office Address Proof

Optional supporting files: Receivables and Payables Ageing; Stock / Inventory Statement; Existing Loan Sanction; Shareholding Pattern.

### Synthetic local test cases

- `DEMO-APP-1001` — expected clean validation case. Use legal name `ABC Distributors Private Limited` and entity type `Private Limited`.
- `DEMO-APP-2002` — expected exception case. The fixture intentionally contains GSTIN and promoter PAN mismatches; Financial Analysis must remain locked.

For either test, upload all eight mandatory files in the Documents stage and confirm the demo legibility attestation. The synthetic identity/tax values are fixture data and do not prove the uploaded documents contain those values. No external portals are queried.

### Validation limitations and production requirements

- This version validates uploaded-file presence/type metadata and exercises field-level matching against a synthetic Excel registry. The legibility checkbox is a demo attestation; OCR, authenticity, expiry, signature, tampering and content extraction are not automated.
- Unknown application IDs fail closed because no approved source has verified the identity/tax fields. Configure a bank-approved extraction and verification adapter before production.
- Replace the mock registry with authorized, consented PAN/GST/MCA/KYC, bureau and banking integrations. Do not use this workbook for real identity verification.
- LLM outputs are assistive; deterministic rules and authorized credit-officer approval remain the controls for binding decisions.

### Run validation tests

```powershell
pytest -q
```


## Synthetic document intelligence update

This version extracts embedded text from uploaded PDFs using `pypdf`, reconciles selected fields to `data/EXL_Bank_Synthetic_Customer_Database.xlsx`, blocks mismatches, and estimates indicative repayment capacity. Scanned PDFs without text are routed for re-upload/manual review (OCR requires a separately configured OCR engine). All database records and policy terms are fictional. The attached policy letter is not a real bank offer. See `APPLICANT_FIELDS_AND_MISMATCH_RULES.md`.
