# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Sweep of the whole interface on the demo dataset.

Unit tests check what their author thought of. This module checks the rest :
it loads the Voltara Energy demo dataset (``scripts/seed_demo_data.py``, which
exercises every model and field) and then

1. follows every link reachable from the dashboard as a superuser,
2. requests those same pages as an administrator who is not a superuser, and
   as a signed-in user with no permission at all,
3. submits every create and edit form empty, then with invalid values.

No page may answer a server error, and no link printed in a page may lead to a
missing one. The first run of this sweep, done by hand, found a dashboard that
failed for every non-superuser with unrestricted scopes and a form that crashed
on submission, both green in the rest of the suite.

It is also the only test that runs the demo seed, so a schema change that
leaves the seed behind fails here.

The sweep is marked ``sweep`` and takes about a minute; deselect it while
iterating with ``pytest -m "not sweep"``.
"""

import contextlib
import io
import re
import shutil
import tempfile
from collections import deque

import pytest
from django.conf import settings
from django.test import Client, TestCase, override_settings

from core.crawl import SKIP, UUID, links_of, page_type
from core.tests import markup_audit

pytestmark = pytest.mark.sweep

SEED_PATH = settings.BASE_DIR / "scripts" / "seed_demo_data.py"
MEDIA_ROOT = tempfile.mkdtemp(prefix="cairn-sweep-media-")

FORM_URL = re.compile(r"/(?:create|edit|update|new|add)(?:/|$)")

# Records opened per page type : enough to catch a template that breaks on
# some rows only, without opening every record of the dataset.
RECORDS_PER_PAGE_TYPE = 2

# What an invalid submission looks like : wrong types everywhere.
JUNK = {
    "name": "x" * 5000,
    "reference": "x",
    "title": "\x00",
    "scopes": "not-a-uuid",
    "owner": "zzz",
    "due_date": "31/02/2026",
    "start_date": "tomorrow",
    "status": "no-such-status",
    "target_status": "no-such-step",
    "priority": "-1",
}


def crawl(client, start="/"):
    """Follow every link from ``start``. Return ``{url: (status, referer)}``."""
    seen, per_type, visited = set(), {}, {}
    queue = deque([(start, "")])
    while queue:
        url, referer = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        kind = page_type(url)
        per_type[kind] = per_type.get(kind, 0) + 1
        if per_type[kind] > RECORDS_PER_PAGE_TYPE:
            continue
        response = client.get(url)
        visited[url] = (response.status_code, referer)
        if response.status_code in (301, 302):
            target = response.get("Location", "")
            if target.startswith("/") and not SKIP.search(target):
                queue.append((target, url))
            continue
        if "text/html" not in response.get("Content-Type", ""):
            continue
        for link in links_of(response.content.decode("utf-8", "replace")):
            queue.append((link, url))
    return visited


def report(failures):
    """One line per page type, so a broken template is listed once."""
    lines, listed = [], set()
    for status, url, detail in failures:
        key = (status, page_type(url))
        if key not in listed:
            listed.add(key)
            lines.append(f"  {status} {url} {detail}".rstrip())
    return "\n".join(lines)


@override_settings(MEDIA_ROOT=MEDIA_ROOT, ALLOWED_HOSTS=["testserver"])
class SiteSweepTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # The seed is a script, executed the way the onboarding runner does.
        namespace = {"SEED_BASE_DIR": str(settings.BASE_DIR), "__name__": "seed_demo_data"}
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(SEED_PATH.read_text(), str(SEED_PATH), "exec"), namespace)  # noqa: S102

        from accounts.models import Group, User

        cls.superuser = User.objects.filter(is_superuser=True, is_active=True).order_by("created_at").first()
        # Every permission, every scope, but through a group : the profile of a
        # real administrator, which a superuser shortcut never exercises.
        cls.administrator = (
            Group.objects.get(name="Administrateur").users.filter(is_superuser=False, is_active=True).first()
        )
        cls.outsider = User.objects.create_user(
            email="outsider@voltara.example", password="x", first_name="No", last_name="Permission",
        )
        superuser_client = Client(raise_request_exception=False)
        superuser_client.force_login(cls.superuser)
        cls.pages = crawl(superuser_client)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def client_for(self, user):
        client = Client(raise_request_exception=False)
        client.force_login(user)
        return client

    def test_the_crawl_reaches_the_whole_interface(self):
        """Guards the sweep itself : a crawl that stops at the dashboard would
        pass every other test of this class while checking nothing."""
        reached = {page_type(url).split("/")[1] for url in self.pages}
        expected = {"context", "assets", "risks", "compliance", "incidents", "documents",
                    "controls", "reports", "accounts", "kanban", "calendar"}
        assert expected <= reached, f"not reached : {sorted(expected - reached)}"
        assert len(self.pages) > 300, f"only {len(self.pages)} pages crawled"

    def test_no_page_fails_and_no_link_is_broken_for_a_superuser(self):
        failures = [
            (status, url, f"<- {referer}")
            for url, (status, referer) in self.pages.items()
            # 405 : a page legitimately prints the URL of a POST-only endpoint.
            if status >= 400 and status != 405
        ]
        assert not failures, f"{len(failures)} pages failed :\n{report(failures)}"

    def test_no_page_fails_for_an_administrator_who_is_not_a_superuser(self):
        assert self.administrator is not None, "the seed no longer puts a user in the Administrateur group"
        self._assert_no_server_error(self.administrator)

    def test_no_page_fails_for_a_user_with_no_permission(self):
        """Refused or hidden, never broken : a 403 is an answer, a 500 is not."""
        self._assert_no_server_error(self.outsider)

    def _assert_no_server_error(self, user):
        client = self.client_for(user)
        failures = []
        for url, (status, _referer) in self.pages.items():
            if status != 200:
                continue
            response = client.get(url)
            if response.status_code >= 500:
                failures.append((response.status_code, url, ""))
        assert not failures, f"{len(failures)} pages failed for {user.email} :\n{report(failures)}"

    def test_an_audit_folds_its_requirements_by_section(self):
        """Every requirement row of an audit belongs to a section header that
        can fold it : a row with no header would stay hidden or never fold."""
        client = self.client_for(self.superuser)
        audits = [url for url in self.pages if re.fullmatch(r"/compliance/assessments/[0-9a-f-]{36}/", url)]
        assert audits, "the crawl reached no compliance assessment"
        checked = 0
        for url in audits:
            html = client.get(url).content.decode()
            headers = set(re.findall(r'data-group-toggle="([^"]+)"', html))
            rows = set(re.findall(r'<tr data-group="([^"]+)"', html))
            if not rows:
                continue
            checked += 1
            assert rows <= headers, f"{url} : rows without a section header {sorted(rows - headers)}"
        assert checked, "no audit with requirement rows in the demo dataset"

    def test_no_page_has_a_markup_accessibility_defect(self):
        """Every image has an alternative, every control a name and a label,
        every acting link an href (see ``markup_audit``)."""
        client = self.client_for(self.superuser)
        offenders, seen = {}, set()
        for url, (status, _referer) in self.pages.items():
            kind = page_type(url)
            if status != 200 or kind in seen:
                continue
            seen.add(kind)
            response = client.get(url)
            if "text/html" not in response.get("Content-Type", ""):
                continue
            for problem in markup_audit.problems(response.content.decode("utf-8", "replace")):
                # One line per defect, not per record it is rendered for.
                key = re.sub(r"\d+", "N", UUID.sub("<id>", problem))
                offenders.setdefault(key, kind)
        assert len(seen) > 150, f"only {len(seen)} page types checked"
        listing = "\n".join(f"  {kind}\n      {problem}" for problem, kind in sorted(offenders.items(), key=lambda item: item[1]))
        assert not offenders, f"{len(offenders)} accessibility defects in the markup :\n{listing}"

    def test_no_form_select_opens_on_a_row_of_dashes(self):
        client = self.client_for(self.superuser)
        offenders, seen = [], set()
        for url, (status, _referer) in self.pages.items():
            kind = page_type(url)
            if status != 200 or not FORM_URL.search(url) or kind in seen:
                continue
            seen.add(kind)
            if ">---------<" in client.get(url).content.decode("utf-8", "replace"):
                offenders.append(kind)
        assert not offenders, "forms printing Django's dashed empty option :\n  " + "\n  ".join(offenders)

    def test_no_form_fails_on_an_empty_or_invalid_submission(self):
        """A form answers its errors (200) or refuses (4xx); it never crashes."""
        client = self.client_for(self.superuser)
        forms = [url for url, (status, _r) in self.pages.items() if status == 200 and FORM_URL.search(url)]
        assert len(forms) > 100, f"only {len(forms)} forms found"
        failures = []
        for url in forms:
            for label, payload in (("empty", {}), ("invalid", JUNK)):
                response = client.post(url, payload)
                if response.status_code >= 500:
                    failures.append((response.status_code, url, f"({label} submission)"))
        assert not failures, f"{len(failures)} form submissions failed :\n{report(failures)}"
