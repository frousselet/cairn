# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""
MCP (Model Context Protocol) server core implementation.

Implements JSON-RPC 2.0 over the Streamable HTTP transport, for two eras of
the protocol on the same endpoint :

- revision ``2026-07-28`` : stateless. Every request carries its protocol
  version and the client's capabilities in ``params._meta``, every result
  carries ``resultType``, ``server/discover`` describes the server, a tool may
  ask the user for a confirmation through elicitation (multi round-trip
  requests) and a long tool may answer with a task
  (``io.modelcontextprotocol/tasks`` extension);
- revision ``2025-03-26`` : the ``initialize`` handshake, kept for the clients
  that predate the stateless revision. A request without the version in its
  ``_meta`` is served under these rules, exactly as before.
"""

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# The revision of the ``initialize`` handshake, served to the clients of the
# previous era.
PROTOCOL_VERSION = "2025-03-26"
# The stateless revision.
MODERN_PROTOCOL_VERSION = "2026-07-28"
# The versions a request may name in ``_meta`` (``server/discover`` lists them).
SUPPORTED_VERSIONS = (MODERN_PROTOCOL_VERSION,)

SERVER_INFO = {"name": "Cairn MCP Server", "version": "1.0.0"}

META_PROTOCOL_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CLIENT_CAPABILITIES = "io.modelcontextprotocol/clientCapabilities"
META_SERVER_INFO = "io.modelcontextprotocol/serverInfo"
TASKS_EXTENSION = "io.modelcontextprotocol/tasks"

# How long a client may keep the tool list and the discovery document : the
# registry only changes when the instance is upgraded.
LIST_TTL_MS = 300_000

SERVER_INSTRUCTIONS = (
    "Cairn is a Governance, Risk and Compliance (GRC) platform : organizational context, "
    "assets, compliance, risks, incidents, documents and security controls. Every tool runs "
    "as the person who authorized the connection, with their permissions and their scopes. "
    "Call the `help` tool for the usage guide (with a topic for field-level documentation) "
    "and `get_glossary` for the names the interface gives each notion. Deleting a record and "
    "some lifecycle transitions ask the user for a confirmation or a comment when the client "
    "supports elicitation; report generation and batch creation answer with a task when the "
    "client supports the tasks extension."
)

# JSON-RPC 2.0 error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
# Errors of the 2026-07-28 revision
HEADER_MISMATCH = -32020
MISSING_REQUIRED_CLIENT_CAPABILITY = -32021
UNSUPPORTED_PROTOCOL_VERSION = -32022


def jsonrpc_error(code, message, req_id=None, data=None):
    resp = {
        "jsonrpc": "2.0",
        "error": {"code": code, "message": message},
        "id": req_id,
    }
    if data is not None:
        resp["error"]["data"] = data
    return resp


def jsonrpc_result(result, req_id):
    return {
        "jsonrpc": "2.0",
        "result": result,
        "id": req_id,
    }


def wrap_tool_result(result):
    """Put what a tool handler returned in the MCP ``CallToolResult`` shape."""
    if isinstance(result, dict) and "content" in result and "isError" in result:
        return result
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result, default=str, ensure_ascii=False),
            }
        ],
        "isError": False,
    }


class InvalidParamsError(Exception):
    pass


class ProtocolError(Exception):
    """A JSON-RPC error answered with its own HTTP status (2026-07-28 rules)."""

    def __init__(self, code, message, data=None, http_status=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data
        self.http_status = http_status


@dataclass
class RequestContext:
    """What one request says about itself : its era and the client's capabilities."""

    protocol_version: str = PROTOCOL_VERSION
    modern: bool = False
    client_capabilities: dict = field(default_factory=dict)

    @property
    def can_elicit_form(self):
        """True when the client declared form-mode elicitation for this request.

        ``elicitation: {}`` is form mode alone; ``{"url": {}}`` without ``form``
        is not.
        """
        if not self.modern:
            return False
        elicitation = self.client_capabilities.get("elicitation")
        if not isinstance(elicitation, dict):
            return False
        return not elicitation or "form" in elicitation

    @property
    def accepts_tasks(self):
        """True when the client declared the tasks extension for this request."""
        if not self.modern:
            return False
        extensions = self.client_capabilities.get("extensions")
        return isinstance(extensions, dict) and TASKS_EXTENSION in extensions


LEGACY_CONTEXT = RequestContext()


def _request_context(params):
    """Read the era and the client capabilities of a request from its ``_meta``.

    No version in ``_meta`` : the request belongs to the ``initialize`` era.
    A version this server does not serve, or a modern request without its
    capabilities, is refused (HTTP 400).
    """
    meta = params.get("_meta") if isinstance(params, dict) else None
    version = meta.get(META_PROTOCOL_VERSION) if isinstance(meta, dict) else None
    if version is None:
        return LEGACY_CONTEXT
    if not isinstance(version, str) or version not in SUPPORTED_VERSIONS:
        raise ProtocolError(
            UNSUPPORTED_PROTOCOL_VERSION,
            "Unsupported protocol version",
            data={"supported": list(SUPPORTED_VERSIONS), "requested": version},
        )
    capabilities = meta.get(META_CLIENT_CAPABILITIES)
    if not isinstance(capabilities, dict):
        raise ProtocolError(
            INVALID_PARAMS,
            f"Invalid params: _meta['{META_CLIENT_CAPABILITIES}'] is required",
        )
    return RequestContext(protocol_version=version, modern=True, client_capabilities=capabilities)


def _expected_name(method, params):
    """The value the ``Mcp-Name`` header must carry for ``method``, or ``None``."""
    if not isinstance(params, dict):
        return None
    if method in ("tools/call", "prompts/get"):
        return params.get("name")
    if method == "resources/read":
        return params.get("uri")
    if method in ("tasks/get", "tasks/update", "tasks/cancel"):
        return params.get("taskId")
    return None


def _check_headers(msg, ctx, headers):
    """Hold a modern HTTP request to the headers that mirror its body.

    ``MCP-Protocol-Version`` must name the version of ``_meta``; ``Mcp-Method``
    and ``Mcp-Name``, when sent, must match the method and its target.
    """
    if not ctx.modern or headers is None:
        return
    sent_version = headers.get("MCP-Protocol-Version")
    if sent_version != ctx.protocol_version:
        raise ProtocolError(
            HEADER_MISMATCH,
            f"Header mismatch: MCP-Protocol-Version header value '{sent_version or ''}' "
            f"does not match body value '{ctx.protocol_version}'",
        )
    method = msg.get("method")
    sent_method = headers.get("Mcp-Method")
    if sent_method is not None and sent_method != method:
        raise ProtocolError(
            HEADER_MISMATCH,
            f"Header mismatch: Mcp-Method header value '{sent_method}' does not match body value '{method}'",
        )
    expected = _expected_name(method, msg.get("params"))
    sent_name = headers.get("Mcp-Name")
    if sent_name is not None and expected is not None and sent_name != str(expected):
        raise ProtocolError(
            HEADER_MISMATCH,
            f"Header mismatch: Mcp-Name header value '{sent_name}' does not match body value '{expected}'",
        )


class McpServer:
    """Stateless MCP server that processes JSON-RPC requests."""

    def __init__(self):
        self._tools = {}  # name -> ToolDefinition

    def register_tool(self, name, description, input_schema, handler):
        """Register an MCP tool.

        Args:
            name: Unique tool name
            description: Human-readable description
            input_schema: JSON Schema for tool parameters
            handler: callable(user, arguments) -> result

        Two attributes of the handler change how a modern client is served :
        ``mcp_elicit`` (a callable ``(user, arguments)`` returning the
        :class:`mcp.elicitation.Elicitation` to put to the user before the
        tool runs, or ``None``) and ``mcp_task`` (``True`` : the call may
        answer with a task). ``mcp.elicitation.asks`` and
        ``mcp.tasks.runs_as_task`` set them.
        """
        self._tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
            "handler": handler,
            "elicit": getattr(handler, "mcp_elicit", None),
            "task": bool(getattr(handler, "mcp_task", False)),
        }

    def iter_tools(self):
        """Yield the registered tool definitions, in registration order.

        Public accessor used by the reference-documentation generator
        (``manage.py generate_docs``) so it never reads the private registry.
        """
        return tuple(self._tools.values())

    def get_tool(self, name):
        """Return a registered tool definition dict, or None.

        Public accessor used for in-process tool execution (e.g. by the
        assistant app) so callers never touch the private registry.
        """
        return self._tools.get(name)

    def handle_request(self, body, user, headers=None):
        """Process a JSON-RPC request and return a response dict (or None for notifications)."""
        return self.handle_http(body, user, headers)[0]

    def handle_http(self, body, user, headers=None):
        """Process a JSON-RPC request; return ``(response, http_status)``.

        ``headers`` (a mapping of the HTTP request headers) is checked against
        the body of a single modern request; a batch is answered with 200.
        """
        try:
            msg = json.loads(body) if isinstance(body, (str, bytes)) else body
        except (json.JSONDecodeError, TypeError):
            return jsonrpc_error(PARSE_ERROR, "Parse error"), 200

        # Handle batch requests
        if isinstance(msg, list):
            results = []
            for item in msg:
                result, _status = self._dispatch(item, user, None)
                if result is not None:
                    results.append(result)
            return (results if results else None), 200

        return self._dispatch(msg, user, headers)

    def _dispatch(self, msg, user, headers):
        if not isinstance(msg, dict):
            return jsonrpc_error(INVALID_REQUEST, "Invalid Request"), 200

        if msg.get("jsonrpc") != "2.0":
            return jsonrpc_error(INVALID_REQUEST, "Invalid Request: jsonrpc must be '2.0'", msg.get("id")), 200

        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params", {})
        if params is None:
            params = {}

        # Notifications have no id
        is_notification = "id" not in msg

        if not method or not isinstance(method, str):
            if is_notification:
                return None, 202
            return jsonrpc_error(INVALID_REQUEST, "Invalid Request: method is required", req_id), 200

        try:
            ctx = _request_context(params)
            _check_headers(msg, ctx, headers)
        except ProtocolError as e:
            if is_notification:
                return None, 202
            return jsonrpc_error(e.code, e.message, req_id, e.data), e.http_status

        handler = self._get_method_handler(method, ctx)
        if handler is None:
            if is_notification:
                return None, 202
            # The stateless revision answers an unknown method with a 404.
            return jsonrpc_error(METHOD_NOT_FOUND, f"Method not found: {method}", req_id), (
                404 if ctx.modern else 200
            )

        try:
            result = handler(params, user, ctx)
            if is_notification:
                return None, 202
            if ctx.modern and isinstance(result, dict):
                result.setdefault("resultType", "complete")
            return jsonrpc_result(result, req_id), 200
        except ProtocolError as e:
            if is_notification:
                return None, 202
            return jsonrpc_error(e.code, e.message, req_id, e.data), e.http_status
        except InvalidParamsError as e:
            logger.debug("Invalid params for MCP method %s: %s", method, e, exc_info=True)
            if is_notification:
                return None, 202
            return jsonrpc_error(INVALID_PARAMS, "Invalid params", req_id), 200
        except Exception:
            logger.exception("MCP method %s failed", method)
            if is_notification:
                return None, 202
            return jsonrpc_error(INTERNAL_ERROR, "Internal error", req_id), 200

    def _get_method_handler(self, method, ctx=LEGACY_CONTEXT):
        if ctx.modern:
            handlers = {
                "server/discover": self._handle_discover,
                "tools/list": self._handle_tools_list,
                "tools/call": self._handle_tools_call,
                "tasks/get": self._handle_tasks_get,
                "tasks/update": self._handle_tasks_update,
                "tasks/cancel": self._handle_tasks_cancel,
            }
        else:
            handlers = {
                "initialize": self._handle_initialize,
                "ping": self._handle_ping,
                "tools/list": self._handle_tools_list,
                "tools/call": self._handle_tools_call,
            }
        return handlers.get(method)

    # ── Discovery ─────────────────────────────────────────

    def _handle_initialize(self, params, user, ctx):
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": False},
            },
            "serverInfo": dict(SERVER_INFO),
        }

    def _handle_discover(self, params, user, ctx):
        return {
            "supportedVersions": list(SUPPORTED_VERSIONS),
            "capabilities": {
                "tools": {},
                "extensions": {TASKS_EXTENSION: {}},
            },
            "instructions": SERVER_INSTRUCTIONS,
            "ttlMs": LIST_TTL_MS,
            "cacheScope": "public",
            "_meta": {META_SERVER_INFO: dict(SERVER_INFO)},
        }

    def _handle_ping(self, params, user, ctx):
        return {}

    # ── Tools ─────────────────────────────────────────────

    def _handle_tools_list(self, params, user, ctx):
        tools = []
        for tool_def in self._tools.values():
            tools.append({
                "name": tool_def["name"],
                "description": tool_def["description"],
                "inputSchema": tool_def["inputSchema"],
            })
        result = {"tools": tools}
        if ctx.modern:
            result["ttlMs"] = LIST_TTL_MS
            result["cacheScope"] = "public"
        return result

    def _handle_tools_call(self, params, user, ctx):
        if not params or "name" not in params:
            raise InvalidParamsError("Tool name is required.")

        tool_name = params["name"]
        arguments = params.get("arguments") or {}

        if tool_name not in self._tools:
            raise InvalidParamsError(f"Unknown tool: {tool_name}")

        tool_def = self._tools[tool_name]

        if ctx.modern and tool_def["elicit"] is not None and ctx.can_elicit_form:
            from mcp import elicitation

            outcome = elicitation.resolve(tool_def, user, arguments, params)
            if outcome.input_required is not None:
                return outcome.input_required
            if outcome.refused is not None:
                return outcome.refused
            arguments = outcome.arguments

        if ctx.modern and tool_def["task"] and ctx.accepts_tasks and _may_run(tool_def, user):
            from mcp import tasks

            return tasks.create(tool_def, user, arguments)

        return wrap_tool_result(tool_def["handler"](user, arguments))

    # ── Tasks (io.modelcontextprotocol/tasks) ─────────────

    def _task_params(self, params, ctx):
        if not ctx.accepts_tasks:
            raise ProtocolError(
                MISSING_REQUIRED_CLIENT_CAPABILITY,
                "Missing required client capability",
                data={"requiredCapabilities": {"extensions": {TASKS_EXTENSION: {}}}},
            )
        task_id = params.get("taskId") if isinstance(params, dict) else None
        if not task_id or not isinstance(task_id, str):
            raise ProtocolError(INVALID_PARAMS, "Invalid params: taskId is required", http_status=200)
        return task_id

    def _handle_tasks_get(self, params, user, ctx):
        from mcp import tasks

        return tasks.get(user, self._task_params(params, ctx))

    def _handle_tasks_update(self, params, user, ctx):
        from mcp import tasks

        return tasks.update(user, self._task_params(params, ctx))

    def _handle_tasks_cancel(self, params, user, ctx):
        from mcp import tasks

        return tasks.cancel(user, self._task_params(params, ctx))


def _may_run(tool_def, user):
    """False when the user lacks the permission the tool requires.

    Such a call is answered at once by the tool's own refusal rather than by a
    task that could only fail.
    """
    codename = getattr(tool_def["handler"], "required_perm", None)
    if not codename or user is None:
        return True
    return user.is_superuser or user.has_perm(codename)
