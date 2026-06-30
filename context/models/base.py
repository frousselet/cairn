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
    is_approved = models.BooleanField(_("Approved"), default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_approved",
        verbose_name=_("Approved by"),
    )
    approved_at = models.DateTimeField(_("Approval date"), null=True, blank=True)
    version = models.PositiveIntegerField(_("Version"), default=1)
    workflow_state = models.CharField(
        _("Lifecycle state"),
        max_length=32,
        default="draft",
        db_index=True,
        help_text=_("Current state of the element in its lifecycle workflow."),
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

    # --- Lifecycle workflow (see core/workflow.py) -------------------------

    def get_workflow(self):
        """Return the :class:`~core.workflow.Workflow` this element runs."""
        from core.workflow import resolve_workflow

        return resolve_workflow(type(self))

    def get_lifecycle_state(self):
        """Return the current :class:`~core.workflow.State` object."""
        return self.get_workflow().state(self.workflow_state)

    @property
    def lifecycle_label(self):
        """Human label of the current state (falls back to the raw code)."""
        step = self._current_step()
        if step is not None:
            return step.label
        try:
            return self.get_lifecycle_state().label
        except Exception:
            return self.workflow_state

    @property
    def lifecycle_tone(self):
        """UI tone of the current state (badge colour category)."""
        step = self._current_step()
        if step is not None:
            return step.tone
        try:
            return self.get_lifecycle_state().tone
        except Exception:
            return "neutral"

    @property
    def counts_in_reports(self):
        """Whether this element is included in reports / KPIs / calendar."""
        step = self._current_step()
        if step is not None:
            return step.counts_in_reports
        try:
            return self.get_lifecycle_state().counts_in_reports
        except Exception:
            return False

    @property
    def is_linkable(self):
        """Whether this element may currently participate in a link."""
        step = self._current_step()
        if step is not None:
            return step.linkable
        try:
            return self.get_lifecycle_state().linkable
        except Exception:
            return False

    @property
    def is_deletable(self):
        """Whether this element may currently be deleted."""
        step = self._current_step()
        if step is not None:
            return step.deletable
        try:
            return self.get_lifecycle_state().deletable
        except Exception:
            return False

    @property
    def is_terminal_state(self):
        """Whether the current lifecycle state is a terminal / archived one.

        Engine-agnostic: the standardised engine's ARCHIVED step kind, or the
        legacy workflow's terminal flag, so callers (link guards, transition
        gating) never reach into a specific engine.
        """
        step = self._current_step()
        if step is not None:
            return step.is_archived
        try:
            return self.get_lifecycle_state().is_terminal
        except Exception:
            return False

    @property
    def workflow_perm_namespace(self):
        """Permission feature path used to build transition codenames.

        Defaults to ``<app_label>.<model_name>``. Models whose permission feature
        differs from their model name (e.g. ``compliance.action_plan``) override
        this when their specific workflow is wired.
        """
        return f"{self._meta.app_label}.{self._meta.model_name}"

    def available_transitions(self, user=None):
        """Transitions leaving the current state (optionally filtered by ``user``)."""
        lifecycle = self.get_lifecycle()
        if lifecycle is not None:
            from core.lifecycle import available_transitions as _avail

            code = self.workflow_state or lifecycle.initial_step.code
            return _avail(lifecycle, code, instance=self, user=user)

        from core.workflow import allowed_transitions

        has_perm = user.has_perm if user is not None else None
        namespace = self.workflow_perm_namespace if user is not None else None
        return allowed_transitions(
            self.get_workflow(),
            self.workflow_state,
            has_perm=has_perm,
            perm_namespace=namespace,
        )

    def transition_to(self, target, user=None, comment=None, *, enforce_permission=False, save=True):
        """Validate and apply a lifecycle transition, then persist.

        Mutates ``workflow_state`` and keeps the legacy ``is_approved`` flag aligned.
        Permission enforcement is opt-in here (the view / API / MCP layer is the
        enforcement point); ``Effect.NOTIFY_OWNER`` is wired in the notification phase.
        """
        from django.utils import timezone

        lifecycle = self.get_lifecycle()
        if lifecycle is not None:
            # Standardised engine: validate, apply and record the event in one
            # place. Returns the matched core.lifecycle.Transition.
            from core.lifecycle import DEFAULT_LIFECYCLE_NAME
            from core.lifecycle_service import perform_transition

            _event, transition = perform_transition(
                self,
                target,
                user=user,
                comment=comment,
                lifecycle=lifecycle,
                enforce_permission=enforce_permission,
                save=False,
            )
            # The default lifecycle keeps the legacy approval flag coupled to the
            # state: reaching the authoritative (validated) step stamps approval,
            # leaving it clears the stamp. Specific lifecycles keep is_approved as
            # an independent axis and never touch it here. Applied before the
            # single save so the move and the stamp share one history record.
            if lifecycle.name == DEFAULT_LIFECYCLE_NAME:
                approved = lifecycle.step(target).counts_in_reports
                if approved:
                    self.is_approved = True
                    if user is not None:
                        self.approved_by = user
                        self.approved_at = timezone.now()
                else:
                    self.is_approved = False
                    self.approved_by = None
                    self.approved_at = None
            if save:
                self.save()
                # Submitting a default-lifecycle element for validation
                # (draft -> pending) notifies its owners (RG-LC-06).
                if user is not None and lifecycle.name == DEFAULT_LIFECYCLE_NAME and target == "pending":
                    from accounts.notifications import notify_lifecycle_submitted

                    notify_lifecycle_submitted(self, actor=user)
            return transition

        from core.workflow import Effect, apply_transition

        workflow = self.get_workflow()
        has_perm = user.has_perm if (enforce_permission and user is not None) else None
        namespace = self.workflow_perm_namespace if (enforce_permission and user is not None) else None
        transition = apply_transition(
            self,
            target,
            workflow=workflow,
            has_perm=has_perm,
            perm_namespace=namespace,
            comment=comment,
        )
        new_state = workflow.state(target)
        if workflow.subsumes_approval:
            # Default-lifecycle-shaped workflows mirror the legacy approval flag;
            # operational workflows keep is_approved as an independent axis.
            self.is_approved = new_state.counts_in_reports
        if Effect.STAMP_VALIDATION in transition.effects and user is not None:
            self.approved_by = user
            self.approved_at = timezone.now()
        if save:
            self.save()
            if Effect.NOTIFY_OWNER in transition.effects:
                from accounts.notifications import notify_lifecycle_submitted

                notify_lifecycle_submitted(self, actor=user)
        return transition

    def _sync_lifecycle_with_approval(self, save_kwargs):
        """Keep ``workflow_state`` coherent with the legacy ``is_approved`` flag.

        During the migration period both the legacy approval flow (which writes
        ``is_approved``) and the workflow path (which writes ``workflow_state``)
        are active. Only the **default lifecycle** mirrors the binary flag onto
        the state (``draft`` <-> ``validated``), without clobbering the richer
        states (``pending``, ``archived``); a model on a specific lifecycle keeps
        ``is_approved`` as an independent axis.
        """
        from core.lifecycle import DEFAULT_LIFECYCLE_NAME

        lifecycle = self.get_lifecycle()
        if lifecycle is None or lifecycle.name != DEFAULT_LIFECYCLE_NAME:
            return
        before = self.workflow_state
        if self.is_approved and self.workflow_state in ("", "draft", "pending"):
            self.workflow_state = "validated"
        elif not self.is_approved and self.workflow_state == "validated":
            self.workflow_state = "draft"
        if self.workflow_state != before:
            update_fields = save_kwargs.get("update_fields")
            if update_fields is not None:
                save_kwargs["update_fields"] = set(update_fields) | {"workflow_state"}

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
        self._sync_lifecycle_with_approval(kwargs)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Block direct deletion unless the current lifecycle state allows it.

        Single source of truth for RG-LC-05 (only a deletable state may be
        deleted), covering the UI, the API and the MCP server. Cascade and bulk
        deletes bypass ``Model.delete()`` by design, so this guards only the
        user-initiated deletion of a single element.
        """
        if not self.is_deletable:
            from core.workflow import LifecycleProtectedError

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
