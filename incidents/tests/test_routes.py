# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Every route in the module must render.

This exists because of what it caught the first time. The module's URLconf
was never mounted in `core/urls.py` and nineteen templates the views named
did not exist on disk, yet the whole suite was green: nothing exercised a
view. A missing mount is worse than a broken page, because the sidebar links
render on every page of the application, so `NoReverseMatch` took down the
dashboard, risks, compliance and assets too.

The test walks `incidents/urls.py` itself rather than listing routes by hand,
so a route added without a template fails here rather than in production.
"""
import pytest
from django.urls import NoReverseMatch, reverse
from django.urls.exceptions import Resolver404

from accounts.tests.factories import UserFactory
from incidents.tests.factories import (
    EvidenceCustodyEventFactory,
    IncidentEvidenceFactory,
    IncidentFactory,
    IncidentNotificationFactory,
    IncidentResponseActionFactory,
    IncidentResponsePlanFactory,
    IncidentTimelineEntryFactory,
    NotificationFilingFactory,
    PersonalDataBreachFactory,
    PostIncidentReviewFactory,
    ReportingAuthorityFactory,
    ReportingObligationTemplateFactory,
    SecurityEventFactory,
)


def _route_names():
    from incidents import urls as incident_urls

    return [p.name for p in incident_urls.urlpatterns if getattr(p, "name", None)]


ROUTE_NAMES = _route_names()


@pytest.fixture
def world(db):
    """One of everything, so any route's arguments can be filled."""
    incident = IncidentFactory()
    evidence = IncidentEvidenceFactory(incident=incident)
    notification = IncidentNotificationFactory(incident=incident)
    IncidentTimelineEntryFactory(incident=incident)
    IncidentResponseActionFactory(incident=incident)
    EvidenceCustodyEventFactory(evidence=evidence)
    NotificationFilingFactory(notification=notification)
    return {
        "incident": incident,
        "evidence": evidence,
        "notification": notification,
        "event": SecurityEventFactory(),
        "plan": IncidentResponsePlanFactory(),
        "review": PostIncidentReviewFactory(incident=IncidentFactory()),
        "breach": PersonalDataBreachFactory(incident=IncidentFactory()),
        "authority": ReportingAuthorityFactory(),
        "template": ReportingObligationTemplateFactory(),
    }


def _candidate_args(world):
    """Every object a `<uuid:pk>` route might be about, most specific first."""
    return [
        world["incident"], world["event"], world["plan"], world["notification"],
        world["evidence"], world["review"], world["breach"],
        world["authority"], world["template"],
    ]


@pytest.mark.django_db
@pytest.mark.parametrize("name", ROUTE_NAMES)
@pytest.mark.parametrize("htmx", [False, True], ids=["plain", "htmx"])
def test_route_renders(client, world, name, htmx):
    """A GET on every route must not raise, on both the page and drawer paths.

    `template_name` and `modal_template_name` are different files; only the
    HX-Request pass renders the second, which is where the missing drawer
    shells hid.
    """
    client.force_login(UserFactory(is_superuser=True))
    headers = {"HTTP_HX_REQUEST": "true"} if htmx else {}

    url = None
    for kwargs in (
        {},
        {"pk": world["incident"].pk},
        {"incident_pk": world["incident"].pk},
        {"notification_pk": world["notification"].pk},
        {"evidence_pk": world["evidence"].pk},
    ):
        try:
            url = reverse(f"incidents:{name}", kwargs=kwargs)
            break
        except NoReverseMatch:
            continue
    if url is None:
        pytest.fail(f"incidents:{name} takes arguments this test does not know how to fill")

    try:
        response = client.get(url, **headers)
    except Resolver404:  # pragma: no cover - a route that 404s by design
        return

    assert response.status_code < 500, (
        f"incidents:{name} returned {response.status_code}"
    )


@pytest.mark.django_db
def test_every_detail_route_finds_its_own_object(client, world):
    """A `<uuid:pk>` route must render the object it is actually about.

    The generic pass above fills every pk with the incident, which resolves
    for routes whose model is something else only because the view 404s. This
    walks each object to its own detail page and demands a 200.
    """
    client.force_login(UserFactory(is_superuser=True))
    pairs = [
        ("incident-detail", world["incident"]),
        ("event-detail", world["event"]),
        ("response-plan-detail", world["plan"]),
        ("notification-detail", world["notification"]),
        ("evidence-detail", world["evidence"]),
        ("review-detail", world["review"]),
        ("breach-detail", world["breach"]),
        ("reporting-authority-detail", world["authority"]),
        ("obligation-template-detail", world["template"]),
    ]

    for name, obj in pairs:
        url = reverse(f"incidents:{name}", kwargs={"pk": obj.pk})
        assert client.get(url).status_code == 200, f"incidents:{name} did not render"


@pytest.mark.django_db
def test_the_module_is_mounted_so_the_sidebar_resolves(client):
    """The sidebar renders on every page, so an unmounted URLconf breaks all of them."""
    client.force_login(UserFactory(is_superuser=True))

    assert reverse("incidents:incident-list") == "/incidents/"
    assert client.get("/").status_code < 500
