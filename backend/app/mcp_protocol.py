"""
Minimal Model Context Protocol implementation, standard library only.

Why this exists: the official `mcp` Python SDK pins dependency versions
that conflict with this project's FastAPI/Pydantic pins. Rather than fight
that, this implements just the slice of the MCP spec a tool-calling client
(Claude Desktop, MCP Inspector, a custom client) actually needs against the
stdio transport: JSON-RPC 2.0 request/response framing (newline-delimited
JSON, one message per line -- the stdio transport's actual wire format),
`initialize`, `tools/list`, `tools/call`, and JSON-RPC-compliant error
handling. No resources, prompts, or sampling -- this project only needs
tools.

This file is transport/protocol only. It knows nothing about buildings,
vendors, or water schedules -- app/mcp_server.py registers those as tools
against the `MCPServer` class defined here.
"""

from __future__ import annotations

import inspect
import json
import sys
import typing
from dataclasses import dataclass, field
from typing import Any, Callable

# --- JSON-RPC 2.0 error codes (per the JSON-RPC spec) ---
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


@dataclass
class JsonRpcRequest:
    """A parsed incoming JSON-RPC message. `id` is None for notifications
    (messages that don't expect a response, e.g. `notifications/initialized`)."""

    method: str
    params: dict[str, Any] = field(default_factory=dict)
    id: Any = None
    jsonrpc: str = "2.0"

    @property
    def is_notification(self) -> bool:
        return self.id is None


@dataclass
class JsonRpcError:
    code: int
    message: str
    data: Any = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            out["data"] = self.data
        return out


@dataclass
class JsonRpcResponse:
    id: Any
    result: Any = None
    error: JsonRpcError | None = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error is not None:
            out["error"] = self.error.to_dict()
        else:
            out["result"] = self.result
        return out


class MCPProtocolError(Exception):
    """Raised for malformed requests -- caught by dispatch_message and
    turned into a proper JSON-RPC error response."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def parse_request(line: str) -> JsonRpcRequest:
    """Parses one line of the stdio transport into a JsonRpcRequest.
    Raises MCPProtocolError(PARSE_ERROR, ...) on invalid JSON, or
    MCPProtocolError(INVALID_REQUEST, ...) if it's valid JSON but not a
    well-formed JSON-RPC request."""
    try:
        raw = json.loads(line)
    except json.JSONDecodeError as exc:
        raise MCPProtocolError(PARSE_ERROR, f"Invalid JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise MCPProtocolError(INVALID_REQUEST, "Request must be a JSON object")

    method = raw.get("method")
    if not isinstance(method, str):
        raise MCPProtocolError(INVALID_REQUEST, "Request must have a string 'method'")

    params = raw.get("params") or {}
    if not isinstance(params, dict):
        raise MCPProtocolError(INVALID_REQUEST, "'params' must be an object")

    return JsonRpcRequest(method=method, params=params, id=raw.get("id"), jsonrpc=raw.get("jsonrpc", "2.0"))


# --- JSON Schema inference from a plain function's type hints ---

_JSON_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


def build_input_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    """Builds an MCP `inputSchema` (JSON Schema) from a function's type
    hints and defaults -- a parameter with no default is required; a
    parameter typed `X | None` (or `Optional[X]`) is treated as optional
    even without a default."""
    hints = typing.get_type_hints(fn)
    signature = inspect.signature(fn)
    properties: dict[str, Any] = {}
    required: list[str] = []

    for name, param in signature.parameters.items():
        hint = hints.get(name, str)
        origin = typing.get_origin(hint)
        is_optional = False

        if origin is typing.Union:
            args = [a for a in typing.get_args(hint) if a is not type(None)]
            is_optional = type(None) in typing.get_args(hint)
            hint = args[0] if args else str

        properties[name] = {"type": _JSON_TYPE_MAP.get(hint, "string")}

        if param.default is inspect.Parameter.empty and not is_optional:
            required.append(name)

    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Any]


class MCPServer:
    """A minimal MCP server: tool registration + JSON-RPC dispatch + a
    stdio read/write loop. No external dependency -- everything here is
    the standard library.
    """

    PROTOCOL_VERSION = "2024-11-05"

    def __init__(self, name: str, version: str = "0.1.0"):
        self.name = name
        self.version = version
        self._tools: dict[str, ToolDefinition] = {}

    def tool(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator that registers a function as an MCP tool. Returns the
        original function unchanged, so it stays directly callable (and
        directly unit-testable) outside the protocol layer."""

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._tools[fn.__name__] = ToolDefinition(
                name=fn.__name__,
                description=(fn.__doc__ or "").strip(),
                input_schema=build_input_schema(fn),
                handler=fn,
            )
            return fn

        return decorator

    # --- MCP method handlers ---

    def _handle_initialize(self) -> dict[str, Any]:
        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": self.name, "version": self.version},
        }

    def _handle_tools_list(self) -> dict[str, Any]:
        return {
            "tools": [
                {"name": t.name, "description": t.description, "inputSchema": t.input_schema}
                for t in self._tools.values()
            ]
        }

    def _handle_tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        tool_name = params.get("name")
        if not isinstance(tool_name, str):
            raise MCPProtocolError(INVALID_PARAMS, "'params.name' is required and must be a string")

        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise MCPProtocolError(INVALID_PARAMS, "'params.arguments' must be an object")

        tool = self._tools.get(tool_name)
        if tool is None:
            # Unknown tool is a protocol-level *result*, not a JSON-RPC
            # error -- this is how MCP distinguishes "the call reached the
            # server but the tool failed" from "the request was malformed."
            return {"isError": True, "content": [{"type": "text", "text": f"Unknown tool '{tool_name}'."}]}

        try:
            result = tool.handler(**arguments)
        except TypeError as exc:
            return {"isError": True, "content": [{"type": "text", "text": f"Invalid arguments for '{tool_name}': {exc}"}]}
        except Exception as exc:  # noqa: BLE001 -- a tool failing must not crash the server
            return {"isError": True, "content": [{"type": "text", "text": f"Tool '{tool_name}' raised: {exc}"}]}

        return {"content": [{"type": "text", "text": json.dumps(result)}]}

    def dispatch_message(self, raw_message: dict[str, Any] | JsonRpcRequest) -> JsonRpcResponse | None:
        """Dispatches one already-parsed request/notification. Returns None
        for notifications (no response expected) or an unrecognized
        no-id message; otherwise returns the JsonRpcResponse to send."""
        request = raw_message if isinstance(raw_message, JsonRpcRequest) else JsonRpcRequest(
            method=raw_message.get("method", ""),
            params=raw_message.get("params") or {},
            id=raw_message.get("id"),
        )

        try:
            if request.method == "initialize":
                result = self._handle_initialize()
            elif request.method == "notifications/initialized":
                return None
            elif request.method == "tools/list":
                result = self._handle_tools_list()
            elif request.method == "tools/call":
                result = self._handle_tools_call(request.params)
            elif request.method == "ping":
                result = {}
            else:
                raise MCPProtocolError(METHOD_NOT_FOUND, f"Method not found: {request.method}")
        except MCPProtocolError as exc:
            if request.is_notification:
                return None
            return JsonRpcResponse(id=request.id, error=JsonRpcError(code=exc.code, message=exc.message))
        except Exception as exc:  # noqa: BLE001 -- never let an unexpected error kill the loop
            if request.is_notification:
                return None
            return JsonRpcResponse(id=request.id, error=JsonRpcError(code=INTERNAL_ERROR, message=str(exc)))

        if request.is_notification:
            return None
        return JsonRpcResponse(id=request.id, result=result)

    def handle_line(self, line: str) -> str | None:
        """Parses and dispatches one line of input, returning the response
        as a JSON string (or None for notifications/blank lines)."""
        line = line.strip()
        if not line:
            return None

        try:
            request = parse_request(line)
        except MCPProtocolError as exc:
            # A malformed request has no reliable id to reply to; JSON-RPC
            # allows replying with id: null in that case.
            response = JsonRpcResponse(id=None, error=JsonRpcError(code=exc.code, message=exc.message))
            return json.dumps(response.to_dict())

        response = self.dispatch_message(request)
        if response is None:
            return None
        return json.dumps(response.to_dict())

    def run(self, in_stream=None, out_stream=None) -> None:
        """The stdio transport: one JSON-RPC message per line on stdin,
        one JSON-RPC response per line on stdout. Runs until stdin closes."""
        in_stream = in_stream or sys.stdin
        out_stream = out_stream or sys.stdout

        for line in in_stream:
            response_line = self.handle_line(line)
            if response_line is not None:
                out_stream.write(response_line + "\n")
                out_stream.flush()