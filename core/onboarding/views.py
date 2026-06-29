"""Views for the first-run onboarding flow.

All views re-check :func:`core.onboarding.state.is_first_run` server-side so the
bootstrap actions (apply migrations, create first admin, seed) are impossible once
any user exists, regardless of the middleware. Progress is reported over a plain
JSON poll (``OnboardingProgressView``) rather than a WebSocket, because on a fresh
database the session/auth tables a WebSocket would need do not exist yet.
"""

from django.contrib import messages
from django.contrib.auth import login
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View

from accounts.forms import CompanySettingsForm
from accounts.models import CompanySettings, User

from .forms import FirstAdminForm
from .runner import is_running, progress_snapshot, start_migrations, start_seed
from .state import is_first_run, mark_initialised, migration_status

# The first super-admin is logged in without going through ``authenticate``, so
# the backend must be named explicitly (the project wires several backends).
LOGIN_BACKEND = "accounts.backends.EmailAuthBackend"


def _render_progress(request, *, heading, complete_url):
    return render(request, "onboarding/progress.html", {
        "heading": heading,
        "poll_url": reverse("onboarding:progress"),
        "complete_url": complete_url,
    })


def _progress_for(request, snap):
    """Render the progress page for the current job, derived from the snapshot
    only (no database access - safe while the job holds the DB)."""
    if snap["kind"] == "seed":
        return _render_progress(
            request, heading=_("Loading sample data"),
            complete_url=reverse("onboarding:complete"))
    if snap.get("upgrade"):
        return _render_progress(
            request, heading=_("Updating the database"), complete_url="/")
    return _render_progress(
        request, heading=_("Setting up the database"),
        complete_url=reverse("onboarding:landing"))


class OnboardingView(View):
    """Onboarding landing.

    Applies any pending migrations automatically behind a progress bar - on a
    fresh database (first run) or an upgrade of an already-initialised one. Once
    the schema is ready, a first run shows the two initialisation choices and an
    upgrade returns to the app.
    """

    def get(self, request):
        # A job is in flight: show its progress without touching the database.
        snap = progress_snapshot()
        if is_running() and snap["status"] == "running":
            return _progress_for(request, snap)

        status = migration_status()
        if status["available"] and not status["up_to_date"]:
            upgrade = not is_first_run()
            start_migrations(upgrade=upgrade)  # idempotent if already running
            return _progress_for(request, {"kind": "migrate", "upgrade": upgrade})

        if not is_first_run():
            return redirect("/")

        return render(request, "onboarding/landing.html", {
            "migration": status,
            "can_initialise": status["available"] and status["up_to_date"],
        })


class OnboardingProgressView(View):
    """JSON progress snapshot for the polling progress bar.

    Deliberately touches neither the database nor the session so it works during
    the migration phase (before any table exists). Exempt from the middleware's
    "redirect away once initialised" rule.
    """

    def get(self, request):
        return JsonResponse(progress_snapshot())


class OnboardingScratchView(View):
    """Two-step "start from scratch" wizard: configure the company, then create
    the first super-admin and sign them in.

    Both steps live in a single page and a single ``<form>``; the company step is
    purely client-side (its values are held in the browser, not the database)
    until the final submit, which creates the admin **and** persists the company
    settings together in one transaction. Nothing is written to the database
    before the administrator exists.
    """

    def _render(self, request, *, form, company_form, active_step):
        return render(request, "onboarding/scratch.html", {
            "form": form,
            "company_form": company_form,
            "active_step": active_step,
        })

    def get(self, request):
        if not is_first_run():
            return redirect("/")
        if not migration_status()["up_to_date"]:
            return redirect("onboarding:landing")
        return self._render(
            request,
            form=FirstAdminForm(),
            company_form=CompanySettingsForm(instance=CompanySettings()),
            active_step=1,
        )

    def post(self, request):
        if not is_first_run():
            return redirect("/")
        if not migration_status()["up_to_date"]:
            return redirect("onboarding:landing")
        form = FirstAdminForm(request.POST)
        company_form = CompanySettingsForm(request.POST, request.FILES, instance=CompanySettings())
        # Validate both before touching the database: the company settings and the
        # admin account are committed together or not at all.
        company_valid = company_form.is_valid()
        admin_valid = form.is_valid()
        if company_valid and admin_valid:
            with transaction.atomic():
                user = form.save()
                company_form.save()
            mark_initialised()
            login(request, user, backend=LOGIN_BACKEND)
            messages.success(request, _("Welcome to Cairn. Your administrator account is ready."))
            return redirect("/")
        # Surface the step that holds the error (company first, then admin).
        active_step = 1 if not company_valid else 2
        return self._render(request, form=form, company_form=company_form, active_step=active_step)


class OnboardingSeedView(View):
    """Kick off the demo seed and show the full-screen progress bar."""

    def get(self, request):
        # Re-entry (page reload while seeding): rejoin the progress stream.
        if is_running() or request.session.get("onboarding_seeding"):
            return _render_progress(
                request,
                heading=_("Loading sample data"),
                complete_url=reverse("onboarding:complete"),
            )
        return redirect("onboarding:landing")

    def post(self, request):
        if not is_first_run():
            return redirect("/")
        status = migration_status()
        if not (status["available"] and status["up_to_date"]):
            messages.error(request, _("The database is not ready yet. Please wait for migrations to finish."))
            return redirect("onboarding:landing")
        request.session["onboarding_seeding"] = True
        start_seed()
        return _render_progress(
            request,
            heading=_("Loading sample data"),
            complete_url=reverse("onboarding:complete"),
        )


class OnboardingCompleteView(View):
    """Post-seed auto-login as the seeded admin, then land on the dashboard.

    Reachable once users exist (the middleware exempts this path), but gated by a
    per-session flag so only the browser that launched the seed can auto-login,
    and only once.
    """

    def get(self, request):
        if not request.session.get("onboarding_seeding"):
            return redirect("/")
        request.session.pop("onboarding_seeding", None)

        admin = User.objects.filter(is_superuser=True).order_by("created_at").first()
        if admin is None:
            # Seed failed and rolled back: no users were created.
            messages.error(request, _("Sample data could not be loaded. Please try again."))
            return redirect("onboarding:landing")

        mark_initialised()
        login(request, admin, backend=LOGIN_BACKEND)
        messages.success(request, _("Sample data loaded. Signed in as %(name)s.") % {"name": admin.display_name})
        return redirect("/")
