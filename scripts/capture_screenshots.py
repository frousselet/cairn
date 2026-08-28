#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Capture the documentation screenshot set from a running Cairn instance.

Every image in ``docs/screenshots/`` is produced by this script, at the project
standard of **2560x1440** (16:9, 1440p), so the set stays visually consistent
from one release to the next instead of drifting as people take ad hoc captures.

It drives headless Chrome over the DevTools Protocol rather than the
``--screenshot`` command line flag, because the flag cannot set a cookie and
every page worth capturing is behind a login. The session is created directly
through Django for an existing superuser, so no password is needed.

    python scripts/capture_screenshots.py --base-url http://127.0.0.1:8001
    python scripts/capture_screenshots.py --only dashboard incidents

Prerequisites : a running instance serving the demo dataset, and
``google-chrome-stable`` on the PATH.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO / "docs" / "screenshots"

WIDTH, HEIGHT = 2560, 1440
DEBUG_PORT = 9333

# Help banners are guidance for a first-time user, not part of the screen being
# documented, and they push the real content down the page.
CLEAN_JS = "document.querySelectorAll('.help-banner').forEach(e => e.remove());"

# name -> (path, seconds to settle). The wait is per page rather than global:
# a chart-heavy page needs longer than a list, and padding every capture to the
# slowest one turns a two-minute run into a ten-minute one.
SHOTS: dict[str, tuple[str, float]] = {
    "dashboard": ("/", 8),
    "calendar": ("/calendar/", 5),
    "tasks-board": ("/kanban/", 5),
    "scopes": ("/context/scopes/", 4),
    "objectives": ("/context/objectives/", 4),
    "indicators": ("/context/indicators/organizational/", 6),
    "essential-assets": ("/assets/essential/", 4),
    "support-assets": ("/assets/support/", 4),
    "suppliers": ("/assets/suppliers/", 4),
    "dependency-graph": ("/assets/dependency-graph/", 7),
    "risk-register": ("/risks/register/", 4),
    "risk-assessment": ("/risks/assessments/", 4),
    "compliance-frameworks": ("/compliance/frameworks/", 4),
    "compliance-assessment": ("/compliance/assessments/", 4),
    "nonconformities": ("/compliance/findings/", 4),
    "action-plans": ("/compliance/action-plans/", 4),
    "incidents": ("/incidents/", 4),
    "security-events": ("/incidents/events/", 4),
    "notification-obligations": ("/incidents/notifications/", 4),
    "management-reviews": ("/reports/management-reviews/", 4),
    "trust-center": ("/trust/", 5),
    "groups": ("/accounts/groups/", 4),
    "users": ("/accounts/users/", 4),
    "lifecycles": ("/config/lifecycles/", 4),
}

# Detail pages are captured from the first record of a list, since the record
# ids differ between datasets. name -> (list path, link selector, seconds).
DETAIL_SHOTS: dict[str, tuple[str, str, float]] = {
    "action-plan-detail": ("/compliance/action-plans/", "table tbody tr td a", 5),
    "incident-detail": ("/incidents/", "table tbody tr td a", 5),
    "risk-detail": ("/risks/register/", "table tbody tr td a", 5),
    "supplier-detail": ("/assets/suppliers/", "table tbody tr td a", 5),
}


class DevTools:
    """A minimal Chrome DevTools Protocol client over a stdlib WebSocket.

    Deliberately dependency-free : the capture runs in CI and in a sandbox where
    adding a Python package is not always possible, and the protocol surface
    used here is four methods wide.
    """

    def __init__(self, url: str) -> None:
        hostport, _, path = url[5:].partition("/")
        host, port = hostport.split(":")
        self.sock = socket.create_connection((host, int(port)))
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall(
            f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n".encode()
        )
        self.buffer = b""
        while b"\r\n\r\n" not in self.buffer:
            self.buffer += self.sock.recv(4096)
        self.buffer = self.buffer.split(b"\r\n\r\n", 1)[1]
        self.message_id = 0

    def _read_exactly(self, count: int) -> bytes:
        while len(self.buffer) < count:
            chunk = self.sock.recv(1 << 20)
            if not chunk:
                raise OSError("DevTools connection closed")
            self.buffer += chunk
        out, self.buffer = self.buffer[:count], self.buffer[count:]
        return out

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        header = bytes([0x80 | opcode])
        size, mask = len(payload), os.urandom(4)
        if size < 126:
            header += bytes([0x80 | size])
        elif size < 65536:
            header += bytes([0x80 | 126]) + struct.pack(">H", size)
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", size)
        self.sock.sendall(
            header + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        )

    def _read_message(self) -> dict:
        data = b""
        while True:
            head = self._read_exactly(2)
            final, opcode, size = head[0] & 0x80, head[0] & 0x0F, head[1] & 0x7F
            if size == 126:
                size = struct.unpack(">H", self._read_exactly(2))[0]
            elif size == 127:
                size = struct.unpack(">Q", self._read_exactly(8))[0]
            payload = self._read_exactly(size)
            if opcode == 0x8:
                raise OSError("DevTools connection closed")
            if opcode == 0x9:            # ping
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:            # pong
                continue
            data += payload
            if final:
                return json.loads(data)

    def call(self, method: str, params: dict | None = None) -> dict:
        self.message_id += 1
        self._send_frame(0x1, json.dumps(
            {"id": self.message_id, "method": method, "params": params or {}}
        ).encode())
        while True:
            message = self._read_message()
            if message.get("id") == self.message_id:
                return message


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


def debugger_url() -> str:
    for _ in range(200):
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{DEBUG_PORT}/json", timeout=5
            ) as response:
                pages = [t for t in json.load(response) if t.get("type") == "page"]
                if pages:
                    return pages[0]["webSocketDebuggerUrl"]
        except Exception:
            time.sleep(0.1)
    raise SystemExit("Chrome did not expose a debugging target.")


def build_session() -> tuple[str, str]:
    """Create a signed-in session for a superuser and return its cookie."""
    import django

    sys.path.insert(0, str(REPO))
    django.setup()

    from django.conf import settings
    from django.contrib.auth import get_user_model
    from importlib import import_module

    user = (get_user_model().objects
            .filter(is_superuser=True, is_active=True).order_by("created_at").first())
    if user is None:
        raise SystemExit("No active superuser to capture as. Seed the database first.")

    store = import_module(settings.SESSION_ENGINE).SessionStore()
    store["_auth_user_id"] = str(user.pk)
    store["_auth_user_backend"] = settings.AUTHENTICATION_BACKENDS[0]
    store["_auth_user_hash"] = user.get_session_auth_hash()
    store.create()
    return settings.SESSION_COOKIE_NAME, store.session_key


def capture(devtools: DevTools, url: str, wait: float, out: Path) -> None:
    devtools.call("Page.navigate", {"url": url})
    time.sleep(wait)
    devtools.call("Runtime.evaluate", {"expression": CLEAN_JS})
    time.sleep(0.5)
    result = devtools.call("Page.captureScreenshot", {"format": "png"})
    out.write_bytes(base64.b64decode(result["result"]["data"]))
    print(f"  {out.name} ({out.stat().st_size // 1024} KB)")


def first_link(devtools: DevTools, base: str, path: str, selector: str) -> str | None:
    """Return the href of the first record in a list, or None when it is empty."""
    devtools.call("Page.navigate", {"url": base + path})
    time.sleep(3)
    result = devtools.call("Runtime.evaluate", {
        "expression": f"(document.querySelector({selector!r}) || {{}}).href || ''",
        "returnByValue": True,
    })
    return result.get("result", {}).get("result", {}).get("value") or None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--only", nargs="*", help="Capture only these names.")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    args.out.mkdir(parents=True, exist_ok=True)

    cookie_name, cookie_value = build_session()

    profile = Path(tempfile.mkdtemp(prefix="cairn-shots-"))
    chrome = start_chrome(profile)
    try:
        devtools = DevTools(debugger_url())
        devtools.call("Network.enable")
        devtools.call("Page.enable")
        devtools.call("Runtime.enable")
        devtools.call("Network.setCookie",
                      {"name": cookie_name, "value": cookie_value, "url": base})
        devtools.call("Emulation.setDeviceMetricsOverride",
                      {"width": WIDTH, "height": HEIGHT,
                       "deviceScaleFactor": 1, "mobile": False})

        wanted = set(args.only) if args.only else None

        print(f"Capturing at {WIDTH}x{HEIGHT} from {base}")
        for name, (path, wait) in SHOTS.items():
            if wanted and name not in wanted:
                continue
            capture(devtools, base + path, wait, args.out / f"{name}.png")

        for name, (path, selector, wait) in DETAIL_SHOTS.items():
            if wanted and name not in wanted:
                continue
            href = first_link(devtools, base, path, selector)
            if not href:
                print(f"  {name}.png skipped : no record in {path}")
                continue
            capture(devtools, href, wait, args.out / f"{name}.png")
    finally:
        chrome.terminate()
        shutil.rmtree(profile, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
