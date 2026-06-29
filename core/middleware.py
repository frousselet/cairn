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

        if runner.is_running():
            # A migration or seed is in flight. Touch nothing in the database
            # (the background job owns it - on SQLite a stray read would contend
            # with its write lock and stall the run): serve onboarding paths as-is
            # and send everything else to the screen.
            if path.startswith(self._onboarding_prefix):
                return self.get_response(request)
            return redirect("onboarding:landing")

        if not schema_ready():
            # Pending migrations - on a fresh database OR an upgrade of an
            # already-initialised one. Funnel to the onboarding screen, which
            # applies them with a live progress bar.
            if not path.startswith(self._onboarding_prefix):
                return redirect("onboarding:landing")
        elif is_first_run():
            if not path.startswith(self._onboarding_prefix):
                return redirect("onboarding:landing")
        else:
            # Initialised: hide the bootstrap screens, but let the post-seed
            # auto-login completion and the progress poll run (the latter covers
            # the brief window where the seed has just created users).
            if path.startswith(self._onboarding_prefix) and path not in self._always_reachable:
                return redirect("/")

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
