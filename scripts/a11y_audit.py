#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Audit the rendered pages against WCAG 2.2 AA with axe-core.

The test suite checks what can be read from the markup and the style sheets
(``core/tests/test_contrast.py``, ``core/tests/test_accessibility.py``). What
a page really looks like once the cascade, the theme and the scripts have run
(the contrast of a badge on a tinted row, the name of a button drawn by a
script, the size of a target) only a browser can tell. This script opens every
page of the screenshot set, in the light and the dark theme, runs axe-core on
it and fails on any violation of a level A or AA rule. A dialog and a filter
panel are opened first (a hidden one is skipped by axe), and a few pages are
audited again at a phone's width.

The same visit tells whether the page *works* : anything the browser refused
under the Content Security Policy (``core/csp.py``) and any error a script
threw fail the page too. An inline handler or a script without its nonce
passes every server-side test and does nothing in a browser.

    python scripts/a11y_audit.py --base-url http://127.0.0.1:8001 --axe axe.min.js
    python scripts/a11y_audit.py --axe axe.min.js --theme dark --only calendar dashboard

Prerequisites : a running instance serving the demo dataset, built by the
real migrations (the help content, the default lifecycles and the reference
data come from data migrations : an instance without them hides the pages'
real content, and hid a refused script once), ``google-chrome-stable`` on the PATH, and a copy
of ``axe.min.js`` (``npm pack axe-core`` : the CI workflow pins the version).
axe-core is not vendored : it is a development tool, never served to a user.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import capture_screenshots as shots  # noqa: E402

DEBUG_PORT = 9334
# Tall enough for the longest open sidebar section to clear the pinned user
# card : a link sliding under it is a scroll position, not a small target.
WIDTH, HEIGHT = 1440, 1400

# The rules a WCAG 2.2 AA conformance claim rests on. axe's "best-practice"
# rules are advice, reported by --best-practice and never failing.
WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]

# Pages opened without a session : what a visitor sees before signing in.
PUBLIC_PAGES: dict[str, str] = {
    "login": "/accounts/login/",
    "trust-center-public": "/trust/",
}

# Signed-in pages on top of the screenshot set : a form page, and the catalogue
# of components (a component broken there is broken everywhere it is used).
EXTRA_PAGES: dict[str, str] = {
    "risk-form": "/risks/register/create/",
    # A form opened as a page of its own : its scope picker is a form widget,
    # whose script is rendered outside the page's template context.
    "issue-form": "/context/issues/create/",
    "tags": "/context/tags/",
    "styleguide": "/styleguide/",
}

# Records audited on top of the screenshot set : the first one of a list, or
# the page a list leads to in several steps (see shots.first_link).
# The test of the demo dataset whose latest run is still being recorded.
CONTROL_TEST = "/controls/tests/?q=Patch+SLA"

EXTRA_DETAILS: dict[str, tuple[str, str | tuple[str, ...]]] = {
    # The permission matrix : a few hundred checkboxes behind folded sections.
    "group-detail": ("/accounts/groups/", "table tbody tr td a"),
    # The pages of an EBIOS RM study : each workshop is a page of its own
    # cards and rows. Workshop 1 is in the screenshot set ("ebios-workshop").
    **{
        f"ebios-workshop-{number}": shots.EBIOS_STUDY + (shots.workshop_link(number),)
        for number in (0, 2, 3, 4, 5)
    },
    # A test of a control, and a run of it still in progress : the page that
    # lists what the run lacks before it is submitted. Reached from the test.
    "control-test-detail": (CONTROL_TEST, "table tbody tr td a"),
    "control-test-run-detail": (CONTROL_TEST, ("table tbody tr td a", "#runs table tbody tr td a")),
    # A version of a document, reached from the page of the document.
    "document-version-detail": ("/documents/policies/", ("table tbody tr td a", "#versions table tbody tr td a")),
    # An acknowledgement campaign and its audience.
    "campaign-detail": ("/documents/campaigns/", "table tbody tr td a"),
    # A reported security event : its assessment and what it still needs.
    "security-event-detail": ("/incidents/events/", "table tbody tr td a"),
    # A response plan : its procedure, folded annexes and what it still needs.
    "response-plan-detail": ("/incidents/response-plans/", "table tbody tr td a"),
    # An evidence item, reached from the incident file : its acquisition, seal
    # and chain of custody. The seeded portal incident holds evidence.
    "evidence-detail": ("/incidents/?q=exposed%20invoices", ("table tbody tr td a", 'a[href*="/incidents/evidence/"]')),
    # Its post-incident review, approved and waiting for its verdict.
    "review-detail": ("/incidents/?q=exposed%20invoices", ("table tbody tr td a", 'a[href*="/incidents/post-incident-reviews/"]')),
    # A reporting authority of the catalogue : its filing channel and procedure.
    "reporting-authority-detail": ("/incidents/reporting-authorities/", "table tbody tr td a"),
    # An obligation template : its clock, its trigger conditions, its checklist.
    "obligation-template-detail": ("/incidents/obligation-templates/", "table tbody tr td a"),
    # The personal data qualification of the seeded portal incident.
    "breach-detail": ("/incidents/?q=exposed%20invoices", ("table tbody tr td a", 'a[href*="/incidents/personal-data-breaches/"]')),
    # A notification obligation : its clock, its decision and its filings.
    "notification-detail": ("/incidents/notifications/", "table tbody tr td a"),
    # A management review : what its closure waits for, its cards and its decisions.
    "management-review-detail": ("/reports/management-reviews/", "table tbody tr td a"),
    # A decision of a management review, reached from the closed seeded review, which holds decisions.
    "decision-detail": ("/reports/management-reviews/?status=closed", ("table tbody tr td a", 'a[href*="/reports/decisions/"]')),
}

# What a page only shows after a click : a hidden dialog or panel is skipped by
# axe, so it is opened first. name -> (path, script that opens it).
OPEN_STATES: dict[str, tuple[str, str]] = {
    "edit-dialog": (
        "/assets/suppliers/",
        "document.querySelector('a[hx-target=\"#drawer-form-content\"]').click()",
    ),
    "filter-panel": ("/risks/register/", "document.querySelector('.list-filter-toggle').click()"),
    # The icon rail, reached through a declarative action (data-on-click) :
    # it only folds if the action dispatcher runs under the policy.
    "sidebar-rail": ("/context/scopes/", "document.querySelector('.sidebar-collapse-toggle').click()"),
    "calendar-year": ("/calendar/", "document.querySelector('#viewToggle [data-view=year]').click()"),
    # Where the product states its own accessibility : the statement is held
    # to what it says.
    "about-dialog": ("/context/scopes/", "document.querySelector('[data-bs-target=\"#aboutModal\"]').click()"),
}

# Pages audited again at a phone's width, where the layout stacks and the
# targets sit closer together.
PHONE = (390, 844)
PHONE_PAGES: dict[str, str] = {
    "dashboard-phone": "/",
    "risk-register-phone": "/risks/register/",
    "calendar-phone": "/calendar/",
}
# Records audited again at that width : name -> the record of the lists above.
# A risk, and a workshop page, whose rows carry their own rows.
PHONE_DETAILS: dict[str, str] = {
    "risk-detail-phone": "risk-detail",
    "ebios-workshop-phone": "ebios-workshop-3",
}

# Installed before any script of the page runs : what the browser refused
# under the Content Security Policy (core/csp.py), and what a script threw.
# Either one means a page that looks right and does not work.
WATCH_PAGE = """
window.__pageIssues = [];
document.addEventListener('securitypolicyviolation', function (e) {
  window.__pageIssues.push('policy : ' + e.violatedDirective + ' refused ' + (e.blockedURI || 'inline code') +
    (e.sourceFile ? ' (' + e.sourceFile.split('/').slice(-1)[0] + ':' + e.lineNumber + ')' : ''));
});
window.addEventListener('error', function (e) {
  window.__pageIssues.push('script error : ' + e.message);
});
window.addEventListener('unhandledrejection', function (e) {
  window.__pageIssues.push('script error : ' + String(e.reason));
});
"""

RUN_AXE = """
(async () => {
  const result = await axe.run(document, {
    runOnly: {type: 'tag', values: %(tags)s},
    resultTypes: ['violations'],
  });
  return JSON.stringify(result.violations.map(v => ({
    id: v.id, impact: v.impact, help: v.help,
    nodes: v.nodes.map(n => ({
      target: n.target.join(' '),
      html: n.html.slice(0, 200),
      why: n.any.concat(n.all, n.none).map(c => c.message).join(' | ').slice(0, 300),
    })),
  })));
})()
"""


def start_chrome(profile: Path) -> subprocess.Popen:
    return subprocess.Popen(
        [
            "google-chrome-stable", "--headless=new", "--no-sandbox", "--disable-gpu",
            "--disable-dev-shm-usage", "--hide-scrollbars",
            f"--remote-debugging-port={DEBUG_PORT}", f"--user-data-dir={profile}",
            f"--window-size={WIDTH},{HEIGHT}", "about:blank",
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def evaluate(devtools, expression: str, *, await_promise: bool = False):
    result = devtools.call("Runtime.evaluate", {
        "expression": expression, "returnByValue": True, "awaitPromise": await_promise,
    })
    return result.get("result", {}).get("result", {}).get("value")


def open_page(devtools, url: str, settle: float) -> None:
    """Navigate and wait for the page to finish loading, then for its scripts."""
    devtools.call("Page.navigate", {"url": url})
    deadline = time.monotonic() + 30
    time.sleep(0.3)
    while time.monotonic() < deadline:
        if evaluate(devtools, "document.readyState") == "complete":
            break
        time.sleep(0.2)
    time.sleep(settle)


def audit(devtools, axe_source: str, tags: list[str]) -> list[dict]:
    evaluate(devtools, axe_source)
    raw = evaluate(devtools, RUN_AXE % {"tags": json.dumps(tags)}, await_promise=True)
    if raw is None:
        raise RuntimeError("axe-core did not return a result")
    return json.loads(raw)


def set_theme(devtools, theme: str) -> None:
    # Reduced motion : the entrance animations would otherwise be measured
    # half-way through their fade.
    devtools.call("Emulation.setEmulatedMedia", {"features": [
        {"name": "prefers-color-scheme", "value": theme},
        {"name": "prefers-reduced-motion", "value": "reduce"},
    ]})


def report(name: str, theme: str, url: str, violations: list[dict], issues: list[str]) -> int:
    count = sum(len(v["nodes"]) for v in violations) + len(issues)
    if not count:
        print(f"  ok    {name} ({theme})")
        return 0
    print(f"  FAIL  {name} ({theme}) : {count} defect(s)  {url}")
    for issue in issues[:8]:
        print(f"        {issue[:220]}")
    for violation in violations:
        print(f"        {violation['id']} [{violation['impact']}] {violation['help']} "
              f"x{len(violation['nodes'])}")
        for node in violation["nodes"][:3]:
            print(f"          {node['target'][:110]}")
            print(f"            {node['why'][:200]}")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--axe", type=Path, required=True, help="Path to axe.min.js.")
    parser.add_argument("--theme", choices=("light", "dark", "both"), default="both")
    parser.add_argument("--only", nargs="*", help="Audit only these page names.")
    parser.add_argument("--best-practice", action="store_true",
                        help="Also report axe's best-practice rules (they never fail the run).")
    parser.add_argument("--report", type=Path, help="Write the full result as JSON.")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    axe_source = args.axe.read_text(encoding="utf-8")
    themes = ["light", "dark"] if args.theme == "both" else [args.theme]
    wanted = set(args.only) if args.only else None

    def selected(name: str) -> bool:
        return wanted is None or name in wanted

    cookie_name, cookie_value = shots.build_session()
    shots.DEBUG_PORT = DEBUG_PORT

    results: dict[str, dict] = {}
    failures = advice = 0
    profile = Path(tempfile.mkdtemp(prefix="cairn-a11y-"))
    chrome = start_chrome(profile)
    try:
        devtools = shots.DevTools(shots.debugger_url())
        for method in ("Network.enable", "Page.enable", "Runtime.enable"):
            devtools.call(method)
        devtools.call("Page.addScriptToEvaluateOnNewDocument", {"source": WATCH_PAGE})

        def viewport(width: int, height: int, mobile: bool) -> None:
            devtools.call("Emulation.setDeviceMetricsOverride",
                          {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": mobile})

        viewport(WIDTH, HEIGHT, False)

        def run(name: str, url: str, theme: str, settle: float, action: str | None = None,
                shell: bool = True) -> None:
            nonlocal failures, advice
            open_page(devtools, url, settle)
            # An error page has nothing to fail on : it would pass for the
            # page it stands in for. A signed-in page always has the shell.
            if shell and not evaluate(devtools, "!!document.getElementById('page-shell')"):
                print(f"  FAIL  {name} ({theme}) : the page did not render  {url}")
                results[f"{name}:{theme}"] = {"url": url, "violations": [], "rendered": False}
                failures += 1
                return
            if action:
                evaluate(devtools, action)
                time.sleep(2.0)  # the request, the swap and the opening transition
            violations = audit(devtools, axe_source, WCAG_TAGS)
            issues = sorted(set(json.loads(evaluate(devtools, "JSON.stringify(window.__pageIssues || [])") or "[]")))
            results[f"{name}:{theme}"] = {"url": url, "violations": violations, "issues": issues}
            failures += report(name, theme, url, violations, issues)
            if args.best_practice:
                for item in audit(devtools, axe_source, ["best-practice"]):
                    advice += len(item["nodes"])
                    print(f"        advice : {item['id']} x{len(item['nodes'])} ({item['help']})")

        def missing(name: str, theme: str) -> None:
            """A record the demo dataset no longer leads to is a page nobody audits : it fails."""
            nonlocal failures
            print(f"  FAIL  {name} ({theme}) : no record to open")
            results[f"{name}:{theme}"] = {"url": None, "violations": [], "rendered": False}
            failures += 1

        print(f"Auditing {base} with axe-core ({', '.join(WCAG_TAGS)})")
        # Public pages first, before the session cookie exists.
        for theme in themes:
            set_theme(devtools, theme)
            for name, path in PUBLIC_PAGES.items():
                if selected(name):
                    run(name, base + path, theme, 1.0, shell=False)

        devtools.call("Network.setCookie", {"name": cookie_name, "value": cookie_value, "url": base})
        # Detail pages are found once : the record ids differ between datasets.
        details = {}
        # A record audited at a phone's width only is still looked for.
        needed_by_phone = {record for name, record in PHONE_DETAILS.items() if selected(name)}
        for name, (path, selector, _wait) in shots.DETAIL_SHOTS.items():
            if selected(name) or name in needed_by_phone:
                details[name] = shots.first_link(devtools, base, path, selector)
        for name, (path, selector) in EXTRA_DETAILS.items():
            if selected(name) or name in needed_by_phone:
                details[name] = shots.first_link(devtools, base, path, selector)

        for theme in themes:
            set_theme(devtools, theme)
            for name, (path, wait) in shots.SHOTS.items():
                if selected(name):
                    # A chart-heavy page (a long screenshot wait) gets longer to draw.
                    run(name, base + path, theme, 2.5 if wait > 5 else 1.0,
                        shell=path not in PUBLIC_PAGES.values())
            for name, path in EXTRA_PAGES.items():
                if selected(name):
                    run(name, base + path, theme, 1.0)
            for name, url in details.items():
                if not selected(name):
                    continue
                if url:
                    run(name, url, theme, 1.5)
                else:
                    missing(name, theme)
            for name, (path, action) in OPEN_STATES.items():
                if selected(name):
                    run(name, base + path, theme, 1.0, action)
            viewport(*PHONE, True)
            for name, path in PHONE_PAGES.items():
                if selected(name):
                    run(name, base + path, theme, 2.5 if path == "/" else 1.0)
            for name, record in PHONE_DETAILS.items():
                if not selected(name):
                    continue
                if details.get(record):
                    run(name, details[record], theme, 1.5)
                else:
                    missing(name, theme)
            viewport(WIDTH, HEIGHT, False)
    finally:
        chrome.terminate()
        shutil.rmtree(profile, ignore_errors=True)

    if args.report:
        args.report.write_text(json.dumps(results, indent=1), encoding="utf-8")
    pages = len(results)
    if failures:
        print(f"\n{failures} defect(s) across {pages} page renderings "
              "(WCAG 2.2 A/AA rules, Content Security Policy violations, script errors).")
        return 1
    print(f"\nNo WCAG 2.2 A/AA violation, no policy violation and no script error across {pages} page renderings."
          + (f" {advice} best-practice remark(s)." if args.best_practice else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
