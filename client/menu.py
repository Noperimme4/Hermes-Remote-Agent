"""
Interactive Menu for Remote Agent Client
"""

import asyncio
import os
import json
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box
from rich.tree import Tree

from client.cli import RemoteAgentClient, CommandResult
from client.file_browser import FileBrowser
from client.hermes import HermesClient
from client.profiles import ProfileManager


@dataclass
class MenuItem:
    key: str
    label: str
    action: Callable
    description: str = ""


class InteractiveMenu:
    """Main interactive menu for the client."""
    
    def __init__(self, client: RemoteAgentClient):
        self.client = client
        self.console = Console()
        self.running = True
        self.current_dir = client.config.cwd if hasattr(client.config, 'cwd') else "/data/workspace"
        
        self.items: List[MenuItem] = [
            MenuItem("1", "🐚 PTY Shell", self.shell_action, "Full terminal (vim, htop, ssh, sudo)"),
            MenuItem("2", "🤖 Hermes AI Chat", self.hermes_action, "Chat with Hermes AI on remote"),
            MenuItem("3", "📁 File Browser", self.files_action, "Browse, upload, download files"),
            MenuItem("4", "⚡ Quick Command", self.quick_cmd_action, "Run a single command"),
            MenuItem("5", "🐳 Docker Manager", self.docker_action, "Containers, images, logs"),
            MenuItem("6", "⚙️  Services (systemd)", self.services_action, "Start/stop/restart services"),
            MenuItem("7", "📊 System Monitor", self.monitor_action, "CPU, RAM, Disk, Processes"),
            MenuItem("8", "📝 View Logs", self.logs_action, "journalctl, dmesg, auth logs"),
            MenuItem("9", "🔧 Settings", self.settings_action, "Change dir, timeout, TLS"),
            MenuItem("0", "🚪 Exit", self.exit_action, "Disconnect and quit"),
        ]
    
    async def run(self):
        """Main menu loop."""
        while self.running:
            self._print_header()
            self._print_menu()
            
            choices = [item.key for item in self.items]
            choice = Prompt.ask("\nSelect option", choices=choices, default="1")
            
            for item in self.items:
                if item.key == choice:
                    try:
                        await item.action()
                    except Exception as e:
                        self.console.print(f"[red]Error: {e}[/red]")
                        import traceback
                        traceback.print_exc()
                    break
            
            if self.running and choice != "0":
                Prompt.ask("\n[dim]Press Enter to continue[/dim]")
    
    def _print_header(self):
        """Print menu header."""
        self.console.clear()
        
        info = Table.grid(padding=1)
        info.add_column(style="cyan", justify="right")
        info.add_column(style="white")
        info.add_row("🔗 Server:", self.client.server_info.get('name', 'unknown'))
        info.add_row("📍 Session:", self.client.session_id[:12] + "..." if self.client.session_id else "N/A")
        info.add_row("📂 Dir:", self.current_dir)
        
        self.console.print(Panel(info, title="🌐 Remote Agent", border_style="blue", box=box.ROUNDED))
    
    def _print_menu(self):
        """Print menu options."""
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        table.add_column("Key", style="bold cyan", width=4)
        table.add_column("Option", style="white", width=30)
        table.add_column("Description", style="dim", width=50)
        
        for item in self.items:
            table.add_row(item.key, item.label, item.description)
        
        self.console.print(table)
    
    # ─── Menu Actions ─────────────────────────────────────────────
    
    async def shell_action(self):
        """Start PTY shell."""
        self.console.print("[cyan]Starting PTY shell...[/cyan]")
        self.console.print("[dim]Press Ctrl+D or type 'exit' to return to menu[/dim]\n")
        await self.client.interactive_shell(cwd=self.current_dir)
    
    async def hermes_action(self):
        """Start Hermes AI chat."""
        hermes = HermesClient(self.client)
        await hermes.chat()
    
    async def files_action(self):
        """File browser."""
        browser = FileBrowser(self.client, self.current_dir)
        new_dir = await browser.run()
        if new_dir:
            self.current_dir = new_dir
    
    async def quick_cmd_action(self):
        """Run a single command."""
        cmd = Prompt.ask("Command", default="ls -la")
        self.console.print(f"[cyan]▶ {cmd}[/cyan]")
        
        def stream_handler(chunk):
            if chunk.chunk_type in ("stdout", "stderr"):
                self.console.print(chunk.data, end="")
        
        try:
            result = await self.client.execute_simple(
                cmd, cwd=self.current_dir, stream=True, progress_cb=stream_handler
            )
            if result.exit_code != 0:
                self.console.print(f"\n[red]Exit code: {result.exit_code}[/red]")
            else:
                self.console.print(f"\n[green]Done ({result.execution_time:.2f}s)[/green]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    async def docker_action(self):
        """Docker manager."""
        while True:
            self.console.clear()
            self.console.print(Panel("🐳 Docker Manager", border_style="blue"))
            
            options = [
                ("1", "📦 List Containers", "docker ps -a"),
                ("2", "🖼️  List Images", "docker images"),
                ("3", "📜 Container Logs", "docker logs"),
                ("4", "▶️  Start Container", "docker start"),
                ("5", "⏹️  Stop Container", "docker stop"),
                ("6", "🔄 Restart Container", "docker restart"),
                ("7", "🗑️  Remove Container", "docker rm"),
                ("8", "📊 Stats", "docker stats --no-stream"),
                ("0", "Back", None),
            ]
            
            table = Table(box=box.SIMPLE)
            table.add_column("Key", style="cyan", width=4)
            table.add_column("Action", style="white")
            for k, v, _ in options:
                table.add_row(k, v)
            self.console.print(table)
            
            choice = Prompt.ask("Select", choices=[o[0] for o in options], default="1")
            
            if choice == "0":
                break
            
            for k, v, cmd in options:
                if k == choice and cmd:
                    if cmd in ("docker logs", "docker start", "docker stop", "docker restart", "docker rm"):
                        target = Prompt.ask("Container name/ID")
                        full_cmd = f"{cmd} {target}"
                    else:
                        full_cmd = cmd
                    
                    self.console.print(f"[cyan]▶ {full_cmd}[/cyan]")
                    try:
                        result = await self.client.execute_simple(full_cmd)
                        self.console.print(result.stdout)
                        if result.stderr:
                            self.console.print(result.stderr, style="red")
                    except Exception as e:
                        self.console.print(f"[red]Error: {e}[/red]")
                    
                    Prompt.ask("\n[dim]Press Enter[/dim]")
    
    async def services_action(self):
        """Systemd services manager."""
        while True:
            self.console.clear()
            self.console.print(Panel("⚙️ Systemd Services", border_style="blue"))
            
            options = [
                ("1", "📋 List All Services", "systemctl list-units --type=service --all"),
                ("2", "▶️  Start Service", "systemctl start"),
                ("3", "⏹️  Stop Service", "systemctl stop"),
                ("4", "🔄 Restart Service", "systemctl restart"),
                ("5", "✅ Enable Service", "systemctl enable"),
                ("6", "❌ Disable Service", "systemctl disable"),
                ("7", "📊 Service Status", "systemctl status"),
                ("8", "📜 Service Logs", "journalctl -u"),
                ("0", "Back", None),
            ]
            
            table = Table(box=box.SIMPLE)
            table.add_column("Key", style="cyan", width=4)
            table.add_column("Action", style="white")
            for k, v, _ in options:
                table.add_row(k, v)
            self.console.print(table)
            
            choice = Prompt.ask("Select", choices=[o[0] for o in options], default="1")
            
            if choice == "0":
                break
            
            for k, v, cmd in options:
                if k == choice and cmd:
                    if cmd in ("systemctl start", "systemctl stop", "systemctl restart",
                               "systemctl enable", "systemctl disable", "systemctl status",
                               "journalctl -u"):
                        target = Prompt.ask("Service name")
                        full_cmd = f"{cmd} {target}"
                    else:
                        full_cmd = cmd
                    
                    self.console.print(f"[cyan]▶ {full_cmd}[/cyan]")
                    try:
                        result = await self.client.execute_simple(full_cmd)
                        self.console.print(result.stdout)
                        if result.stderr:
                            self.console.print(result.stderr, style="red")
                    except Exception as e:
                        self.console.print(f"[red]Error: {e}[/red]")
                    
                    Prompt.ask("\n[dim]Press Enter[/dim]")
    
    async def monitor_action(self):
        """System monitor."""
        self.console.print("[cyan]Fetching system info...[/cyan]")
        
        cmds = [
            ("CPU", "top -bn1 | head -5"),
            ("Memory", "free -h"),
            ("Disk", "df -h /"),
            ("Load", "uptime"),
            ("Processes", "ps aux --sort=-%cpu | head -10"),
        ]
        
        for name, cmd in cmds:
            self.console.print(f"\n[bold cyan]{name}:[/bold cyan]")
            try:
                result = await self.client.execute_simple(cmd)
                self.console.print(result.stdout)
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
    
    async def logs_action(self):
        """View system logs."""
        self.console.print("[cyan]Fetching logs...[/cyan]")
        
        options = [
            ("1", "System Log (last 50)", "journalctl -n 50 --no-pager"),
            ("2", "Kernel Log (last 50)", "dmesg -T | tail -50"),
            ("3", "SSH Auth Log", "journalctl -u sshd -n 50 --no-pager"),
            ("4", "Custom Service Log", None),
            ("0", "Back", None),
        ]
        
        table = Table(box=box.SIMPLE)
        table.add_column("Key", style="cyan", width=4)
        table.add_column("Log", style="white")
        for k, v, _ in options:
            table.add_row(k, v)
        self.console.print(table)
        
        choice = Prompt.ask("Select", choices=[o[0] for o in options], default="1")
        
        if choice == "0":
            return
        
        for k, v, cmd in options:
            if k == choice:
                if cmd is None:
                    service = Prompt.ask("Service name")
                    cmd = f"journalctl -u {service} -n 50 --no-pager"
                
                self.console.print(f"[cyan]▶ {cmd}[/cyan]")
                try:
                    result = await self.client.execute_simple(cmd)
                    self.console.print(result.stdout)
                except Exception as e:
                    self.console.print(f"[red]Error: {e}[/red]")
                break
        
        Prompt.ask("\n[dim]Press Enter[/dim]")
    
    async def settings_action(self):
        """Settings menu."""
        while True:
            self.console.clear()
            self.console.print(Panel("🔧 Settings", border_style="blue"))
            
            info = Table.grid(padding=1)
            info.add_column(style="cyan")
            info.add_column(style="white")
            info.add_row("Current Dir:", self.current_dir)
            info.add_row("Timeout:", f"{self.client.config.timeout}s")
            info.add_row("TLS:", "Yes" if self.client.config.use_tls else "No")
            self.console.print(info)
            
            options = [
                ("1", "Change Directory", self.change_dir),
                ("2", "Change Timeout", self.change_timeout),
                ("3", "Toggle TLS", self.toggle_tls),
                ("0", "Back", None),
            ]
            
            table = Table(box=box.SIMPLE)
            table.add_column("Key", style="cyan", width=4)
            table.add_column("Option", style="white")
            for k, v, _ in options:
                table.add_row(k, v)
            self.console.print(table)
            
            choice = Prompt.ask("Select", choices=[o[0] for o in options], default="1")
            
            if choice == "0":
                break
            
            for k, v, action in options:
                if k == choice and action:
                    await action()
    
    async def change_dir(self):
        new_dir = Prompt.ask("New directory", default=self.current_dir)
        try:
            result = await self.client.execute_simple(f"test -d {new_dir} && echo OK")
            if "OK" in result.stdout:
                self.current_dir = new_dir
                self.console.print(f"[green]Directory changed to {new_dir}[/green]")
            else:
                self.console.print("[red]Directory does not exist[/red]")
        except:
            self.console.print("[red]Error checking directory[/red]")
    
    async def change_timeout(self):
        try:
            timeout = int(Prompt.ask("Timeout (seconds)", default=str(self.client.config.timeout)))
            self.client.config.timeout = timeout
            self.console.print(f"[green]Timeout set to {timeout}s[/green]")
        except ValueError:
            self.console.print("[red]Invalid number[/red]")
    
    async def toggle_tls(self):
        self.client.config.use_tls = not self.client.config.use_tls
        self.console.print(f"[green]TLS {'enabled' if self.client.config.use_tls else 'disabled'}[/green]")
        self.console.print("[yellow]Reconnect required for TLS changes[/yellow]")
    
    async def exit_action(self):
        if Confirm.ask("Disconnect and exit?"):
            self.running = False