# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The hand-written MCP guide names only tools that exist.

The guide (``help``, without a topic and for each topic) tells an agent that
"every tool listed by help / this guide is registered under its exact name".
Written by hand, it drifted : an example still called ``approve_risk_assessment``
after the approval tools were removed. This test reads every text of the guide
and fails on a tool name that is not registered.

A tool name is a word that starts with one of the verbs the tools use
(``list_``, ``get_``, ``create_``, ``transition_``...). Such a word that names
something else is listed below with the reason.
"""

import re

from mcp.server import McpServer
from mcp.tools import register_all_tools

#: The verbs a tool name starts with.
VERBS = (
    "acknowledge", "add", "approve", "ask", "batch", "capture", "check", "consolidate", "create", "declare",
    "delete", "download", "excuse", "export", "generate", "get", "link", "list", "mark", "post", "promote",
    "raise", "record", "reject", "set", "transition", "unlink", "update", "verify",
)

#: Words of the guide that start with a verb and are no tool, with the reason.
NOT_TOOLS = {
    "download_url": "a field of an evidence item of a control test run",
    "post_incident_review": "the heading of the post-incident review entity",
    "transition_incident_response_action": "named to say there is no such tool (a response action runs no lifecycle)",
}


def _server():
    server = McpServer()
    register_all_tools(server)
    return server


def _guide_texts(server):
    """The guide without a topic, and the text of every topic it offers."""
    handler = server.get_tool("help")["handler"]
    texts = {"(guide)": handler(None, {})}
    unknown = handler(None, {"topic": "no-such-topic"})
    topics = re.search(r"Available topics: ([a-z_, ]+)", unknown).group(1).split(", ")
    assert len(topics) > 5
    for topic in topics:
        texts[topic] = handler(None, {"topic": topic})
    return texts


def test_every_tool_the_guide_names_is_registered():
    server = _server()
    registered = {definition["name"] for definition in server.iter_tools()}
    word = re.compile(r"\b(?:%s)_[a-z0-9_]*[a-z0-9]\b" % "|".join(VERBS))
    unknown, seen = [], set()
    for topic, text in _guide_texts(server).items():
        for name in sorted(set(word.findall(text))):
            if name in registered:
                continue
            if name in NOT_TOOLS:
                seen.add(name)
                continue
            unknown.append(f"{topic} : {name}")
    assert unknown == [], "The guide names tools that are not registered :\n" + "\n".join(unknown)
    assert set(NOT_TOOLS) <= seen, f"Words no longer in the guide : {sorted(set(NOT_TOOLS) - seen)}"
