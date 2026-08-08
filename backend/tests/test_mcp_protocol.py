import json

import pytest

from app.mcp_protocol import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    MCPProtocolError,
    MCPServer,
    build_input_schema,
    parse_request,
)


# --- parse_request ---

def test_parse_request_valid_json_rpc():
    req = parse_request('{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}')
    assert req.method == "tools/list"
    assert req.id == 1
    assert req.params == {}
    assert not req.is_notification


def test_parse_request_notification_has_no_id():
    req = parse_request('{"jsonrpc": "2.0", "method": "notifications/initialized"}')
    assert req.id is None
    assert req.is_notification


def test_parse_request_defaults_missing_params_to_empty_dict():
    req = parse_request('{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}')
    assert req.params == {}


def test_parse_request_rejects_invalid_json():
    with pytest.raises(MCPProtocolError) as exc_info:
        parse_request("{not valid json")
    assert exc_info.value.code == PARSE_ERROR


def test_parse_request_rejects_non_object():
    with pytest.raises(MCPProtocolError) as exc_info:
        parse_request("[1, 2, 3]")
    assert exc_info.value.code == INVALID_REQUEST


def test_parse_request_rejects_missing_method():
    with pytest.raises(MCPProtocolError) as exc_info:
        parse_request('{"jsonrpc": "2.0", "id": 1}')
    assert exc_info.value.code == INVALID_REQUEST


def test_parse_request_rejects_non_object_params():
    with pytest.raises(MCPProtocolError) as exc_info:
        parse_request('{"jsonrpc": "2.0", "id": 1, "method": "x", "params": "not an object"}')
    assert exc_info.value.code == INVALID_REQUEST


# --- build_input_schema ---

def test_build_input_schema_required_and_optional_params():
    def example(name: str, count: int, note: str | None = None) -> dict:
        return {}

    schema = build_input_schema(example)
    assert schema["type"] == "object"
    assert schema["properties"]["name"] == {"type": "string"}
    assert schema["properties"]["count"] == {"type": "integer"}
    assert schema["properties"]["note"] == {"type": "string"}
    assert set(schema["required"]) == {"name", "count"}


def test_build_input_schema_no_required_params_omits_required_key():
    def example(flag: bool = True) -> dict:
        return {}

    schema = build_input_schema(example)
    assert "required" not in schema


def test_build_input_schema_no_params():
    def example() -> dict:
        return {}

    schema = build_input_schema(example)
    assert schema == {"type": "object", "properties": {}}


# --- MCPServer: tool registration ---

def test_tool_decorator_returns_function_unchanged():
    server = MCPServer("test")

    @server.tool()
    def add(a: int, b: int) -> dict:
        """Adds two numbers."""
        return {"sum": a + b}

    # still directly callable, not wrapped
    assert add(2, 3) == {"sum": 5}
    assert "add" in server._tools
    assert server._tools["add"].description == "Adds two numbers."


# --- MCPServer: dispatch_message / handle_line ---

@pytest.fixture()
def server():
    s = MCPServer("test-server", version="1.2.3")

    @s.tool()
    def echo(text: str) -> dict:
        """Echoes text back."""
        return {"echo": text}

    @s.tool()
    def boom() -> dict:
        """Always raises."""
        raise RuntimeError("kaboom")

    return s


def test_initialize(server):
    line = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    response = json.loads(server.handle_line(line))

    assert response["id"] == 1
    assert response["result"]["serverInfo"] == {"name": "test-server", "version": "1.2.3"}
    assert response["result"]["protocolVersion"]
    assert "tools" in response["result"]["capabilities"]


def test_notifications_initialized_gets_no_response(server):
    line = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert server.handle_line(line) is None


def test_tools_list(server):
    line = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    response = json.loads(server.handle_line(line))

    names = {t["name"] for t in response["result"]["tools"]}
    assert names == {"echo", "boom"}


def test_tools_call_success(server):
    line = json.dumps({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "echo", "arguments": {"text": "hi"}},
    })
    response = json.loads(server.handle_line(line))

    content_text = response["result"]["content"][0]["text"]
    assert json.loads(content_text) == {"echo": "hi"}
    assert "isError" not in response["result"]


def test_tools_call_unknown_tool_is_a_result_not_a_json_rpc_error(server):
    line = json.dumps({
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "nonexistent", "arguments": {}},
    })
    response = json.loads(server.handle_line(line))

    assert "error" not in response  # not a JSON-RPC-level error
    assert response["result"]["isError"] is True
    assert "Unknown tool" in response["result"]["content"][0]["text"]


def test_tools_call_handler_exception_becomes_error_result_not_crash(server):
    line = json.dumps({
        "jsonrpc": "2.0", "id": 5, "method": "tools/call",
        "params": {"name": "boom", "arguments": {}},
    })
    response = json.loads(server.handle_line(line))

    assert response["result"]["isError"] is True
    assert "kaboom" in response["result"]["content"][0]["text"]


def test_tools_call_missing_name_is_invalid_params(server):
    line = json.dumps({"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {}})
    response = json.loads(server.handle_line(line))

    assert response["error"]["code"] == INVALID_PARAMS


def test_unknown_method_returns_method_not_found(server):
    line = json.dumps({"jsonrpc": "2.0", "id": 7, "method": "nonexistent/method"})
    response = json.loads(server.handle_line(line))

    assert response["error"]["code"] == METHOD_NOT_FOUND


def test_malformed_json_line_returns_parse_error(server):
    response = json.loads(server.handle_line("{not json"))
    assert response["error"]["code"] == PARSE_ERROR
    assert response["id"] is None


def test_blank_line_returns_none(server):
    assert server.handle_line("") is None
    assert server.handle_line("   \n") is None


def test_ping(server):
    line = json.dumps({"jsonrpc": "2.0", "id": 8, "method": "ping"})
    response = json.loads(server.handle_line(line))
    assert response["result"] == {}


# --- MCPServer.run: the stdio loop end to end ---

def test_run_processes_multiple_lines_from_a_stream():
    import io

    server = MCPServer("loop-test")

    @server.tool()
    def double(n: int) -> dict:
        """Doubles a number."""
        return {"result": n * 2}

    requests = "\n".join([
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),  # no response expected
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "double", "arguments": {"n": 21}}}),
    ]) + "\n"

    in_stream = io.StringIO(requests)
    out_stream = io.StringIO()

    server.run(in_stream=in_stream, out_stream=out_stream)

    lines = [line for line in out_stream.getvalue().splitlines() if line]
    assert len(lines) == 2  # the notification produced no output line

    first = json.loads(lines[0])
    assert first["id"] == 1
    assert first["result"]["serverInfo"]["name"] == "loop-test"

    second = json.loads(lines[1])
    assert second["id"] == 2
    assert json.loads(second["result"]["content"][0]["text"]) == {"result": 42}