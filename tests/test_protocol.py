"""Tests for shared protocol"""

import json
from shared.protocol import (
    MessageType, CommandStatus,
    AuthRequest, AuthResponse, CommandRequest, CommandResponse,
    CommandStream, Heartbeat, ErrorMessage, FileListRequest,
    parse_message, create_command_request, create_auth_request
)


def test_auth_request():
    req = create_auth_request("test-token", client_name="test-client")
    assert req.type == MessageType.AUTH_REQUEST
    assert req.token == "test-token"
    assert req.client_name == "test-client"
    assert req.capabilities == ["command", "file", "shell"]


def test_auth_response():
    resp = AuthResponse(
        request_id="req-123",
        success=True,
        message="OK",
        session_id="sess-456",
        allowed_commands=["ls", "cat"]
    )
    assert resp.success is True
    assert resp.session_id == "sess-456"
    assert "ls" in resp.allowed_commands


def test_command_request():
    req = create_command_request("ls", ["-la"], working_dir="/tmp", timeout=30)
    assert req.command == "ls"
    assert req.args == ["-la"]
    assert req.working_dir == "/tmp"
    assert req.timeout == 30


def test_command_response():
    resp = CommandResponse(
        request_id="req-123",
        status=CommandStatus.COMPLETED,
        exit_code=0,
        stdout="output\n",
        stderr="",
        execution_time=0.5
    )
    assert resp.status == CommandStatus.COMPLETED
    assert resp.exit_code == 0


def test_command_stream():
    chunk = CommandStream(
        request_id="req-123",
        chunk_type="stdout",
        data="hello\n",
        sequence=1
    )
    assert chunk.chunk_type == "stdout"
    assert chunk.sequence == 1


def test_heartbeat():
    hb = Heartbeat(client_id="client-1")
    assert hb.type == MessageType.HEARTBEAT
    assert hb.client_id == "client-1"


def test_error_message():
    err = ErrorMessage(code="NOT_AUTH", message="Invalid token", request_id="req-1")
    assert err.code == "NOT_AUTH"
    assert err.message == "Invalid token"


def test_parse_message():
    data = json.dumps({
        "type": "command_request",
        "request_id": "req-1",
        "timestamp": "2024-01-01T00:00:00",
        "command": "echo",
        "args": ["hello"],
        "timeout": 10
    })
    msg = parse_message(data)
    assert isinstance(msg, CommandRequest)
    assert msg.command == "echo"
    assert msg.args == ["hello"]


def test_serialization_roundtrip():
    req = create_command_request("ls", ["-la"])
    json_str = req.to_json()
    parsed = parse_message(json_str)
    assert parsed.command == req.command
    assert parsed.args == req.args


if __name__ == "__main__":
    test_auth_request()
    test_auth_response()
    test_command_request()
    test_command_response()
    test_command_stream()
    test_heartbeat()
    test_error_message()
    test_parse_message()
    test_serialization_roundtrip()
    print("✅ All protocol tests passed!")