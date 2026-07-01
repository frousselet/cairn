import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ReferenceGeneratorMixin(models.Model):
    """Mixin that adds an auto-generated reference field (PREFIX-N)."""

    REFERENCE_PREFIX = ""

    reference = models.CharField(_("Reference"), max_length=50, unique=True, blank=True)

    @classmethod
    def _generate_next_reference(cls):
        """Generate the next unique reference in the format PREFIX-N."""
        prefix = cls.REFERENCE_PREFIX
        if not prefix:
            return ""
        prefix_with_dash = f"{prefix}-"
        existing_refs = cls.objects.filter(
            reference__startswith=prefix_with_dash
        ).values_list("reference", flat=True)
        max_num = 0
        prefix_len = len(prefix_with_dash)
        for ref in existing_refs:
            try:
                num = int(ref[prefix_len:])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue
        return f"{prefix}-{max_num + 1}"

    def save(self, *args, **kwargs):
        if not self.reference and self.REFERENCE_PREFIX:
            self.reference = self._generate_next_reference()
        super().save(*args, **kwargs)

    class Meta:
        abstract = True


class LegacyStatusMixin:
    """Expose ``status`` as a read/write alias of the lifecycle ``workflow_state``.

    For the entities whose legacy ``status`` column merely duplicated
    ``workflow_state`` (the lifecycle step code, kept in sync by the now-removed
    ``sync_legacy_status``): the duplicate DB column is dropped, while
    ``obj.status`` (read and write, including ``Model(status=...)`` since Django
    accepts property kwargs) and ``obj.get_status_display()`` keep working by
    delegating to the single ``workflow_state`` field and its lifecycle step.
    Mixed in *before* :class:`BaseModel` so the property shadows nothing.
    """

    @property
    def status(self):
        return self.workflow_state

    @status.setter
    def status(self, value):
        self.workflow_state = value

    def get_status_display(self):
        return str(self.lifecycle_label)


class BaseModel(ReferenceGeneratorMixin):
    REQUIRED_PREFIX_LENGTH = 4

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        prefix = cls.__dict__.get("REFERENCE_PREFIX")
        if prefix and len(prefix) != cls.REQUIRED_PREFIX_LENGTH:
            raise ValueError(
                f"{cls.__name__}.REFERENCE_PREFIX '{prefix}' must be exactly "
                f"{cls.REQUIRED_PREFIX_LENGTH} characters"
            )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
        verbose_name=_("Created by"),
    )
    version = models.PositiveIntegerField(_("Version"), default=1)
    workflow_state = models.CharField(
        _("Lifecycle state"),
        max_length=32,
        default="draft",
        db_index=True,
        help_text=_("Current state of the element in its lifecycle."),
    )
    tags = models.ManyToManyField(
        "context.Tag",
        blank=True,
        related_name="%(app_label)s_%(class)s_set",
        verbose_name=_("Tags"),
    )

    # --- Lifecycle ---------------------------------------------------------
    #
    # Two engines coexist during the migration. A model that sets
    # ``LIFECYCLE_NAME`` runs the standardised engine (``core/lifecycle.py``):
    # ``workflow_state`` holds the step code, governance / transitions / history
    # route through it. Every other model keeps the first-generation engine
    # (``core/workflow.py``) below.
    LIFECYCLE_NAME = None

    def get_lifecycle(self):
        """Return the :class:`~core.lifecycle.Lifecycle` this element runs.

        A model declaring ``LIFECYCLE_NAME`` runs that lifecycle; every other
        model runs the standardised default lifecycle. Never ``None`` (every
        ``BaseModel`` is governed by the lifecycle engine).
        """
        from core.lifecycle import resolve_lifecycle

        return resolve_lifecycle(type(self))

    def _current_step(self, lifecycle=None):
        """The current :class:`~core.lifecycle.Step` (new engine), or ``None``."""
        lifecycle = lifecycle or self.get_lifecycle()
        if lifecycle is None:
            return None
        code = self.workflow_state or lifecycle.initial_step.code
        try:
            return lifecycle.step(code)
        except Exception:
            return None

    # --- Lifecycle governance (read off the current step) ------------------

    @property
    def lifecycle_label(self):
        """Human label of the current step (falls back to the raw code)."""
        step = self._current_step()
        return step.label if step is not None else self.workflow_state

    @property
    def lifecycle_tone(self):
        """UI tone of the current step (badge colour category)."""
        step = self._current_step()
        return step.tone if step is not None else "neutral"

    @property
    def counts_in_reports(self):
        """Whether this element is included in reports / KPIs / calendar."""
        step = self._current_step()
        return step.counts_in_reports if step is not None else False

    @property
    def is_linkable(self):
        """Whether this element may currently participate in a link."""
        step = self._current_step()
        return step.linkable if step is not None else False

    @property
    def is_deletable(self):
        """Whether this element may currently be deleted."""
        step = self._current_step()
        return step.deletable if step is not None else False

    @property
    def is_terminal_state(self):
        """Whether the current step is a terminal / archived one."""
        step = self._current_step()
        return step.is_archived if step is not None else False

    @property
    def workflow_perm_namespace(self):
        """Permission feature path used to build transition codenames.

        Defaults to ``<app_label>.<model_name>``. Models whose permission feature
        differs from their model name (e.g. ``compliance.action_plan``) override
        this.
        """
        return f"{self._meta.app_label}.{self._meta.model_name}"

    def available_transitions(self, user=None):
        """Transitions leaving the current step (optionally filtered by ``user``)."""
        from core.lifecycle import available_transitions as _avail

        lifecycle = self.get_lifecycle()
        code = self.workflow_state or lifecycle.initial_step.code
        return _avail(lifecycle, code, instance=self, user=user)

    def transition_to(self, target, user=None, comment=None, *, enforce_permission=False, save=True):
        """Validate, apply and record a lifecycle transition, then persist.

        Returns the matched :class:`core.lifecycle.Transition`. Permission
        enforcement is opt-in here (the view / API / MCP layer is the enforcement
        point). Submitting a default-lifecycle element notifies its owners.
        """
        from core.lifecycle import DEFAULT_LIFECYCLE_NAME
        from core.lifecycle_service import perform_transition

        lifecycle = self.get_lifecycle()
        _event, transition = perform_transition(
            self,
            target,
            user=user,
            comment=comment,
            lifecycle=lifecycle,
            enforce_permission=enforce_permission,
            save=save,
        )
        if save:
            # Submitting a default-lifecycle element for validation
            # (draft -> pending) notifies its owners (RG-LC-06).
            if user is not None and lifecycle.name == DEFAULT_LIFECYCLE_NAME and target == "pending":
                from accounts.notifications import notify_lifecycle_submitted

                notify_lifecycle_submitted(self, actor=user)
        return transition

    def _ensure_initial_step(self):
        """On creation, snap ``workflow_state`` to the lifecycle's initial step.

        The field default (``"draft"``) is only valid for lifecycles that have a
        draft step; a specific lifecycle whose entry step uses a different code
        (e.g. a risk starting at ``identified``) gets its initial step here, so a
        freshly created element is never parked on a code outside its lifecycle.
        Only acts on new rows and never overrides a value that is already a valid
        step of the lifecycle.
        """
        if not self._state.adding:
            return
        lifecycle = self.get_lifecycle()
        if lifecycle is None:
            return
        if not self.workflow_state or not lifecycle.has_step(self.workflow_state):
            self.workflow_state = lifecycle.initial_step.code

    def save(self, *args, **kwargs):
        self._ensure_initial_step()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Block direct deletion unless the current lifecycle state allows it.

        Single source of truth for RG-LC-05 (only a deletable state may be
        deleted), covering the UI, the API and the MCP server. Cascade and bulk
        deletes bypass ``Model.delete()`` by design, so this guards only the
        user-initiated deletion of a single element.
        """
        if not self.is_deletable:
            from core.lifecycle import LifecycleProtectedError

            raise LifecycleProtectedError(
                f"{self._meta.verbose_name} cannot be deleted in its current "
                f"lifecycle state ('{self.workflow_state}')."
            )
        return super().delete(*args, **kwargs)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class ScopedModel(BaseModel):
    scopes = models.ManyToManyField(
        "context.Scope",
        related_name="%(class)s_set",
        verbose_name=_("Scopes"),
        blank=True,
    )

    class Meta:
        abstract = True
