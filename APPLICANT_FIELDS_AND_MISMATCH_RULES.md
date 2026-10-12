# Applicant intake fields and document rules

The first page should capture the applicant-entered values below. The backend then checks these values against the uploaded documents and the synthetic database. A mismatch blocks progression and requests corrected details/documents.

## Required first-page fields
- Application ID (choose a seeded DEMO-APP-#### value for demo)
- Legal business name exactly as registered
- Entity type (Private Limited / LLP / Partnership / Proprietorship)
- Registered office address and PIN
- Business PAN
- GSTIN (if GST registered)
- CIN/LLPIN where applicable
- Promoter/director full legal name
- Promoter PAN
- Date of birth and role
- Ownership percentage
- Masked Aadhaar last four digits or accepted OVD reference where relevant (never store full Aadhaar)
- Loan amount requested, tenure, purpose, industry, business vintage
- Annual turnover, EBITDA, existing debt service and bank cashflow assumptions
- Consent for synthetic demo validation

## Mandatory uploads (8)
1. Business PAN card
2. Director / promoter PAN card
3. GST registration certificate
4. Business bank statement covering 12–36 months
5. P&L and balance sheet
6. Latest GSTR-1 filing
7. Latest ITR
8. Registered office address proof

## Mismatch rules
- PAN, GSTIN, promoter name, business legal name or ITR PAN mismatch: BLOCK and ask for corrected details / re-upload.
- Document missing, unreadable, wrong type or required field not extractable: BLOCK or REVIEW with specific re-upload instructions.
- Aadhaar/OVD: compare only masked/test reference values in demo; never store full Aadhaar. If a submitted accepted identity proof conflicts, request re-upload or authorized officer review.
- Approximate names are not auto-approved. Route close matches to manual review.
- Requested facility above indicative eligibility: show formula, eligible amount, excess amount and reason, then refer to credit officer; never silently approve or reduce amount.
- The Excel database and policy are synthetic demonstration artefacts, not real banking records or a binding credit offer.
