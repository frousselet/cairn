# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Files sent to a tool (the ``io.modelcontextprotocol/files`` extension).

A tool marks an argument as a file with ``x-mcp-file`` in its schema
(:func:`file_schema`) and declares it on its handler (:func:`takes_files`).
The client then sends a ``FileInput`` (``id``, ``name``, ``mimeType``,
``size``, optional ``digest``) and the bytes travel one of two ways :

- **inline** : base64 in ``data``, up to :data:`MAX_INLINE_BYTES` per
  request, from any client;
- **out of band** : the first call answers ``upload_required`` with one
  target per file, a ``PUT`` to ``/api/v1/mcp/uploads/<id>`` on this instance
  with the client's own credential (``credentials: "include"``). The client
  sends the bytes, then retries the call with the ``requestState`` it was
  given; the tool runs on the bytes received.

What holds it together :

- the metadata is what the client asserts : the size and the type are checked
  again on the bytes, and a ``digest``, when sent, is verified;
- the ``requestState`` is signed (``SECRET_KEY``, one hour) and binds the
  person, the tool, the arguments and the uploads; each upload is written
  once, by the person it was issued to, and consumed once, atomically : the
  tools that take files write a record, and are not run twice for one call;
- staged bytes live under ``MEDIA_ROOT/mcp_uploads/`` until the retry
  consumes them or their ``requestState`` expires, then are deleted.

The handler reads a file with :func:`read_file`, which only returns the bytes
this module confirmed : a value the client sent cannot pass for them.
"""

import base64
import binascii
import hashlib
import json
import posixpath
from dataclasses import dataclass
from datetime import UTC, timedelta

from django.core import signing
from django.db import transaction
from django.utils import timezone

from mcp.server import (
    FILES_EXTENSION,
    INVALID_PARAMS,
    MAX_INLINE_FILE_BYTES,
    MISSING_REQUIRED_CLIENT_CAPABILITY,
    ProtocolError,
)

MAX_INLINE_BYTES = MAX_INLINE_FILE_BYTES
UPLOAD_LIFETIME = timedelta(hours=1)
REQUEST_STATE_SALT = "mcp.files.request-state"
#: Where the confirmed bytes of a file argument wait for the handler. A key a
#: JSON client cannot send : :func:`prepare` removes it from what it received.
CONTENT_KEY = "\x00content"

FILE_INPUT_PROPERTIES = {
    "id": {"type": "string", "minLength": 1, "maxLength": 128},
    "name": {"type": "string"},
    "mimeType": {"type": "string"},
    "size": {"type": "integer", "minimum": 0},
    "digest": {
        "type": "object",
        "properties": {
            "algorithm": {"const": "sha-256"},
            "value": {"type": "string"},
        },
        "required": ["algorithm", "value"],
    },
    "data": {"type": "string"},
}


def file_schema(description, *, accept=(), max_size):
    """The JSON Schema of a file argument : a ``FileInput`` marked ``x-mcp-file``."""
    descriptor = {"maxSize": max_size}
    if accept:
        descriptor["accept"] = list(accept)
    return {
        "type": "object",
        "description": description,
        "x-mcp-file": descriptor,
        "properties": dict(FILE_INPUT_PROPERTIES),
        "required": ["id", "mimeType", "size"],
    }


def takes_files(**descriptors):
    """Declare the file arguments of a tool handler : ``name={"accept": [...], "maxSize": n}``.

    ``functools.wraps`` (used by ``require_perm``) carries the attribute to the
    wrapper.
    """
    def decorator(handler):
        handler.mcp_files = descriptors
        return handler
    return decorator


@dataclass(frozen=True)
class ReceivedFile:
    name: str
    mime_type: str
    content: bytes


def read_file(arguments, param):
    """The confirmed file of argument ``param``; ``None`` when absent."""
    value = arguments.get(param)
    if not isinstance(value, dict):
        return None
    received = value.get(CONTENT_KEY)
    if not isinstance(received, ReceivedFile):
        return None
    return received


# ── Checks ────────────────────────────────────────────────


@dataclass
class Outcome:
    arguments: dict = None
    result: dict = None  # an upload_required answer, or a refusal (isError)


def _refusal(message):
    return {
        "content": [{"type": "text", "text": json.dumps({"error": message}, ensure_ascii=False)}],
        "isError": True,
    }


def _base_name(name):
    base = posixpath.basename(str(name or "").replace("\\", "/"))
    return "file" if base in ("", ".", "..") else base[:255]


def _accepted(descriptor, name, mime_type):
    """Whether a file of this name and type may be what the tool accepts.

    ``accept`` lists media types and dot-prefixed extensions. A client that
    does not know the type sends ``application/octet-stream`` : the name then
    decides, and the bytes are checked by the tool.
    """
    accept = descriptor.get("accept") or ()
    if not accept:
        return True
    lowered = str(name or "").lower()
    for item in accept:
        if item.startswith(".") and lowered.endswith(item.lower()):
            return True
        if not item.startswith(".") and item.lower() == str(mime_type or "").lower():
            return True
    return False


def _digest_matches(file_input, content):
    digest = file_input.get("digest")
    if not digest:
        return True
    if not isinstance(digest, dict) or digest.get("algorithm") != "sha-256":
        return False
    expected = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).decode("ascii").rstrip("=")
    return digest.get("value") == expected


def _canonical(arguments):
    """The arguments as one string : member order and number spelling do not matter."""
    def clean(value):
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items() if k != CONTENT_KEY}
        if isinstance(value, list):
            return [clean(v) for v in value]
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value
    encoded = json.dumps(clean(arguments), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _iso(moment):
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def purge_expired():
    """Forget the uploads whose ``requestState`` expired, with their bytes."""
    from mcp.models import McpUpload

    for upload in McpUpload.objects.filter(expires_at__lt=timezone.now()):
        upload.discard()


# ── The call ──────────────────────────────────────────────


def prepare(tool_def, user, arguments, params, ctx):
    """Resolve the file arguments of a call : run, refuse, or ask for an upload."""
    descriptors = tool_def["files"]
    arguments = dict(arguments)
    files = {}
    for param in descriptors:
        value = arguments.get(param)
        if value is None:
            continue
        if not isinstance(value, dict):
            return Outcome(result=_refusal(f"{param} must be a file."))
        value = {k: v for k, v in value.items() if k != CONTENT_KEY}
        arguments[param] = value
        files[param] = value
    if not files:
        return Outcome(arguments=arguments)

    ids = [f.get("id") for f in files.values()]
    if len(set(map(str, ids))) != len(ids):
        return Outcome(result=_refusal("Two files of the call share one id."))

    pending, inline_total = [], 0
    for param, value in files.items():
        descriptor = descriptors[param]
        file_id, mime_type, size = value.get("id"), value.get("mimeType"), value.get("size")
        if not isinstance(file_id, str) or not 1 <= len(file_id) <= 128 or not isinstance(mime_type, str) \
                or not isinstance(size, int) or isinstance(size, bool) or size < 0:
            return Outcome(result=_refusal(f"{param} is not a valid file (id, mimeType and size are required)."))
        if size > descriptor["maxSize"]:
            return Outcome(result=_refusal(f"{param} exceeds {descriptor['maxSize']} bytes."))
        if not _accepted(descriptor, value.get("name"), mime_type):
            return Outcome(result=_refusal(f"{param} is not of a type this tool accepts."))
        name = _base_name(value.get("name"))
        if "data" in value:
            data = value["data"]
            try:
                content = base64.b64decode(data, validate=True) if isinstance(data, str) else None
            except (binascii.Error, ValueError):
                content = None
            if content is None:
                return Outcome(result=_refusal(f"{param} carries data that is not base64."))
            inline_total += len(content)
            if inline_total > MAX_INLINE_BYTES:
                return Outcome(result=_refusal(f"Inline files exceed {MAX_INLINE_BYTES} bytes in total."))
            if len(content) != size or not _digest_matches(value, content):
                return Outcome(result=_refusal(f"{param} does not match its declared size or digest."))
            value[CONTENT_KEY] = ReceivedFile(name, mime_type, content)
        elif size == 0:
            if not _digest_matches(value, b""):
                return Outcome(result=_refusal(f"{param} does not match its digest."))
            value[CONTENT_KEY] = ReceivedFile(name, mime_type, b"")
        else:
            pending.append((param, value, name))

    if not pending:
        return Outcome(arguments=arguments)

    state = params.get("requestState")
    if isinstance(state, str) and state:
        return _retry(tool_def, user, arguments, pending, state)

    files_capability = (ctx.client_capabilities.get("extensions") or {}).get(FILES_EXTENSION) if ctx.modern else None
    if not isinstance(files_capability, dict) or "upload" not in files_capability:
        raise ProtocolError(
            MISSING_REQUIRED_CLIENT_CAPABILITY,
            "This client cannot send files to this server, so the tool did not run.",
            data={"requiredCapabilities": {"extensions": {FILES_EXTENSION: {"upload": {}}}}},
        )
    return _request_upload(tool_def, user, arguments, pending, ctx)


def _request_upload(tool_def, user, arguments, pending, ctx):
    from mcp.models import McpUpload

    purge_expired()
    expires = timezone.now() + UPLOAD_LIFETIME
    targets, upload_ids = [], []
    for _param, value, name in pending:
        upload = McpUpload.objects.create(
            user=user, tool_name=tool_def["name"], file_id=value["id"], name=name,
            mime_type=value["mimeType"], size=value["size"], expires_at=expires,
        )
        upload_ids.append(str(upload.pk))
        targets.append({
            "fileId": value["id"],
            "url": f"{ctx.base_url}/api/v1/mcp/uploads/{upload.pk}",
            "method": "PUT",
            "headers": {"Content-Type": value["mimeType"]},
            "credentials": "include",
            "expiresAt": _iso(expires),
        })
    state = signing.dumps(
        {"k": "files", "u": str(user.pk), "t": tool_def["name"], "a": _canonical(arguments), "up": upload_ids},
        salt=REQUEST_STATE_SALT, compress=True,
    )
    return Outcome(result={"resultType": "upload_required", "uploads": targets, "requestState": state})


def _retry(tool_def, user, arguments, pending, state):
    from mcp.models import McpUpload

    invalid = ProtocolError(INVALID_PARAMS, "Invalid params: requestState does not answer this call", http_status=200)
    try:
        payload = signing.loads(state, salt=REQUEST_STATE_SALT, max_age=UPLOAD_LIFETIME.total_seconds())
    except signing.BadSignature:
        raise invalid from None
    if not isinstance(payload, dict) or payload.get("k") != "files" or payload.get("u") != str(user.pk) \
            or payload.get("t") != tool_def["name"] or payload.get("a") != _canonical(arguments):
        raise invalid

    uploads = {str(u.pk): u for u in McpUpload.objects.filter(pk__in=payload.get("up") or [], user=user)}
    by_file_id = {u.file_id: u for u in uploads.values()}
    if len(uploads) != len(payload.get("up") or []) or len(by_file_id) != len(pending):
        raise invalid
    for _param, value, _name in pending:
        upload = by_file_id.get(value["id"])
        if upload is None or upload.consumed_at is not None:
            raise invalid
        if upload.received_at is None or not upload.file:
            return Outcome(result=_refusal("A file was not received : the tool did not run."))

    # Consumed once, atomically, by the first retry that gets here.
    with transaction.atomic():
        claimed = McpUpload.objects.filter(
            pk__in=list(uploads), consumed_at__isnull=True, received_at__isnull=False,
        ).update(consumed_at=timezone.now())
        if claimed != len(uploads):
            transaction.set_rollback(True)
            raise invalid

    for _param, value, name in pending:
        upload = by_file_id[value["id"]]
        with upload.file.open("rb") as handle:
            content = handle.read()
        if len(content) != value["size"] or not _digest_matches(value, content):
            return Outcome(result=_refusal("A file does not match its declared size or digest : the tool did not run."))
        value[CONTENT_KEY] = ReceivedFile(name, value["mimeType"], content)
    # The bytes are in hand and the uploads consumed : the staging place goes.
    for upload in uploads.values():
        upload.discard()
    return Outcome(arguments=arguments)

