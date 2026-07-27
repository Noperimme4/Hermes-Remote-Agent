#!/usr/bin/env python3
"""
Remote Agent Client - Core CLI functionality
"""

import asyncio
import os
import sys
import base64
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

# Add shared to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from protocol import (
    MessageType, CommandStatus, BaseMessage,
    AuthRequest, AuthResponse, CommandRequest, CommandResponse,
    CommandStream, Heartbeat, ErrorMessage, FileListRequest, FileInfo,
    ShellStartRequest, ShellStartResponse, ShellData, ShellResize, ShellExit,
    parse_message, create_command_request, create_auth_request
)


@dataclass
class ClientConfig:
    """Client configuration."""
    host: str = "localhost"
    port: int = 8765
    token: str = ""
    client_name: str = "remote-agent-client"
    client_version: str = "2.0.0"
    timeout: int = 60
    heartbeat_interval: int = 30
    use_tls: bool = False
    verify_tls: bool = True
    ca_cert: Optional[str] = None
    log_level: str = "WARNING"


@dataclass
class CommandResult:
    """Result of command execution."""
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    status: CommandStatus


class RemoteAgentClient:
    """Client for connecting to remote agent server."""
    
    def __init__(self, config: ClientConfig):
        self.config = config
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.session_id: Optional[str] = None
        self.server_info: Dict[str, Any] = {}
        self.running = False
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.stream_handlers: Dict[str, List[Callable]] = {}
        self.shells: Dict[str, Any] = {}
        
        # Setup logging
        import logging
        level = getattr(logging, config.log_level.upper(), logging.WARNING)
        logging.basicConfig(
            level=level,
            format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
        )
        self.logger = logging.getLogger("client")
    
    async def connect(self) -> bool:
        """Connect to server and authenticate."""
        try:
            ssl_context = None
            if self.config.use_tls:
                import ssl
                ssl_context = ssl.create_default_context()
                if self.config.ca_cert:
                    ssl_context.load_verify_locations(self.config.ca_cert)
                elif not self.config.verify_tls:
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
            
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.config.host, self.config.port, ssl=ssl_context),
                timeout=10
            )
            
            self.logger.info(f"Connected to {self.config.host}:{self.config.port}")
            
            # Authenticate
            auth = create_auth_request(
                self.config.token,
                client_name=self.config.client_name,
                client_version=self.config.client_version
            )
            await self._send_message(auth)
            
            # Wait for auth response
            response = await self._wait_for_response(auth.request_id, timeout=10)
            
            if not response or not isinstance(response, AuthResponse) or not response.success:
                error_msg = response.message if response else "No response"
                self.logger.error(f"Authentication failed: {error_msg}")
                return False
            
            self.session_id = response.session_id
            self.server_info = {
                "name": response.server_name,
                "version": response.server_version,
                "allowed_commands": response.allowed_commands
            }
            
            self.logger.info(f"Authenticated! Session: {self.session_id}")
            self.logger.info(f"Server: {response.server_name} v{response.server_version}")
            
            # Start background tasks
            self.running = True
            asyncio.create_task(self._reader_loop())
            asyncio.create_task(self._heartbeat_loop())
            
            return True
            
        except asyncio.TimeoutError:
            self.logger.error("Connection timeout")
            return False
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from server."""
        self.running = False
        if self.writer:
            try:
                await self._send_message(BaseMessage(
                    type=MessageType.DISCONNECT,
                    request_id="disconnect",
                    timestamp=datetime.utcnow().isoformat()
                ))
            except:
                pass
            self.writer.close()
            await self.writer.wait_closed()
        self.logger.info("Disconnected")
    
    async def _reader_loop(self):
        """Background task to read messages from server."""
        try:
            while self.running and self.reader:
                # Read length prefix
                length_bytes = await self.reader.readexactly(4)
                length = int.from_bytes(length_bytes, 'big')
                
                if length > 10 * 1024 * 1024:
                    self.logger.warning(f"Message too large: {length}")
                    break
                
                data = await self.reader.readexactly(length)
                message = parse_message(data.decode('utf-8'))
                
                await self._handle_message(message)
                
        except asyncio.IncompleteReadError:
            self.logger.info("Server disconnected")
        except Exception as e:
            self.logger.exception(f"Reader error: {e}")
        finally:
            self.running = False
    
    async def _handle_message(self, message: BaseMessage):
        """Route incoming message."""
        if message.type == MessageType.AUTH_RESPONSE:
            # Already handled in connect()
            pass
        
        elif message.type == MessageType.COMMAND_RESPONSE:
            future = self.pending_requests.pop(message.request_id, None)
            if future and not future.done():
                future.set_result(message)
        
        elif message.type == MessageType.COMMAND_STREAM:
            handlers = self.stream_handlers.get(message.request_id, [])
            for handler in handlers:
                try:
                    handler(message)
                except Exception as e:
                    self.logger.exception(f"Stream handler error: {e}")
        
        elif message.type == MessageType.HEARTBEAT:
            # Echo back
            ack = Heartbeat(client_id=message.client_id)
            ack.request_id = message.request_id
            await self._send_message(ack)
        
        elif message.type == MessageType.ERROR:
            future = self.pending_requests.pop(message.request_id, None)
            if future and not future.done():
                future.set_exception(Exception(f"{message.code}: {message.message}"))
        
        elif message.type == MessageType.SHELL_START:
            # Handle shell start response
            pass
        
        elif message.type == MessageType.SHELL_DATA:
            # Shell data received
            pass
        
        elif message.type == MessageType.SHELL_EXIT:
            # Shell exited
            pass
    
    async def _send_message(self, message: BaseMessage):
        """Send message with length prefix."""
        if not self.writer:
            raise RuntimeError("Not connected")
        
        data = message.to_json().encode('utf-8')
        length = len(data).to_bytes(4, 'big')
        self.writer.write(length + data)
        await self.writer.drain()
    
    async def _wait_for_response(self, request_id: str, timeout: float = None) -> Optional[BaseMessage]:
        """Wait for a response to a request."""
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        try:
            return await asyncio.wait_for(future, timeout=timeout or self.config.timeout)
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            return None
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats."""
        while self.running:
            await asyncio.sleep(self.config.heartbeat_interval)
            if not self.running:
                break
            try:
                hb = Heartbeat(client_id=self.session_id or "unknown")
                await self._send_message(hb)
            except Exception as e:
                self.logger.error(f"Heartbeat failed: {e}")
                break
    
    # ─── Public API ───────────────────────────────────────────────────
    
    async def execute(
        self, 
        command: str, 
        args: List[str] = None, 
        cwd: str = None, 
        env: Dict[str, str] = None,
        timeout: int = None,
        shell: bool = False,
        stream: bool = False,
        progress_cb: Callable = None
    ) -> CommandResult:
        """Execute a command on the remote server."""
        if not self.running:
            raise RuntimeError("Not connected")
        
        request = create_command_request(
            command=command,
            args=args or [],
            working_dir=cwd,
            env=env or {},
            timeout=timeout or self.config.timeout,
            stream_output=stream,
            shell=shell
        )
        
        # Register stream handler if needed
        if stream and progress_cb:
            self.stream_handlers[request.request_id] = [progress_cb]
        
        await self._send_message(request)
        response = await self._wait_for_response(request.request_id, timeout=(timeout or self.config.timeout) + 10)
        
        # Cleanup
        self.stream_handlers.pop(request.request_id, None)
        
        if response is None:
            raise TimeoutError(f"Command timed out after {timeout or self.config.timeout}s")
        
        if isinstance(response, ErrorMessage):
            raise Exception(f"{response.code}: {response.message}")
        
        if not isinstance(response, CommandResponse):
            raise Exception(f"Unexpected response type: {type(response)}")
        
        return CommandResult(
            exit_code=response.exit_code,
            stdout=response.stdout,
            stderr=response.stderr,
            execution_time=response.execution_time,
            status=response.status
        )
    
    async def execute_simple(
        self, 
        command_line: str, 
        cwd: str = None, 
        stream: bool = False,
        progress_cb: Callable = None
    ) -> CommandResult:
        """Execute a simple command line string."""
        parts = command_line.strip().split()
        if not parts:
            raise ValueError("Empty command")
        return await self.execute(parts[0], parts[1:], cwd=cwd, stream=stream, progress_cb=progress_cb)
    
    async def interactive_shell(self, cwd: str = None):
        """Start interactive PTY shell."""
        from client.pty_shell import PTYShell
        shell = PTYShell(self)
        await shell.run(cwd)
    
    async def list_files(self, path: str = ".", recursive: bool = False) -> List[Dict]:
        """List files on remote server."""
        if not self.running:
            raise RuntimeError("Not connected")
        
        request = FileListRequest(path=path, recursive=recursive)
        await self._send_message(request)
        
        files = []
        while True:
            response = await self._wait_for_response(request.request_id, timeout=10)
            if response is None:
                break
            if response.type == MessageType.FILE_LIST and hasattr(response, 'name'):
                files.append({
                    "name": response.name,
                    "path": response.path,
                    "size": response.size,
                    "is_dir": response.is_dir,
                    "modified": response.modified,
                    "permissions": response.permissions
                })
            elif response.type == MessageType.FILE_LIST and not hasattr(response, 'name'):
                # End marker
                break
            elif isinstance(response, ErrorMessage):
                raise Exception(f"{response.code}: {response.message}")
        
        return files
    
    async def start_pty_shell(self, cols: int = 80, rows: int = 24, cwd: str = None, env: Dict = None) -> str:
        """Start a PTY shell session."""
        request = ShellStartRequest(
            cols=cols,
            rows=rows,
            cwd=cwd,
            env=env or {}
        )
        await self._send_message(request)
        response = await self._wait_for_response(request.request_id, timeout=10)
        
        if isinstance(response, ShellStartResponse) and response.success:
            return response.shell_id
        raise Exception(f"Failed to start shell: {response.message if response else 'No response'}")
    
    async def send_pty_input(self, shell_id: str, data: bytes):
        """Send input to PTY shell."""
        encoded = base64.b64encode(data).decode('ascii')
        msg = ShellData(shell_id=shell_id, data=encoded, direction="stdin")
        await self._send_message(msg)
    
    async def resize_pty(self, shell_id: str, cols: int, rows: int):
        """Resize PTY shell."""
        msg = ShellResize(shell_id=shell_id, cols=cols, rows=rows)
        await self._send_message(msg)
    
    async def close_pty(self, shell_id: str):
        """Close PTY shell."""
        msg = ShellExit(shell_id=shell_id)
        await self._send_message(msg)