#!/usr/bin/env python3
"""
Remote Agent Client - Runs on local machine.
Connects to server and sends commands.
"""

import asyncio
import json
import os
import sys
import uuid
import readline
import signal
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

# Add shared to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from protocol import (
    MessageType, CommandStatus, BaseMessage,
    AuthRequest, AuthResponse, CommandRequest, CommandResponse,
    CommandStream, Heartbeat, ErrorMessage, FileListRequest,
    parse_message
)

# ─── Configuration ────────────────────────────────────────────────

@dataclass
class ClientConfig:
    host: str = "localhost"
    port: int = 8765
    token: str = ""
    client_name: str = "remote-agent-client"
    client_version: str = "1.0.0"
    timeout: int = 60
    heartbeat_interval: int = 30
    use_tls: bool = False
    verify_tls: bool = True
    ca_cert: Optional[str] = None
    log_level: str = "WARNING"
    
    @classmethod
    def from_env(cls) -> 'ClientConfig':
        return cls(
            host=os.getenv("AGENT_HOST", "localhost"),
            port=int(os.getenv("AGENT_PORT", "8765")),
            token=os.getenv("AGENT_TOKEN", ""),
            client_name=os.getenv("AGENT_CLIENT_NAME", "remote-agent-client"),
            timeout=int(os.getenv("AGENT_TIMEOUT", "60")),
            heartbeat_interval=int(os.getenv("AGENT_HEARTBEAT", "30")),
            use_tls=os.getenv("AGENT_USE_TLS", "false").lower() == "true",
            verify_tls=os.getenv("AGENT_VERIFY_TLS", "true").lower() == "true",
            ca_cert=os.getenv("AGENT_CA_CERT"),
            log_level=os.getenv("AGENT_LOG_LEVEL", "WARNING"),
        )


# ─── Client ───────────────────────────────────────────────────────

class RemoteAgentClient:
    """Client for connecting to remote agent server."""
    
    def __init__(self, config: ClientConfig):
        self.config = config
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.session_id: Optional[str] = None
        self.server_info: Dict = {}
        self.running = False
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.stream_handlers: Dict[str, List[Callable]] = {}
        self._setup_logging()
    
    def _setup_logging(self):
        import logging
        level = getattr(logging, self.config.log_level.upper(), logging.WARNING)
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
            auth = AuthRequest(
                token=self.config.token,
                client_name=self.config.client_name,
                client_version=self.config.client_version
            )
            await self._send_message(auth)
            
            # Wait for auth response
            response = await asyncio.wait_for(
                self._wait_for_response(auth.request_id),
                timeout=10
            )
            
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
                    request_id=str(uuid.uuid4()),
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
        else:
            self.logger.debug(f"Unhandled message: {message.type}")
    
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
        except Exception:
            self.pending_requests.pop(request_id, None)
            raise
    
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
    
    # ─── Public API ───────────────────────────────────────────────
    
    async def execute(self, command: str, args: List[str] = None, 
                      cwd: str = None, env: Dict[str, str] = None,
                      timeout: int = None, shell: bool = False,
                      stream: bool = False, progress_cb: Callable = None) -> CommandResponse:
        """Execute a command on the remote server."""
        if not self.running:
            raise RuntimeError("Not connected")
        
        request = CommandRequest(
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
        response = await self._wait_for_response(request.request_id, timeout=timeout or self.config.timeout + 10)
        
        # Cleanup
        self.stream_handlers.pop(request.request_id, None)
        
        if response is None:
            raise TimeoutError(f"Command timed out after {timeout or self.config.timeout}s")
        
        if isinstance(response, ErrorMessage):
            raise Exception(f"{response.code}: {response.message}")
        
        return response
    
    async def execute_simple(self, command_line: str, **kwargs) -> CommandResponse:
        """Execute a simple command line string."""
        parts = command_line.strip().split()
        if not parts:
            raise ValueError("Empty command")
        return await self.execute(parts[0], parts[1:], **kwargs)
    
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


# ─── Interactive Shell ────────────────────────────────────────────

class InteractiveShell:
    """Interactive shell for the client."""
    
    def __init__(self, client: RemoteAgentClient):
        self.client = client
        self.history_file = Path.home() / ".remote_agent_history"
        self._load_history()
    
    def _load_history(self):
        try:
            readline.read_history_file(str(self.history_file))
        except:
            pass
    
    def _save_history(self):
        try:
            readline.write_history_file(str(self.history_file))
        except:
            pass
    
    def _completer(self, text, state):
        commands = [
            "help", "exit", "quit", "cd", "pwd", "ls", "cat", "head", "tail",
            "grep", "find", "ps", "top", "df", "du", "free", "uptime",
            "whoami", "date", "echo", "python3", "python", "git", "docker",
            "systemctl", "journalctl", "ssh", "scp", "rsync", "tar", "zip",
            "apt", "pip", "npm", "make", "cargo", "go", "vim", "nano"
        ]
        matches = [c for c in commands if c.startswith(text)]
        if state < len(matches):
            return matches[state]
        return None
    
    async def run(self):
        """Run interactive shell."""
        readline.set_completer(self._completer)
        readline.parse_and_bind("tab: complete")
        
        print(f"\n🔗 Connected to {self.client.server_info.get('name', 'remote-agent')}")
        print(f"📍 Session: {self.client.session_id[:8]}...")
        print("Type 'help' for commands, 'exit' to quit\n")
        
        cwd = "/data/workspace"
        
        while self.client.running:
            try:
                prompt = f"🌐 {cwd} $ "
                line = await asyncio.get_event_loop().run_in_executor(None, input, prompt)
                line = line.strip()
                
                if not line:
                    continue
                
                if line in ("exit", "quit"):
                    break
                elif line == "help":
                    self._print_help()
                    continue
                elif line.startswith("cd "):
                    cwd = line[3:].strip() or "/data/workspace"
                    continue
                elif line == "pwd":
                    print(cwd)
                    continue
                
                # Execute command
                print(f"  ▶ {line}")
                
                def stream_handler(chunk: CommandStream):
                    if chunk.chunk_type in ("stdout", "stderr"):
                        sys.stdout.write(chunk.data)
                        sys.stdout.flush()
                
                try:
                    response = await self.client.execute_simple(
                        line, cwd=cwd, stream=True, progress_cb=stream_handler
                    )
                    if response.stdout and not response.stdout.endswith('\n'):
                        print()
                    if response.stderr and response.exit_code != 0:
                        print(f"  ❌ Exit code: {response.exit_code}", file=sys.stderr)
                    elif response.exit_code == 0:
                        print(f"  ✓ Done ({response.execution_time:.2f}s)")
                except Exception as e:
                    print(f"  ❌ Error: {e}")
                
            except KeyboardInterrupt:
                print("\n  ^C")
                continue
            except EOFError:
                break
        
        self._save_history()
        print("\n👋 Goodbye!")
    
    def _print_help(self):
        print("""
Available commands:
  help          - Show this help
  exit, quit    - Exit shell
  cd <dir>      - Change working directory (local tracking)
  pwd           - Show current directory
  <any command> - Execute on remote server

Examples:
  ls -la
  cat /etc/os-release
  git status
  docker ps
  python3 script.py
  systemctl status nginx
""")


# ─── CLI Entry Point ─────────────────────────────────────────────

def print_banner():
    print("""
╔══════════════════════════════════════════════════════════╗
║              🌐 Remote Agent Client v1.0                 ║
║         Secure remote command execution tool             ║
╚══════════════════════════════════════════════════════════╝
""")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Remote Agent Client")
    parser.add_argument("--host", default=os.getenv("AGENT_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("AGENT_PORT", "8765")))
    parser.add_argument("--token", default=os.getenv("AGENT_TOKEN", ""))
    parser.add_argument("--tls", action="store_true", help="Use TLS")
    parser.add_argument("--ca-cert", help="CA certificate for TLS verification")
    parser.add_argument("-c", "--command", help="Execute single command and exit")
    parser.add_argument("--cwd", default="/data/workspace", help="Working directory")
    parser.add_argument("--timeout", type=int, default=60, help="Command timeout")
    parser.add_argument("--shell", action="store_true", help="Execute via shell")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive shell")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        os.environ["AGENT_LOG_LEVEL"] = "DEBUG"
    
    config = ClientConfig(
        host=args.host,
        port=args.port,
        token=args.token,
        timeout=args.timeout,
        use_tls=args.tls,
        ca_cert=args.ca_cert
    )
    
    if not config.token:
        print("❌ Error: Token required. Set AGENT_TOKEN env var or use --token")
        sys.exit(1)
    
    client = RemoteAgentClient(config)
    
    print_banner()
    
    try:
        connected = await client.connect()
        if not connected:
            sys.exit(1)
        
        if args.command:
            # Single command mode
            print(f"▶ {args.command}")
            def stream_handler(chunk: CommandStream):
                if chunk.chunk_type in ("stdout", "stderr"):
                    sys.stdout.write(chunk.data)
                    sys.stdout.flush()
            
            try:
                response = await client.execute_simple(
                    args.command, cwd=args.cwd, stream=True, progress_cb=stream_handler
                )
                if response.stdout and not response.stdout.endswith('\n'):
                    print()
                sys.exit(response.exit_code or 0)
            except Exception as e:
                print(f"❌ Error: {e}", file=sys.stderr)
                sys.exit(1)
        
        elif args.interactive or (not args.command and sys.stdin.isatty()):
            # Interactive mode
            shell = InteractiveShell(client)
            await shell.run()
        
        else:
            # No command, no TTY - show help
            parser.print_help()
    
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())