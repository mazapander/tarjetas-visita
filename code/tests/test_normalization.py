from tarjetasvisita.normalization import extract_emails, extract_phone_numbers, extract_urls, normalize_phone


def test_extract_contact_methods():
    text = "Email: Ander@Test.COM Tel: +34 600 123 456 web www.example.com"

    assert extract_emails(text) == ["ander@test.com"]
    assert extract_phone_numbers(text) == ["+34600123456"]
    assert extract_urls(text) == ["https://www.example.com"]
    assert normalize_phone("+34 600 123 456") == "+34600123456"
