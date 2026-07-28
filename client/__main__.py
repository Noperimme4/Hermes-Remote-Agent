#!/usr/bin/env python3
"""
Remote Agent Client CLI - Main entry point with interactive menu
"""

import asyncio
import os
import sys
import getpass
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box

from client.menu import InteractiveMenu
from client.hermes import run_hermes_panel
from client.file_browser import FileBrowser
from client.cli import RemoteAgentClient, ClientConfig
from client.profile_manager import ProfileManager, ServerProfile


console = Console()


def print_banner():
    console.print("""
╔═══════════════════════════════════════════════════════════════════╗
║                    🌐 Remote Agent Client v2.0                  ║
║         Secure Remote Control + Hermes AI Integration           ║
╚═══════════════════════════════════════════════════════════════════╝
""")


def print_help():
    console.print("""
[bold]Usage:[/bold] agent [OPTIONS]

[bold]Options:[/bold]
  --host HOST         Server hostname/IP (default: localhost)
  --port PORT         Server port (default: 8765)
  --token TOKEN       Auth token (or set AGENT_TOKEN env)
  --profile NAME      Use saved profile
  --save-profile      Save current connection as profile
  -i, --interactive   Interactive menu mode (default)
  -c, --command CMD   Execute single command and exit
  -s, --shell         Start PTY shell session
  --hermes            Start Hermes AI chat
  --files             File browser mode
  --profiles          Manage server profiles
  -v, --verbose       Verbose output
  -h, --help          Show this help

[bold]Examples:[/bold]
  agent                                    # Interactive menu with profiles
  agent --host 192.168.1.100 --token xxx  # Connect to server
  agent --profile myserver                # Use saved profile
  agent -c "ls -la /data"                 # Run single command
  agent --hermes                          # Chat with Hermes AI
  agent --files                           # File browser
  agent --profiles                        # Manage profiles

[bold]Environment:[/bold]
  AGENT_TOKEN      Default auth token
  AGENT_HOST       Default server host
  AGENT_PORT       Default server port
""")


async def main():
    parser = argparse.ArgumentParser(description="Remote Agent Client", add_help=False)
    parser.add_argument("--host", default=os.getenv("AGENT_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("AGENT_PORT", "8765")))
    parser.add_argument("--token", default=os.getenv("AGENT_TOKEN", ""))
    parser.add_argument("--profile", help="Use saved profile")
    parser.add_argument("--save-profile", action="store_true")
    parser.add_argument("-i", "--interactive", action="store_true", default=True)
    parser.add_argument("-c", "--command", help="Execute single command")
    parser.add_argument("-s", "--shell", action="store_true", help="PTY shell")
    parser.add_argument("--hermes", action="store_true", help="Hermes AI chat")
    parser.add_argument("--files", action="store_true", help="File browser")
    parser.add_argument("--remote-files", action="store_true", help="Remote file browser (access local files from server)")
    parser.add_argument("--profiles", action="store_true", help="Manage profiles")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-h", "--help", action="store_true")
    
    args = parser.parse_args()
    
    if args.help:
        print_help()
        return 0
    
    print_banner()
    
    # Initialize profile manager
    profile_manager = ProfileManager()
    
    # Handle profile management mode
    if args.profiles:
        await profile_manager.interactive()
        return 0
    
    # Load profile if specified
    host = args.host
    port = args.port
    token = args.token
    cwd = "/data/workspace"
    
    if args.profile:
        profile = profile_manager.get(args.profile)
        if profile:
            host = profile.host
            port = profile.port
            token = profile.token
            cwd = profile.cwd
            console.print(f"📋 Loaded profile: [green]{profile.name}[/green] ({profile.host}:{profile.port})")
        else:
            console.print(f"[red]Profile not found: {args.profile}[/red]")
            return 1
    else:
        # Check for current profile
        current = profile_manager.get_current()
        if current and not args.profile:
            console.print(f"📋 Using current profile: [green]{current.name}[/green]")
            host = current.host
            port = current.port
            token = current.token
            cwd = current.cwd
    
    # Get token if not provided
    if not token:
        token = getpass.getpass("🔑 Enter auth token: ").strip()
    
    if not token:
        console.print("[red]Token required[/red]")
        return 1
    
    # Create client
    config = ClientConfig(
        host=host,
        port=port,
        token=token,
        timeout=args.verbose and 10 or 60,
        log_level="DEBUG" if args.verbose else "WARNING"
    )
    
    client = RemoteAgentClient(config)
    
    console.print(f"🔌 Connecting to [bold]{host}:{port}[/bold]...")
    connected = await client.connect()
    
    if not connected:
        console.print("[red]❌ Connection failed[/red]")
        return 1
    
    console.print(f"✅ Connected! Session: [cyan]{client.session_id[:8]}...[/cyan]")
    console.print(f"🖥️  Server: [green]{client.server_info.get('name', 'unknown')}[/green]")
    console.print()
    
    # Save profile if requested
    if args.save_profile:
        name = Prompt.ask("Profile name", default="default")
        profile_manager.add(ServerProfile(
            name=name,
            host=host,
            port=port,
            token=token,
            cwd=cwd
        ))
        console.print(f"💾 Profile '[green]{name}[/green]' saved")
    
    # Route to appropriate mode
    try:
        if args.command:
            # Single command mode
            result = await client.execute_simple(args.command, cwd=cwd)
            console.print(result.stdout)
            if result.stderr:
                console.print(result.stderr, style="red")
            return result.exit_code
        
        elif args.shell:
            # PTY Shell
            console.print("🐚 Starting PTY shell... (Ctrl+D to exit)")
            await client.interactive_shell(cwd=cwd)
        
        elif args.hermes:
            # Hermes AI Panel
            await run_hermes_panel(client)
        
        elif args.files:
            # File Browser
            browser = FileBrowser(client, cwd)
            await browser.run()
        
        elif args.remote_files:
            # Remote File Browser (access local files from server perspective)
            from client.remote_files import RemoteFileBrowser
            browser = RemoteFileBrowser(client)
            await browser.run()

        else:
            # Interactive Menu (default)
            menu = InteractiveMenu(client, profile_manager)
            await menu.run()
    
    finally:
        await client.disconnect()
    
    return 0


def run():
    """Entry point for setuptools."""
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if os.getenv("AGENT_DEBUG"):
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run()