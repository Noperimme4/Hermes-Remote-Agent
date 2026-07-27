"""
Profile Manager - Manage multiple server profiles
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box


@dataclass
class ServerProfile:
    """Server connection profile."""
    name: str
    host: str
    port: int = 8765
    token: str = ""
    use_tls: bool = False
    ca_cert: str = ""
    timeout: int = 60
    cwd: str = "/data/workspace"
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServerProfile':
        return cls(**data)


class ProfileManager:
    """Manage server profiles."""
    
    def __init__(self):
        self.console = Console()
        self.config_dir = Path.home() / ".config" / "remote-agent"
        self.config_file = self.config_dir / "profiles.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.profiles: Dict[str, ServerProfile] = {}
        self.current_profile: Optional[str] = None
        self._load()
    
    def _load(self):
        """Load profiles from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.profiles = {k: ServerProfile.from_dict(v) for k, v in data.get("profiles", {}).items()}
                    self.current_profile = data.get("current")
            except Exception as e:
                self.console.print(f"[red]Error loading profiles: {e}[/red]")
                self.profiles = {}
    
    def _save(self):
        """Save profiles to file."""
        try:
            data = {
                "profiles": {k: v.to_dict() for k, v in self.profiles.items()},
                "current": self.current_profile
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
            # Restrict permissions
            os.chmod(self.config_file, 0o600)
        except Exception as e:
            self.console.print(f"[red]Error saving profiles: {e}[/red]")
    
    def add(self, profile: ServerProfile) -> bool:
        """Add or update profile."""
        if profile.name in self.profiles:
            if not Confirm.ask(f"Profile '{profile.name}' exists. Overwrite?"):
                return False
        
        self.profiles[profile.name] = profile
        self._save()
        return True
    
    def remove(self, name: str) -> bool:
        """Remove profile."""
        if name not in self.profiles:
            return False
        
        if Confirm.ask(f"Delete profile '{name}'?"):
            del self.profiles[name]
            if self.current_profile == name:
                self.current_profile = None
            self._save()
            return True
        return False
    
    def get(self, name: str) -> Optional[ServerProfile]:
        """Get profile by name."""
        return self.profiles.get(name)
    
    def list(self) -> List[ServerProfile]:
        """List all profiles."""
        return list(self.profiles.values())
    
    def set_current(self, name: str) -> bool:
        """Set current profile."""
        if name in self.profiles:
            self.current_profile = name
            self._save()
            return True
        return False
    
    def get_current(self) -> Optional[ServerProfile]:
        """Get current profile."""
        if self.current_profile:
            return self.profiles.get(self.current_profile)
        return None
    
    def interactive(self) -> Optional[ServerProfile]:
        """Interactive profile management."""
        while True:
            self.console.clear()
            
            # Current profile
            current = self.get_current()
            info = Table.grid(padding=1)
            info.add_column(style="cyan", justify="right")
            info.add_column(style="white")
            if current:
                info.add_row("Current:", f"[green]{current.name}[/green] ({current.host}:{current.port})")
            else:
                info.add_row("Current:", "[dim]None selected[/dim]")
            
            self.console.print(Panel(info, title="🔧 Profile Manager", border_style="blue", box=box.ROUNDED))
            
            # List profiles
            if self.profiles:
                table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
                table.add_column("#", style="dim", width=4)
                table.add_column("Name", style="bold white", width=20)
                table.add_column("Host", style="white", width=25)
                table.add_column("Port", style="dim", width=6)
                table.add_column("TLS", style="dim", width=5)
                table.add_column("Description", style="dim", width=30)
                
                for i, p in enumerate(self.profiles.values(), 1):
                    star = " ⭐" if p.name == self.current_profile else ""
                    table.add_row(
                        str(i),
                        f"{p.name}{star}",
                        p.host,
                        str(p.port),
                        "✓" if p.use_tls else "✗",
                        p.description[:30]
                    )
                
                self.console.print(table)
            else:
                self.console.print("[dim]No profiles yet[/dim]")
            
            # Menu
            self.console.print("\n[dim]Actions: [bold]a[/bold]dd | [bold]c[/bold]onnect | "
                              "[bold]s[/bold]elect | [bold]e[/bold]dit | "
                              "[bold]d[/bold]elete | [bold]q[/bold]uit[/dim]")
            
            action = Prompt.ask("Action", choices=["a", "c", "s", "e", "d", "q", "1", "2", "3", "4", "5", "6", "7", "8", "9"], default="q")
            
            if action == "q":
                return current
            elif action == "a":
                self._add_interactive()
            elif action == "c":
                return self._connect_interactive()
            elif action == "s":
                self._select_interactive()
            elif action == "e":
                self._edit_interactive()
            elif action == "d":
                self._delete_interactive()
            elif action.isdigit() and self.profiles:
                idx = int(action) - 1
                profiles = list(self.profiles.values())
                if 0 <= idx < len(profiles):
                    self.set_current(profiles[idx].name)
                    self.console.print(f"[green]Selected: {profiles[idx].name}[/green]")
                    await asyncio.sleep(0.5)
        
        return current
    
    def _add_interactive(self):
        """Add new profile interactively."""
        self.console.print(Panel("Add New Profile", border_style="green"))
        
        name = Prompt.ask("Name", default="myserver")
        if name in self.profiles:
            self.console.print("[red]Name already exists[/red]")
            return
        
        host = Prompt.ask("Host/IP")
        port = int(Prompt.ask("Port", default="8765"))
        token = Prompt.ask("Token", password=True)
        use_tls = Confirm.ask("Use TLS?", default=False)
        ca_cert = ""
        if use_tls:
            ca_cert = Prompt.ask("CA Cert path", default="")
        timeout = int(Prompt.ask("Timeout (sec)", default="60"))
        cwd = Prompt.ask("Working directory", default="/data/workspace")
        description = Prompt.ask("Description", default="")
        
        profile = ServerProfile(
            name=name,
            host=host,
            port=port,
            token=token,
            use_tls=use_tls,
            ca_cert=ca_cert,
            timeout=timeout,
            cwd=cwd,
            description=description
        )
        
        self.add(profile)
        self.console.print(f"[green]✓ Profile '{name}' added[/green]")
    
    def _connect_interactive(self) -> Optional[ServerProfile]:
        """Connect to a profile."""
        if not self.profiles:
            self.console.print("[red]No profiles available[/red]")
            return None
        
        names = list(self.profiles.keys())
        name = Prompt.ask("Profile to connect", choices=names, default=self.current_profile)
        
        if name:
            self.set_current(name)
            return self.profiles[name]
        return None
    
    def _select_interactive(self):
        """Select current profile."""
        if not self.profiles:
            return
        
        names = list(self.profiles.keys())
        name = Prompt.ask("Select profile", choices=names, default=self.current_profile)
        if name:
            self.set_current(name)
            self.console.print(f"[green]✓ Current: {name}[/green]")
    
    def _edit_interactive(self):
        """Edit existing profile."""
        if not self.profiles:
            return
        
        names = list(self.profiles.keys())
        name = Prompt.ask("Profile to edit", choices=names, default=self.current_profile)
        
        if name not in self.profiles:
            return
        
        profile = self.profiles[name]
        self.console.print(Panel(f"Editing: {name}", border_style="yellow"))
        
        # Edit each field
        profile.host = Prompt.ask("Host", default=profile.host)
        profile.port = int(Prompt.ask("Port", default=str(profile.port)))
        token = Prompt.ask("Token (leave empty to keep)", password=True, default="")
        if token:
            profile.token = token
        profile.use_tls = Confirm.ask("Use TLS?", default=profile.use_tls)
        if profile.use_tls:
            profile.ca_cert = Prompt.ask("CA Cert path", default=profile.ca_cert)
        profile.timeout = int(Prompt.ask("Timeout", default=str(profile.timeout)))
        profile.cwd = Prompt.ask("Working dir", default=profile.cwd)
        profile.description = Prompt.ask("Description", default=profile.description)
        
        self._save()
        self.console.print(f"[green]✓ Profile '{name}' updated[/green]")
    
    def _delete_interactive(self):
        """Delete profile."""
        if not self.profiles:
            return
        
        names = list(self.profiles.keys())
        name = Prompt.ask("Profile to delete", choices=names)
        
        if name and self.remove(name):
            self.console.print(f"[green]✓ Deleted '{name}'[/green]")


async def test_profile_manager():
    """Test profile manager."""
    import asyncio
    pm = ProfileManager()
    await pm.interactive()