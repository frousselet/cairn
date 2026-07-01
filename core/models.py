import logging
import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class LifecycleEvent(models.Model):
    """An immutable record of one performed lifecycle transition.

    The canonical history of how an element moved through its lifecycle: who
    moved it, when, from which step to which, with the optional comment and the
    cleaned data of any per-transition form. Generic (content-type) so a single
    table logs transitions for every entity, regardless of PK type.

    Events are append-only: they are never edited or deleted in the normal flow
    (deletion of the host object cascades via ``content_type``/``object_id`` only
    if the caller chooses to clean up; there is no DB-level cascade).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Content type"),
    )
    # CharField so both UUID and integer primary keys are supported.
    object_id = models.CharField(_("Object id"), max_length=64, db_index=True)
    target = GenericForeignKey("content_type", "object_id")

    lifecycle_name = models.CharField(_("Lifecycle"), max_length=100)
    from_step = models.CharField(_("From step"), max_length=64, blank=True, default="")
    to_step = models.CharField(_("To step"), max_length=64)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lifecycle_events",
        verbose_name=_("Actor"),
    )
    comment = models.TextField(_("Comment"), blank=True, default="")
    form_data = models.JSONField(_("Form data"), default=dict, blank=True)
    created_at = models.DateTimeField(_("Performed at"), auto_now_add=True)

    class Meta:
        verbose_name = _("Lifecycle event")
        verbose_name_plural = _("Lifecycle events")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.lifecycle_name}: {self.from_step or '∅'} -> {self.to_step}"

    @classmethod
    def record(cls, instance, *, lifecycle_name, from_step, to_step, actor=None, comment="", form_data=None):
        """Append an event for a transition just performed on ``instance``."""
        return cls.objects.create(
            content_type=ContentType.objects.get_for_model(type(instance)),
            object_id=str(instance.pk),
            lifecycle_name=lifecycle_name,
            from_step=from_step or "",
            to_step=to_step,
            actor=actor,
            comment=comment or "",
            form_data=form_data or {},
        )

    @classmethod
    def for_instance(cls, instance):
        """The chronological event log for one instance (most recent first)."""
        return cls.objects.filter(
            content_type=ContentType.objects.get_for_model(type(instance)),
            object_id=str(instance.pk),
        )
