"""The "Last modified by <user> on <date>" line in the detail-page header.

Rendered by the shared {% page_header %} tag (core.templatetags.ui) for any
BaseDetailView whose object is historised, just before the action buttons.
"""

import pytest
from django.urls import reverse

from accounts.tests.factories import UserFactory
from assets.tests.factories import SupplierFactory


@pytest.mark.django_db
class TestHeaderLastModified:
    def test_detail_header_shows_last_modified_by_user(self, client):
        editor = UserFactory(first_name="Sofia", last_name="Lindqvist")
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        s = SupplierFactory()
        # Attribute the latest history record to a user, as a real request would.
        s._history_user = editor
        s.save()
        html = client.get(reverse("assets:supplier-detail", kwargs={"pk": s.pk})).content.decode()
        assert "page-header__modified" in html
        assert "Last modified by" in html
        assert editor.display_name in html
        # The user component is the dashboard-style chip (solid-navy avatar).
        assert "user-badge--chip" in html

    def test_detail_header_fallback_without_user(self, client):
        # A history record with no attributed user (factory save) still yields the
        # date, shown via the "Last modified on <date>" fallback (no chip).
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        s = SupplierFactory()
        html = client.get(reverse("assets:supplier-detail", kwargs={"pk": s.pk})).content.decode()
        assert "page-header__modified" in html

    def test_no_leading_clock_icon(self, client):
        # The clock icon was dropped: it duplicated the evaluation-history button.
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        s = SupplierFactory()
        html = client.get(reverse("assets:supplier-detail", kwargs={"pk": s.pk})).content.decode()
        assert "page-header__modified-icon" not in html

    def test_list_header_has_no_last_modified(self, client):
        # Only detail pages (BaseDetailView) get the line, never list pages.
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        SupplierFactory()
        html = client.get(reverse("assets:supplier-list")).content.decode()
        # Check for the rendered element, not the class name or text (its CSS rule
        # and comment are inlined in base.html on every page).
        assert '<div class="page-header__modified">' not in html
