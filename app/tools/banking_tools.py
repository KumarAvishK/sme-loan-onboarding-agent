from langchain_core.tools import tool
from app.sample_data import APPLICATION


@tool
def verify_kyb(application_id: str) -> dict:
    """Mock KYB verification."""
    return {
        "kyb_status": "PASS",
        "pan_verified": True,
        "gstin_verified": True,
        "entity_verified": True,
        "ownership_check": "PASS",
        "screening": "CLEAR",
    }


@tool
def get_credit_bureau(application_id: str) -> dict:
    """Mock business/promoter credit bureau result."""
    return {
        "bureau_score": APPLICATION["bureau_score"],
        "business_dpd": APPLICATION["business_dpd"],
        "promoter_dpd": APPLICATION["promoter_dpd"],
        "recent_enquiries": APPLICATION["recent_bureau_enquiries"],
        "outstanding_exposure": APPLICATION["existing_debt"],
    }


@tool
def get_gst_data(application_id: str) -> dict:
    """Mock GST summary."""
    variance = (APPLICATION["gst_turnover"] - APPLICATION["annual_turnover"]) / APPLICATION["annual_turnover"]
    return {
        "gst_turnover": APPLICATION["gst_turnover"],
        "filings_current": APPLICATION["gst_filings_current"],
        "turnover_variance_pct": round(variance, 4),
    }


@tool
def get_bank_cashflow(application_id: str) -> dict:
    """Mock consented banking/cash-flow summary."""
    surplus = APPLICATION["avg_monthly_business_inflows"] - APPLICATION["avg_monthly_business_outflows"]
    return {
        "avg_monthly_inflows": APPLICATION["avg_monthly_business_inflows"],
        "avg_monthly_outflows": APPLICATION["avg_monthly_business_outflows"],
        "cashflow_volatility": APPLICATION["cashflow_volatility"],
        "monthly_surplus": surplus,
    }


@tool
def calculate_financial_metrics(application_id: str) -> dict:
    """Deterministic financial metrics; demo thresholds only."""
    current_ratio = APPLICATION["current_assets"] / APPLICATION["current_liabilities"]
    debt_to_ebitda = APPLICATION["existing_debt"] / APPLICATION["annual_ebitda"]
    proposed_debt_service = APPLICATION["requested_amount"] / (APPLICATION["tenure_months"] / 12)
    dscr = APPLICATION["annual_ebitda"] / (
        APPLICATION["annual_interest"] + APPLICATION["annual_principal"] + proposed_debt_service
    )
    return {
        "current_ratio": round(current_ratio, 2),
        "debt_to_ebitda": round(debt_to_ebitda, 2),
        "annual_ebitda": APPLICATION["annual_ebitda"],
        "dscr_demo": round(dscr, 2),
    }


@tool
def run_fraud_checks(application_id: str) -> dict:
    """Mock deterministic fraud/anomaly checks."""
    return {
        "fraud_risk": "LOW" if not APPLICATION["fraud_flags"] else "HIGH",
        "flags": APPLICATION["fraud_flags"],
    }
