"""Compliance signals.

These handlers keep the aggregated compliance levels on Section and Framework
in sync with the underlying Requirement state. Without them, the levels only
refreshed when a ComplianceAssessment was validated, which matched what the QA
report flagged as CAIRN-REQ-03 (RC-01 / RC-02 only triggered on validation).

They also drive *risk-driven applicability*: when a Framework has
``applicability_managed_by_risks`` enabled, a requirement's ``is_applicable`` is
recomputed automatically from its linked risks (see
``compliance.applicability``) whenever the link, a risk's reportable state, or
the framework option itself changes.
"""

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import (
    m2m_changed,
    post_delete,
    post_save,
    pre_delete,
    pre_save,
)
from django.dispatch import receiver


def _recalculate_chain(requirement):
    """Walk up the section tree from a requirement and refresh every level.

    Section.recalculate_compliance cascades down to its children, so refreshing
    the root recomputes the whole branch. Framework.recalculate_compliance is
    called afterwards to refresh the overall framework level (RC-01).
    """
    # During a Framework cascade delete the requirement's related section /
    # framework rows may already be gone, so accessing the FK raises
    # ObjectDoesNotExist (not caught by getattr's default) instead of returning
    # the related object. Treat a vanished relation as "nothing to recompute".
    try:
        section = requirement.section
    except ObjectDoesNotExist:
        section = None
    if section is not None:
        root = section
        while root.parent_section_id:
            root = root.parent_section
        try:
            root.recalculate_compliance()
        except Exception:
            # Never let aggregation failures bubble up from a save signal.
            pass

    try:
        framework = requirement.framework
    except ObjectDoesNotExist:
        framework = None
    if framework is not None:
        try:
            framework.recalculate_compliance()
        except Exception:
            pass


@receiver(post_save, sender="compliance.Requirement")
def requirement_post_save(sender, instance, created, **kwargs):
    _recalculate_chain(instance)


@receiver(post_delete, sender="compliance.Requirement")
def requirement_post_delete(sender, instance, **kwargs):
    _recalculate_chain(instance)


# --------------------------------------------------------------------------- #
# Risk-driven applicability
# --------------------------------------------------------------------------- #


def _recompute_requirements(requirements):
    from compliance.applicability import recompute_requirement_applicability

    for requirement in requirements:
        recompute_requirement_applicability(requirement)


def _managed_requirements(pks):
    """Requirements among *pks* whose framework manages applicability by risks."""
    from compliance.models import Requirement

    pks = [pk for pk in (pks or [])]
    if not pks:
        return Requirement.objects.none()
    return Requirement.objects.filter(
        pk__in=pks, framework__applicability_managed_by_risks=True
    ).select_related("framework")


@receiver(post_save, sender="compliance.Requirement")
def requirement_applicability_post_save(sender, instance, created, **kwargs):
    """Enforce risk-driven applicability on every requirement write.

    Covers all creation/update paths (form, API, MCP, ORM, seed, import) so a
    requirement in a managed framework always reflects the rule. No-op when the
    framework does not manage applicability. Recompute only writes on an actual
    change, so the re-entrant save this triggers finds nothing to do and stops.
    """
    from compliance.applicability import recompute_requirement_applicability

    recompute_requirement_applicability(instance)


def on_risk_requirements_changed(sender, instance, action, reverse, pk_set, **kwargs):
    """Sync applicability when the Risk <-> Requirement link changes.

    Covers every link entry point (forms, REST, MCP link/unlink/set, seeds) in
    both directions of the M2M. Connected in ``ComplianceConfig.ready`` because
    the sender is the through model, which is only resolvable once apps load.
    """
    if action == "pre_clear" and not reverse:
        # pk_set is None on a clear: snapshot the requirements about to detach.
        instance._cleared_requirement_pks = list(
            instance.linked_requirements.values_list("pk", flat=True)
        )
        return
    if action not in ("post_add", "post_remove", "post_clear"):
        return

    if reverse:
        # instance is a Requirement whose set of risks changed.
        _recompute_requirements(_managed_requirements([instance.pk]))
    else:
        # instance is a Risk; pk_set holds the affected requirement pks.
        if action == "post_clear":
            pks = getattr(instance, "_cleared_requirement_pks", [])
        else:
            pks = list(pk_set or [])
        _recompute_requirements(_managed_requirements(pks))


@receiver(pre_save, sender="risks.Risk")
def _stash_risk_state(sender, instance, **kwargs):
    """Remember the risk's previous lifecycle state to detect reportable flips."""
    if not instance.pk:
        instance._old_workflow_state = None
        return
    from risks.models import Risk

    instance._old_workflow_state = (
        Risk.objects.filter(pk=instance.pk)
        .values_list("workflow_state", flat=True)
        .first()
    )


@receiver(post_save, sender="risks.Risk")
def _risk_saved(sender, instance, created, **kwargs):
    """Recompute linked requirements when a risk's lifecycle state changes.

    A transition to/from an archived or cancelled state flips whether the risk
    counts as active, which changes the applicability of any managed requirement
    it is linked to. New risks have no links yet, so they are handled by the M2M
    signal once links are added.
    """
    if created:
        return
    if getattr(instance, "_old_workflow_state", None) == instance.workflow_state:
        return
    _recompute_requirements(
        instance.linked_requirements.filter(
            framework__applicability_managed_by_risks=True
        ).select_related("framework")
    )


@receiver(pre_delete, sender="risks.Risk")
def _stash_risk_requirements(sender, instance, **kwargs):
    """Snapshot managed requirements before the M2M rows vanish on hard delete."""
    instance._applicability_requirement_pks = list(
        instance.linked_requirements.filter(
            framework__applicability_managed_by_risks=True
        ).values_list("pk", flat=True)
    )


@receiver(post_delete, sender="risks.Risk")
def _risk_deleted(sender, instance, **kwargs):
    """Recompute requirements that lost this risk (m2m_changed does not fire)."""
    _recompute_requirements(
        _managed_requirements(getattr(instance, "_applicability_requirement_pks", []))
    )


@receiver(pre_save, sender="compliance.Framework")
def _stash_framework_managed(sender, instance, **kwargs):
    """Remember whether the framework already managed applicability by risks."""
    if not instance.pk:
        instance._was_managed = False
        return
    from compliance.models import Framework

    instance._was_managed = bool(
        Framework.objects.filter(pk=instance.pk)
        .values_list("applicability_managed_by_risks", flat=True)
        .first()
    )


@receiver(post_save, sender="compliance.Framework")
def _framework_saved(sender, instance, created, **kwargs):
    """When risk-driven applicability is switched on, recompute every requirement."""
    if not instance.applicability_managed_by_risks:
        return
    if not created and getattr(instance, "_was_managed", False):
        return  # already managed; the option did not just turn on
    _recompute_requirements(instance.requirements.all())


def connect_risk_link_signal():
    """Connect the M2M handler. Called from ``ComplianceConfig.ready``."""
    from risks.models import Risk

    m2m_changed.connect(
        on_risk_requirements_changed,
        sender=Risk.linked_requirements.through,
        dispatch_uid="compliance_risk_applicability_m2m",
    )
