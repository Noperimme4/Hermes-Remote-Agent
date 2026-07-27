"""
Hermes AI Client - Chat with Hermes through remote connection
"""

import asyncio
import json
from typing import Optional, List, Dict, Any
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich import box


class HermesClient:
    """Hermes AI chat client through remote agent."""
    
    def __init__(self, client):
        self.client = client
        self.console = Console()
        self.history: List[Dict[str, str]] = []
        self.session_id: Optional[str] = None
    
    async def chat(self):
        """Start Hermes chat session."""
        self.console.clear()
        
        # Check if Hermes is available
        self.console.print("[cyan]Checking Hermes availability...[/cyan]")
        try:
            result = await self.client.execute_simple("which hermes || echo 'NOT_FOUND'")
            if "NOT_FOUND" in result.stdout:
                self.console.print("[yellow]⚠️  Hermes not installed on remote server[/yellow]")
                self.console.print("[dim]Install with: pip install hermes-agent[/dim]")
                if not Prompt.ask("Continue anyway?", choices=["y", "n"], default="n") == "y":
                    return
        except:
            pass
        
        self.console.print(Panel(
            "[bold green]🤖 Hermes AI Chat[/bold green]\n"
            "[dim]Connected to remote Hermes instance[/dim]\n"
            "[dim]Commands: /new (new session), /history, /save, /help, exit/quit[/dim]",
            title="Hermes Chat",
            border_style="green",
            box=box.ROUNDED
        ))
        
        await self._new_session()
        
        while True:
            try:
                user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
                
                if not user_input.strip():
                    continue
                
                # Handle commands
                if user_input.lower() in ('exit', 'quit', '/q'):
                    break
                elif user_input.lower() == '/new':
                    await self._new_session()
                    continue
                elif user_input.lower() == '/history':
                    self._show_history()
                    continue
                elif user_input.lower() == '/save':
                    self._save_chat()
                    continue
                elif user_input.lower() == '/help':
                    self._show_help()
                    continue
                
                # Send to Hermes
                self.console.print("[dim]Thinking...[/dim]")
                
                cmd = f'hermes chat -q "{user_input}"'
                if self.session_id:
                    cmd += f" --resume {self.session_id}"
                
                def stream_handler(chunk):
                    if chunk.chunk_type in ("stdout", "stderr"):
                        self.console.print(chunk.data, end="")
                
                result = await self.client.execute_simple(
                    cmd, timeout=120, stream=True, progress_cb=stream_handler
                )
                
                if result.stdout:
                    for line in result.stdout.split('\n'):
                        if 'session_id:' in line.lower():
                            self.session_id = line.split(':')[-1].strip()
                
                # Store in history
                self.history.append({"role": "user", "content": user_input})
                self.history.append({"role": "assistant", "content": result.stdout})
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted[/yellow]")
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
    
    async def _new_session(self):
        """Start new Hermes session."""
        self.history = []
        self.session_id = None
        self.console.print("[green]✓ New session started[/green]")
    
    def _show_history(self):
        if not self.history:
            self.console.print("[dim]No history yet[/dim]")
            return
        
        for msg in self.history:
            if msg["role"] == "user":
                self.console.print(Panel(msg["content"], title="You", border_style="cyan"))
            else:
                self.console.print(Panel(msg["content"][:500], title="Hermes", border_style="green"))
    
    def _save_chat(self):
        import datetime
        filename = f"hermes_chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
        self.console.print(f"[green]Chat saved to {filename}[/green]")
    
    def _show_help(self):
        help_text = """
[bold]Hermes Chat Commands:[/bold]
  /new      - Start new session
  /history  - Show conversation history
  /save     - Save chat to file
  /help     - Show this help
  exit/quit - Return to menu
        """
        self.console.print(Panel(help_text, title="Help", border_style="blue"))