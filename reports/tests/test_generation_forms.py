# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The report generation forms say what came of a generation.

A generation used to land on the register without a word, a failure showing
only as a row reading *Failed*; the three buttons of the register all read
*Generate*; and the audit report form showed an empty picker when no
assessment was completed.
"""

from unittest.mock import patch

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse

from accounts.tests.factories import UserFactory
from compliance.tests.factories import FrameworkFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(client):
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    return user


def _said(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


class TestAGenerationSaysWhatCameOfIt:
    @patch("reports.views.generate_soa_pdf", return_value=("SoA.pdf", b"%PDF-1.4"))
    def test_a_generated_report_is_announced(self, _generate, client, admin):
        framework = FrameworkFactory(short_name="ISO 27001")

        response = client.post(reverse("reports:soa-create"), {"frameworks": [str(framework.pk)]}, follow=True)

        assert response.redirect_chain[-1][0] == reverse("reports:report-list")
        assert any("is generated : download it from the list" in text for text in _said(response))

    @patch("reports.views.generate_soa_pdf", side_effect=Exception("PDF error"))
    def test_a_failed_generation_says_so(self, _generate, client, admin):
        framework = FrameworkFactory()

        response = client.post(reverse("reports:soa-create"), {"frameworks": [str(framework.pk)]}, follow=True)

        assert any("could not be generated" in text for text in _said(response))


class TestTheRegisterAndItsForms:
    def test_each_button_names_what_it_generates(self, client, admin):
        html = client.get(reverse("reports:report-list")).content.decode()

        for label in ("Generate a Statement of Applicability", "Generate an audit report",
                      "Generate management review materials"):
            assert label in html, label

    def test_with_no_completed_assessment_the_audit_form_says_what_to_do_first(self, client, admin):
        html = client.get(reverse("reports:audit-report-create")).content.decode()

        assert "No assessment is completed yet." in html
        assert f'href="{reverse("compliance:assessment-list")}"' in html
        assert "Generate PDF" not in html
