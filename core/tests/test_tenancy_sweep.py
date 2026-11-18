# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Sweep of scope tenancy on the demo dataset, through the surfaces themselves.

``core/tests/test_scoping.py`` checks the rule and the structure : the helper
that filters, the mixin a class must carry. This module checks the result. It
loads the Voltara Energy demo dataset, signs in a user who holds **every
permission** but is given **one scope**, and asks each surface for what lies
outside that scope :

1. every ``list_`` tool of the MCP server, and every tool that takes an
   identifier, given the identifier of a record out of reach;
2. every list and every single-record route of the REST API;
3. every page of the web interface that shows one record.

Nothing out of reach may come back. With every permission granted, a refusal
can only come from the scopes : a tool or a route that answers is a leak.

It exists because a check on the helper once passed while sixty families of
MCP tools were registered with the scope filter switched off : a user limited
to one scope listed, read, changed and deleted the risks and the requirements
of every other. The helper was right, the tools did not call it.

Marked ``sweep`` like the interface sweep (it loads the same dataset).
"""

import contextlib
import io
import json
import re
import shutil
import tempfile

import pytest
from django.apps import apps
from django.conf import settings
from django.test import Client, TestCase, override_settings

from core.scoping import filter_queryset_by_scopes, resolve_scope_lookup, user_can_reach

pytestmark = pytest.mark.sweep

SEED_PATH = settings.BASE_DIR / "scripts" / "seed_demo_data.py"
MEDIA_ROOT = tempfile.mkdtemp(prefix="cairn-tenancy-media-")
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

# A tool that answers when handed an identifier out of reach, and why that is
# not a record served across scopes.
MCP_TOOLS_THAT_MAY_ANSWER = {}

# A REST route that serves a scoped model another way, and why.
API_ROUTES_SCOPED_ANOTHER_WAY = {
    "policy-acknowledgements": "a notice is readable by its addressee or within the scopes (RG-DOC-22)",
}


def _has_uuid_key(model):
    from django.db.models import UUIDField

    return isinstance(model._meta.pk, UUIDField)


@override_settings(MEDIA_ROOT=MEDIA_ROOT, ALLOWED_HOSTS=["testserver"])
class TenancySweepTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        namespace = {"SEED_BASE_DIR": str(settings.BASE_DIR), "__name__": "seed_demo_data"}
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(SEED_PATH.read_text(), str(SEED_PATH), "exec"), namespace)  # noqa: S102

        from accounts.models import Group, Permission, User
        from context.models import Scope

        # One scope among several, and every permission : whatever is refused
        # is refused by the scopes.
        cls.scope = Scope.objects.filter(parent_scope__isnull=False).order_by("name").first()
        assert cls.scope is not None, "the seed no longer builds child scopes"
        cls.user = User.objects.create_user(
            email="one.scope@voltara.example", password="x", first_name="One", last_name="Scope",
        )
        group = Group.objects.create(name="Every permission, one scope")
        group.permissions.set(Permission.objects.all())
        group.allowed_scopes.set([cls.scope])
        group.users.add(cls.user)
        allowed = cls.user.get_allowed_scope_ids()
        assert allowed == {cls.scope.pk}, allowed

        # What the registers hide from this user, per model : the queryset rule
        # (lists, REST, MCP). And what they may not open by its address : the
        # record rule, which leaves a record filed under nothing reachable.
        cls.hidden, cls.out_of_reach = {}, {}
        for model in apps.get_models():
            if resolve_scope_lookup(model) is None or model._meta.proxy or not model._meta.managed:
                continue
            if model.__name__.startswith("Historical"):
                continue
            everything = model._base_manager.all()
            shown = set(filter_queryset_by_scopes(everything, allowed).values_list("pk", flat=True))
            hidden = [pk for pk in everything.values_list("pk", flat=True) if pk not in shown]
            if hidden:
                cls.hidden[model] = hidden
                closed = [
                    obj.pk for obj in everything.filter(pk__in=hidden[:25]) if not user_can_reach(cls.user, obj)
                ]
                if closed:
                    cls.out_of_reach[model] = closed
        # Identifiers compared across models are the UUID ones : the number 3
        # is a record of every model keyed by a counter.
        cls.hidden_ids = {
            str(pk) for model, pks in cls.hidden.items() if _has_uuid_key(model) for pk in pks
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    # ── The sweep is worth something ────────────────────────────────────────

    def test_the_dataset_holds_records_out_of_reach_in_every_module(self):
        """A sweep with nothing to find would pass whatever the surfaces do."""
        modules = {model._meta.app_label for model in self.hidden}
        expected = {"assets", "compliance", "context", "risks", "incidents", "documents", "controls", "reports"}
        assert expected <= modules, f"nothing out of reach in : {sorted(expected - modules)}"
        assert len(self.hidden) >= 40, f"only {len(self.hidden)} models hold a record out of reach"
        assert len(self.hidden_ids) >= 500, f"only {len(self.hidden_ids)} records out of reach"

    # ── MCP ─────────────────────────────────────────────────────────────────

    def _mcp(self):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        server = McpServer()
        register_all_tools(server)
        return server

    def _call(self, server, tool, arguments):
        """``(answered, text)`` : whether the tool answered something else than an error."""
        result = server.handle_request(json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        }), self.user)
        if "error" in result:
            return False, json.dumps(result["error"])
        payload = result.get("result") or {}
        text = "".join(part.get("text", "") for part in payload.get("content", []))
        if payload.get("isError"):
            return False, text
        try:
            body = json.loads(text)
        except ValueError:
            return True, text
        # A JSON-RPC error carried in the text is an error as well.
        if isinstance(body, dict) and set(body) >= {"jsonrpc", "error"}:
            return False, text
        return True, text

    def test_no_mcp_list_tool_returns_a_record_out_of_reach(self):
        server = self._mcp()
        tools = sorted(name for name in server._tools if name.startswith("list_"))
        assert len(tools) > 80, f"only {len(tools)} list tools found"
        leaks = []
        for tool in tools:
            answered, text = self._call(server, tool, {"limit": 100})
            if not answered:
                continue
            try:
                body = json.loads(text)
            except ValueError:
                continue
            rows = body.get("items", body) if isinstance(body, dict) else body
            if not isinstance(rows, list):
                continue
            listed = {str(row.get("id")) for row in rows if isinstance(row, dict)}
            found = listed & self.hidden_ids
            if found:
                leaks.append(f"{tool} : {len(found)} of {len(listed)} rows are out of reach")
        assert not leaks, "MCP list tools serve records of another scope :\n  " + "\n  ".join(leaks)

    def test_no_mcp_tool_answers_for_a_record_out_of_reach(self):
        """Every tool that takes an identifier, handed one of each model out of reach.

        The tools that change or delete are called too : none may answer, and
        nothing out of reach may have moved afterwards.
        """
        import logging

        server = self._mcp()
        samples = {model: pks[0] for model, pks in self.hidden.items() if _has_uuid_key(model)}
        before = {model: model._base_manager.filter(pk__in=pks).count() for model, pks in self.hidden.items()}
        answered_for = []
        calls = 0
        # An identifier of the wrong model is an error the server logs : thousands
        # of them are expected here.
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        for tool in sorted(server._tools):
            # A list filtered on a record out of reach is checked by its rows, above.
            if tool.startswith("list_") or tool in MCP_TOOLS_THAT_MAY_ANSWER:
                continue
            schema = server._tools[tool].get("inputSchema") or {}
            properties = schema.get("properties") or {}
            names = [name for name in properties if name == "id" or name.endswith("_id")]
            for name in names:
                for model, pk in samples.items():
                    calls += 1
                    answered, text = self._call(server, tool, {name: str(pk)})
                    if answered and str(pk) in text:
                        answered_for.append(f"{tool}({name}=<{model._meta.label}>)")
        assert calls > 5000, f"only {calls} calls made"
        assert not answered_for, (
            f"{len(answered_for)} MCP calls answered with a record of another scope :\n  "
            + "\n  ".join(sorted(set(answered_for))[:40])
        )
        after = {model: model._base_manager.filter(pk__in=pks).count() for model, pks in self.hidden.items()}
        gone = [model._meta.label for model in before if after[model] != before[model]]
        assert not gone, f"records out of reach were deleted through MCP : {gone}"

    # ── REST ────────────────────────────────────────────────────────────────

    def _api(self):
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(self.user)
        return client

    def _api_routes(self):
        """``[(list url, model)]`` for the list routes of the API that take no argument."""
        from django.urls import get_resolver

        routes = []

        def walk(patterns, prefix=""):
            for pattern in patterns:
                if hasattr(pattern, "url_patterns"):
                    walk(pattern.url_patterns, prefix + str(pattern.pattern))
                    continue
                cls = getattr(pattern.callback, "cls", None)
                actions = getattr(pattern.callback, "actions", None) or {}
                path = prefix + str(pattern.pattern)
                if cls is None or actions.get("get") != "list" or "<" in path or "(?P" in path:
                    continue
                queryset = getattr(cls, "queryset", None)
                model = queryset.model if queryset is not None else None
                routes.append(("/" + path.lstrip("^").rstrip("$"), model, getattr(pattern, "name", "") or ""))

        walk(get_resolver().url_patterns)
        return [route for route in routes if route[0].startswith("/api/")]

    def test_no_api_list_returns_a_record_out_of_reach(self):
        api = self._api()
        routes = self._api_routes()
        assert len(routes) > 60, f"only {len(routes)} list routes found"
        leaks = []
        for url, _model, name in routes:
            if any(exception in url for exception in API_ROUTES_SCOPED_ANOTHER_WAY):
                continue
            response = api.get(url, {"page_size": 200})
            if response.status_code != 200:
                continue
            try:
                payload = response.json()
            except ValueError:
                continue
            rows = payload
            for key in ("data", "results"):
                if isinstance(rows, dict) and key in rows:
                    rows = rows[key]
            if not isinstance(rows, list):
                continue
            listed = {str(row.get("id")) for row in rows if isinstance(row, dict)}
            found = listed & self.hidden_ids
            if found:
                leaks.append(f"{url} : {len(found)} of {len(listed)} rows are out of reach")
        assert not leaks, "API lists serve records of another scope :\n  " + "\n  ".join(leaks)

    def test_no_api_route_serves_a_record_out_of_reach(self):
        api = self._api()
        served = []
        checked = 0
        for url, model, _name in self._api_routes():
            if model is None or model not in self.hidden:
                continue
            if any(exception in url for exception in API_ROUTES_SCOPED_ANOTHER_WAY):
                continue
            for pk in self.hidden[model][:3]:
                checked += 1
                response = api.get(f"{url.rstrip('/')}/{pk}/")
                if response.status_code == 200:
                    served.append(f"{url}<id> ({model._meta.label})")
        assert checked > 60, f"only {checked} records asked for"
        assert not served, "API routes serve a record of another scope :\n  " + "\n  ".join(sorted(set(served)))

    # ── Web ─────────────────────────────────────────────────────────────────

    def _record_pages(self):
        """``[(url name, model)]`` for the pages that take one record of a scoped model."""
        from django.urls import get_resolver

        pages = []

        def walk(patterns, namespace=""):
            for pattern in patterns:
                if hasattr(pattern, "url_patterns"):
                    inner = f"{namespace}{pattern.namespace}:" if getattr(pattern, "namespace", None) else namespace
                    walk(pattern.url_patterns, inner)
                    continue
                view = getattr(pattern.callback, "view_class", None)
                model = getattr(view, "model", None)
                converters = getattr(pattern.pattern, "converters", {})
                if model is None or list(converters) != ["pk"] or not pattern.name:
                    continue
                pages.append((f"{namespace}{pattern.name}", model))

        walk(get_resolver().url_patterns)
        return pages

    def test_no_page_shows_a_record_out_of_reach(self):
        """Every page that takes one record (its page, its edit form, its deletion), asked by its address."""
        from django.urls import NoReverseMatch, reverse

        client = Client(raise_request_exception=False)
        client.force_login(self.user)
        shown = []
        checked = 0
        for name, model in self._record_pages():
            for pk in self.out_of_reach.get(model, [])[:2]:
                try:
                    url = reverse(name, kwargs={"pk": pk})
                except NoReverseMatch:
                    continue
                checked += 1
                response = client.get(url)
                if response.status_code == 200:
                    shown.append(f"{name} ({model._meta.label})")
        assert checked > 150, f"only {checked} pages asked for"
        assert not shown, "pages show a record of another scope :\n  " + "\n  ".join(sorted(set(shown)))

    def test_no_creation_form_offers_a_record_out_of_reach(self):
        """Every form that takes no record : none of its choices names a record of another scope."""
        from django.urls import get_resolver
        from django.views.generic.edit import FormMixin

        urls = []

        def walk(patterns, prefix=""):
            for pattern in patterns:
                if hasattr(pattern, "url_patterns"):
                    walk(pattern.url_patterns, prefix + str(pattern.pattern))
                    continue
                view = getattr(pattern.callback, "view_class", None)
                path = prefix + str(pattern.pattern)
                if view is not None and issubclass(view, FormMixin) and "<" not in path and "(?P" not in path:
                    urls.append("/" + path.lstrip("^").rstrip("$"))

        walk(get_resolver().url_patterns)
        assert len(urls) >= 40, f"only {len(urls)} creation forms found"
        client = Client(raise_request_exception=False)
        client.force_login(self.user)
        choice = re.compile(r'value="(' + UUID.pattern + r')"')
        offered = []
        for url in sorted(set(urls)):
            for headers in ({}, {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "drawer-form-content"}):
                response = client.get(url, **headers)
                if response.status_code != 200:
                    continue
                found = set(choice.findall(response.content.decode(errors="replace"))) & self.hidden_ids
                if found:
                    offered.append(f"{url} : {len(found)} choices out of reach")
                    break
        assert not offered, "forms offer records of another scope :\n  " + "\n  ".join(offered)

    def test_no_register_lists_a_record_out_of_reach(self):
        """Every list page of a scoped model : none of its rows links to a record the registers hide."""
        from django.urls import get_resolver
        from django.views.generic.list import MultipleObjectMixin

        registers = []

        def walk(patterns, prefix=""):
            for pattern in patterns:
                if hasattr(pattern, "url_patterns"):
                    walk(pattern.url_patterns, prefix + str(pattern.pattern))
                    continue
                view = getattr(pattern.callback, "view_class", None)
                path = prefix + str(pattern.pattern)
                if view is None or not issubclass(view, MultipleObjectMixin) or "<" in path or "(?P" in path:
                    continue
                model = getattr(view, "model", None)
                if model is None and getattr(view, "queryset", None) is not None:
                    model = view.queryset.model
                if model in self.hidden and _has_uuid_key(model):
                    registers.append(("/" + path.lstrip("^").rstrip("$"), model))

        walk(get_resolver().url_patterns)
        assert len(registers) > 40, f"only {len(registers)} registers found"
        client = Client(raise_request_exception=False)
        client.force_login(self.user)
        leaks = []
        for url, model in sorted(set(registers), key=lambda item: item[0]):
            response = client.get(url)
            if response.status_code != 200:
                continue
            hidden = {str(pk) for pk in self.hidden[model]}
            found = set(UUID.findall(response.content.decode(errors="replace"))) & hidden
            if found:
                leaks.append(f"{url} : {len(found)} rows of {model._meta.label} out of reach")
        assert not leaks, "registers list records of another scope :\n  " + "\n  ".join(leaks)
