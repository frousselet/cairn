# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
import datetime

import factory

from accounts.tests.factories import UserFactory
from context.constants import (
    ImpactLevel,
    IssueCategory,
    IssueType,
    ObjectiveCategory,
    ObjectiveStatus,
    ObjectiveType,
    SwotQuadrant,
    SwotStrategyQuadrant,
)
from context.constants import SiteType
from context.models.activity import Activity
from context.models.indicator import Indicator
from context.models.issue import Issue
from context.models.objective import Objective
from context.models.role import Responsibility, Role
from context.models.scope import Scope
from context.models.site import Site
from context.models.stakeholder import Stakeholder, StakeholderExpectation
from context.models.stakeholder_feedback import StakeholderFeedback
from context.models.swot import SwotAnalysis, SwotItem, SwotStrategy


class ScopeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Scope

    name = factory.Sequence(lambda n: f"Scope {n}")
    description = "Test scope"


class SiteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Site
        skip_postgeneration_save = True  # the hooks below only set relations

    name = factory.Sequence(lambda n: f"Site {n}")
    type = SiteType.OFFICE

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.add(*extracted)


class IssueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Issue
        skip_postgeneration_save = True  # the hooks below only set relations

    name = factory.Sequence(lambda n: f"Issue {n}")
    type = IssueType.INTERNAL
    category = IssueCategory.STRATEGIC
    impact_level = ImpactLevel.MEDIUM

    @factory.post_generation
    def scope(self, create, extracted, **kwargs):
        """Accept scope= for backwards compatibility, adds to scopes M2M."""
        if not create:
            return
        if extracted:
            self.scopes.add(extracted)

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.add(*extracted)


class StakeholderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Stakeholder
        skip_postgeneration_save = True  # the hook below only sets relations

    name = factory.Sequence(lambda n: f"Stakeholder {n}")
    type = IssueType.EXTERNAL
    category = "customers"
    influence_level = "medium"
    interest_level = "medium"

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.add(*extracted)


class StakeholderFeedbackFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StakeholderFeedback
        skip_postgeneration_save = True  # the hook below only sets relations

    stakeholder = factory.SubFactory(StakeholderFactory)
    channel = "survey"
    received_date = datetime.date(2026, 10, 1)
    subject = factory.Sequence(lambda n: f"Feedback {n}")
    content = "What the stakeholder said."

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.set(extracted)


class StakeholderExpectationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StakeholderExpectation

    stakeholder = factory.SubFactory(StakeholderFactory)
    description = factory.Sequence(lambda n: f"Expectation {n}")
    type = "expectation"
    priority = "medium"


class RoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Role
        skip_postgeneration_save = True  # the hook below only sets relations

    name = factory.Sequence(lambda n: f"Role {n}")
    type = "governance"

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.add(*extracted)


class ResponsibilityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Responsibility

    role = factory.SubFactory(RoleFactory)
    description = factory.Sequence(lambda n: f"Responsibility {n}")
    raci_type = "responsible"


class ActivityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Activity
        skip_postgeneration_save = True  # the hook below only sets relations

    name = factory.Sequence(lambda n: f"Activity {n}")
    type = "core_business"
    criticality = "medium"
    owner = factory.SubFactory(UserFactory)

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.add(*extracted)


class IndicatorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Indicator
        skip_postgeneration_save = True  # the hook below only sets relations

    name = factory.Sequence(lambda n: f"Indicator {n}")
    indicator_type = "organizational"
    collection_method = "manual"
    format = "number"
    review_frequency = "monthly"
    first_review_date = factory.LazyFunction(lambda: datetime.date.today() + datetime.timedelta(days=30))

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.add(*extracted)


class SwotAnalysisFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SwotAnalysis
        skip_postgeneration_save = True  # the hooks below only set relations

    name = factory.Sequence(lambda n: f"SWOT Analysis {n}")
    description = "Test SWOT analysis"
    analysis_date = factory.LazyFunction(datetime.date.today)

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.add(*extracted)


class SwotItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SwotItem

    swot_analysis = factory.SubFactory(SwotAnalysisFactory)
    quadrant = SwotQuadrant.STRENGTH
    description = factory.Sequence(lambda n: f"SWOT item {n}")
    impact_level = ImpactLevel.MEDIUM


class SwotStrategyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SwotStrategy

    swot_analysis = factory.SubFactory(SwotAnalysisFactory)
    quadrant = SwotStrategyQuadrant.SO
    description = factory.Sequence(lambda n: f"SWOT strategy {n}")


class ObjectiveFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Objective
        skip_postgeneration_save = True  # saved explicitly below

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        """Save once the scopes are set : `Objective.save()` checks that a
        child shares a scope with its parent, which it can only do then."""
        super()._after_postgeneration(instance, create, results)
        if create and results:
            instance.save()

    reference = factory.Sequence(lambda n: f"OBJ-{n:03d}")
    name = factory.Sequence(lambda n: f"Objective {n}")
    category = ObjectiveCategory.CONFIDENTIALITY
    type = ObjectiveType.SECURITY
    owner = factory.SubFactory(UserFactory)
    status = ObjectiveStatus.ACTIVE

    @factory.post_generation
    def scope(self, create, extracted, **kwargs):
        """Accept scope= for backwards compatibility, adds to scopes M2M."""
        if not create:
            return
        if extracted:
            self.scopes.add(extracted)

    @factory.post_generation
    def scopes(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.scopes.add(*extracted)
