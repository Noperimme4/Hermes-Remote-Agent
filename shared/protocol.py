"""
Shared protocol definitions for Remote Agent.
Used by both server and client.
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime


class MessageType(Enum):
    """Message types for client-server communication."""
    # Authentication
    AUTH_REQUEST = "auth_request"
    AUTH_RESPONSE = "auth_response"
    
    # Commands
    COMMAND_REQUEST = "command_request"
    COMMAND_RESPONSE = "command_response"
    COMMAND_STREAM = "command_stream"
    
    # System
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"
    DISCONNECT = "disconnect"
    ERROR = "error"
    
    # File operations
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    FILE_LIST = "file_list"
    
    # Process management
    PROCESS_LIST = "process_list"
    PROCESS_KILL = "process_kill"
    
    # Shell/Interactive
    SHELL_START = "shell_start"
    SHELL_DATA = "shell_data"
    SHELL_RESIZE = "shell_resize"


class CommandStatus(Enum):
    """Command execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


# ─── Base Message ─────────────────────────────────────────────────

@dataclass
class BaseMessage:
    """Base message class with common fields."""
    type: MessageType = MessageType.ERROR
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        data = asdict(self)
        data['type'] = self.type.value
        return json.dumps(data, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, data: str) -> 'BaseMessage':
        """Deserialize from JSON."""
        obj = json.loads(data)
        obj['type'] = MessageType(obj['type'])
        return cls(**obj)


# ─── Authentication ──────────────────────────────────────────────

@dataclass(kw_only=True)
class AuthRequest(BaseMessage):
    """Authentication request from client."""
    token: str
    client_name: str = "remote-agent-client"
    client_version: str = "1.0.0"
    capabilities: List[str] = field(default_factory=lambda: ["command", "file", "shell"])
    
    def __post_init__(self):
        self.type = MessageType.AUTH_REQUEST


@dataclass(kw_only=True)
class AuthResponse(BaseMessage):
    """Authentication response from server."""
    success: bool
    message: str
    session_id: Optional[str] = None
    server_name: Optional[str] = None
    server_version: Optional[str] = None
    allowed_commands: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self.type = MessageType.AUTH_RESPONSE


# ─── Commands ────────────────────────────────────────────────────

@dataclass(kw_only=True)
class CommandRequest(BaseMessage):
    """Command execution request."""
    command: str
    args: List[str] = field(default_factory=list)
    working_dir: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    timeout: int = 60
    stream_output: bool = False
    shell: bool = False
    
    def __post_init__(self):
        self.type = MessageType.COMMAND_REQUEST


@dataclass(kw_only=True)
class CommandResponse(BaseMessage):
    """Command execution response."""
    request_id: str
    status: CommandStatus
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    execution_time: float = 0.0
    
    def __post_init__(self):
        self.type = MessageType.COMMAND_RESPONSE
        if isinstance(self.status, str):
            self.status = CommandStatus(self.status)


@dataclass(kw_only=True)
class CommandStream(BaseMessage):
    """Streaming command output chunk."""
    request_id: str
    chunk_type: str  # "stdout", "stderr", "exit"
    data: str
    sequence: int = 0
    
    def __post_init__(self):
        self.type = MessageType.COMMAND_STREAM


# ─── Heartbeat ───────────────────────────────────────────────────

@dataclass(kw_only=True)
class Heartbeat(BaseMessage):
    """Heartbeat message."""
    client_id: str
    
    def __post_init__(self):
        self.type = MessageType.HEARTBEAT


# ─── Error ───────────────────────────────────────────────────────

@dataclass(kw_only=True)
class ErrorMessage(BaseMessage):
    """Error message."""
    code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    
    def __post_init__(self):
        self.type = MessageType.ERROR

# ─── File Operations ─────────────────────────────────────────────

@dataclass(kw_only=True)
class FileListRequest(BaseMessage):
    """File listing request."""
    path: str = "."
    recursive: bool = False
    show_hidden: bool = False
    
    def __post_init__(self):
        self.type = MessageType.FILE_LIST


@dataclass(kw_only=True)
class FileInfo(BaseMessage):
    """File information."""
    request_id: str
    name: str
    path: str
    size: int
    is_dir: bool
    modified: str
    permissions: str
    
    def __post_init__(self):
        self.type = MessageType.FILE_LIST


# ─── Message Parsing ─────────────────────────────────────────────

_TYPE_MAP = {
    MessageType.AUTH_REQUEST: AuthRequest,
    MessageType.AUTH_RESPONSE: AuthResponse,
    MessageType.COMMAND_REQUEST: CommandRequest,
    MessageType.COMMAND_RESPONSE: CommandResponse,
    MessageType.COMMAND_STREAM: CommandStream,
    MessageType.HEARTBEAT: Heartbeat,
    MessageType.ERROR: ErrorMessage,
    MessageType.FILE_LIST: FileListRequest,
    MessageType.DISCONNECT: BaseMessage,
}


def parse_message(data: str) -> BaseMessage:
    """Parse JSON string to appropriate message type."""
    obj = json.loads(data)
    msg_type = MessageType(obj.get('type', 'error'))
    cls = _TYPE_MAP.get(msg_type, BaseMessage)
    
    # Remove 'type' from obj since it's handled by __post_init__
    obj.pop('type', None)
    return cls(**obj)


# ─── Utility Functions ───────────────────────────────────────────

def create_command_request(command: str, args: List[str] = None, **kwargs) -> CommandRequest:
    """Create a command request."""
    return CommandRequest(command=command, args=args or [], **kwargs)


def create_auth_request(token: str, **kwargs) -> AuthRequest:
    """Create an auth request."""
    return AuthRequest(token=token, **kwargs)