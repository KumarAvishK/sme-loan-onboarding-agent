from app.policy.engine import run_policy_engine


def test_policy_passes_demo_application():
    app = {
        "business_vintage_years": 8,
    }
    kyb = {"kyb_status": "PASS"}
    bureau = {"bureau_score": 748, "business_dpd": 0}
    gst = {"filings_current": True}
    financials = {"dscr_demo": 1.25}
    fraud = {"fraud_risk": "LOW"}
    result = run_policy_engine(app, kyb, bureau, gst, financials, fraud)
    assert result["outcome"] == "PASS"
