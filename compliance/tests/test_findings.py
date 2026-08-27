# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from accounts.tests.factories import UserFactory
from context.tests.factories import ScopeFactory

from compliance.constants import (
    EffectivenessVerdict,
    FindingSource,
    FindingType,
    FINDING_REFERENCE_PREFIXES,
    FINDING_TYPE_COMPLIANCE_LEVEL,
)
from compliance.models import Finding
from .factories import (
    ComplianceAssessmentFactory,
    FindingFactory,
    FrameworkFactory,
    RequirementFactory,
)


@pytest.mark.django_db
class TestFindingModel:
    def test_create_finding(self):
        finding = FindingFactory()
        assert finding.pk is not None
        assert finding.reference.startswith("NCMAJ-")

    def test_reference_generation_by_type(self):
        """Each finding type generates a reference with the correct prefix."""
        assessment = ComplianceAssessmentFactory()
        for ft_value, prefix in FINDING_REFERENCE_PREFIXES.items():
            finding = FindingFactory(
                assessment=assessment,
                finding_type=ft_value,
            )
            assert finding.reference.startswith(f"{prefix}-"), (
                f"Expected {prefix}- prefix for {ft_value}, got {finding.reference}"
            )

    def test_reference_uniqueness(self):
        """References are unique and auto-increment."""
        f1 = FindingFactory(finding_type=FindingType.MAJOR_NON_CONFORMITY)
        f2 = FindingFactory(finding_type=FindingType.MAJOR_NON_CONFORMITY)
        assert f1.reference != f2.reference
        # Both start with NCMAJ-
        assert f1.reference.startswith("NCMAJ-")
        assert f2.reference.startswith("NCMAJ-")
        # Second should have a higher number
        num1 = int(f1.reference.split("-")[1])
        num2 = int(f2.reference.split("-")[1])
        assert num2 > num1

    def test_reference_across_types(self):
        """Different finding types have independent reference sequences."""
        f_major = FindingFactory(finding_type=FindingType.MAJOR_NON_CONFORMITY)
        f_obs = FindingFactory(finding_type=FindingType.OBSERVATION)
        assert f_major.reference.startswith("NCMAJ-")
        assert f_obs.reference.startswith("OBS-")

    def test_finding_requirements_m2m(self):
        """Findings can be linked to requirements."""
        fw = FrameworkFactory()
        assessment = ComplianceAssessmentFactory(framework=fw)
        req1 = RequirementFactory(framework=fw)
        req2 = RequirementFactory(framework=fw)
        finding = FindingFactory(assessment=assessment)
        finding.requirements.add(req1, req2)
        assert finding.requirements.count() == 2
        assert req1.findings.count() == 1

    def test_str_representation(self):
        finding = FindingFactory(finding_type=FindingType.OBSERVATION)
        assert "OBS-" in str(finding)

    def test_finding_type_compliance_level_mapping(self):
        """Verify compliance level mapping is complete."""
        for ft in FindingType:
            assert ft.value in FINDING_TYPE_COMPLIANCE_LEVEL, (
                f"Missing compliance level for {ft.value}"
            )

    def test_deleting_the_assessment_keeps_the_nonconformity(self):
        """A nonconformity survives the audit that raised it.

        It used to be CASCADE, from when a finding could only exist inside an
        audit. Now that this is the organisation's single nonconformity
        register, deleting an audit must not destroy the register entries it
        produced : that is the whole point of a register (RG-FND-03).
        """
        finding = FindingFactory()
        finding_pk = finding.pk

        finding.assessment.delete()

        finding.refresh_from_db()
        assert Finding.objects.filter(pk=finding_pk).exists()
        assert finding.assessment_id is None


@pytest.mark.django_db
class TestNonconformityRegister:
    """The register holds nonconformities from every source, not only audits."""

    def test_default_source_keeps_existing_rows_meaning_audit(self):
        assert FindingFactory().source == FindingSource.AUDIT

    def test_an_incident_born_nonconformity_needs_no_assessment(self):
        finding = Finding(
            source=FindingSource.INCIDENT,
            finding_type=FindingType.MINOR_NON_CONFORMITY,
            description="The joiner-mover-leaver procedure is not followed.",
        )

        finding.full_clean(exclude=["reference"])
        finding.save()

        assert finding.assessment_id is None
        assert finding.assessor_id is None
        assert finding.reference.startswith("NCMIN-")

    def test_an_audit_finding_still_requires_its_audit_and_its_author(self):
        finding = Finding(
            source=FindingSource.AUDIT,
            finding_type=FindingType.MAJOR_NON_CONFORMITY,
            description="Access reviews are not performed.",
        )

        with pytest.raises(ValidationError) as exc:
            finding.full_clean(exclude=["reference"])

        assert set(exc.value.message_dict) == {"assessment", "assessor"}

    def test_an_effectiveness_verdict_requires_its_review_date(self):
        finding = FindingFactory(effectiveness_verdict=EffectivenessVerdict.EFFECTIVE)

        with pytest.raises(ValidationError) as exc:
            finding.full_clean(exclude=["reference"])

        assert "effectiveness_reviewed_at" in exc.value.message_dict

    def test_effectiveness_is_recorded_on_the_nonconformity(self):
        finding = FindingFactory(
            effectiveness_verdict=EffectivenessVerdict.NOT_EFFECTIVE,
            effectiveness_reviewed_at=timezone.now(),
        )

        finding.full_clean(exclude=["reference"])

        assert finding.effectiveness_verdict == EffectivenessVerdict.NOT_EFFECTIVE

    def test_audit_scoring_never_sees_a_nonconformity_from_another_source(self):
        """The reverse accessor does the filtering, so no query has to remember.

        `apply_findings_to_results()` iterates `assessment.findings`, which is
        the reverse of a nullable FK : a nonconformity with no assessment can
        never appear in it (RG-FND-04).
        """
        assessment = ComplianceAssessmentFactory()
        FindingFactory(assessment=assessment)
        Finding.objects.create(
            source=FindingSource.INCIDENT,
            finding_type=FindingType.MAJOR_NON_CONFORMITY,
            description="Raised by an incident, belongs to no audit.",
        )

        assert assessment.findings.count() == 1
        assert Finding.objects.count() == 2


@pytest.fixture
def superuser(db):
    return UserFactory(is_superuser=True)


@pytest.mark.django_db
class TestNonconformityRegisterViews:
    """The register is reachable outside any audit, which is its whole point."""

    def test_register_lists_findings_from_every_source(self, client, superuser):
        client.force_login(superuser)
        audit_born = FindingFactory()
        incident_born = Finding.objects.create(
            source=FindingSource.INCIDENT,
            finding_type=FindingType.MAJOR_NON_CONFORMITY,
            description="Raised by an incident.",
        )

        html = client.get(reverse("compliance:finding-list")).content.decode()

        assert audit_born.reference in html
        assert incident_born.reference in html

    def test_a_nonconformity_without_an_audit_has_a_detail_page(self, client, superuser):
        client.force_login(superuser)
        finding = Finding.objects.create(
            source=FindingSource.MONITORING,
            finding_type=FindingType.OBSERVATION,
            description="Privileged access review skipped.",
        )

        response = client.get(reverse("compliance:finding-detail", args=[finding.pk]))

        assert response.status_code == 200
        assert finding.reference in response.content.decode()

    def test_raising_one_from_the_register_needs_no_assessment(self, client, superuser):
        client.force_login(superuser)

        response = client.post(
            reverse("compliance:finding-register-create"),
            {
                "source": FindingSource.COMPLAINT,
                "finding_type": FindingType.MINOR_NON_CONFORMITY,
                "description": "A customer received another customer's report.",
                "recommendation": "Add a recipient assertion.",
                "evidence": "",
                "effectiveness_verdict": "",
                "requirements": [],
            },
        )

        assert response.status_code in (200, 204, 302)
        raised = Finding.objects.get(source=FindingSource.COMPLAINT)
        assert raised.assessment_id is None
        assert raised.assessor_id == superuser.id

    def test_a_scoped_user_still_sees_nonconformities_that_have_no_audit(self):
        """The parent join must not drop parentless rows.

        `scope_parent_lookup` alone produces an INNER JOIN, which would hide
        every incident-born nonconformity from anyone but a superuser. That is
        why `Finding` sets `scope_parent_optional`.
        """
        from core.scoping import filter_queryset_by_scopes

        parentless = Finding.objects.create(
            source=FindingSource.INCIDENT,
            finding_type=FindingType.MAJOR_NON_CONFORMITY,
            description="No audit raised this one.",
        )
        scope = ScopeFactory()

        visible = filter_queryset_by_scopes(Finding.objects.all(), [scope.id])

        assert parentless in visible
