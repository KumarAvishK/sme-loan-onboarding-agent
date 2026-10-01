def run_policy_engine(app, kyb, bureau, gst, financials, fraud):
    checks = [
        {"rule": "Business vintage >= 3 years", "passed": app["business_vintage_years"] >= 3, "value": app["business_vintage_years"]},
        {"rule": "Bureau score >= 700", "passed": bureau["bureau_score"] >= 700, "value": bureau["bureau_score"]},
        {"rule": "Business DPD = 0", "passed": bureau["business_dpd"] == 0, "value": bureau["business_dpd"]},
        {"rule": "GST filings current", "passed": gst["filings_current"], "value": gst["filings_current"]},
        {"rule": "KYB PASS", "passed": kyb["kyb_status"] == "PASS", "value": kyb["kyb_status"]},
        {"rule": "Fraud risk not HIGH", "passed": fraud["fraud_risk"] != "HIGH", "value": fraud["fraud_risk"]},
        {"rule": "DSCR demo >= 1.20", "passed": financials["dscr_demo"] >= 1.20, "value": financials["dscr_demo"]},
    ]
    failed = [c for c in checks if not c["passed"]]
    return {"outcome": "REFER" if failed else "PASS", "checks": checks, "failed_rules": failed}
