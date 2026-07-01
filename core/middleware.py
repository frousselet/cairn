"""Project-wide middleware."""

from functools import cached_property

from django.conf import settings
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse

from core.onboarding import runner
from core.onboarding.state import is_first_run, schema_ready


class OnboardingMiddleware:
    """Funnel an un-initialised instance to the first-run onboarding screen.

    While the instance has no users, every request (except onboarding itself and
    static/i18n assets) is redirected to ``onboarding:landing``. Once a user
    exists, the onboarding screens are no longer reachable - the only exception
    is ``onboarding:complete``, which performs the post-seed auto-login and runs
    when users already exist.

    Disabled wholesale when ``settings.ONBOARDING_REDIRECT_ENABLED`` is ``False``
    (the test settings turn it off so the rest of the suite is unaffected).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "ONBOARDING_REDIRECT_ENABLED", True):
            return self.get_response(request)

        path = request.path

        if self._is_asset(path):
            return self.get_response(request)

        on_onboarding = path.startswith(self._onboarding_prefix)

        # Fast path: a fully set-up instance (schema migrated and a user exists).
        # Both checks are process-sticky once confirmed, so this costs nothing
        # after the first request and, crucially, avoids a shared-cache round
        # trip (runner.is_running) on every request once onboarding is over.
        if schema_ready() and not is_first_run():
            # Initialised: hide the bootstrap screens, but let the post-seed
            # auto-login completion and the progress poll run (the latter covers
            # the brief window where the seed has just created users).
            if on_onboarding and path not in self._always_reachable:
                return redirect("/")
            return self.get_response(request)

        # Un-initialised window: a fresh database (first run) or an upgrade of an
        # already-initialised one with pending migrations. The runner state is
        # shared across workers, so every worker agrees on whether a job is in
        # flight - one worker applies the migrations, the others funnel here and
        # watch the same progress bar instead of launching a rival migration.
        if runner.is_running():
            # A migration or seed is in flight. Touch nothing in the database
            # (the background job owns it): serve onboarding paths as-is and send
            # everything else to the screen.
            if on_onboarding:
                return self.get_response(request)
            return redirect("onboarding:landing")

        # No job running yet: funnel to the onboarding screen, which applies any
        # pending migrations with a live progress bar and then offers the setup
        # choices.
        if not on_onboarding:
            return redirect("onboarding:landing")
        return self.get_response(request)

    def _is_asset(self, path):
        for prefix in (settings.STATIC_URL, settings.MEDIA_URL, "/i18n/"):
            if prefix and path.startswith(prefix):
                return True
        return False

    @cached_property
    def _onboarding_prefix(self):
        try:
            return reverse("onboarding:landing")
        except NoReverseMatch:
            return "/onboarding/"

    @cached_property
    def _always_reachable(self):
        """Onboarding paths that stay reachable even once the instance is set up."""
        paths = set()
        for name, fallback in (("onboarding:complete", "/onboarding/complete/"),
                               ("onboarding:progress", "/onboarding/progress.json")):
            try:
                paths.add(reverse(name))
            except NoReverseMatch:
                paths.add(fallback)
        return paths
