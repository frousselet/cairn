import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class SavedFilter(models.Model):
    """A named, reusable filter for a list page, owned by a user.

    ``view_key`` is the list it belongs to (``app_label.model_name``) and
    ``query`` is the raw query string that reproduces the filter (facets, text
    rules and advanced rules). Personal by default; ``is_shared`` makes it
    visible to every user on that list.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_filters",
        verbose_name=_("Owner"),
    )
    view_key = models.CharField(_("List"), max_length=100, db_index=True)
    name = models.CharField(_("Name"), max_length=120)
    query = models.TextField(_("Query string"), blank=True, default="")
    is_shared = models.BooleanField(_("Shared with everyone"), default=False)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        verbose_name = _("Saved filter")
        verbose_name_plural = _("Saved filters")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "view_key", "name"], name="uniq_saved_filter_owner_view_name"
            )
        ]

    def __str__(self):
        return self.name
