from app.validation.matrix import MANDATORY_DOCUMENTS, run_validation_matrix


def _uploaded(readable=True, omit=None):
    omitted = omit or set()
    return {
        "uploaded": {
            key: {"name": f"{key}.pdf", "size": 128, "type": "application/pdf"}
            for key, _ in MANDATORY_DOCUMENTS if key not in omitted
        },
        "readability_confirmed": readable,
    }


def test_clean_synthetic_case_unlocks_financial_analysis():
    app = {
        "application_id": "DEMO-APP-1001",
        "applicant_name": "ABC Distributors Private Limited",
        "entity_type": "Private Limited",
    }
    result = run_validation_matrix(app, _uploaded())
    assert result["summary"]["total"] == 33
    assert result["can_proceed"] is True
    assert result["summary"]["blocking"] == 0


def test_exception_synthetic_case_blocks_financial_analysis():
    app = {
        "application_id": "DEMO-APP-2002",
        "applicant_name": "XYZ Trading Solutions Private Limited",
        "entity_type": "Private Limited",
    }
    result = run_validation_matrix(app, _uploaded())
    assert result["can_proceed"] is False
    assert any(c["check"] == "GST registration number" and c["status"] == "BLOCKED" for c in result["checks"])


def test_missing_mandatory_document_blocks_gate():
    app = {
        "application_id": "DEMO-APP-1001",
        "applicant_name": "ABC Distributors Private Limited",
        "entity_type": "Private Limited",
    }
    result = run_validation_matrix(app, _uploaded(omit={"itr"}))
    assert result["can_proceed"] is False
    assert any(c["check"] == "All 8 mandatory documents" and c["status"] == "BLOCKED" for c in result["checks"])


def test_unrecognized_application_fails_closed():
    app = {
        "application_id": "LOCAL-APP-UNKNOWN",
        "applicant_name": "Example Private Limited",
        "entity_type": "Private Limited",
    }
    result = run_validation_matrix(app, _uploaded())
    assert result["can_proceed"] is False
    assert result["source_mode"] == "manual_unverified"
