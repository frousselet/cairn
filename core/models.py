import logging
import uuid

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class VersioningConfig(models.Model):
    """Per-model configuration for versioning and approval behavior.

    Each record controls how a specific BaseModel subclass handles
    version increments and approval workflow.
    """

    model_name = models.CharField(
        _("Model identifier"),
        max_length=100,
        unique=True,
        help_text=_("Django model label, e.g. 'context.scope'"),
    )
    model_label = models.CharField(
        _("Display name"),
        max_length=200,
        blank=True,
    )
    approval_enabled = models.BooleanField(
        _("Approval enabled"),
        default=True,
        help_text=_("When disabled, approval workflow is hidden for this item type."),
    )
    major_fields = models.JSONField(
        _("Major change fields"),
        default=list,
        blank=True,
        help_text=_(
            "List of field names whose modification triggers a version increment "
            "and approval reset. If empty, all field changes are considered major."
        ),
    )
    workflow_name = models.CharField(
        _("Workflow"),
        max_length=100,
        blank=True,
        help_text=_(
            "Name of the lifecycle workflow for this item type. "
            "Leave blank to use the default workflow."
        ),
    )

    class Meta:
        verbose_name = _("Versioning configuration")
        verbose_name_plural = _("Versioning configurations")
        ordering = ["model_name"]

    def __str__(self):
        return self.model_label or self.model_name

    @property
    def major_fields_display(self):
        """Return major_fields as a list of (field_name, verbose_name) tuples."""
        if not self.major_fields:
            return []
        try:
            model = apps.get_model(self.model_name)
            result = []
            for fname in self.major_fields:
                try:
                    field = model._meta.get_field(fname)
                    label = str(field.verbose_name)
                    result.append((fname, label[:1].upper() + label[1:]))
                except Exception:
                    result.append((fname, fname))
            return result
        except (LookupError, ValueError):
            return [(f, f) for f in self.major_fields]

    @classmethod
    def get_config(cls, model_class):
        """Return the VersioningConfig for a model class, or None if not configured."""
        label = f"{model_class._meta.app_label}.{model_class._meta.model_name}"
        try:
            return cls.objects.get(model_name=label)
        except cls.DoesNotExist:
            return None

    @classmethod
    def _get_config_cached(cls, model_label):
        """Return cached config for a model label. Uses a simple module-level cache."""
        cache = _config_cache
        if model_label in cache:
            return cache[model_label]
        try:
            config = cls.objects.get(model_name=model_label)
        except cls.DoesNotExist:
            config = None
        cache[model_label] = config
        return config

    @classmethod
    def is_approval_enabled(cls, model_class):
        """Check if approval is enabled for a given model class."""
        label = f"{model_class._meta.app_label}.{model_class._meta.model_name}"
        config = cls._get_config_cached(label)
        if config is None:
            return True  # Default: approval enabled
        return config.approval_enabled

    @classmethod
    def get_major_fields(cls, model_class):
        """Return the set of major fields for a model, or None if all fields are major."""
        label = f"{model_class._meta.app_label}.{model_class._meta.model_name}"
        config = cls._get_config_cached(label)
        if config is None:
            return None  # Default: all fields are major
        fields = config.major_fields
        if not fields:
            return None  # Empty list means all fields are major
        return set(fields)

    @classmethod
    def get_workflow_name(cls, model_class):
        """Return the assigned workflow name for a model, or None for the default."""
        label = f"{model_class._meta.app_label}.{model_class._meta.model_name}"
        config = cls._get_config_cached(label)
        if config is None or not config.workflow_name:
            return None
        return config.workflow_name

    @classmethod
    def clear_cache(cls):
        """Clear the in-memory config cache."""
        _config_cache.clear()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        _config_cache.pop(self.model_name, None)

    def delete(self, *args, **kwargs):
        _config_cache.pop(self.model_name, None)
        super().delete(*args, **kwargs)


# Simple in-process cache for VersioningConfig lookups.
_config_cache: dict = {}


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
