# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Content Security Policy (``core/csp.py``).

The policy lets a page run the instance's own script files and the inline
scripts that carry the nonce of the response, and nothing else. These tests
hold both sides of that contract : the header says so, and no template writes
script where the policy would refuse it (an inline handler, a script without
its nonce, an ``hx-on`` attribute). What a browser actually refuses is checked
by ``scripts/a11y_audit.py``, which fails on any policy violation.
"""

import re
import subprocess

import pytest
from django.conf import settings
from django.test import Client, RequestFactory, override_settings
from django.urls import reverse

from accounts.tests.factories import UserFactory
from core import csp
from core.tests import markup_audit

pytestmark = pytest.mark.django_db

HEADER = "Content-Security-Policy"
DATA_TYPES = ("application/json", "text/template", "text/x-template", "application/ld+json")


def _client():
    client = Client()
    client.force_login(UserFactory(is_superuser=True))
    return client


def _directives(response):
    return {
        part.split()[0]: part.split()[1:]
        for part in response[HEADER].split("; ")
    }


def _nonce(response):
    return re.search(r"'nonce-([^']+)'", response[HEADER]).group(1)


def _inline_scripts(html):
    """The attributes of every executable inline script of a page.

    Parsed, not matched : a script that mentions ``<script>`` in a comment
    must not count as one.
    """
    return [
        node.attrs for node in markup_audit.parse(html).walk()
        if node.tag == "script" and "src" not in node.attrs
        and (node.attrs.get("type") or "").lower() not in DATA_TYPES
    ]


class TestHeader:
    def test_a_page_runs_its_own_scripts_and_nothing_else(self):
        response = _client().get(reverse("home"))
        policy = _directives(response)
        assert policy["default-src"] == ["'self'"]
        assert policy["script-src"] == ["'self'", f"'nonce-{_nonce(response)}'"]
        assert policy["object-src"] == ["'none'"]
        assert policy["base-uri"] == ["'self'"]
        assert policy["form-action"] == ["'self'"]
        assert policy["frame-ancestors"] == ["'none'"]
        # Nothing that would bring inline or evaluated script back.
        assert "'unsafe-inline'" not in policy["script-src"]
        assert "'unsafe-eval'" not in response[HEADER]

    def test_every_inline_script_carries_the_nonce_of_its_response(self):
        response = _client().get(reverse("home"))
        scripts = _inline_scripts(response.content.decode())
        assert len(scripts) > 10
        nonce = _nonce(response)
        for attributes in scripts:
            assert attributes.get("nonce") == nonce, attributes

    def test_the_nonce_changes_with_every_response(self):
        client = _client()
        first, second = client.get(reverse("home")), client.get(reverse("home"))
        assert _nonce(first) != _nonce(second)
        assert len(_nonce(first)) >= 20

    def test_a_response_with_no_inline_script_carries_no_nonce(self):
        response = _client().get("/api/v1/dependencies/")
        assert response.status_code == 200
        assert "nonce-" not in response[HEADER]
        assert "script-src 'self';" in response[HEADER]

    @pytest.mark.parametrize("path", ["/accounts/login/", "/trust/"])
    def test_the_pages_shown_before_signing_in_are_covered(self, path):
        response = Client().get(path)
        if response.status_code == 404:  # the Trust Center is not published in this database
            assert HEADER in response
            return
        assert response.status_code == 200
        nonce = _nonce(response)
        for attributes in _inline_scripts(response.content.decode()):
            assert attributes.get("nonce") == nonce

    def test_htmx_gives_swapped_scripts_the_page_nonce_and_evaluates_nothing(self):
        response = _client().get(reverse("home"))
        html = response.content.decode()
        assert f"htmx.config.inlineScriptNonce = '{_nonce(response)}';" in html
        assert "htmx.config.allowEval = false;" in html


class TestNonceOutsideThePageContext:
    """A form widget and an inclusion tag are rendered with a context of their
    own, where a context variable would be empty : their script would carry
    ``nonce=""`` and be refused. ``{% csp_nonce %}`` reads the request itself.

    These pages only break on a real instance (help content comes from a data
    migration, a full-page form is reached by opening its link in a new tab),
    which is how the first version of the policy got past the browser audit.
    """

    def test_a_form_widget_script_carries_the_nonce_on_a_full_page(self):
        """The scope tree is a form widget, rendered by the form renderer."""
        response = _client().get(reverse("context:issue-create"))
        html = response.content.decode()
        assert "scope-tree-filter" in html
        nonce = _nonce(response)
        scripts = _inline_scripts(html)
        assert scripts and all(attributes.get("nonce") == nonce for attributes in scripts)

    def test_an_inclusion_tag_script_carries_the_nonce(self):
        """The help dialog is an inclusion tag, shown where help content exists."""
        from helpers.models import HelpContent

        # Present already where the migrations ran (they seed the help content).
        HelpContent.objects.get_or_create(
            key="accounts.action_log_list", language="en",
            defaults={"title": "Action log", "body": "<p>Help</p>"},
        )
        response = _client().get(reverse("accounts:action-log-list"))
        html = response.content.decode()
        assert "window.cairnActions.dismissHelper" in html
        nonce = _nonce(response)
        assert all(attributes.get("nonce") == nonce for attributes in _inline_scripts(html))

    def test_no_nonce_outside_a_request(self):
        from django.template import Context, Template

        assert csp.current_nonce() == ""
        assert Template('<script nonce="{% csp_nonce %}">').render(Context()) == '<script nonce="">'

    def test_the_tag_needs_no_load_in_a_page_template(self):
        assert "core.templatetags.csp" in settings.TEMPLATES[0]["OPTIONS"]["builtins"]


class TestSources:
    def test_by_default_a_page_reaches_no_other_origin(self):
        """No map provider, no geocoder unless the operator names one : the
        policy of a fresh instance lists the instance and nothing else."""
        response = _client().get(reverse("home"))
        assert "http://" not in response[HEADER].replace("ws://testserver", "")
        assert "https://" not in response[HEADER]

    @override_settings(
        MAP_TILE_URL="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        MAP_GEOCODER_URL="https://photon.komoot.io/api/",
    )
    def test_the_map_tiles_and_the_geocoder_are_the_only_other_origins(self):
        policy = _directives(_client().get(reverse("home")))
        # Exact sources, compared as sets : each is a whole origin of the
        # policy, never a fragment of a longer one.
        tiles, geocoder = {"https://tile.openstreetmap.org"}, {"https://photon.komoot.io"}
        assert tiles <= set(policy["img-src"])
        assert geocoder <= set(policy["connect-src"])
        outside = {
            source for sources in policy.values() for source in sources
            if source.split(":", 1)[0] in ("http", "https")
        }
        assert outside == tiles | geocoder

    @override_settings(
        MAP_TILE_URL="https://{s}.tiles.example.org/{z}/{x}/{y}.png?key=abc",
        MAP_TILE_URL_DARK="https://dark.example.net/{z}/{x}/{y}.png",
        MAP_GEOCODER_URL="",
    )
    def test_the_origins_follow_the_settings(self):
        policy = csp.build_policy(RequestFactory().get("/"), "n")
        assert {"https://*.tiles.example.org", "https://dark.example.net"} <= set(policy["img-src"])
        # No geocoder : nothing but the instance and its own WebSocket.
        assert policy["connect-src"] == ["'self'", "ws://testserver", "wss://testserver"]

    @override_settings(MAP_TILE_URL="", MAP_TILE_URL_DARK="", MAP_GEOCODER_URL="")
    def test_an_instance_with_no_map_reaches_no_other_origin(self):
        serialized = csp.serialize(csp.build_policy(RequestFactory().get("/"), "n"))
        assert "http" not in serialized.replace("ws://testserver", "").replace("wss://testserver", "")

    @override_settings(MAP_GEOCODER_URL="")
    def test_the_geocoder_can_be_switched_off(self):
        response = _client().get(reverse("home"))
        assert '"geocoder": ""' in response.content.decode()
        assert _directives(response)["connect-src"] == ["'self'", "ws://testserver", "wss://testserver"]

    def test_a_malformed_url_adds_no_source(self):
        assert csp._origin("not a url") is None
        assert csp._origin("javascript:alert(1)") is None
        assert csp._origin("//example.org/x") is None

    @override_settings(X_FRAME_OPTIONS="SAMEORIGIN")
    def test_framing_follows_the_frame_options_setting(self):
        assert csp.build_policy(RequestFactory().get("/"))["frame-ancestors"] == ["'self'"]


class TestOtherResponseHeaders:
    def test_no_other_site_may_embed_a_page_or_use_the_browser_features(self):
        response = _client().get(reverse("home"))
        assert response["Cross-Origin-Resource-Policy"] == "same-origin"
        permissions = response["Permissions-Policy"]
        for feature in ("camera", "microphone", "geolocation", "payment", "usb"):
            assert f"{feature}=()" in permissions
        # Passkeys must keep working : their feature is not switched off.
        assert "publickey-credentials" not in permissions

    def test_an_api_answer_carries_them_too(self):
        response = _client().get("/api/v1/dependencies/")
        assert response["Cross-Origin-Resource-Policy"] == "same-origin"

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_an_https_only_instance_upgrades_stray_http_references(self):
        policy = csp.build_policy(RequestFactory().get("/"), "n")
        assert "upgrade-insecure-requests" in csp.serialize(policy)
        assert "upgrade-insecure-requests" not in csp.serialize(
            csp.build_policy(RequestFactory().get("/"), "n", exclude={"upgrade-insecure-requests"})
        )

    def test_a_plain_http_instance_does_not(self):
        assert "upgrade-insecure-requests" not in csp.serialize(csp.build_policy(RequestFactory().get("/"), "n"))


class TestModes:
    @override_settings(CSP_MODE="report")
    def test_report_mode_only_reports(self):
        response = _client().get(reverse("home"))
        assert HEADER not in response
        assert "Content-Security-Policy-Report-Only" in response

    @override_settings(CSP_MODE="off")
    def test_off_sends_no_policy(self):
        response = _client().get(reverse("home"))
        assert HEADER not in response and "Content-Security-Policy-Report-Only" not in response

    def test_a_view_can_drop_a_directive_that_cannot_hold_for_it(self):
        """The OAuth consent page is answered by a redirect to the client's
        own address, which ``form-action 'self'`` would refuse."""
        policy = csp.build_policy(RequestFactory().get("/"), "n", exclude={"form-action"})
        assert "form-action" not in policy and "script-src" in policy


class TestTemplatesWriteNoScriptThePolicyRefuses:
    """Static checks over the sources : the browser audit sees the pages it
    visits, these see every template."""

    @staticmethod
    def _sources(*patterns):
        names = subprocess.run(  # noqa: S603, S607 - fixed command, repository files
            ["git", "ls-files", *patterns], cwd=settings.BASE_DIR, capture_output=True, text=True, check=True,
        ).stdout.split()
        for name in names:
            path = settings.BASE_DIR / name
            if name.startswith(("static/vendor/", "docs/")) or "/tests/" in name or not path.is_file():
                continue
            yield name, path.read_text(errors="replace")

    def test_no_inline_event_handler(self):
        """``onclick="..."`` is script in the markup : refused by the policy,
        so the control would silently do nothing. Name an action instead
        (``data-on-click``, ``static/js/cairn/actions.js``)."""
        handler = re.compile(r"""\son[a-z]+\s*=\s*["'][^"']""")
        offenders = []
        for name, text in self._sources("*.html", "*.py"):
            for number, line in enumerate(text.splitlines(), 1):
                if handler.search(line) and "<" in line:
                    offenders.append(f"{name}:{number}")
        assert not offenders, "inline event handlers :\n  " + "\n  ".join(offenders)

    def test_no_inline_script_without_its_nonce(self):
        offenders = []
        for name, text in self._sources("*.html"):
            # Template comments may mention a script tag : they are not markup.
            text = re.sub(r"\{% comment %\}.*?\{% endcomment %\}", "", text, flags=re.S)
            for attributes in _inline_scripts(text):
                if attributes.get("nonce") != "{% csp_nonce %}":
                    offenders.append(f"{name} : <script {attributes}>")
        assert not offenders, "inline scripts without nonce=\"{% csp_nonce %}\" :\n  " + "\n  ".join(offenders)

    def test_nothing_asks_htmx_to_evaluate_an_attribute(self):
        """``hx-on``, a ``js:`` value or a trigger filter are evaluated by
        htmx, which ``allowEval = false`` (and the policy) forbid."""
        evaluated = re.compile(r"""hx-on[:\-=]|hx-vars=|hx-(?:vals|headers)=["']js:|hx-trigger="[^"]*\[[^"]*\]""")
        offenders = [
            f"{name}:{number}"
            for name, text in self._sources("*.html")
            for number, line in enumerate(text.splitlines(), 1)
            if evaluated.search(line) and "{% comment" not in line and not line.strip().startswith(("/*", "*", "in an attribute"))
            and "htmx evaluates nothing" not in line and "(hx-on" not in line
        ]
        assert not offenders, "attributes htmx would evaluate :\n  " + "\n  ".join(offenders)

    def test_no_javascript_url(self):
        offenders = [
            f"{name}:{number}"
            for name, text in self._sources("*.html")
            for number, line in enumerate(text.splitlines(), 1)
            if re.search(r"""(?:href|src|action)=["']\s*javascript:""", line, re.I)
        ]
        assert not offenders, offenders

    def test_every_action_a_template_names_is_registered(self):
        """A typo in ``data-on-click`` would leave a button that does nothing."""
        named, registered = {}, set()
        for name, text in self._sources("*.html", "*.js"):
            for action in re.findall(r"""data-on-(?:click|change|input|keyup|submit)=\\?["']([A-Za-z_]\w*)""", text):
                named.setdefault(action, name)
            registered.update(re.findall(r"(?:cairnActions|actions)\.([A-Za-z_]\w*)\s*=", text))
        missing = {action: where for action, where in named.items() if action not in registered}
        assert len(named) > 20
        assert not missing, f"actions named but never registered : {missing}"

    def test_the_error_pages_need_no_script(self):
        """The 500 page is rendered with no context : it could carry no nonce."""
        for name in ("errors/base.html", "400.html", "403.html", "403_csrf.html", "404.html", "500.html"):
            text = (settings.BASE_DIR / "templates" / name).read_text()
            assert "<script" not in text and "data-on-" not in text, name

    def test_the_action_dispatcher_is_loaded_where_actions_are_named(self):
        for name in ("templates/base.html", "templates/onboarding/base.html", "accounts/templates/accounts/login.html"):
            assert "js/cairn/actions.js" in (settings.BASE_DIR / name).read_text(), name
