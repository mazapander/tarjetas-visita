from tarjetasvisita.extraction import extract_contact_entities_rule_based


def test_extract_business_card_entities():
    text = """ANDER FERNANDEZ
Product Manager
ACME SOLUTIONS S.L.
ander@acme.com
+34 600 123 456
www.acme.com
Calle Mayor 1
48001 Bilbao
"""

    contacts = extract_contact_entities_rule_based(text, document_id="doc-1", source_file="card.txt")

    assert len(contacts) == 1
    contact = contacts[0]
    assert contact.full_name == "ANDER FERNANDEZ"
    assert contact.company == "ACME SOLUTIONS S.L."
    assert contact.job_title == "Product Manager"
    assert contact.website == "https://www.acme.com"
    assert contact.postal_code == "48001"
    assert any(method.method_type == "email" and method.normalized_value == "ander@acme.com" for method in contact.contact_methods)
    assert any(method.normalized_value == "+34600123456" for method in contact.contact_methods)
