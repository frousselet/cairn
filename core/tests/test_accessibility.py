# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Keyboard and screen-reader structure of the shared shell and components.

Contrast is guarded by ``test_contrast.py``, the markup of every page by the
sweep (``test_site_sweep.py``, through ``markup_audit``), and the rendered
result by ``scripts/a11y_audit.py`` in CI. This file pins the structural
choices those rest on : the skip link, the named landmarks, the controls that
give the keyboard what the mouse does by dragging, and the checker itself.
"""

import re

import pytest
from django.conf import settings
from django.template import Context, Template
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory
from core.modal_forms import LabelledRowsFormSet
from core.tests import markup_audit

pytestmark = pytest.mark.django_db

CSS = settings.BASE_DIR / "static" / "css" / "cairn"


def _page(url_name="home"):
    client = Client()
    client.force_login(UserFactory(is_superuser=True))
    return client.get(reverse(url_name)).content.decode()


class TestShell:
    def test_the_first_stop_of_the_keyboard_skips_to_the_page(self):
        html = _page()
        body = html.split("<body", 1)[1]
        first_link = re.search(r"<a\b[^>]*>", body).group(0)
        assert 'class="skip-link"' in first_link and 'href="#page-shell"' in first_link
        # The target takes the focus : without tabindex the jump only scrolls.
        assert re.search(r'<main class="main-content" id="page-shell" tabindex="-1"', html)

    def test_the_landmarks_are_named(self):
        html = _page()
        assert re.search(r'<aside class="sidebar" id="sidebar" aria-label="[^"]+"', html)
        assert re.search(r'<nav class="sidebar-body" aria-label="[^"]+"', html)
        assert html.count("<main") == 1

    def test_the_mobile_menu_button_has_a_name(self):
        assert re.search(r'<button type="button" class="mobile-menu-toggle"[^>]*aria-label="[^"]+"', _page())

    def test_the_page_declares_its_language(self):
        assert re.search(r'<html lang="[a-z-]+"', _page())


class TestFocusRing:
    def test_the_generic_ring_and_the_buttons_use_the_focus_token(self):
        content = (CSS / "05-content.css").read_text()
        assert re.search(r":focus-visible \{[^}]*outline: 2px solid var\(--focus-ring\)", content, re.S)
        elements = (CSS / "03-elements.css").read_text()
        assert re.search(r"\.btn:focus-visible \{[^}]*var\(--focus-ring\)", elements, re.S)

    def test_no_focus_style_is_a_pale_glow_alone(self):
        """A rule that removes the outline on focus must draw something that
        reaches 3:1 : the focus ring, or a border in the accent ink. The
        accent glow (20 % alpha) alone is invisible to many."""
        offenders = []
        for sheet in sorted(CSS.glob("*.css")):
            css = re.sub(r"/\*.*?\*/", "", sheet.read_text(), flags=re.S)
            for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
                if "focus" not in selector or not re.search(r"outline:\s*(none|0)", body):
                    continue
                if ":not(:focus-visible)" in selector:
                    continue  # a mouse focus : no ring wanted
                if "--focus-ring" in body or "--accent-text" in body:
                    continue
                offenders.append(f"{sheet.name} : {' '.join(selector.split())}")
        # Text inputs that keep their caret and their parent's focus-within style.
        allowed = {
            "04-overlays.css : .search-input-wrap input",
            "05-content.css : .pell-content:focus",
            "02-shell.css : .main-content:focus",
            "10-framework.css : .detail-main .section-card:focus",
        }
        unexpected = [line for line in offenders if line not in allowed]
        assert not unexpected, "focus styles with no visible indicator :\n  " + "\n  ".join(unexpected)


class TestComponents:
    def test_a_collapsible_card_keeps_its_actions_out_of_the_toggle(self):
        """A button inside a <summary> is a control inside a control."""
        out = Template(
            '{% load ui %}{% section_card "Versions" collapsible=True %}'
            '{% slot actions %}<a class="btn" href="/new/">Add</a>{% endslot %}Body{% endsection_card %}'
        ).render(Context({}))
        summary = re.search(r"<summary.*?</summary>", out, re.S).group(0)
        assert "<a " not in summary and "<button" not in summary
        assert 'href="/new/"' in out.split("</summary>", 1)[1]

    def test_a_grid_formset_names_every_control(self):
        from risks.forms import LikelihoodFormSet
        from risks.tests.factories import RiskCriteriaFactory

        assert issubclass(LikelihoodFormSet, LabelledRowsFormSet)
        formset = LikelihoodFormSet(instance=RiskCriteriaFactory())
        html = formset.empty_form.as_p()
        for control in re.findall(r"<(?:input|select|textarea)\b[^>]*>", html):
            if 'type="hidden"' in control:
                continue
            assert "aria-label=" in control, control

    def test_the_dashboard_widgets_can_be_reordered_without_dragging(self):
        html = _page()
        assert 'class="dash-widget__btn dash-widget__move" data-move="earlier"' in html
        assert 'class="dash-widget__btn dash-widget__move" data-move="later"' in html
        assert "function moveWidget(" in html

    def test_the_dashboard_cards_are_second_level_headings(self):
        html = _page()
        assert '<h2 class="card-title' in html
        assert '<h5 class="card-title' not in html

    def test_a_progress_bar_has_a_name(self):
        html = _page()
        for bar in re.findall(r"<div[^>]*role=\"progressbar\"[^>]*>", html, re.S):
            assert "aria-label=" in bar, bar[:120]

    def test_the_calendar_reads_whatever_the_category_colour(self):
        html = _page("calendar")
        # The hue is a tint and a rule; the title is in the text colour.
        assert "--ev:'+ev.color" in html
        assert "background:'+ev.color" not in html.split("year-mini-dot")[0]
        assert re.search(r'id="calPrev" aria-label="', html) and re.search(r'id="calNext" aria-label="', html)
        # A day with events in the year view is a button, not a clickable div.
        assert "var tag=dayEv.length?'button':'div';" in html


class TestScriptedStates:
    """What the shell's scripts do for a screen reader and a keyboard once a
    page is live. The behaviour itself is exercised by the browser audit; this
    pins that the hooks are still wired."""

    def test_a_replaced_select_leaves_the_screen_readers_tree(self):
        """Tom Select keeps the native select, visually hidden, and takes its
        label : left as is, it is a second field with no name."""
        html = _page()
        assert "function hideReplacedSelects()" in html
        assert html.count("hideReplacedSelects();") >= 1
        assert "el.setAttribute('aria-hidden', 'true');" in html

    def test_a_dialog_filled_over_htmx_is_named_after_its_title(self):
        html = _page()
        assert "function nameDialog(modal)" in html
        assert "modal.setAttribute('aria-labelledby', title.id);" in html

    def test_a_table_that_scrolls_sideways_is_a_focus_stop(self):
        html = _page()
        assert "function markScrollRegions()" in html
        assert "wrap.setAttribute('tabindex', '0');" in html
        assert "wrap.setAttribute('role', 'region');" in html

    def test_so_is_a_risk_matrix_which_scrolls_sideways_on_a_phone(self):
        """`.risk-matrix-wrapper` scrolls under 992 px (06-responsive.css) : it is
        held to the same rule as a table, and named after its own title."""
        from django.conf import settings

        html = _page()
        responsive = (settings.BASE_DIR / "static" / "css" / "cairn" / "06-responsive.css").read_text()

        assert ".risk-matrix-wrapper { overflow-x: auto;" in responsive
        assert "document.querySelectorAll('.table-responsive, .risk-matrix-wrapper')" in html
        assert "wrap.querySelector(':scope > h3')" in html

    def test_the_progress_rows_keep_their_height_on_a_phone(self):
        """The stacked layout must win over the fixed-tile rules that follow it
        in the sheet : without it the rows collapse onto each other."""
        html = _page()
        stacked = html.split("@media (max-width: 1199.98px)", 1)[1].split("}\n  }", 1)[0]
        assert "flex: none !important;" in stacked and "min-height: auto !important;" in stacked


class TestMarkupAudit:
    """The checker the sweep runs on every page : it must see what it claims to."""

    @pytest.mark.parametrize("html,expected", [
        ('<img src="a.png">', "image without alt"),
        ('<button type="button"><i class="bi bi-x" aria-hidden="true"></i></button>', "control without a name"),
        ('<a href="/x/"><i class="bi bi-eye"></i></a>', "control without a name"),
        ('<a hx-get="/x/" class="btn">Edit</a>', "link without href"),
        ('<input type="text" name="q">', "form control without a label"),
        ('<select name="s"><option>1</option></select>', "form control without a label"),
        ('<div tabindex="3">x</div>', "positive tabindex"),
        ('<button type="button" onclick="go()">Go</button>', "inline event handler"),
    ])
    def test_it_reports(self, html, expected):
        assert any(expected in problem for problem in markup_audit.problems(html)), markup_audit.problems(html)

    @pytest.mark.parametrize("html", [
        '<img src="a.png" alt="">',
        '<button type="button" aria-label="Close"><i class="bi bi-x" aria-hidden="true"></i></button>',
        '<a href="/x/"><span class="visually-hidden">Open</span></a>',
        '<a href="/x/"><img src="a.png" alt="Logo"></a>',
        '<a href="/x/" hx-get="/x/">Edit</a>',
        '<label for="q">Search</label><input type="text" id="q" name="q">',
        '<label>Search <input type="text" name="q"></label>',
        '<input type="hidden" name="csrf">',
        '<input type="text" name="q" aria-label="Search">',
        '<div aria-hidden="true"><button type="button"></button></div>',
        '<script>var h = \'<a hx-get="/x/">x</a>\';</script>',
        '<div tabindex="-1">x</div>',
        '<button type="button" data-on-click="go">Go</button>',
    ])
    def test_it_accepts(self, html):
        assert markup_audit.problems(html) == []


class TestBrowserAudit:
    def test_ci_runs_the_browser_audit(self):
        workflow = (settings.BASE_DIR / ".github" / "workflows" / "tests.yml").read_text()
        assert "scripts/a11y_audit.py" in workflow
        assert "axe-core@" in workflow

    def test_ci_audits_an_instance_built_by_the_real_migrations(self):
        """The help content, the default lifecycles and the reference data
        come from data migrations. An instance built straight from the models
        has none of them : audited that way, the help dialog's refused script
        went unseen."""
        workflow = (settings.BASE_DIR / ".github" / "workflows" / "tests.yml").read_text()
        job = workflow.split("  accessibility:", 1)[1]
        assert "python manage.py migrate --noinput" in job
        assert "--run-syncdb" not in job and "SCHEMA_FROM_MODELS" not in job
        assert 'LOCAL_POSTGRES: "1"' in job and "image: postgres:" in job

    def test_the_cached_database_is_still_a_migrated_one(self):
        """The job keeps the migrated database as a dump to save the replay.
        The dump is keyed on every migration file, and `migrate` runs after a
        restore as after a miss : a shortcut that stops being the real
        migrations is how the audit went blind once."""
        workflow = (settings.BASE_DIR / ".github" / "workflows" / "tests.yml").read_text()
        job = workflow.split("  accessibility:", 1)[1]
        assert "hashFiles('**/migrations/*.py')" in job
        restore, migrate, seed = (job.index("pg_restore --no-owner"), job.index("python manage.py migrate --noinput"),
                                  job.index("seed_demo_data.py"))
        assert restore < migrate < seed
        # The dump is taken before the demo data goes in.
        assert migrate < job.index("pg_dump -U") < seed

    def test_a_page_that_does_not_render_fails_the_audit(self):
        """An error page has no contrast defect : it must not pass for the
        page it replaced."""
        source = (settings.BASE_DIR / "scripts" / "a11y_audit.py").read_text()
        assert "the page did not render" in source
        assert "document.getElementById('page-shell')" in source

    def test_the_reference_rows_can_be_rebuilt_without_migrations(self):
        """The audit instance and the test suite build their schema from the
        models : both rely on this to get the permissions and system groups."""
        from accounts.constants import SYSTEM_GROUPS, get_all_permissions
        from accounts.models import Group, Permission
        from accounts.reference_data import sync_system_permissions

        sync_system_permissions()
        sync_system_permissions()  # idempotent
        assert Permission.objects.count() == len(list(get_all_permissions()))
        for name in SYSTEM_GROUPS:
            assert Group.objects.get(name=name).permissions.exists(), name

    def test_the_audit_covers_the_screenshot_set_in_both_themes(self):
        source = (settings.BASE_DIR / "scripts" / "a11y_audit.py").read_text()
        assert "shots.SHOTS" in source and "shots.DETAIL_SHOTS" in source
        assert '["light", "dark"]' in source
        for tag in ("wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"):
            assert f'"{tag}"' in source

    def test_the_audit_opens_what_is_hidden_and_looks_at_a_phone(self):
        """A closed dialog is skipped by axe, and a layout only stacks on a
        narrow screen : both found defects the desktop pages did not show."""
        source = (settings.BASE_DIR / "scripts" / "a11y_audit.py").read_text()
        assert '"edit-dialog"' in source and '"filter-panel"' in source
        assert "PHONE_PAGES" in source and "viewport(*PHONE, True)" in source
