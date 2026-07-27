"""
File Browser Client - Browse and manage remote files
"""

import asyncio
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box


@dataclass
class FileItem:
    name: str
    path: str
    size: int
    is_dir: bool
    modified: str
    permissions: str


class FileBrowser:
    """Interactive file browser for remote files."""
    
    def __init__(self, client, start_path: str = "/"):
        self.client = client
        self.current_path = start_path
        self.console = Console()
        self.running = True
        self.selected_index = 0
        self.files: List[FileItem] = []
    
    async def run(self) -> Optional[str]:
        """Run file browser, return new directory if changed."""
        while self.running:
            await self._refresh()
            self._display()
            action = await self._get_action()
            
            if action == "exit":
                break
            elif action == "enter":
                await self._enter_selected()
            elif action == "up":
                await self._go_up()
            elif action == "download":
                await self._download_selected()
            elif action == "upload":
                await self._upload()
            elif action == "delete":
                await self._delete_selected()
            elif action == "mkdir":
                await self._mkdir()
            elif action == "view":
                await self._view_selected()
            elif action == "refresh":
                continue
        
        return self.current_path if self.current_path != self.client.config.cwd else None
    
    async def _refresh(self):
        """Refresh file list."""
        try:
            files_data = await self.client.list_files(self.current_path)
            self.files = []
            for f in files_data:
                self.files.append(FileItem(
                    name=f["name"],
                    path=f["path"],
                    size=f["size"],
                    is_dir=f["is_dir"],
                    modified=f["modified"],
                    permissions=f["permissions"]
                ))
            # Sort: directories first, then by name
            self.files.sort(key=lambda x: (not x.is_dir, x.name.lower()))
            self.selected_index = min(self.selected_index, len(self.files) - 1) if self.files else 0
        except Exception as e:
            self.console.print(f"[red]Error listing files: {e}[/red]")
            self.files = []
    
    def _display(self):
        """Display file browser."""
        self.console.clear()
        
        # Header
        header = Table.grid(padding=1)
        header.add_column(style="cyan", justify="right")
        header.add_column(style="white")
        header.add_row("📂 Path:", self.current_path)
        header.add_row("📊 Items:", str(len(self.files)))
        
        self.console.print(Panel(header, title="📁 File Browser", border_style="blue", box=box.ROUNDED))
        
        # File table
        if not self.files:
            self.console.print("[dim]No files or empty directory[/dim]")
        else:
            table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
            table.add_column("#", style="dim", width=4)
            table.add_column("Name", style="white", width=40)
            table.add_column("Size", style="green", width=12, justify="right")
            table.add_column("Modified", style="dim", width=20)
            table.add_column("Perm", style="dim", width=10)
            
            for i, f in enumerate(self.files):
                prefix = "► " if i == self.selected_index else "  "
                name = f"📁 {f.name}" if f.is_dir else f"📄 {f.name}"
                size = self._format_size(f.size) if not f.is_dir else "—"
                
                style = "bold cyan" if i == self.selected_index else ""
                
                table.add_row(
                    f"{prefix}{i+1}",
                    name,
                    size,
                    f.modified[:16] if f.modified else "—",
                    f.permissions,
                    style=style
                )
            
            self.console.print(table)
        
        # Help
        help_text = (
            "[dim]Keys: [bold]↑/↓[/bold] navigate | [bold]Enter[/bold] open | "
            "[bold]Backspace[/bold] up | [bold]v[/bold] view | [bold]d[/bold] download | "
            "[bold]u[/bold] upload | [bold]Del[/bold] delete | [bold]n[/bold] new folder | "
            "[bold]r[/bold] refresh | [bold]q[/bold] quit[/dim]"
        )
        self.console.print(help_text)
    
    async def _get_action(self) -> str:
        """Get user action."""
        key = Prompt.ask("\nAction", 
            choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "q", "v", "d", "u", "n", "r", "enter", "up"],
            default="enter")
        
        # Handle numeric selection
        if key.isdigit():
            idx = int(key) - 1
            if 0 <= idx < len(self.files):
                self.selected_index = idx
                return "enter"
        
        key_map = {
            "q": "exit",
            "v": "view",
            "d": "download",
            "u": "upload",
            "n": "mkdir",
            "r": "refresh",
            "enter": "enter",
            "up": "up",
            "\x7f": "up",  # Backspace
            "\x08": "up",  # Backspace
        }
        
        return key_map.get(key, "refresh")
    
    async def _enter_selected(self):
        """Enter selected file/directory."""
        if not self.files or self.selected_index >= len(self.files):
            return
        
        item = self.files[self.selected_index]
        
        if item.is_dir:
            new_path = f"{self.current_path.rstrip('/')}/{item.name}"
            self.current_path = new_path
            self.selected_index = 0
        else:
            await self._view_file(item)
    
    async def _go_up(self):
        """Go to parent directory."""
        if self.current_path != "/":
            parent = str(Path(self.current_path).parent)
            self.current_path = parent if parent != "." else "/"
            self.selected_index = 0
    
    async def _view_selected(self):
        """View selected file."""
        if not self.files or self.selected_index >= len(self.files):
            return
        
        item = self.files[self.selected_index]
        if not item.is_dir:
            await self._view_file(item)
    
    async def _view_file(self, item: FileItem):
        """View file content."""
        try:
            result = await self.client.execute_simple(f"cat '{self.current_path}/{item.name}' | head -100")
            self.console.clear()
            self.console.print(Panel(
                result.stdout,
                title=f"📄 {item.name}",
                border_style="cyan",
                box=box.ROUNDED
            ))
            Prompt.ask("\n[dim]Press Enter to continue[/dim]")
        except Exception as e:
            self.console.print(f"[red]Error viewing file: {e}[/red]")
            await asyncio.sleep(1)
    
    async def _download_selected(self):
        """Download selected file."""
        if not self.files or self.selected_index >= len(self.files):
            return
        
        item = self.files[self.selected_index]
        if item.is_dir:
            self.console.print("[yellow]Cannot download directory (use tar/scp)[/yellow]")
            await asyncio.sleep(1)
            return
        
        local_path = Prompt.ask("Local save path", default=f"./{item.name}")
        
        try:
            self.console.print(f"[cyan]Downloading {item.name}...[/cyan]")
            
            # Read file as base64
            result = await self.client.execute_simple(
                f"base64 -w 0 '{self.current_path}/{item.name}'"
            )
            
            import base64
            data = base64.b64decode(result.stdout)
            
            with open(local_path, "wb") as f:
                f.write(data)
            
            self.console.print(f"[green]✓ Saved to {local_path} ({len(data)} bytes)[/green]")
        except Exception as e:
            self.console.print(f"[red]Download failed: {e}[/red]")
        
        await asyncio.sleep(1)
    
    async def _upload(self):
        """Upload local file."""
        local_path = Prompt.ask("Local file path")
        
        try:
            path = Path(local_path).expanduser()
            if not path.exists():
                self.console.print("[red]File not found[/red]")
                await asyncio.sleep(1)
                return
            
            # Read and encode
            import base64
            data = path.read_bytes()
            encoded = base64.b64encode(data).decode()
            
            remote_name = path.name
            remote_path = f"{self.current_path}/{remote_name}"
            
            self.console.print(f"[cyan]Uploading {remote_name} ({len(data)} bytes)...[/cyan]")
            
            # Write via base64 decode
            cmd = f"base64 -d <<< '{encoded}' > '{remote_path}'"
            result = await self.client.execute_simple(cmd)
            
            if result.exit_code == 0:
                self.console.print(f"[green]✓ Uploaded to {remote_path}[/green]")
            else:
                self.console.print(f"[red]Upload failed: {result.stderr}[/red]")
        except Exception as e:
            self.console.print(f"[red]Upload failed: {e}[/red]")
        
        await asyncio.sleep(1)
    
    async def _delete_selected(self):
        """Delete selected file."""
        if not self.files or self.selected_index >= len(self.files):
            return
        
        item = self.files[self.selected_index]
        
        if not Confirm.ask(f"Delete {item.name}?"):
            return
        
        try:
            cmd = f"rm -rf '{self.current_path}/{item.name}'"
            result = await self.client.execute_simple(cmd)
            
            if result.exit_code == 0:
                self.console.print(f"[green]✓ Deleted {item.name}[/green]")
            else:
                self.console.print(f"[red]Failed: {result.stderr}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
        
        await asyncio.sleep(1)
    
    async def _mkdir(self):
        """Create new directory."""
        name = Prompt.ask("Folder name")
        if not name:
            return
        
        try:
            cmd = f"mkdir -p '{self.current_path}/{name}'"
            result = await self.client.execute_simple(cmd)
            
            if result.exit_code == 0:
                self.console.print(f"[green]✓ Created {name}[/green]")
            else:
                self.console.print(f"[red]Failed: {result.stderr}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
        
        await asyncio.sleep(1)
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Format file size."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}PB"