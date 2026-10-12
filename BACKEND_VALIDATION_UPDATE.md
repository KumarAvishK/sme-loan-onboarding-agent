# EXL Bank backend validation update

This package is based on the uploaded V6 EXL Bank UI codebase and adds a matrix-driven validation gate.

## What changed
- Added `app/validation/matrix.py` to evaluate the 33 rows in the validation master matrix.
- Added the master matrix and synthetic registry under `data/`.
- Replaced the older entity/loan-purpose-specific document list with exactly 8 mandatory and 4 optional documents.
- Added validation results to the Financial Analysis screen.
- Added a fail-closed check inside the LangGraph financial-analysis node so direct stage calls cannot bypass the gate.
- Added tests for the clean demo case, mismatch case, missing documents and unknown application IDs.
- Reduced document audit logging to counts rather than uploaded file names.

## Local test
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
streamlit run streamlit_app.py
```

## Synthetic scenarios
Use application ID `DEMO-APP-1001` with legal business name `ABC Distributors Private Limited` and entity type `Private Limited` for the clean synthetic scenario. Use `DEMO-APP-2002` with `XYZ Trading Solutions Private Limited` for the intentional mismatch scenario. Upload all eight mandatory files and confirm the demo legibility attestation.

## Important limitations
The uploaded files are not parsed by OCR in this version. The legibility checkbox is a demo attestation, not an authenticity check. The Excel registry is synthetic and does not query government or financial institutions. Unknown IDs remain blocked pending approved verification adapters. Do not use this prototype to make real lending decisions or process real customer identity data.
