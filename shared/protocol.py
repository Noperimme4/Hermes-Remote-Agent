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
    
    # Remote File Access (Virtual FS) - Requests
    REMOTE_FILE_OPEN = "remote_file_open"
    REMOTE_FILE_READ = "remote_file_read"
    REMOTE_FILE_WRITE = "remote_file_write"
    REMOTE_FILE_SEEK = "remote_file_seek"
    REMOTE_FILE_CLOSE = "remote_file_close"
    REMOTE_FILE_STAT = "remote_file_stat"
    REMOTE_FILE_LIST = "remote_file_list"
    
    # Remote File Access - Responses
    REMOTE_FILE_OPEN_RESPONSE = "remote_file_open_response"
    REMOTE_FILE_CHUNK = "remote_file_chunk"
    REMOTE_FILE_ERROR = "remote_file_error"
    REMOTE_FILE_STAT_RESPONSE = "remote_file_stat_response"
    REMOTE_FILE_LIST_RESPONSE = "remote_file_list_response"
    
    # Process management
    PROCESS_LIST = "process_list"
    PROCESS_KILL = "process_kill"
    
    # Shell/Interactive PTY
    SHELL_START = "shell_start"
    SHELL_DATA = "shell_data"
    SHELL_RESIZE = "shell_resize"
    SHELL_EXIT = "shell_exit"


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


# ─── Remote File Access (Virtual FS over Agent Channel) ──────────

@dataclass(kw_only=True)
class RemoteFileOpenRequest(BaseMessage):
    """Open a remote file on the client side."""
    path: str
    mode: str = "rb"  # rb, r, wb, w
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        self.type = MessageType.REMOTE_FILE_OPEN


@dataclass(kw_only=True)
class RemoteFileOpenResponse(BaseMessage):
    """Response to remote file open request."""
    request_id: str
    success: bool = True
    error: str = ""
    handle: str = ""
    size: int = 0
    is_dir: bool = False
    
    def __post_init__(self):
        self.type = MessageType.REMOTE_FILE_OPEN_RESPONSE


@dataclass(kw_only=True)
class RemoteFileReadRequest(BaseMessage):
    """Read chunk from remote file."""
    handle: str
    offset: int
    length: int
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        self.type = MessageType.REMOTE_FILE_READ


@dataclass(kw_only=True)
class RemoteFileWriteRequest(BaseMessage):
    """Write chunk to remote file."""
    handle: str
    offset: int
    data: str  # base64 encoded
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        self.type = MessageType.REMOTE_FILE_WRITE


@dataclass(kw_only=True)
class RemoteFileSeekRequest(BaseMessage):
    """Seek in remote file."""
    handle: str
    offset: int
    whence: int = 0  # 0=absolute, 1=relative, 2=from end
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        self.type = MessageType.REMOTE_FILE_SEEK


@dataclass(kw_only=True)
class RemoteFileCloseRequest(BaseMessage):
    """Close remote file handle."""
    handle: str
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        self.type = MessageType.REMOTE_FILE_CLOSE


@dataclass(kw_only=True)
class RemoteFileStatRequest(BaseMessage):
    """Stat remote file (get metadata without opening)."""
    path: str
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        self.type = MessageType.REMOTE_FILE_STAT


@dataclass(kw_only=True)
class RemoteFileStatResponse(BaseMessage):
    """Response to remote file stat."""
    request_id: str
    success: bool = True
    error: str = ""
    size: int = 0
    is_dir: bool = False
    modified: str = ""
    permissions: str = ""
    
    def __post_init__(self):
        self.type = MessageType.REMOTE_FILE_STAT_RESPONSE


@dataclass(kw_only=True)
class RemoteFileListRequest(BaseMessage):
    """List remote directory."""
    path: str = "."
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        self.type = MessageType.REMOTE_FILE_LIST


@dataclass(kw_only=True)
class RemoteFileListResponse(BaseMessage):
    """Response to remote directory list."""
    request_id: str
    entries: List[FileInfo] = field(default_factory=list)
    success: bool = True
    error: str = ""
    
    def __post_init__(self):
        self.type = MessageType.REMOTE_FILE_LIST_RESPONSE


@dataclass(kw_only=True)
class RemoteFileChunk(BaseMessage):
    """File data chunk (base64 encoded)."""
    handle: str
    offset: int
    data: str  # base64 encoded
    eof: bool = False
    request_id: str = ""
    
    def __post_init__(self):
        self.type = MessageType.REMOTE_FILE_CHUNK


@dataclass(kw_only=True)
class RemoteFileError(BaseMessage):
    """Error in remote file operation."""
    handle: str = ""
    request_id: str
    code: str
    message: str
    
    def __post_init__(self):
        self.type = MessageType.REMOTE_FILE_ERROR


# ─── PTY Shell Operations ────────────────────────────────────────


@dataclass(kw_only=True)
class ShellStartRequest(BaseMessage):
    """Start a new PTY shell session."""
    cols: int = 80
    rows: int = 24
    env: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    
    def __post_init__(self):
        self.type = MessageType.SHELL_START


@dataclass(kw_only=True)
class ShellStartResponse(BaseMessage):
    """Response to shell start request."""
    request_id: str
    success: bool
    message: str
    shell_id: Optional[str] = None
    
    def __post_init__(self):
        self.type = MessageType.SHELL_START


@dataclass(kw_only=True)
class ShellData(BaseMessage):
    """PTY data chunk (stdin/stdout)."""
    shell_id: str
    data: str  # base64 encoded binary data
    direction: str  # "stdin" (client->server) or "stdout" (server->client)
    
    def __post_init__(self):
        self.type = MessageType.SHELL_DATA


@dataclass(kw_only=True)
class ShellResize(BaseMessage):
    """Resize PTY terminal."""
    shell_id: str
    cols: int
    rows: int
    
    def __post_init__(self):
        self.type = MessageType.SHELL_RESIZE


@dataclass(kw_only=True)
class ShellExit(BaseMessage):
    """Exit/close PTY shell session."""
    shell_id: str
    exit_code: Optional[int] = None
    
    def __post_init__(self):
        self.type = MessageType.SHELL_EXIT


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
    MessageType.SHELL_START: ShellStartRequest,
    MessageType.SHELL_DATA: ShellData,
    MessageType.SHELL_RESIZE: ShellResize,
    MessageType.SHELL_EXIT: ShellExit,
    # Remote File Access
    MessageType.REMOTE_FILE_OPEN: RemoteFileOpenRequest,
    MessageType.REMOTE_FILE_READ: RemoteFileReadRequest,
    MessageType.REMOTE_FILE_WRITE: RemoteFileWriteRequest,
    MessageType.REMOTE_FILE_SEEK: RemoteFileSeekRequest,
    MessageType.REMOTE_FILE_CLOSE: RemoteFileCloseRequest,
    MessageType.REMOTE_FILE_STAT: RemoteFileStatRequest,
    MessageType.REMOTE_FILE_LIST: RemoteFileListRequest,
    MessageType.REMOTE_FILE_CHUNK: RemoteFileChunk,
    MessageType.REMOTE_FILE_ERROR: RemoteFileError,
    MessageType.REMOTE_FILE_OPEN_RESPONSE: RemoteFileOpenResponse,
    MessageType.REMOTE_FILE_STAT_RESPONSE: RemoteFileStatResponse,
    MessageType.REMOTE_FILE_LIST_RESPONSE: RemoteFileListResponse,
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