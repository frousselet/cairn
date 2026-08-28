# Adding a report

Cairn generates PDF, DOCX, PPTX and XLSX deliverables : the Statement of
Applicability, the audit report, the risk register, management review minutes.
They are the artefacts that leave the platform and land in an auditor's inbox,
which sets the bar for what "done" means here.

## The libraries

| Format | Library | Used for |
| --- | --- | --- |
| PDF | WeasyPrint | Anything laid out as a document : the SoA, the audit report |
| XLSX | `openpyxl` | Tabular exports : the risk register |
| DOCX | `python-docx` | Editable deliverables |
| PPTX | `python-pptx` | Steering decks |

WeasyPrint renders **HTML and CSS**, which is the reason PDF generation here is
a template exercise rather than a drawing exercise. The report template is a
Django template like any other, and the print stylesheet is CSS.

## The shape of a generator

`reports/generators.py`, one function per deliverable, taking the domain objects
and the requesting user:

```python
def generate_supplier_attestation_pdf(supplier, user):
    """Render the supplier's attestation summary as a PDF."""
    html = render_to_string("reports/supplier_attestations.html", {
        "supplier": supplier,
        "attestations": reportable(supplier.attestations.all()),
        "generated_by": user,
        "generated_at": timezone.now(),
        "company": CompanySettings.objects.first(),
    })
    return HTML(string=html, base_url=settings.STATIC_ROOT).write_pdf()
```

Separate the **data** from the **rendering** when the data is non-trivial. The
SoA does this : `build_soa_frameworks_data(frameworks)` returns a structure, and
`generate_soa_pdf(frameworks, user)` renders it. That split is what makes the
data testable without parsing a PDF.

## Four things a report must get right

**Only reportable records.** Use `reportable()`, never a hardcoded status. A
report that counts draft rows is a report that disagrees with the dashboard, and
whichever one the auditor read first is the one you will be defending.

**The caller's perimeter.** A report is a read like any other. Filter by the
user's scopes; a PDF is an excellent way to exfiltrate a perimeter someone was
never granted.

**Provenance on the page.** Who generated it, when, from which version, for
which scope. A deliverable that does not say what it is a snapshot of cannot be
reconciled with anything later.

**Both languages.** Report templates are translated like every other template.
A French user generating an English deliverable is a defect.

## Registering it

`ReportType` in `reports/constants.py`, then wire the generator into
`reports/views.py` and the API. Add the matching
[MCP tool](mcp-tool.md) so an assistant can produce the deliverable too.

## Testing

Do not assert on PDF bytes. Test the data function directly, and for the
rendered output assert that generation succeeds and that the response carries
the right content type and filename.

```python
def test_soa_data_excludes_draft_frameworks():
    data = build_soa_frameworks_data(Framework.objects.all())
    assert draft_framework.name not in [f["name"] for f in data]


def test_report_respects_scope(client, user_in_one_scope):
    response = client.get(reverse("reports:soa-pdf"))
    assert response["Content-Type"] == "application/pdf"
```

The scope test is the one that earns its keep.

## Checklist

- [ ] Generator in `reports/generators.py`, data split from rendering if non-trivial
- [ ] Only `reportable()` records included
- [ ] Filtered by the caller's scopes
- [ ] Provenance rendered on the document
- [ ] Template translated, both languages checked
- [ ] `ReportType` entry added, view and API wired
- [ ] MCP tool added
- [ ] Tests cover the data function and the scope filtering
