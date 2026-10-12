from app.validation.document_intelligence import parse_document, norm
def test_parse_pan_document():
    t="Business PAN Card\nEntity\nABC Distributors Private Limited\nPAN\nAABCA1234K\n"
    d=parse_document("business_pan",t)
    assert d["business_name"]=="ABC Distributors Private Limited"
    assert d["business_pan"]=="AABCA1234K"
def test_normalization():
    assert norm("ABC Distributors Pvt. Ltd.") == norm("ABC Distributors Pvt Ltd")
