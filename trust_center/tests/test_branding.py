import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from accounts.models import CompanySettings
from accounts.tests.factories import UserFactory
from trust_center.models import TrustCenterSettings
from trust_center.sanitizers import clean_css, clean_html

pytestmark = pytest.mark.django_db


def _enable(**kwargs):
    s = TrustCenterSettings.get()
    s.is_published = True
    for key, value in kwargs.items():
        setattr(s, key, value)
    s.save()
    return s


# --- Rich-text rendering ----------------------------------------------------


def test_intro_html_is_rendered_and_sanitized():
    _enable(
        intro='<p>Hello <strong>world</strong></p><script>alert(1)</script>'
    )
    content = Client().get("/trust/").content
    assert b"<strong>world</strong>" in content  # rendered, not escaped
    assert b"&lt;strong&gt;" not in content
    assert b"<script>alert(1)" not in content  # stripped


def test_clean_html_allowlist():
    out = clean_html(
        '<p>ok</p><script>x</script>'
        '<a href="javascript:alert(1)">bad</a>'
        '<a href="https://example.test">good</a>'
        '<img src=x onerror=alert(1)>'
    )
    assert "<p>ok</p>" in out
    assert "script" not in out.lower()
    assert "javascript:" not in out.lower()
    assert "onerror" not in out.lower()
    assert "<img" not in out.lower()
    assert 'href="https://example.test"' in out
    assert "nofollow" in out


# --- Hero branding ----------------------------------------------------------


def test_hero_shows_company_name_and_data_uri_logo():
    company = CompanySettings.get()
    company.name = "ACME Industries"
    # Logos are stored as data-URI images (uploaded + resized), not inline SVG.
    company.logo_128 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg=="
    company.save()
    _enable(headline="Trust posture")
    content = Client().get("/trust/").content.decode()
    assert "ACME Industries" in content
    assert "tc-hero-brand" in content
    assert "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==" in content
    assert "<img" in content  # rendered as an <img>, not an empty white tile


def test_logo_html_handles_data_uri_svg_and_junk():
    from trust_center.sanitizers import logo_html

    assert logo_html("data:image/png;base64,AAAA").startswith("<img")
    assert "<svg" in logo_html('<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>')
    assert logo_html("javascript:alert(1)") == ""
    assert logo_html("") == ""


def test_favicon_and_theme_color_present():
    company = CompanySettings.get()
    company.logo_64 = "data:image/png;base64,AAAA"
    company.save()
    _enable(theme_accent="#123abc")
    content = Client().get("/trust/").content.decode()
    assert 'name="theme-color"' in content
    assert "#123abc" in content
    assert 'rel="icon"' in content


def test_header_line_removed():
    _enable()
    content = Client().get("/trust/").content.decode()
    assert "tc-header" not in content


# --- Document file-type icon ------------------------------------------------


def test_document_file_icon_by_extension():
    from trust_center.tests.factories import TrustCenterDocumentFactory

    assert TrustCenterDocumentFactory.build(file_name="soa.pdf").file_icon == "bi-filetype-pdf"
    assert TrustCenterDocumentFactory.build(file_name="minutes.docx").file_icon == "bi-filetype-docx"
    assert TrustCenterDocumentFactory.build(file_name="deck.pptx").file_icon == "bi-filetype-pptx"
    assert TrustCenterDocumentFactory.build(file_name="noext").file_icon == "bi-file-earmark-text"


def test_landing_shows_document_type_icon():
    from trust_center.tests.factories import TrustCenterDocumentFactory, publish

    _enable()
    publish(TrustCenterDocumentFactory(title="Security whitepaper", file_name="wp.pdf"))
    content = Client().get("/trust/").content.decode()
    assert "bi-filetype-pdf" in content


# --- Custom CSS -------------------------------------------------------------


def test_custom_css_injected_and_sanitized():
    _enable(custom_css="body { background: rebeccapurple; } </style><script>alert(1)</script>")
    content = Client().get("/trust/").content
    assert b"rebeccapurple" in content  # custom CSS present
    assert b"<script>alert(1)" not in content  # breakout neutralized


def test_clean_css_strips_dangerous_constructs():
    out = clean_css("a{} </style> @import url(evil); x{behavior:url(b)} expression(1) javascript:")
    lowered = out.lower()
    assert "</style" not in lowered
    assert "@import" not in lowered
    assert "expression(" not in lowered
    assert "javascript:" not in lowered
    assert "behavior:" not in lowered
    assert "a{}" in out  # benign CSS preserved


# --- CSS upload -------------------------------------------------------------


def test_settings_css_upload_populates_field():
    client = Client()
    client.force_login(UserFactory(is_superuser=True))
    css = b".tc-card { border-radius: 0; }"
    resp = client.post(
        "/trust-center/manage/settings/",
        {
            "headline": "",
            "intro": "",
            "contact_email": "",
            "theme_accent": "#1e3a8a",
            "custom_domain": "",
            "custom_css": "",
            "css_file": SimpleUploadedFile("theme.css", css, content_type="text/css"),
        },
    )
    assert resp.status_code == 302
    assert "border-radius: 0" in TrustCenterSettings.get().custom_css
