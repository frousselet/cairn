# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
""""Today" is the day in the organisation's time zone, not the UTC day.

``timezone.now().date()`` is the UTC date. In Europe/Paris it is the previous
day for the first hour or two of every local day : during that window an action
plan due yesterday was not overdue yet, a contract ending yesterday had not
expired, and a completion was dated a day early. ``timezone.localdate()`` is
the business date.
"""

import datetime
import re
from pathlib import Path
from unittest import mock

import pytest
from django.conf import settings
from django.utils import timezone

# 00:30 in Paris on the 17th is still 23:30 on the 16th in UTC.
JUST_AFTER_MIDNIGHT = datetime.datetime(2026, 11, 16, 23, 30, tzinfo=datetime.timezone.utc)
YESTERDAY_LOCAL = datetime.date(2026, 11, 16)


@pytest.fixture
def just_after_midnight():
    with mock.patch("django.utils.timezone.now", return_value=JUST_AFTER_MIDNIGHT):
        assert timezone.localdate() == datetime.date(2026, 11, 17)
        yield


def test_an_action_plan_due_yesterday_is_overdue_from_midnight(just_after_midnight):
    from compliance.models import ComplianceActionPlan

    plan = ComplianceActionPlan(target_date=YESTERDAY_LOCAL)
    assert plan.is_overdue


def test_a_contract_ending_today_has_expired_from_midnight(just_after_midnight):
    from assets.constants import ContractStatus
    from assets.models import Contract

    contract = Contract(end_date=datetime.date(2026, 11, 17), status=ContractStatus.ACTIVE)
    assert contract.is_expired


@pytest.mark.django_db
def test_a_document_reviewed_just_after_midnight_is_reviewed_today():
    from accounts.tests.factories import UserFactory
    from documents.models.policy import add_months
    from documents.tests.factories import PolicyVersionFactory, put_in_force

    version = put_in_force(PolicyVersionFactory(effective_from=datetime.date(2025, 1, 31)))
    policy = version.policy
    policy.refresh_from_db()
    with mock.patch("django.utils.timezone.now", return_value=JUST_AFTER_MIDNIGHT):
        policy.record_review(UserFactory(), "Still accurate")
        # Twelve months from the 17th, the local day of the review, not the 16th.
        assert policy.next_review_date == add_months(datetime.date(2026, 11, 17), 12)


def test_no_application_code_takes_the_utc_date_for_today():
    """The two spellings that return the wrong day for part of every night."""
    pattern = re.compile(r"timezone\.now\(\)\.date\(\)|\bdate\.today\(\)|datetime\.now\(\)\.date\(\)")
    offenders = []
    for path in Path(settings.BASE_DIR).rglob("*.py"):
        parts = path.relative_to(settings.BASE_DIR).parts
        if parts[0] in {".venv", "scripts", "staticfiles"} or "tests" in parts or "migrations" in parts:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line) and not line.lstrip().startswith("#"):
                offenders.append(f"{path.relative_to(settings.BASE_DIR)}:{number}")
    assert not offenders, "use timezone.localdate() :\n" + "\n".join(offenders)
