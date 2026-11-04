# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Notifications of module 8 (README §7).

Same contract as ``documents.notifications`` : one in-app row per recipient,
rendered in the recipient's language, created in the surrounding transaction,
delivered on commit.
"""

from django.urls import reverse
from django.utils.translation import gettext as _

from accounts.constants import NotificationType
from documents.notifications import _send


def notify_test_failed(run, control=None, actor=None):
    # The caller passes the control it just recomputed : `run.test.control`
    # may be a cached instance still holding the previous effectiveness.
    control = control or run.test.control
    recipients = [control.owner] if control.owner_id else []
    url = reverse("controls:controltestrun-detail", kwargs={"pk": run.pk})

    def render():
        return (
            _("Control test failed : %(control)s") % {"control": control.name},
            _("Run %(ref)s of %(test)s ended with the result \"%(result)s\". The control is now %(effectiveness)s.") % {
                "ref": run.reference, "test": run.test.name, "result": run.get_result_display(),
                "effectiveness": control.get_effectiveness_display().lower(),
            },
        )

    return _send(recipients, NotificationType.CONTROL_TEST_FAILED, run, url, render, actor=actor)


def notify_test_due(test, overdue):
    control = test.control
    recipients = [test.tester or control.owner]
    if overdue and control.owner_id:
        recipients.append(control.owner)
    url = reverse("controls:controltest-detail", kwargs={"pk": test.pk})
    kind = NotificationType.CONTROL_TEST_OVERDUE if overdue else NotificationType.CONTROL_TEST_DUE

    def render():
        values = {"test": test.name, "control": control.name, "date": test.next_due_date.isoformat()}
        if overdue:
            return (
                _("Control test overdue : %(test)s") % values,
                _("%(test)s (%(control)s) was due on %(date)s.") % values,
            )
        return (
            _("Control test due : %(test)s") % values,
            _("%(test)s (%(control)s) is due on %(date)s.") % values,
        )

    return _send(recipients, kind, test, url, render)
