# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""factory-boy factories for module 7 (documents).

Every factory produces a row in its lifecycle's `draft` step. A test that needs
a version in force walks it there with `put_in_force()`, through the recorded
transitions, never by assigning `workflow_state`.
"""
import factory
from django.utils import timezone

from accounts.tests.factories import UserFactory
from documents.constants import VERSION_IN_FORCE, VERSION_IN_REVIEW, DocumentType
from documents.models import AcknowledgementCampaign, Policy, PolicyVersion


class PolicyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Policy
        skip_postgeneration_save = True

    title = factory.Sequence(lambda n: f"Policy {n}")
    document_type = DocumentType.POLICY
    owner = factory.SubFactory(UserFactory)
    created_by = factory.SelfAttribute("owner")


class PolicyVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PolicyVersion

    policy = factory.SubFactory(PolicyFactory)
    version_label = factory.Sequence(lambda n: f"1.{n}")
    content = "<p>The organisation protects its information.</p>"
    change_summary = "Initial version."


class AcknowledgementCampaignFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AcknowledgementCampaign
        skip_postgeneration_save = True

    name = factory.Sequence(lambda n: f"Campaign {n}")
    policy_version = factory.SubFactory(PolicyVersionFactory)
    due_date = factory.LazyFunction(lambda: timezone.localdate() + timezone.timedelta(days=30))


def put_in_force(version, user=None):
    """Walk a draft version to `in_force` through its recorded transitions."""
    user = user or version.policy.owner or UserFactory()
    version.transition_to(VERSION_IN_REVIEW, user)
    version.transition_to(VERSION_IN_FORCE, user)
    version.refresh_from_db()
    return version
