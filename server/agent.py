"""
Remote Agent Server - Runs on the remote machine (VPS/Server).
Accepts authenticated connections and executes commands.
"""

import asyncio
import json
import logging
import os
import pty
import signal
import struct
import subprocess
import sys
import termios
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import fcntl
import base64

# Add shared to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from protocol import (
    MessageType, CommandStatus, BaseMessage,
    AuthRequest, AuthResponse, CommandRequest, CommandResponse,
    CommandStream, Heartbeat, ErrorMessage, FileListRequest, FileInfo,
    ShellStartRequest, ShellStartResponse, ShellData, ShellResize, ShellExit,
    # Remote File Access
    RemoteFileOpenRequest, RemoteFileOpenResponse,
    RemoteFileReadRequest, RemoteFileWriteRequest,
    RemoteFileSeekRequest, RemoteFileCloseRequest,
    RemoteFileStatRequest, RemoteFileStatResponse,
    RemoteFileListRequest, RemoteFileListResponse,
    RemoteFileChunk, RemoteFileError,
    parse_message,
)

from .remote_files import RemoteFileServer


# ─── Configuration ────────────────────────────────────────────────

@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8765
    token: str = ""  # Must be set via env or config
    allowed_commands: List[str] = field(default_factory=lambda: [
        "ls", "cat", "head", "tail", "grep", "find", "ps", "top", "htop",
        "df", "du", "free", "uptime", "whoami", "pwd", "echo", "date",
        "python3", "python", "pip", "npm", "node", "git", "docker", "kubectl",
        "systemctl", "journalctl", "ss", "netstat", "lsof", "curl", "wget",
        "tar", "gzip", "gunzip", "zip", "unzip", "rsync", "scp", "ssh",
        "mkdir", "touch", "cp", "mv", "rm", "chmod", "chown", "ln",
        "apt", "apt-get", "yum", "dnf", "pacman", "pip3", "pipx",
        "vim", "nano", "code", "less", "more", "bat", "fd", "rg",
        "make", "cmake", "cargo", "go", "rustc", "gcc", "clang",
    ])
    blocked_commands: List[str] = field(default_factory=lambda: [
        "reboot", "shutdown", "halt", "poweroff", "init", "systemctl reboot",
        "systemctl poweroff", "systemctl halt", "mkfs", "fdisk", "parted",
        "dd", "wipefs", "cryptsetup", "passwd", "userdel", "groupdel",
        "visudo", "chroot", "pivot_root", "kexec", "mount", "umount",
    ])
    max_command_timeout: int = 300
    default_timeout: int = 60
    heartbeat_interval: int = 30
    log_level: str = "INFO"
    log_file: Optional[str] = None
    working_dir: str = "/data/workspace"
    max_output_size: int = 1024 * 1024  # 1MB
    allow_shell: bool = False
    allow_file_ops: bool = True
    tls_cert: Optional[str] = None
    tls_key: Optional[str] = None
    # Remote file access mount points: "remote_path:local_path,remote_path:local_path"
    remote_mounts: Dict[str, str] = field(default_factory=lambda: {
        "/": "/",
        "/home": "/home",
        "/data": "/data",
        "/tmp": "/tmp",
    })

    @classmethod
    def from_env(cls) -> 'ServerConfig':
        """Load config from environment variables."""
        # Parse remote mounts from AGENT_REMOTE_MOUNTS
        remote_mounts_str = os.getenv("AGENT_REMOTE_MOUNTS", "")
        remote_mounts = {}
        if remote_mounts_str:
            for pair in remote_mounts_str.split(","):
                if ":" in pair:
                    remote, local = pair.split(":", 1)
                    remote_mounts[remote] = local
        else:
            remote_mounts = {
                "/": "/",
                "/home": "/home",
                "/data": "/data",
                "/tmp": "/tmp",
            }
        
        return cls(
            host=os.getenv("AGENT_HOST", "0.0.0.0"),
            port=int(os.getenv("AGENT_PORT", "8765")),
            token=os.getenv("AGENT_TOKEN", ""),
            allowed_commands=os.getenv("AGENT_ALLOWED_COMMANDS", "").split(",") if os.getenv("AGENT_ALLOWED_COMMANDS") else None,
            blocked_commands=os.getenv("AGENT_BLOCKED_COMMANDS", "").split(",") if os.getenv("AGENT_BLOCKED_COMMANDS") else None,
            max_command_timeout=int(os.getenv("AGENT_MAX_TIMEOUT", "300")),
            default_timeout=int(os.getenv("AGENT_DEFAULT_TIMEOUT", "60")),
            heartbeat_interval=int(os.getenv("AGENT_HEARTBEAT", "30")),
            log_level=os.getenv("AGENT_LOG_LEVEL", "INFO"),
            log_file=os.getenv("AGENT_LOG_FILE"),
            working_dir=os.getenv("AGENT_WORKDIR", "/data/workspace"),
            max_output_size=int(os.getenv("AGENT_MAX_OUTPUT", str(1024 * 1024))),
            allow_shell=os.getenv("AGENT_ALLOW_SHELL", "false").lower() == "true",
            allow_file_ops=os.getenv("AGENT_ALLOW_FILES", "true").lower() == "true",
            tls_cert=os.getenv("AGENT_TLS_CERT"),
            tls_key=os.getenv("AGENT_TLS_KEY"),
            remote_mounts=remote_mounts,
        )

    def __post_init__(self):
        if self.allowed_commands is None:
            self.allowed_commands = self.__dataclass_fields__['allowed_commands'].default_factory()
        if self.blocked_commands is None:
            self.blocked_commands = self.__dataclass_fields__['blocked_commands'].default_factory()


# ─── Session Management ──────────────────────────────────────────

@dataclass
class ClientSession:
    """Represents a connected client session."""
    session_id: str
    client_name: str
    client_version: str
    capabilities: List[str]
    connected_at: float
    last_heartbeat: float
    writer: asyncio.StreamWriter
    reader: asyncio.StreamReader
    current_dir: str = "/data/workspace"
    active_commands: Dict[str, asyncio.Task] = field(default_factory=dict)
    authenticated: bool = False
    shells: Dict[str, 'ShellSession'] = field(default_factory=dict)


@dataclass
class ShellSession:
    """Represents a PTY shell session."""
    shell_id: str
    session_id: str
    master_fd: int
    slave_fd: int
    process: asyncio.subprocess.Process
    cols: int
    rows: int
    created_at: float
    last_activity: float
    reader_task: Optional[asyncio.Task] = None


# ─── Command Executor ────────────────────────────────────────────

class CommandExecutor:
    """Handles command execution with safety checks."""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.logger = logging.getLogger("executor")
    
    def is_command_allowed(self, command: str, args: List[str]) -> bool:
        """Check if command is in allowlist and not in blocklist."""
        full_cmd = f"{command} {' '.join(args)}".strip()
        
        # Check blocklist first (exact match or prefix)
        for blocked in self.config.blocked_commands:
            if full_cmd.startswith(blocked.strip()):
                self.logger.warning(f"Blocked command: {full_cmd} (matches {blocked})")
                return False
        
        # If allowlist is empty, allow all (except blocked)
        if not self.config.allowed_commands:
            return True
        
        # Check allowlist
        base_cmd = command.split('/')[-1]  # Get basename
        for allowed in self.config.allowed_commands:
            allowed = allowed.strip()
            if base_cmd == allowed or full_cmd.startswith(allowed):
                return True
        
        self.logger.warning(f"Command not in allowlist: {full_cmd}")
        return False
    
    async def execute(self, request: CommandRequest, session: ClientSession) -> CommandResponse:
        """Execute a command and return response."""
        start_time = time.time()
        
        # Safety check
        if not self.is_command_allowed(request.command, request.args):
            return CommandResponse(
                request_id=request.request_id,
                status=CommandStatus.FAILED,
                exit_code=-1,
                stderr=f"Command not allowed: {request.command}",
                execution_time=time.time() - start_time
            )
        
        # Prepare environment
        env = os.environ.copy()
        env.update(request.env)
        
        # Working directory
        cwd = request.working_dir or session.current_dir
        if not os.path.isabs(cwd):
            cwd = os.path.join(session.current_dir, cwd)
        cwd = os.path.normpath(cwd)
        
        # Ensure cwd exists and is within allowed paths
        if not os.path.exists(cwd):
            return CommandResponse(
                request_id=request.request_id,
                status=CommandStatus.FAILED,
                exit_code=-1,
                stderr=f"Working directory does not exist: {cwd}",
                execution_time=time.time() - start_time
            )
        
        # Build command
        if request.shell and self.config.allow_shell:
            cmd_str = f"{request.command} {' '.join(request.args)}"
            cmd = ["bash", "-c", cmd_str]
        else:
            cmd = [request.command] + request.args
        
        self.logger.info(f"Executing: {' '.join(cmd)} (cwd={cwd})")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=self.config.max_output_size
            )
            
            session.active_commands[request.request_id] = asyncio.current_task()
            
            stdout_chunks = []
            stderr_chunks = []
            
            try:
                await asyncio.wait_for(process.wait(), timeout=request.timeout)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return CommandResponse(
                    request_id=request.request_id,
                    status=CommandStatus.TIMEOUT,
                    exit_code=-1,
                    stderr=f"Command timed out after {request.timeout}s",
                    execution_time=time.time() - start_time
                )
            finally:
                session.active_commands.pop(request.request_id, None)
            
            stdout, stderr = await process.communicate()
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')
            
            status = CommandStatus.COMPLETED if process.returncode == 0 else CommandStatus.FAILED
            return CommandResponse(
                request_id=request.request_id,
                status=status,
                exit_code=process.returncode,
                stdout=stdout_str,
                stderr=stderr_str,
                execution_time=time.time() - start_time
            )
        
        except Exception as e:
            self.logger.exception(f"Execution error: {e}")
            return CommandResponse(
                request_id=request.request_id,
                status=CommandStatus.FAILED,
                exit_code=-1,
                stderr=f"Execution error: {str(e)}",
                execution_time=time.time() - start_time
            )


# ─── File Operations ─────────────────────────────────────────────

class FileManager:
    """Handles file operations."""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.logger = logging.getLogger("files")
    
    def list_files(self, request: FileListRequest, session: ClientSession) -> List[FileInfo]:
        """List files in a directory."""
        path = request.path
        if not os.path.isabs(path):
            path = os.path.join(session.current_dir, path)
        path = os.path.normpath(path)
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"Path not found: {path}")
        
        if not os.path.isdir(path):
            raise NotADirectoryError(f"Not a directory: {path}")
        
        files = []
        if request.recursive:
            for root, dirs, filenames in os.walk(path):
                for name in dirs + filenames:
                    full = os.path.join(root, name)
                    rel = os.path.relpath(full, path)
                    files.append(self._file_info(name, rel, full))
        else:
            for name in sorted(os.listdir(path)):
                full = os.path.join(path, name)
                files.append(self._file_info(name, name, full))
        
        return files
    
    def _file_info(self, name: str, rel_path: str, full_path: str) -> FileInfo:
        """Get file info for a single file."""
        try:
            stat = os.stat(full_path)
            is_dir = os.path.isdir(full_path)
            return FileInfo(
                request_id="",
                name=name,
                path=rel_path,
                size=stat.st_size,
                is_dir=is_dir,
                modified=str(stat.st_mtime),
                permissions=oct(stat.st_mode)[-3:]
            )
        except Exception:
            return FileInfo(
                request_id="",
                name=name,
                path=rel_path,
                size=0,
                is_dir=False,
                modified="",
                permissions="000"
            )


# ─── Main Server Class ───────────────────────────────────────────

class RemoteAgentServer:
    """Main server class."""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.logger = logging.getLogger("server")
        self.executor = CommandExecutor(config)
        self.file_manager = FileManager(config)
        
        # Remote File Access Server
        self.remote_file_server = RemoteFileServer(self._send_message)
        
        self.sessions: Dict[str, ClientSession] = {}
        self.server: Optional[asyncio.Server] = None
        self.running = False
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging."""
        level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        handlers = [logging.StreamHandler(sys.stdout)]
        if self.config.log_file:
            handlers.append(logging.FileHandler(self.config.log_file))
        
        logging.basicConfig(
            level=level,
            format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            handlers=handlers
        )
    
    async def start(self):
        """Start the server."""
        self.running = True
        
        # SSL context if certs provided
        ssl_context = None
        if self.config.tls_cert and self.config.tls_key:
            import ssl
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(self.config.tls_cert, self.config.tls_key)
            self.logger.info("TLS enabled")
        
        self.server = await asyncio.start_server(
            self._handle_client,
            self.config.host,
            self.config.port,
            ssl=ssl_context
        )
        
        addr = self.server.sockets[0].getsockname()
        self.logger.info(f"Server listening on {addr[0]}:{addr[1]}")
        
        # Start heartbeat monitor
        asyncio.create_task(self._heartbeat_monitor())
        
        async with self.server:
            await self.server.serve_forever()
    
    async def stop(self):
        """Stop the server."""
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Kill all active commands
        for session in self.sessions.values():
            for task in session.active_commands.values():
                task.cancel()
        
        self.logger.info("Server stopped")
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a client connection."""
        peer = writer.get_extra_info('peername')
        self.logger.info(f"New connection from {peer}")
        
        session = None
        try:
            while self.running:
                # Read message (length-prefixed)
                length_bytes = await reader.readexactly(4)
                length = int.from_bytes(length_bytes, 'big')
                
                if length > 10 * 1024 * 1024:  # 10MB max
                    self.logger.warning(f"Message too large: {length}")
                    break
                
                data = await reader.readexactly(length)
                message = parse_message(data.decode('utf-8'))
                
                # Handle message
                await self._handle_message(message, reader, writer, session)
        
        except asyncio.IncompleteReadError:
            self.logger.info(f"Client {peer} disconnected")
        except Exception as e:
            self.logger.exception(f"Error handling client {peer}: {e}")
        finally:
            if session and session.session_id in self.sessions:
                # Unregister from remote file server
                self.remote_file_server.unregister_client(session.session_id)
                del self.sessions[session.session_id]
            writer.close()
            await writer.wait_closed()
    
    async def _handle_message(self, message: BaseMessage, reader: asyncio.StreamReader,
                              writer: asyncio.StreamWriter, session: Optional[ClientSession]):
        """Route message to appropriate handler."""
        # Remote File Access messages
        if message.type in (
            MessageType.REMOTE_FILE_OPEN,
            MessageType.REMOTE_FILE_READ,
            MessageType.REMOTE_FILE_WRITE,
            MessageType.REMOTE_FILE_SEEK,
            MessageType.REMOTE_FILE_CLOSE,
            MessageType.REMOTE_FILE_STAT,
            MessageType.REMOTE_FILE_LIST,
            MessageType.REMOTE_FILE_CHUNK,
            MessageType.REMOTE_FILE_ERROR,
        ):
            await self._handle_remote_file(message, session, writer)
        elif message.type == MessageType.AUTH_REQUEST:
            await self._handle_auth(message, writer)
        elif message.type == MessageType.COMMAND_REQUEST:
            await self._handle_command(message, session, writer)
        elif message.type == MessageType.HEARTBEAT:
            await self._handle_heartbeat(message, session, writer)
        elif message.type == MessageType.FILE_LIST:
            await self._handle_file_list(message, session, writer)
        elif message.type == MessageType.SHELL_START:
            await self._handle_shell_start(message, session, writer)
        elif message.type == MessageType.SHELL_DATA:
            await self._handle_shell_data(message, session, writer)
        elif message.type == MessageType.SHELL_RESIZE:
            await self._handle_shell_resize(message, session, writer)
        elif message.type == MessageType.SHELL_EXIT:
            await self._handle_shell_exit(message, session, writer)
        elif message.type == MessageType.DISCONNECT:
            self.logger.info("Client requested disconnect")
            writer.close()
        else:
            self.logger.warning(f"Unhandled message type: {message.type}")
    
    async def _handle_remote_file(self, message: BaseMessage, session: Optional[ClientSession], writer: asyncio.StreamWriter):
        """Handle remote file access messages."""
        if not session or not session.authenticated:
            await self._send_message(writer, ErrorMessage(
                code="NOT_AUTHENTICATED",
                message="Not authenticated",
                request_id=message.request_id
            ))
            return
        
        # Route to remote file server
        response = await self.remote_file_server.handle_message(message)
        if response:
            await self._send_message(writer, response)
    
    async def _handle_auth(self, message: AuthRequest, writer: asyncio.StreamWriter):
        """Handle authentication request."""
        if not self.config.token:
            response = AuthResponse(
                request_id=message.request_id,
                success=False,
                message="Server not configured (no token set)"
            )
        elif message.token != self.config.token:
            self.logger.warning(f"Invalid token from client: {message.client_name}")
            response = AuthResponse(
                request_id=message.request_id,
                success=False,
                message="Invalid authentication token"
            )
        else:
            session_id = str(uuid.uuid4())
            session = ClientSession(
                session_id=session_id,
                client_name=message.client_name,
                client_version=message.client_version,
                capabilities=message.capabilities,
                connected_at=time.time(),
                last_heartbeat=time.time(),
                writer=writer,
                reader=reader,  # We have the reader in the handler
                authenticated=True
            )
            self.sessions[session_id] = session
            
            # Register client with Remote File Server
            self.remote_file_server.register_client(session_id, self.config.remote_mounts)
            
            self.logger.info(f"Client authenticated: {message.client_name} (session: {session_id})")
            
            response = AuthResponse(
                request_id=message.request_id,
                success=True,
                message="Authentication successful",
                allowed_commands=self.config.allowed_commands,
                session_id=session_id
            )
        
        await self._send_message(writer, response)
    
    async def _handle_command(self, message: CommandRequest, session: ClientSession, writer: asyncio.StreamWriter):
        """Handle command execution request."""
        if not session or not session.authenticated:
            await self._send_message(writer, ErrorMessage(
                code="NOT_AUTHENTICATED",
                message="Not authenticated",
                request_id=message.request_id
            ))
            return
        
        response = await self.executor.execute(message, session)
        await self._send_message(writer, response)
    
    async def _handle_heartbeat(self, message: Heartbeat, session: ClientSession, writer: asyncio.StreamWriter):
        """Handle heartbeat from client."""
        if session:
            session.last_heartbeat = time.time()
        
        await self._send_message(writer, Heartbeat(client_id="server"))
    
    async def _handle_file_list(self, message: FileListRequest, session: ClientSession, writer: asyncio.StreamWriter):
        """Handle file listing request."""
        if not session or not session.authenticated:
            await self._send_message(writer, ErrorMessage(
                code="NOT_AUTHENTICATED",
                message="Not authenticated",
                request_id=message.request_id
            ))
            return
        
        if not self.config.allow_file_ops:
            await self._send_message(writer, ErrorMessage(
                code="FILE_OPS_DISABLED",
                message="File operations are disabled on this server",
                request_id=message.request_id
            ))
            return
        
        try:
            files = self.file_manager.list_files(message, session)
            # Send each file as separate message
            for f in files:
                f.request_id = message.request_id
                await self._send_message(writer, f)
            
            # Send end marker
            await self._send_message(writer, BaseMessage(
                type=MessageType.FILE_LIST,
                request_id=message.request_id,
                timestamp=datetime.utcnow().isoformat()
            ))
        except Exception as e:
            await self._send_message(writer, ErrorMessage(
                code="FILE_LIST_ERROR",
                message=str(e),
                request_id=message.request_id
            ))
    
    # ─── Shell/PTY Handlers ────────────────────────────────────────────
    
    async def _handle_shell_start(self, message: ShellStartRequest, session: ClientSession, writer: asyncio.StreamWriter):
        """Start a new PTY shell session."""
        if not session or not session.authenticated:
            await self._send_message(writer, ErrorMessage(
                code="NOT_AUTHENTICATED",
                message="Not authenticated",
                request_id=message.request_id
            ))
            return
        
        if not self.config.allow_shell:
            await self._send_message(writer, ErrorMessage(
                code="SHELL_DISABLED",
                message="Shell access is disabled on this server",
                request_id=message.request_id
            ))
            return
        
        # Working directory
        cwd = message.cwd or session.current_dir
        if not os.path.isabs(cwd):
            cwd = os.path.join(session.current_dir, cwd)
        cwd = os.path.normpath(cwd)
        
        if not os.path.exists(cwd):
            cwd = session.current_dir
        
        # Start shell process
        shell = os.environ.get("SHELL", "/bin/bash")
        
        master_fd, slave_fd = pty.openpty()
        
        env = os.environ.copy()
        env.update(message.env)
        env["TERM"] = "xterm-256color"
        
        process = await asyncio.create_subprocess_exec(
            shell,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=cwd,
            env=env,
            start_new_session=True,
        )
        
        # Close slave_fd in parent (we only need master_fd)
        os.close(slave_fd)
        
        # Create shell session
        shell_id = str(uuid.uuid4())
        shell_session = ShellSession(
            shell_id=shell_id,
            session_id=session.session_id,
            master_fd=master_fd,
            slave_fd=-1,  # Already closed
            process=process,
            cols=message.cols,
            rows=message.rows,
            created_at=time.time(),
            last_activity=time.time(),
        )
        
        session.shells[shell_id] = shell_session
        
        # Start reader task to forward PTY output to client
        shell_session.reader_task = asyncio.create_task(
            self._shell_reader(shell_session, session, writer)
        )
        
        self.logger.info(f"Started shell {shell_id} for session {session.session_id}")
        
        response = ShellStartResponse(
            request_id=message.request_id,
            success=True,
            message="Shell started",
            shell_id=shell_id
        )
        await self._send_message(writer, response)
    
    async def _shell_reader(self, shell_session: ShellSession, session: ClientSession, writer: asyncio.StreamWriter):
        """Read from PTY master and send to client."""
        loop = asyncio.get_running_loop()
        master_fd = shell_session.master_fd
        
        # Make master_fd non-blocking
        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        
        try:
            while self.running and shell_session.process.returncode is None:
                try:
                    data = await loop.run_in_executor(None, os.read, master_fd, 4096)
                    if not data:
                        break
                    
                    shell_session.last_activity = time.time()
                    
                    # Send as base64 encoded data
                    encoded = base64.b64encode(data).decode('ascii')
                    shell_data = ShellData(
                        shell_id=shell_session.shell_id,
                        data=encoded,
                        direction="stdout"
                    )
                    await self._send_message(writer, shell_data)
                
                except BlockingIOError:
                    await asyncio.sleep(0.01)
                except OSError:
                    break
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Shell reader error: {e}")
        finally:
            # Process exited
            exit_code = shell_session.process.returncode
            if exit_code is None:
                try:
                    exit_code = await shell_session.process.wait()
                except:
                    exit_code = -1
            
            shell_exit = ShellExit(
                shell_id=shell_session.shell_id,
                exit_code=exit_code
            )
            try:
                await self._send_message(writer, shell_exit)
            except:
                pass
            
            self.logger.info(f"Shell {shell_session.shell_id} exited with code {exit_code}")
    
    async def _handle_shell_data(self, message: ShellData, session: ClientSession, writer: asyncio.StreamWriter):
        """Handle stdin data for PTY shell."""
        if not session or not session.authenticated:
            return
        
        shell_session = session.shells.get(message.shell_id)
        if not shell_session:
            return
        
        shell_session.last_activity = time.time()
        
        if message.direction == "stdin":
            try:
                data = base64.b64decode(message.data)
                os.write(shell_session.master_fd, data)
            except Exception as e:
                self.logger.error(f"Shell stdin write error: {e}")
    
    async def _handle_shell_resize(self, message: ShellResize, session: ClientSession, writer: asyncio.StreamWriter):
        """Handle PTY terminal resize."""
        if not session or not session.authenticated:
            return
        
        shell_session = session.shells.get(message.shell_id)
        if not shell_session:
            return
        
        shell_session.cols = message.cols
        shell_session.rows = message.rows
        shell_session.last_activity = time.time()
        
        winsize = struct.pack("HHHH", message.rows, message.cols, 0, 0)
        try:
            fcntl.ioctl(shell_session.master_fd, termios.TIOCSWINSZ, winsize)
        except Exception as e:
            self.logger.error(f"Shell resize error: {e}")
    
    async def _handle_shell_exit(self, message: ShellExit, session: ClientSession, writer: asyncio.StreamWriter):
        """Handle shell exit request."""
        if not session or not session.authenticated:
            return
        
        shell_session = session.shells.pop(message.shell_id, None)
        if not shell_session:
            return
        
        if shell_session.reader_task:
            shell_session.reader_task.cancel()
            try:
                await shell_session.reader_task
            except asyncio.CancelledError:
                pass
        
        if shell_session.process.returncode is None:
            shell_session.process.terminate()
            try:
                await asyncio.wait_for(shell_session.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                shell_session.process.kill()
                await shell_session.process.wait()
        
        try:
            os.close(shell_session.master_fd)
        except:
            pass
        
        self.logger.info(f"Shell {message.shell_id} closed")
    
    async def _heartbeat_monitor(self):
        """Monitor client heartbeats and disconnect stale ones."""
        while self.running:
            await asyncio.sleep(self.config.heartbeat_interval)
            now = time.time()
            stale = []
            
            for session_id, session in self.sessions.items():
                if now - session.last_heartbeat > self.config.heartbeat_interval * 3:
                    self.logger.warning(f"Session {session_id} heartbeat timeout")
                    stale.append(session_id)
            
            for session_id in stale:
                session = self.sessions.get(session_id)
                if session:
                    session.writer.close()
                    await session.writer.wait_closed()
                    del self.sessions[session_id]
    
    async def _send_message(self, writer: asyncio.StreamWriter, message: BaseMessage):
        """Send a message with length prefix."""
        data = message.to_json().encode('utf-8')
        length = len(data).to_bytes(4, 'big')
        writer.write(length + data)
        await writer.drain()


# ─── Entry Point ─────────────────────────────────────────────────

async def main():
    """Main entry point."""
    config = ServerConfig.from_env()
    
    if not config.token:
        print("ERROR: AGENT_TOKEN environment variable is required")
        sys.exit(1)
    
    server = RemoteAgentServer(config)
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        await server.stop()


if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(main())