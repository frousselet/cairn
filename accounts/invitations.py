"""User provisioning via invitation (no plaintext password).

A user can be created without a password crossing any boundary: the account is
saved with an *unusable* password (``set_unusable_password``) and a signed,
single-use activation link is minted from Django's ``default_token_generator``.
The invitee follows the link to set their first password (see
``accounts.views.UserActivateView``); until then the account cannot be logged
into, yet it exists and can already be referenced as an owner / reviewer.

Shared by the MCP ``create_user`` tool and the DRF ``users/invite`` endpoint so
both provision users identically.
"""

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext as _

from accounts.constants import AccessEventType, UserType
from accounts.models import AccessLog, Group, User


def build_activation_url(user):
    """Return the absolute activation URL for ``user`` (empty host if unset).

    The link embeds the base64 user id and a ``default_token_generator`` token.
    Setting a password invalidates the token, so the link is single-use.
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse("accounts:activate", args=[uid, token])
    site_url = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    return f"{site_url}{path}"


def provision_user(
    *,
    email,
    last_name,
    first_name="",
    user_type=UserType.HUMAN,
    job_title="",
    department="",
    phone="",
    language=None,
    group_names=None,
    created_by=None,
):
    """Create an invited user with an unusable password and assign groups.

    ``group_names`` are matched against existing ``Group.name`` values; unknown
    names raise ``ValidationError`` before anything is written. Returns the saved
    ``User``. Raises ``ValidationError`` on a duplicate email, unknown group or
    invalid ``user_type``.
    """
    if not email:
        raise ValidationError(_("An email address is required."))
    email = User.objects.normalize_email(email)
    if not last_name:
        raise ValidationError(_("A last name is required."))
    if user_type not in UserType.values:
        raise ValidationError(
            _('Invalid user type "%(value)s".') % {"value": user_type}
        )
    if User.objects.filter(email__iexact=email).exists():
        raise ValidationError(
            _('A user with email "%(email)s" already exists.') % {"email": email}
        )

    groups = []
    if group_names:
        for name in group_names:
            try:
                groups.append(Group.objects.get(name=name))
            except Group.DoesNotExist:
                raise ValidationError(
                    _('No role / group named "%(name)s".') % {"name": name}
                )

    user = User(
        email=email,
        last_name=last_name,
        first_name=first_name or "",
        user_type=user_type,
        job_title=job_title or "",
        department=department or "",
        phone=phone or "",
        created_by=created_by,
    )
    if language:
        user.language = language
    user.set_unusable_password()
    user.full_clean(exclude=["password"])
    user.save()

    for group in groups:
        group.users.add(user)

    AccessLog.objects.create(
        user=created_by if getattr(created_by, "pk", None) else None,
        event_type=AccessEventType.USER_INVITED,
        email_attempted=email,
        metadata={
            "invited_user_id": str(user.pk),
            "invited_email": email,
            "groups": [g.name for g in groups],
        },
    )
    return user
