"""Tests for the ISO 27005 risk assessment DOCX export."""

import io
import zipfile

import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory
from context.tests.factories import ScopeFactory
from reports.iso27005_report import generate_iso27005_report_docx
from risks.tests.factories import (
    ISO27005RiskFactory,
    RiskAcceptanceFactory,
    RiskAssessmentFactory,
    RiskCriteriaFactory,
    RiskFactory,
    RiskLevelFactory,
    RiskTreatmentPlanFactory,
    ScaleLevelFactory,
    ThreatFactory,
    VulnerabilityFactory,
)


pytestmark = pytest.mark.django_db


def _docx_text(content):
    """Extract text content from a DOCX bytes blob (concatenated XML text)."""
    zf = zipfile.ZipFile(io.BytesIO(content))
    xml = zf.read("word/document.xml").decode("utf-8")
    # Strip XML tags coarsely; good enough for substring assertions.
    import re
    return re.sub(r"<[^>]+>", " ", xml)


class TestIso27005DocxGenerator:
    def test_minimal_assessment_produces_valid_docx(self):
        user = UserFactory(is_superuser=True)
        assessment = RiskAssessmentFactory(name="Annual 2026")
        filename, content = generate_iso27005_report_docx(assessment, user)
        assert filename.endswith(".docx")
        assert assessment.reference in filename
        # DOCX is a ZIP archive containing word/document.xml.
        zf = zipfile.ZipFile(io.BytesIO(content))
        assert "word/document.xml" in zf.namelist()

    def test_includes_assessment_metadata(self):
        user = UserFactory(is_superuser=True)
        assessment = RiskAssessmentFactory(name="Phoenix")
        _, content = generate_iso27005_report_docx(assessment, user)
        text = _docx_text(content)
        assert "Phoenix" in text
        assert assessment.reference in text
        assert "Context" in text

    def test_includes_criteria_section(self):
        user = UserFactory(is_superuser=True)
        criteria = RiskCriteriaFactory(name="Standard 3x3")
        for i in range(1, 4):
            ScaleLevelFactory(criteria=criteria, scale_type="likelihood", level=i, name=f"L{i}")
            ScaleLevelFactory(criteria=criteria, scale_type="impact", level=i, name=f"I{i}")
        for i in range(1, 4):
            RiskLevelFactory(criteria=criteria, level=i, name=f"R{i}")
        criteria.rebuild_risk_matrix()

        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        _, content = generate_iso27005_report_docx(assessment, UserFactory(is_superuser=True))
        text = _docx_text(content)
        assert "Standard 3x3" in text
        assert "Likelihood scale" in text
        assert "Impact scale" in text
        assert "Risk matrix" in text

    def test_includes_threats_and_vulnerabilities(self):
        user = UserFactory(is_superuser=True)
        assessment = RiskAssessmentFactory()
        threat = ThreatFactory(name="MalwareInjection")
        vuln = VulnerabilityFactory(name="MissingMFA")
        ISO27005RiskFactory(
            assessment=assessment, threat=threat, vulnerability=vuln,
        )
        _, content = generate_iso27005_report_docx(assessment, user)
        text = _docx_text(content)
        assert "MalwareInjection" in text
        assert "MissingMFA" in text

    def test_includes_treatment_plans_and_acceptances(self):
        user = UserFactory(is_superuser=True)
        assessment = RiskAssessmentFactory()
        risk = RiskFactory(assessment=assessment, name="DataLeak")
        plan = RiskTreatmentPlanFactory(risk=risk, name="MitigationA")
        acceptance = RiskAcceptanceFactory(risk=risk, justification="Within tolerance")
        _, content = generate_iso27005_report_docx(assessment, user)
        text = _docx_text(content)
        assert "DataLeak" in text
        assert "MitigationA" in text
        assert acceptance.reference in text

    def test_handles_empty_collections_gracefully(self):
        user = UserFactory(is_superuser=True)
        assessment = RiskAssessmentFactory()
        _, content = generate_iso27005_report_docx(assessment, user)
        text = _docx_text(content)
        assert "No ISO 27005 analyses" in text
        assert "No consolidated risks" in text
        assert "No treatment plans" in text
        assert "No risk acceptances" in text


class TestIso27005ReportExportView:
    def _superuser(self):
        user = UserFactory(is_superuser=True, is_staff=True)
        client = Client()
        client.force_login(user)
        return client, user

    def test_login_required(self):
        assessment = RiskAssessmentFactory()
        resp = Client().get(
            reverse("risks:assessment-export-docx", args=[assessment.pk]),
        )
        assert resp.status_code == 302

    def test_superuser_can_export(self):
        client, user = self._superuser()
        assessment = RiskAssessmentFactory()
        resp = client.get(
            reverse("risks:assessment-export-docx", args=[assessment.pk]),
        )
        assert resp.status_code == 200
        assert resp["Content-Type"].startswith(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert resp["Content-Disposition"].startswith("attachment;")

        from reports.constants import ReportType
        from reports.models import Report
        assert Report.objects.filter(
            report_type=ReportType.ISO27005_REPORT, created_by=user,
        ).exists()

    def test_unknown_assessment_returns_404(self):
        import uuid
        client, _ = self._superuser()
        resp = client.get(
            reverse("risks:assessment-export-docx", args=[uuid.uuid4()]),
        )
        assert resp.status_code == 404

    def test_scope_filter_denies_outsider(self):
        scope_in = ScopeFactory()
        scope_out = ScopeFactory()

        assessment_in = RiskAssessmentFactory()
        assessment_in.scopes.add(scope_in)
        assessment_out = RiskAssessmentFactory()
        assessment_out.scopes.add(scope_out)

        from accounts.models import Group, Permission
        group = Group.objects.create(name="Test scope group")
        group.allowed_scopes.add(scope_in)
        for codename in ["risks.assessment.read", "risks.export.read"]:
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={
                    "name": codename, "module": codename.split(".")[0],
                    "feature": codename.split(".")[1],
                    "action": codename.split(".")[2],
                    "is_system": True,
                },
            )
            group.permissions.add(perm)

        user = UserFactory(is_superuser=False, is_staff=False)
        group.users.add(user)

        client = Client()
        client.force_login(user)

        resp = client.get(
            reverse("risks:assessment-export-docx", args=[assessment_in.pk]),
        )
        assert resp.status_code == 200

        resp = client.get(
            reverse("risks:assessment-export-docx", args=[assessment_out.pk]),
        )
        assert resp.status_code == 403


class TestIso27005ReportMCP:
    def setup_method(self):
        import json  # noqa: F401
        from mcp.server import McpServer
        from mcp.tools import register_all_tools
        self.srv = McpServer()
        register_all_tools(self.srv)
        self.user = UserFactory(is_superuser=True)

    def _call(self, name, arguments):
        import json
        result = self.srv.handle_request(json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }), self.user)
        return json.loads(result["result"]["content"][0]["text"])

    def test_tool_is_registered(self):
        assert "generate_iso27005_report" in self.srv._tools

    def test_generates_report(self):
        from reports.constants import ReportType
        from reports.models import Report
        assessment = RiskAssessmentFactory()
        result = self._call(
            "generate_iso27005_report",
            {"assessment_id": str(assessment.pk)},
        )
        assert "error" not in result, result
        assert result["report_type"] == ReportType.ISO27005_REPORT
        assert result["status"] == "completed"
        report = Report.objects.get(pk=result["id"])
        assert report.file_name.endswith(".docx")
        assert report.file_content

    def test_unknown_assessment_returns_error(self):
        import uuid
        result = self._call(
            "generate_iso27005_report",
            {"assessment_id": str(uuid.uuid4())},
        )
        assert "error" in result

    def test_missing_assessment_id_raises(self):
        result = self.srv.handle_request(
            __import__("json").dumps({
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "generate_iso27005_report", "arguments": {}},
            }),
            self.user,
        )
        # Either error in result body or JSON-RPC error envelope.
        assert "error" in result or result["result"]["isError"] is True
