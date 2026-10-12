# Streamlit Cloud startup and workflow hardening

This update addresses three failure-prone areas in the demo:

1. **Logo path**: the logo is resolved relative to `streamlit_app.py`, with an inline text-logo fallback if the SVG is missing.
2. **Chroma startup**: the vector retriever is initialized lazily and uses an in-memory collection. It no longer writes to `./chroma_sme_loan` or initializes a database merely by importing the app. If Chroma is unavailable or fails, retrieval falls back to deterministic keyword matching against the local synthetic policy snippets.
3. **Credit memo retrieval**: retrieval exceptions are caught, and the memo can continue using the supplied case evidence. The deterministic policy engine and human credit-officer decision remain unchanged.

## Deploy the updated package

1. Download and extract the ZIP.
2. Copy the contents of the `sme-loan-onboarding-agent` folder into the root of the GitHub repository (the folder containing `streamlit_app.py` and `requirements.txt`).
3. Commit and push the changes to the branch configured in Streamlit Community Cloud.
4. In Streamlit Cloud, open the app's menu and select **Reboot**. If the app still fails, open **View logs** and use the first traceback as the next diagnostic.

The test suite passed (7 tests) and Python compilation passed in the build environment. The app was not directly deployed or verified against the user's live Streamlit workspace from this environment.
