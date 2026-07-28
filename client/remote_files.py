"""
Remote File Provider - Client side handler for remote file access.
Receives requests from server, performs local file operations, sends responses.
"""

import asyncio
import base64
import os
import logging
import uuid
from dataclasses import dataclass
from typing import Dict, Optional, Callable, Awaitable, Any

from shared.protocol import (
    BaseMessage,
    MessageType,
    RemoteFileOpenRequest,
    RemoteFileOpenResponse,
    RemoteFileReadRequest,
    RemoteFileWriteRequest,
    RemoteFileSeekRequest,
    RemoteFileCloseRequest,
    RemoteFileStatRequest,
    RemoteFileStatResponse,
    RemoteFileListRequest,
    RemoteFileListResponse,
    RemoteFileChunk,
    RemoteFileError,
    FileInfo,
    parse_message,
)

logger = logging.getLogger(__name__)


@dataclass
class LocalFileHandle:
    """Represents an open local file on the client."""
    handle_id: str
    path: str
    mode: str
    file_obj: Any = None
    size: int = 0


class RemoteFileProvider:
    """
    Client-side handler for remote file operations.
    
    When server needs to access a file on the client's machine:
    1. Server sends REMOTE_FILE_OPEN with path
    2. Provider opens local file, returns handle + metadata
    3. Server sends READ/SEEK/CLOSE with handle
    4. Provider performs operation, sends chunk/response
    """
    
    def __init__(
        self,
        send_callback: Callable[[str], Awaitable[None]],
        allowed_roots: list[str] = None,
        max_chunk_size: int = 1024 * 1024,  # 1MB chunks
    ):
        """
        Args:
            send_callback: Async function to send message to server
            allowed_roots: List of allowed root directories (security)
            max_chunk_size: Maximum bytes per read chunk
        """
        self.send_callback = send_callback
        self.allowed_roots = [os.path.abspath(r) for r in (allowed_roots or [os.getcwd()])]
        self.max_chunk_size = max_chunk_size
        self.handles: Dict[str, LocalFileHandle] = {}
        self._lock = asyncio.Lock()
    
    def _is_allowed(self, path: str) -> bool:
        """Check if path is within allowed roots."""
        abs_path = os.path.abspath(path)
        return any(abs_path.startswith(root) for root in self.allowed_roots)
    
    def _resolve_path(self, path: str) -> str:
        """Resolve and validate path."""
        abs_path = os.path.abspath(os.path.expanduser(path))
        if not self._is_allowed(abs_path):
            raise PermissionError(f"Path not allowed: {path}")
        return abs_path
    
    async def handle_message(self, message: BaseMessage) -> None:
        """Handle incoming remote file message from server.
        
        All responses are sent via send_callback.
        """
        if isinstance(message, RemoteFileOpenRequest):
            await self._handle_open(message)
        elif isinstance(message, RemoteFileReadRequest):
            await self._handle_read(message)
        elif isinstance(message, RemoteFileWriteRequest):
            await self._handle_write(message)
        elif isinstance(message, RemoteFileSeekRequest):
            await self._handle_seek(message)
        elif isinstance(message, RemoteFileCloseRequest):
            await self._handle_close(message)
        elif isinstance(message, RemoteFileStatRequest):
            await self._handle_stat(message)
        elif isinstance(message, RemoteFileListRequest):
            await self._handle_list(message)
    
    async def _handle_open(self, req: RemoteFileOpenRequest) -> None:
        try:
            local_path = self._resolve_path(req.path)
            
            if not os.path.exists(local_path):
                resp = RemoteFileOpenResponse(
                    request_id=req.request_id,
                    success=False,
                    error=f"File not found: {req.path}"
                )
                await self.send_callback(resp.to_json())
                return
            
            is_dir = os.path.isdir(local_path)
            
            if is_dir:
                # For directories, just return stat info
                stat = os.stat(local_path)
                resp = RemoteFileOpenResponse(
                    request_id=req.request_id,
                    success=True,
                    handle="",
                    size=stat.st_size,
                    is_dir=True
                )
                await self.send_callback(resp.to_json())
                return
            
            # Open file
            mode_map = {"rb": "rb", "r": "r", "wb": "wb", "w": "w"}
            file_mode = mode_map.get(req.mode, "rb")
            file_obj = open(local_path, file_mode)
            
            stat = os.stat(local_path)
            handle_id = str(uuid.uuid4())
            
            self.handles[handle_id] = LocalFileHandle(
                handle_id=handle_id,
                path=local_path,
                mode=req.mode,
                file_obj=file_obj,
                size=stat.st_size
            )
            
            resp = RemoteFileOpenResponse(
                request_id=req.request_id,
                success=True,
                handle=handle_id,
                size=stat.st_size,
                is_dir=False
            )
            await self.send_callback(resp.to_json())
        
        except PermissionError as e:
            resp = RemoteFileOpenResponse(
                request_id=req.request_id,
                success=False,
                error=str(e)
            )
            await self.send_callback(resp.to_json())
        except Exception as e:
            logger.exception(f"Open error: {e}")
            resp = RemoteFileOpenResponse(
                request_id=req.request_id,
                success=False,
                error=str(e)
            )
            await self.send_callback(resp.to_json())
        except Exception as e:
            logger.exception(f"Error opening remote file: {e}")
            return RemoteFileOpenResponse(
                request_id=req.request_id,
                success=False,
                error=f"Server error: {str(e)}"
            )
    
    async def _handle_read(self, req: RemoteFileReadRequest):
        handle = self.handles.get(req.handle)
        if not handle or not handle.file_obj:
            await self.send_callback(
                RemoteFileError(
                    handle=req.handle,
                    request_id=req.request_id,
                    code="HANDLE_NOT_FOUND",
                    message="Invalid file handle"
                ).to_json()
            )
            return
        
        try:
            length = min(req.length, self.max_chunk_size)
            handle.file_obj.seek(req.offset)
            data = handle.file_obj.read(length)
            
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            b64_data = base64.b64encode(data).decode('ascii')
            eof = len(data) < length
            
            chunk = RemoteFileChunk(
                handle=req.handle,
                offset=req.offset,
                data=b64_data,
                eof=eof,
                request_id=req.request_id
            )
            await self.send_callback(chunk.to_json())
        
        except Exception as e:
            logger.exception(f"Error reading remote file: {e}")
            await self.send_callback(
                RemoteFileError(
                    handle=req.handle,
                    request_id=req.request_id,
                    code="READ_ERROR",
                    message=str(e)
                ).to_json()
            )
    
    async def _handle_write(self, req: RemoteFileWriteRequest):
        handle = self.handles.get(req.handle)
        if not handle or not handle.file_obj:
            await self.send_callback(
                RemoteFileError(
                    handle=req.handle,
                    request_id=req.request_id,
                    code="HANDLE_NOT_FOUND",
                    message="Invalid file handle"
                ).to_json()
            )
            return
        
        try:
            data = base64.b64decode(req.data)
            handle.file_obj.seek(req.offset)
            handle.file_obj.write(data)
            handle.file_obj.flush()
            
            # Send success response (empty chunk)
            chunk = RemoteFileChunk(
                handle=req.handle,
                offset=req.offset,
                data="",
                eof=True,
                request_id=req.request_id
            )
            await self.send_callback(chunk.to_json())
        
        except Exception as e:
            logger.exception(f"Error writing remote file: {e}")
            await self.send_callback(
                RemoteFileError(
                    handle=req.handle,
                    request_id=req.request_id,
                    code="WRITE_ERROR",
                    message=str(e)
                ).to_json()
            )
    
    async def _handle_seek(self, req: RemoteFileSeekRequest):
        handle = self.handles.get(req.handle)
        if not handle or not handle.file_obj:
            await self.send_callback(
                RemoteFileError(
                    handle=req.handle,
                    request_id=req.request_id,
                    code="HANDLE_NOT_FOUND",
                    message="Invalid file handle"
                ).to_json()
            )
            return
        
        try:
            if req.whence == 0:
                handle.file_obj.seek(req.offset)
            elif req.whence == 1:
                handle.file_obj.seek(req.offset, 1)
            elif req.whence == 2:
                handle.file_obj.seek(req.offset, 2)
            
            # Send empty chunk as acknowledgment
            chunk = RemoteFileChunk(
                handle=req.handle,
                offset=handle.file_obj.tell(),
                data="",
                eof=False,
                request_id=req.request_id
            )
            await self.send_callback(chunk.to_json())
        
        except Exception as e:
            logger.exception(f"Error seeking remote file: {e}")
            await self.send_callback(
                RemoteFileError(
                    handle=req.handle,
                    request_id=req.request_id,
                    code="SEEK_ERROR",
                    message=str(e)
                ).to_json()
            )
    
    async def _handle_close(self, req: RemoteFileCloseRequest):
        handle = self.handles.pop(req.handle, None)
        if not handle:
            await self.send_callback(
                RemoteFileError(
                    handle=req.handle,
                    request_id=req.request_id,
                    code="HANDLE_NOT_FOUND",
                    message="Invalid file handle"
                ).to_json()
            )
            return
        
        try:
            if handle.file_obj:
                handle.file_obj.close()
            # Send empty chunk as acknowledgment
            chunk = RemoteFileChunk(
                handle=req.handle,
                offset=0,
                data="",
                eof=True,
                request_id=req.request_id
            )
            await self.send_callback(chunk.to_json())
        except Exception as e:
            logger.exception(f"Error closing remote file: {e}")
            await self.send_callback(
                RemoteFileError(
                    handle=req.handle,
                    request_id=req.request_id,
                    code="CLOSE_ERROR",
                    message=str(e)
                ).to_json()
            )
    
    async def _handle_stat(self, req: RemoteFileStatRequest):
        try:
            local_path = self._resolve_path(req.path)
            
            if not os.path.exists(local_path):
                await self.send_callback(RemoteFileStatResponse(
                    request_id=req.request_id,
                    success=False,
                    error=f"File not found: {req.path}"
                ).to_json())
                return
            
            stat = os.stat(local_path)
            is_dir = os.path.isdir(local_path)
            
            await self.send_callback(RemoteFileStatResponse(
                request_id=req.request_id,
                success=True,
                size=stat.st_size,
                is_dir=is_dir,
                modified=str(stat.st_mtime),
                permissions=oct(stat.st_mode)[-3:]
            ).to_json())
        
        except PermissionError as e:
            await self.send_callback(RemoteFileStatResponse(
                request_id=req.request_id,
                success=False,
                error=str(e)
            ).to_json())
        except Exception as e:
            logger.exception(f"Error stating remote file: {e}")
            await self.send_callback(RemoteFileStatResponse(
                request_id=req.request_id,
                success=False,
                error=str(e)
            ).to_json())
    
    async def _handle_list(self, req: RemoteFileListRequest):
        try:
            local_path = self._resolve_path(req.path)
            
            if not os.path.isdir(local_path):
                await self.send_callback(RemoteFileListResponse(
                    request_id=req.request_id,
                    success=False,
                    error=f"Not a directory: {req.path}",
                    entries=[]
                ).to_json())
                return
            
            entries = []
            for name in sorted(os.listdir(local_path)):
                full_path = os.path.join(local_path, name)
                try:
                    stat = os.stat(full_path)
                    is_dir = os.path.isdir(full_path)
                    entries.append(FileInfo(
                        request_id=req.request_id,
                        name=name,
                        path=os.path.join(req.path, name),
                        size=stat.st_size,
                        is_dir=is_dir,
                        modified=str(stat.st_mtime),
                        permissions=oct(stat.st_mode)[-3:]
                    ))
                except Exception:
                    continue
            
            # Send entries in batches
            batch_size = 50
            for i in range(0, len(entries), batch_size):
                batch = entries[i:i+batch_size]
                await self.send_callback(RemoteFileListResponse(
                    request_id=req.request_id,
                    success=True,
                    entries=batch
                ).to_json())
            
            # Send end marker
            await self.send_callback(RemoteFileListResponse(
                request_id=req.request_id,
                success=True,
                entries=[]
            ).to_json())
        
        except PermissionError as e:
            await self.send_callback(RemoteFileListResponse(
                request_id=req.request_id,
                success=False,
                error=str(e),
                entries=[]
            ).to_json())
        except Exception as e:
            logger.exception(f"Error listing remote directory: {e}")
            await self.send_callback(RemoteFileListResponse(
                request_id=req.request_id,
                success=False,
                error=str(e),
                entries=[]
            ).to_json())


class RemoteFileBrowser:
    """Interactive TUI for browsing remote files (client's local files from server)."""
    
    def __init__(self, client):
        self.client = client
        self.current_path = "/"
        self.selected_index = 0
        self.entries = []
        self.running = True
    
    async def run(self):
        """Run the remote file browser."""
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.prompt import Prompt
        from rich.text import Text
        import asyncio
        
        console = Console()
        
        await self._refresh()
        
        while self.running:
            console.clear()
            self._render(console)
            
            # Get user input
            try:
                choice = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: Prompt.ask(
                        "\n[bold cyan]Action[/bold cyan]",
                        choices=["l", "u", "d", "v", "c", "q", "h"],
                        default="l"
                    )
                )
            except (KeyboardInterrupt, EOFError):
                break
            
            if choice == "q":
                break
            elif choice == "h":
                self._show_help(console)
            elif choice == "l":
                await self._refresh()
            elif choice == "u":
                await self._go_up()
            elif choice == "d":
                await self._download_selected()
            elif choice == "v":
                await self._view_selected()
            elif choice == "c":
                await self._change_dir()
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(self.entries):
                    await self._handle_entry(idx)
        
        console.print("[green]Remote file browser closed.[/green]")
    
    def _render(self, console):
        """Render the file browser UI."""
        # Header
        header = Panel(
            f"[bold]Remote File Browser[/bold] — Accessing YOUR local files from server\n"
            f"Current path: [cyan]{self.current_path}[/cyan]",
            title="📁 Remote Files (Virtual FS)",
            border_style="blue"
        )
        console.print(header)
        
        # Table
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("#", width=4)
        table.add_column("Type", width=6)
        table.add_column("Name", width=50)
        table.add_column("Size", width=12, justify="right")
        table.add_column("Modified", width=20)
        
        for i, entry in enumerate(self.entries):
            style = "bold yellow" if i == self.selected_index else ""
            type_icon = "📁" if entry.is_dir else "📄"
            size_str = self._format_size(entry.size) if not entry.is_dir else "—"
            modified = entry.modified[:19] if entry.modified else "—"
            
            table.add_row(
                str(i + 1),
                type_icon,
                Text(entry.name, style=style),
                Text(size_str, style=style),
                Text(modified, style=style)
            )
        
        console.print(table)
        
        # Legend
        legend = Text()
        legend.append("Keys: ", style="bold")
        legend.append("[1-9] select  ", style="cyan")
        legend.append("[l] refresh  ", style="cyan")
        legend.append("[u] up  ", style="cyan")
        legend.append("[d] download  ", style="cyan")
        legend.append("[v] view  ", style="cyan")
        legend.append("[c] cd  ", style="cyan")
        legend.append("[h] help  ", style="cyan")
        legend.append("[q] quit", style="cyan")
        console.print(Panel(legend, border_style="dim"))
    
    def _format_size(self, size: int) -> str:
        """Format file size human-readable."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"
    
    async def _refresh(self):
        """Refresh directory listing."""
        try:
            resp = await self.client.remote_list(self.current_path)
            if resp.success:
                self.entries = resp.entries
                self.selected_index = 0
            else:
                self.entries = []
        except Exception as e:
            self.entries = []
    
    async def _go_up(self):
        """Go to parent directory."""
        if self.current_path == "/":
            return
        parent = os.path.dirname(self.current_path.rstrip('/'))
        if not parent:
            parent = "/"
        self.current_path = parent
        await self._refresh()
    
    async def _change_dir(self):
        """Change to selected directory."""
        if self.selected_index < len(self.entries):
            entry = self.entries[self.selected_index]
            if entry.is_dir:
                self.current_path = entry.path
                await self._refresh()
    
    async def _handle_entry(self, idx: int):
        """Handle entry selection (enter directory or view file)."""
        entry = self.entries[idx]
        if entry.is_dir:
            self.current_path = entry.path
            await self._refresh()
        else:
            await self._view_file(entry.path)
    
    async def _view_selected(self):
        """View selected file."""
        if self.selected_index < len(self.entries):
            entry = self.entries[self.selected_index]
            if not entry.is_dir:
                await self._view_file(entry.path)
    
    async def _view_file(self, path: str):
        """View file content (streamed)."""
        from rich.console import Console
        from rich.syntax import Syntax
        import asyncio
        
        console = Console()
        
        try:
            # Open file
            resp = await self.client.remote_open(path, "rb")
            if not resp.success:
                console.print(f"[red]Error: {resp.error}[/red]")
                return
            
            handle = resp.handle
            
            # Stream content
            console.print(f"\n[bold]Viewing: {path}[/bold]")
            console.print("—" * 60)
            
            buffer = []
            while True:
                chunk = await self.client.remote_read(handle, 0, 8192)
                data = base64.b64decode(chunk.data)
                if not data:
                    break
                buffer.append(data.decode('utf-8', errors='replace'))
                if chunk.eof:
                    break
            
            await self.client.remote_close(handle)
            
            content = "".join(buffer)
            console.print(Syntax(content, "text", theme="monokai", line_numbers=True))
            
        except Exception as e:
            console.print(f"[red]Error viewing file: {e}[/red]")
        
        Prompt.ask("\n[dim]Press Enter to continue[/dim]")
    
    async def _download_selected(self):
        """Download selected file to server's current directory."""
        from rich.console import Console
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn
        import asyncio
        
        console = Console()
        
        if self.selected_index >= len(self.entries):
            return
        
        entry = self.entries[self.selected_index]
        if entry.is_dir:
            console.print("[yellow]Cannot download directory[/yellow]")
            await asyncio.sleep(1)
            return
        
        try:
            resp = await self.client.remote_open(entry.path, "rb")
            if not resp.success:
                console.print(f"[red]Error: {resp.error}[/red]")
                return
            
            handle = resp.handle
            file_size = resp.size
            
            # Save to server's workspace
            save_path = os.path.join(self.client.config.working_dir, entry.name)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                console=console
            ) as progress:
                task = progress.add_task(f"Downloading {entry.name}", total=file_size)
                
                offset = 0
                with open(save_path, "wb") as f:
                    while offset < file_size:
                        chunk = await self.client.remote_read(handle, offset, 65536)
                        data = base64.b64decode(chunk.data)
                        if not data:
                            break
                        f.write(data)
                        offset += len(data)
                        progress.update(task, advance=len(data))
                        
                        if chunk.eof:
                            break
            
            await self.client.remote_close(handle)
            console.print(f"\n[green]✓ Downloaded to {save_path}[/green]")
            
        except Exception as e:
            console.print(f"[red]Download failed: {e}[/red]")
        
        await asyncio.sleep(1.5)
    
    def _show_help(self, console):
        """Show help panel."""
        help_text = """
[bold]Remote File Browser Help[/bold]

This browser lets you access YOUR LOCAL FILES from the server side.
Files are streamed on-demand — no upload needed!

[bold cyan]Navigation:[/bold cyan]
  [1-9]     Select file/directory
  [l]       Refresh listing
  [u]       Go to parent directory
  [c]       Change into selected directory

[bold cyan]Actions:[/bold cyan]
  [v]       View file content (streamed)
  [d]       Download file to server workspace

[bold cyan]Other:[/bold cyan]
  [h]       Show this help
  [q]       Quit

[bold yellow]Note:[/bold yellow] Files are streamed in chunks (64KB). 
Large files (even 1GB+) work fine — only requested parts are transferred.
        """
        console.print(Panel(help_text, title="Help", border_style="green"))
        Prompt.ask("\n[dim]Press Enter to continue[/dim]")