# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""An access token names the account it acts as, and ends.

Until now a token was tied to its application only and acted as the owner of
that application. For a public client (dynamic registration, authorization
code), the owner was whoever authorized it first : anyone who authorized the
same client afterwards received a token acting as that first user. And no
token ever expired.

The existing tokens are dealt with here :

- those of public clients are deleted. They may act as someone other than the
  person who obtained them, and nothing recorded tells which ones do. Their
  users go through the consent page once more;
- those of confidential clients (client credentials) are attached to the
  owner of their application, which is who they always acted as, and their
  "never" expiry is brought back to the configured lifetime from today.
"""

from datetime import timedelta

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def bind_and_expire(apps, schema_editor):
    token_model = apps.get_model("mcp", "OAuthAccessToken")
    token_model.objects.filter(application__token_endpoint_auth_method="none").delete()
    limit = timezone.now() + timedelta(days=getattr(settings, "OAUTH_ACCESS_TOKEN_LIFETIME_DAYS", 90))
    for token in token_model.objects.select_related("application").iterator():
        token.user_id = token.application.user_id
        if token.expires_at > limit:
            token.expires_at = limit
        token.save(update_fields=["user", "expires_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("mcp", "0003_alter_oauthauthorizationcode_redirect_uri"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="oauthaccesstoken",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="oauth_access_tokens",
                to=settings.AUTH_USER_MODEL,
                verbose_name="User",
            ),
        ),
        # No way back for the deleted tokens : reversing only drops the column.
        migrations.RunPython(bind_and_expire, migrations.RunPython.noop),
    ]
