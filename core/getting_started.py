# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The first steps of a new instance.

A fresh instance used to open on an empty dashboard that read "Nothing urgent
today - everything is in order" : true, and of no help to someone who has
never used the product. Until the instance holds its first records, the
dashboard opens on a short list of what to do first, in the order the work is
done : say what is covered, list what matters, list what it relies on, choose
what to comply with, assess the risks, bring the colleagues in.

A step is done when the instance holds the thing, whoever created it : the
list describes the instance, not the reader. Each reader sees the steps they
may open, and may hide the list for themselves (``User.dismissed_helpers``)
and bring it back from the dashboard header. Once every step is done the list
is gone for good : the answer is kept for the life of the process, so a
running instance pays nothing for it.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.apps import apps
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

#: Key under which a reader's "hide the first steps" is kept.
DISMISS_KEY = "getting_started"

# Sticky per process : an instance that has taken every step is started.
_instance_started = False


def reset_getting_started_state():
    """Forget the cached answer (used by tests)."""
    global _instance_started
    _instance_started = False


def _exists(app_label, model_name):
    def check():
        return apps.get_model(app_label, model_name)._default_manager.exists()

    return check


def _several_people():
    User = apps.get_model("accounts", "User")
    return User._default_manager.filter(is_active=True).count() > 1


@dataclass(frozen=True)
class FirstStep:
    """One thing to do first.

    ``title`` is the act, ``why`` one sentence a newcomer understands,
    ``url_name`` the page where it is done, ``read`` the permission that page
    asks for (the step is shown to who holds it) and ``act`` the permission
    the act itself asks for (without it the step is shown, with no button).
    """

    key: str
    title: str
    why: str
    icon: str
    url_name: str
    read: str
    act: str
    done: callable


STEPS = (
    FirstStep(
        "scope",
        _("Define a scope"),
        _("A scope is what your security work applies to : the whole company, one site or one activity. Every other record is filed under a scope."),
        "diagram-3", "context:scope-list", "context.scope.read", "context.scope.create",
        _exists("context", "Scope"),
    ),
    FirstStep(
        "essential_asset",
        _("List the essential assets"),
        _("Your essential assets : the information you hold and the activities you run, such as the customer file, payroll or production."),
        "gem", "assets:essential-asset-list", "assets.essential_asset.read", "assets.essential_asset.create",
        _exists("assets", "EssentialAsset"),
    ),
    FirstStep(
        "support_asset",
        _("List the support assets"),
        _("Your support assets : the systems, premises and suppliers your essential assets depend on."),
        "hdd-stack", "assets:support-asset-list", "assets.support_asset.read", "assets.support_asset.create",
        _exists("assets", "SupportAsset"),
    ),
    FirstStep(
        "framework",
        _("Choose a framework"),
        _("A framework is a standard or a regulation, ISO 27001 for instance : its requirements become the list you work through."),
        "clipboard-check", "compliance:framework-list", "compliance.framework.read", "compliance.framework.create",
        _exists("compliance", "Framework"),
    ),
    FirstStep(
        "risk_assessment",
        _("Start a risk assessment"),
        _("What could go wrong for your essential assets, how likely it is, and what you decide to do about it."),
        "shield-exclamation", "risks:assessment-list", "risks.assessment.read", "risks.assessment.create",
        _exists("risks", "RiskAssessment"),
    ),
    FirstStep(
        "team",
        _("Add users"),
        _("Security is not one person's job : give everyone involved an account and a role."),
        "people", "accounts:user-list", "system.users.read", "system.users.create",
        _several_people,
    ),
)


def is_dismissed(user):
    dismissed = getattr(user, "dismissed_helpers", None)
    return isinstance(dismissed, list) and DISMISS_KEY in dismissed


def set_dismissed(user, hidden):
    """Hide the first steps for ``user``, or bring them back."""
    dismissed = user.dismissed_helpers if isinstance(user.dismissed_helpers, list) else []
    if hidden and DISMISS_KEY not in dismissed:
        dismissed = [*dismissed, DISMISS_KEY]
    elif not hidden and DISMISS_KEY in dismissed:
        dismissed = [key for key in dismissed if key != DISMISS_KEY]
    else:
        return
    user.dismissed_helpers = dismissed
    user.save(update_fields=["dismissed_helpers"])


def first_steps_for(user):
    """What the dashboard shows of the first steps to ``user``, or ``None``.

    ``None`` once the instance has taken every step. Otherwise a dict :
    ``steps`` (the ones the user may open, each with ``done``, ``url``,
    ``can_act`` and ``is_next``), ``done`` / ``total`` over those, ``next``
    (the first one left) and ``hidden`` (the user hid the list : the dashboard
    then offers to bring it back, and shows nothing else).
    """
    global _instance_started
    if _instance_started:
        return None
    states = [(step, bool(step.done())) for step in STEPS]
    if all(done for _step, done in states):
        _instance_started = True
        return None

    visible = []
    for step, done in states:
        if not (user.is_superuser or user.has_perm(step.read)):
            continue
        visible.append({
            "key": step.key,
            "title": step.title,
            "why": step.why,
            "icon": step.icon,
            "url": reverse(step.url_name),
            "done": done,
            "can_act": user.is_superuser or user.has_perm(step.act),
            "is_next": False,
        })
    left = [entry for entry in visible if not entry["done"]]
    if not left:
        # Everything this reader may open is done : nothing to show them.
        return None
    left[0]["is_next"] = True
    return {
        "steps": visible,
        "done": len(visible) - len(left),
        "total": len(visible),
        "next": left[0],
        "hidden": is_dismissed(user),
    }
