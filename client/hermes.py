"""
Hermes AI Panel - Full-featured Hermes AI interface through remote agent
Beautiful, interactive panel with complete Hermes access
"""

import asyncio
import json
import os
import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass, asdict

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.tree import Tree
from rich.columns import Columns
from rich.align import Align
from rich.live import Live
from rich.spinner import Spinner
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.rule import Rule


@dataclass
class HermesMessage:
    """Single message in conversation."""
    role: str  # user, assistant, system
    content: str
    timestamp: str
    metadata: Dict[str, Any] = None


@dataclass
class HermesSession:
    """Hermes chat session."""
    id: str
    name: str
    created_at: str
    updated_at: str
    messages: List[HermesMessage]
    system_prompt: str = ""
    model: str = "default"
    metadata: Dict[str, Any] = None


class HermesPanel:
    """Full-featured Hermes AI Panel."""
    
    def __init__(self, client):
        self.client = client
        self.console = Console()
        self.sessions: Dict[str, HermesSession] = {}
        self.current_session: Optional[HermesSession] = None
        self.running = True
        self.config = {
            "stream": True,
            "timeout": 120,
            "auto_save": True,
            "show_timestamps": True,
            "syntax_theme": "monokai",
            "max_history_display": 50,
        }
        self.shortcuts = {
            "ctrl+n": "New session",
            "ctrl+s": "Save session",
            "ctrl+l": "List sessions",
            "ctrl+h": "History",
            "ctrl+e": "Export",
            "ctrl+p": "Persona/System prompt",
            "ctrl+m": "Model select",
            "ctrl+f": "File analysis",
            "ctrl+c": "Copy last response",
            "ctrl+q": "Quit",
        }
        
    async def run(self):
        """Main panel entry point."""
        await self._initialize()
        
        while self.running:
            await self._show_main_menu()
            
    async def _initialize(self):
        """Initialize panel - check Hermes, load sessions."""
        self.console.clear()
        self._print_banner()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            task = progress.add_task("Checking Hermes...", total=None)
            
            # Check Hermes availability
            self.hermes_available = await self._check_hermes()
            
            if self.hermes_available:
                progress.update(task, description="Loading sessions...")
                await self._load_sessions()
                progress.update(task, description="Ready!")
            else:
                progress.update(task, description="Hermes not found")
        
        await asyncio.sleep(0.5)
        
    def _print_banner(self):
        """Print beautiful banner."""
        banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                        🤖 HERMES AI PANEL v2.0                              ║
║              Complete AI Assistant Interface for Remote Agent               ║
╚═════════════════════════════════════════════════════════════════════════════╝
        """
        self.console.print(Align.center(banner), style="bold cyan")
        
        # Status bar
        status_items = []
        if self.hermes_available:
            status_items.append("[green]● Hermes: Connected[/green]")
        else:
            status_items.append("[red]● Hermes: Not Available[/red]")
        status_items.append(f"[cyan]Sessions: {len(self.sessions)}[/cyan]")
        if self.current_session:
            status_items.append(f"[yellow]Active: {self.current_session.name}[/yellow]")
        
        self.console.print(Align.center("  │  ".join(status_items)))
        self.console.print()
        
    async def _check_hermes(self) -> bool:
        """Check if Hermes is available on remote."""
        try:
            result = await self.client.execute_simple("which hermes || echo 'NOT_FOUND'", timeout=10)
            if "NOT_FOUND" in result.stdout:
                return False
            # Get version
            result = await self.client.execute_simple("hermes --version", timeout=10)
            self.hermes_version = result.stdout.strip()
            return True
        except:
            return False
            
    async def _load_sessions(self):
        """Load saved sessions from local storage."""
        sessions_dir = Path.home() / ".config" / "remote-agent" / "hermes_sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        
        for session_file in sessions_dir.glob("*.json"):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                session = HermesSession(
                    id=data.get("id", session_file.stem),
                    name=data.get("name", session_file.stem),
                    created_at=data.get("created_at", ""),
                    updated_at=data.get("updated_at", ""),
                    messages=[HermesMessage(**m) for m in data.get("messages", [])],
                    system_prompt=data.get("system_prompt", ""),
                    model=data.get("model", "default"),
                    metadata=data.get("metadata", {}),
                )
                self.sessions[session.id] = session
            except Exception as e:
                self.console.print(f"[dim]Failed to load {session_file}: {e}[/dim]")
                
    def _save_session(self, session: HermesSession):
        """Save session to local storage."""
        sessions_dir = Path.home() / ".config" / "remote-agent" / "hermes_sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        
        session_file = sessions_dir / f"{session.id}.json"
        data = {
            "id": session.id,
            "name": session.name,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "messages": [asdict(m) for m in session.messages],
            "system_prompt": session.system_prompt,
            "model": session.model,
            "metadata": session.metadata or {},
        }
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return f"hermes_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        
    # ─── Main Menu ────────────────────────────────────────────────────
    
    async def _show_main_menu(self):
        """Display main menu and handle selection."""
        self.console.clear()
        self._print_banner()
        
        # Quick stats
        stats_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="white")
        stats_table.add_row("🤖 Hermes Version", getattr(self, 'hermes_version', 'Unknown'))
        stats_table.add_row("💾 Sessions", str(len(self.sessions)))
        stats_table.add_row("📝 Current Session", self.current_session.name if self.current_session else "None")
        stats_table.add_row("⚙️  Config", f"Stream: {'On' if self.config['stream'] else 'Off'} | Timeout: {self.config['timeout']}s")
        
        self.console.print(Panel(stats_table, title="📊 Status", border_style="blue", box=box.ROUNDED))
        self.console.print()
        
        # Menu options
        menu_items = [
            ("1", "💬 Chat", "Start/continue chat with Hermes", "chat"),
            ("2", "📋 Sessions", "Manage sessions (list, create, delete, resume)", "sessions"),
            ("3", "🎭 Personas", "System prompts & personas management", "personas"),
            ("4", "🔧 Tools", "Code execution, file analysis, web search", "tools"),
            ("5", "📤 Export/Import", "Backup, restore, share conversations", "export"),
            ("6", "⚙️  Settings", "Configure panel behavior", "settings"),
            ("7", "ℹ️  Help", "Shortcuts, commands, documentation", "help"),
            ("0", "🚪 Exit", "Return to main menu", "exit"),
        ]
        
        menu_table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
        menu_table.add_column("Key", style="bold cyan", width=6)
        menu_table.add_column("Option", style="white", width=20)
        menu_table.add_column("Description", style="dim", width=50)
        
        for key, label, desc, _ in menu_items:
            menu_table.add_row(key, label, desc)
            
        self.console.print(Panel(menu_table, title="🎯 Main Menu", border_style="green", box=box.ROUNDED))
        
        # Shortcuts hint
        shortcuts_text = "  ".join([f"[bold cyan]{k}[/bold cyan]: {v}" for k, v in self.shortcuts.items()])
        self.console.print(Align.center(Text(shortcuts_text, style="dim")), style="dim")
        self.console.print()
        
        choice = Prompt.ask("Select option", choices=[m[0] for m in menu_items], default="1")
        
        action_map = {m[0]: m[3] for m in menu_items}
        action = action_map.get(choice)
        
        if action == "chat":
            await self._chat_mode()
        elif action == "sessions":
            await self._sessions_menu()
        elif action == "personas":
            await self._personas_menu()
        elif action == "tools":
            await self._tools_menu()
        elif action == "export":
            await self._export_menu()
        elif action == "settings":
            await self._settings_menu()
        elif action == "help":
            await self._show_help()
        elif action == "exit":
            self.running = False
            
    # ─── Chat Mode ────────────────────────────────────────────────────
    
    async def _chat_mode(self):
        """Main chat interface."""
        if not self.hermes_available:
            self.console.print("[red]Hermes not available on remote server![/red]")
            self.console.print("[dim]Install with: pip install hermes-agent[/dim]")
            if not Confirm.ask("Continue anyway?"):
                return
                
        # Select or create session
        if not self.current_session:
            await self._select_or_create_session()
            if not self.current_session:
                return
                
        self.console.clear()
        self._print_chat_header()
        
        # Display existing messages
        self._display_messages()
        
        # Chat loop
        while self.running:
            try:
                user_input = await self._get_chat_input()
                
                if not user_input:
                    continue
                    
                # Handle chat commands
                if user_input.startswith("/"):
                    handled = await self._handle_chat_command(user_input)
                    if handled == "exit":
                        break
                    elif handled == "continue":
                        continue
                        
                # Send to Hermes
                await self._send_to_hermes(user_input)
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use /quit to exit[/yellow]")
            except EOFError:
                break
                
    def _print_chat_header(self):
        """Print chat header with session info."""
        session = self.current_session
        header_items = [
            f"[bold]{session.name}[/bold]",
            f"[dim]ID: {session.id[:20]}...[/dim]",
            f"[dim]Messages: {len(session.messages)}[/dim]",
            f"[dim]Model: {session.model}[/dim]",
        ]
        if session.system_prompt:
            header_items.append(f"[dim]Persona: {session.system_prompt[:30]}...[/dim]")
            
        header = Table.grid(padding=(0, 2))
        header.add_column()
        for item in header_items:
            header.add_row(item)
            
        self.console.print(Panel(header, title="💬 Chat", border_style="cyan", box=box.ROUNDED))
        self.console.print()
        
    def _display_messages(self, limit: int = None):
        """Display conversation messages."""
        messages = self.current_session.messages
        if limit:
            messages = messages[-limit:]
            
        for msg in messages:
            self._render_message(msg)
            
    def _render_message(self, msg: HermesMessage):
        """Render a single message beautifully."""
        timestamp = ""
        if self.config["show_timestamps"] and msg.timestamp:
            try:
                dt = datetime.datetime.fromisoformat(msg.timestamp)
                timestamp = f"[dim]{dt.strftime('%H:%M:%S')}[/dim] "
            except:
                pass
                
        if msg.role == "user":
            content = msg.content
            # Try to render as markdown if it looks like it
            panel = Panel(
                content,
                title=f"{timestamp}👤 You",
                title_align="left",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        elif msg.role == "assistant":
            content = msg.content
            # Detect code blocks and render with syntax highlighting
            panel = Panel(
                Markdown(content) if self._looks_like_markdown(content) else content,
                title=f"{timestamp}🤖 Hermes",
                title_align="left",
                border_style="green",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        else:  # system
            panel = Panel(
                msg.content,
                title=f"{timestamp}⚙️ System",
                title_align="left",
                border_style="yellow",
                box=box.ROUNDED,
                padding=(0, 1),
            )
            
        self.console.print(panel)
        
    def _looks_like_markdown(self, text: str) -> bool:
        """Check if text contains markdown formatting."""
        md_indicators = ['```', '**', '*', '# ', '## ', '### ', '- ', '1. ', '> ', '|', '`']
        return any(indicator in text for indicator in md_indicators)
        
    async def _get_chat_input(self) -> str:
        """Get user input with multiline support."""
        self.console.print()
        # Use Prompt.ask with multiline hint
        user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
        return user_input.strip()
        
    async def _handle_chat_command(self, cmd: str) -> str:
        """Handle chat slash commands. Returns 'exit', 'continue', or 'process'."""
        parts = cmd[1:].split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        commands = {
            "quit": lambda: "exit",
            "exit": lambda: "exit",
            "q": lambda: "exit",
            "new": lambda: self._cmd_new_session(),
            "clear": lambda: self._cmd_clear_chat(),
            "save": lambda: self._cmd_save_session(),
            "history": lambda: self._cmd_show_history(),
            "sessions": lambda: self._cmd_list_sessions(),
            "switch": lambda: self._cmd_switch_session(args[0] if args else None),
            "persona": lambda: self._cmd_set_persona(" ".join(args)),
            "model": lambda: self._cmd_set_model(" ".join(args)),
            "export": lambda: self._cmd_export_chat(args[0] if args else None),
            "import": lambda: self._cmd_import_chat(args[0] if args else None),
            "search": lambda: self._cmd_search_history(" ".join(args)),
            "stats": lambda: self._cmd_session_stats(),
            "help": lambda: self._cmd_chat_help(),
            "tools": lambda: self._cmd_tools_menu(),
            "analyze": lambda: self._cmd_analyze_file(" ".join(args)),
            "code": lambda: self._cmd_generate_code(" ".join(args)),
            "review": lambda: self._cmd_code_review(" ".join(args)),
        }
        
        if command in commands:
            result = await commands[command]()
            return "continue" if result != "exit" else "exit"
        else:
            self.console.print(f"[red]Unknown command: /{command}[/red]")
            self.console.print("[dim]Type /help for available commands[/dim]")
            return "continue"
            
    async def _send_to_hermes(self, user_input: str):
        """Send message to Hermes and handle streaming response."""
        # Add user message
        user_msg = HermesMessage(
            role="user",
            content=user_input,
            timestamp=datetime.datetime.now().isoformat(),
        )
        self.current_session.messages.append(user_msg)
        self._render_message(user_msg)
        
        # Build command
        cmd_parts = ['hermes', 'chat', '-q', user_input]
        if self.current_session.system_prompt:
            cmd_parts.extend(['--system', self.current_session.system_prompt])
        if self.current_session.id:
            cmd_parts.extend(['--session', self.current_session.id])
        if self.current_session.model != "default":
            cmd_parts.extend(['--model', self.current_session.model])
            
        cmd = " ".join(cmd_parts)
        
        # Stream response
        self.console.print()
        assistant_content = ""
        
        with Live(Panel("", title="🤖 Hermes (thinking...)", border_style="green", box=box.ROUNDED), 
                  console=self.console, refresh_per_second=10) as live:
            
            def stream_handler(chunk):
                nonlocal assistant_content
                if chunk.chunk_type in ("stdout", "stderr"):
                    assistant_content += chunk.data
                    # Update live display with markdown
                    display_content = Markdown(assistant_content) if self._looks_like_markdown(assistant_content) else assistant_content
                    live.update(Panel(display_content, title="🤖 Hermes", border_style="green", box=box.ROUNDED, padding=(0, 1)))
                    
            try:
                result = await self.client.execute_simple(
                    cmd, 
                    timeout=self.config["timeout"], 
                    stream=self.config["stream"],
                    progress_cb=stream_handler if self.config["stream"] else None
                )
                
                # Final render
                final_content = result.stdout or assistant_content
                if not final_content:
                    final_content = "[dim](No response)[/dim]"
                    
            except Exception as e:
                final_content = f"[red]Error: {e}[/red]"
                
        # Add assistant message
        assistant_msg = HermesMessage(
            role="assistant",
            content=final_content,
            timestamp=datetime.datetime.now().isoformat(),
        )
        self.current_session.messages.append(assistant_msg)
        self.current_session.updated_at = datetime.datetime.now().isoformat()
        
        # Re-render final message nicely
        self.console.print()
        self._render_message(assistant_msg)
        
        # Auto-save
        if self.config["auto_save"]:
            self._save_session(self.current_session)
            
    # ─── Chat Commands ────────────────────────────────────────────────
    
    async def _cmd_new_session(self):
        """Create new session."""
        name = Prompt.ask("Session name", default=f"Chat {len(self.sessions) + 1}")
        await self._create_session(name)
        
    async def _cmd_clear_chat(self):
        """Clear current session messages."""
        if Confirm.ask("Clear all messages in this session?"):
            self.current_session.messages = []
            self.current_session.updated_at = datetime.datetime.now().isoformat()
            self._save_session(self.current_session)
            self.console.print("[green]Chat cleared[/green]")
            self.console.clear()
            self._print_chat_header()
            
    async def _cmd_save_session(self):
        """Save current session."""
        self._save_session(self.current_session)
        self.console.print(f"[green]Session saved: {self.current_session.name}[/green]")
        
    async def _cmd_show_history(self):
        """Show full history."""
        self.console.clear()
        self._print_chat_header()
        self._display_messages()
        Prompt.ask("\n[dim]Press Enter to continue[/dim]")
        self.console.clear()
        self._print_chat_header()
        self._display_messages()
        
    async def _cmd_list_sessions(self):
        """List all sessions."""
        await self._list_sessions_display()
        Prompt.ask("\n[dim]Press Enter to continue[/dim]")
        self.console.clear()
        self._print_chat_header()
        self._display_messages()
        
    async def _cmd_switch_session(self, session_id: str = None):
        """Switch to another session."""
        if not session_id:
            await self._list_sessions_display()
            session_id = Prompt.ask("Session ID to switch to")
            
        if session_id in self.sessions:
            self.current_session = self.sessions[session_id]
            self._save_session(self.current_session)
            self.console.print(f"[green]Switched to: {self.current_session.name}[/green]")
            self.console.clear()
            self._print_chat_header()
            self._display_messages()
        else:
            self.console.print("[red]Session not found[/red]")
            
    async def _cmd_set_persona(self, persona: str):
        """Set system prompt/persona."""
        if not persona:
            self.console.print("[bold]Current Persona:[/bold]")
            self.console.print(self.current_session.system_prompt or "[dim]None[/dim]")
            persona = Prompt.ask("New persona (empty to clear)")
            
        self.current_session.system_prompt = persona
        self.current_session.updated_at = datetime.datetime.now().isoformat()
        self._save_session(self.current_session)
        self.console.print("[green]Persona updated[/green]")
        
    async def _cmd_set_model(self, model: str):
        """Set model."""
        if not model:
            self.console.print(f"[bold]Current Model:[/bold] {self.current_session.model}")
            model = Prompt.ask("Model name (empty for default)")
            
        self.current_session.model = model or "default"
        self.current_session.updated_at = datetime.datetime.now().isoformat()
        self._save_session(self.current_session)
        self.console.print(f"[green]Model set to: {self.current_session.model}[/green]")
        
    async def _cmd_export_chat(self, format: str = None):
        """Export chat."""
        await self._export_session(self.current_session, format)
        
    async def _cmd_import_chat(self, file: str = None):
        """Import chat."""
        await self._import_session(file)
        
    async def _cmd_search_history(self, query: str = None):
        """Search message history."""
        if not query:
            query = Prompt.ask("Search query")
            
        results = []
        for msg in self.current_session.messages:
            if query.lower() in msg.content.lower():
                results.append(msg)
                
        if not results:
            self.console.print("[yellow]No matches found[/yellow]")
            return
            
        self.console.print(f"\n[bold]Found {len(results)} matches:[/bold]\n")
        for msg in results[:20]:
            preview = msg.content[:100] + ("..." if len(msg.content) > 100 else "")
            role_icon = "👤" if msg.role == "user" else "🤖"
            self.console.print(f"  {role_icon} {preview}")
            
    async def _cmd_session_stats(self):
        """Show session statistics."""
        msgs = self.current_session.messages
        user_msgs = [m for m in msgs if m.role == "user"]
        asst_msgs = [m for m in msgs if m.role == "assistant"]
        total_chars = sum(len(m.content) for m in msgs)
        
        stats = Table(box=box.SIMPLE, show_header=False)
        stats.add_column("Metric", style="cyan")
        stats.add_column("Value", style="white")
        stats.add_row("Total Messages", str(len(msgs)))
        stats.add_row("User Messages", str(len(user_msgs)))
        stats.add_row("Assistant Messages", str(len(asst_msgs)))
        stats.add_row("Total Characters", f"{total_chars:,}")
        stats.add_row("Avg Message Length", f"{total_chars // max(len(msgs), 1):,} chars")
        stats.add_row("Created", self.current_session.created_at[:19] if self.current_session.created_at else "Unknown")
        stats.add_row("Updated", self.current_session.updated_at[:19] if self.current_session.updated_at else "Unknown")
        
        self.console.print(Panel(stats, title="📊 Session Stats", border_style="blue", box=box.ROUNDED))
        
    async def _cmd_chat_help(self):
        """Show chat help."""
        help_text = """
[bold cyan]Chat Commands:[/bold cyan]
  /new              - Create new session
  /clear            - Clear current session messages
  /save             - Save session manually
  /history          - Show full conversation history
  /sessions         - List all sessions
  /switch [id]      - Switch to another session
  /persona [text]   - Set/change system prompt
  /model [name]     - Set/change model
  /export [format]  - Export session (json/md/txt)
  /import [file]    - Import session
  /search [query]   - Search message history
  /stats            - Show session statistics
  /tools            - Open tools menu
  /analyze [file]   - Analyze a file with Hermes
  /code [prompt]    - Generate code
  /review [code]    - Code review
  /help             - Show this help
  /quit, /exit, /q  - Exit chat mode

[bold cyan]Keyboard Shortcuts:[/bold cyan]
  Ctrl+N  - New session
  Ctrl+S  - Save session
  Ctrl+L  - List sessions
  Ctrl+H  - History
  Ctrl+E  - Export
  Ctrl+P  - Persona
  Ctrl+M  - Model
  Ctrl+F  - File analysis
  Ctrl+C  - Copy last response
  Ctrl+Q  - Quit
        """
        self.console.print(Panel(help_text, title="❓ Chat Help", border_style="blue", box=box.ROUNDED))
        
    async def _cmd_tools_menu(self):
        """Open tools submenu."""
        await self._tools_menu()
        
    async def _cmd_analyze_file(self, filepath: str):
        """Analyze file with Hermes."""
        if not filepath:
            filepath = Prompt.ask("File path on remote server")
            
        self.console.print(f"[cyan]Analyzing {filepath}...[/cyan]")
        cmd = f'hermes analyze "{filepath}"'
        result = await self.client.execute_simple(cmd, timeout=60)
        
        if result.stdout:
            self.console.print(Panel(
                Markdown(result.stdout) if self._looks_like_markdown(result.stdout) else result.stdout,
                title=f"📄 Analysis: {filepath}",
                border_style="green",
                box=box.ROUNDED
            ))
        else:
            self.console.print("[red]No output[/red]")
            
    async def _cmd_generate_code(self, prompt: str):
        """Generate code with Hermes."""
        if not prompt:
            prompt = Prompt.ask("Code generation prompt")
            
        self.console.print(f"[cyan]Generating code...[/cyan]")
        cmd = f'hermes code -q "{prompt}"'
        result = await self.client.execute_simple(cmd, timeout=60)
        
        if result.stdout:
            self.console.print(Panel(
                Markdown(result.stdout),
                title="💻 Generated Code",
                border_style="green",
                box=box.ROUNDED
            ))
            
    async def _cmd_code_review(self, code: str):
        """Code review with Hermes."""
        if not code:
            code = Prompt.ask("Code to review (or file path)")
            
        # Check if it's a file path
        if "\n" not in code and ("." in code or "/" in code):
            # Likely a file path
            result = await self.client.execute_simple(f'cat "{code}"', timeout=10)
            if result.exit_code == 0:
                code = result.stdout
                
        self.console.print("[cyan]Reviewing code...[/cyan]")
        cmd = f'hermes review -q "{code}"'
        result = await self.client.execute_simple(cmd, timeout=60)
        
        if result.stdout:
            self.console.print(Panel(
                Markdown(result.stdout),
                title="🔍 Code Review",
                border_style="green",
                box=box.ROUNDED
            ))
            
    # ─── Session Management ──────────────────────────────────────────
    
    async def _select_or_create_session(self):
        """Select existing or create new session."""
        if not self.sessions:
            name = Prompt.ask("No sessions exist. Create first session name", default="Default Chat")
            await self._create_session(name)
            return
            
        await self._list_sessions_display()
        
        choices = ["new"] + list(self.sessions.keys())
        choice = Prompt.ask("Select session ID or 'new'", choices=choices, default="new")
        
        if choice == "new":
            name = Prompt.ask("Session name", default=f"Chat {len(self.sessions) + 1}")
            await self._create_session(name)
        else:
            self.current_session = self.sessions[choice]
            self.console.print(f"[green]Loaded: {self.current_session.name}[/green]")
            
    async def _create_session(self, name: str):
        """Create new session."""
        session_id = self._generate_session_id()
        now = datetime.datetime.now().isoformat()
        
        session = HermesSession(
            id=session_id,
            name=name,
            created_at=now,
            updated_at=now,
            messages=[],
            system_prompt="",
            model="default",
        )
        
        self.sessions[session_id] = session
        self.current_session = session
        self._save_session(session)
        self.console.print(f"[green]✓ Created session: {name}[/green]")
        
    async def _sessions_menu(self):
        """Sessions management menu."""
        while True:
            self.console.clear()
            self._print_banner()
            
            await self._list_sessions_display()
            
            self.console.print()
            options = [
                ("1", "➕ New Session", "Create new chat session"),
                ("2", "🔄 Switch Session", "Switch to different session"),
                ("3", "✏️  Rename Session", "Rename selected session"),
                ("4", "🗑️  Delete Session", "Delete session permanently"),
                ("5", "📋 Duplicate Session", "Copy session"),
                ("6", "📤 Export Session", "Export to file"),
                ("7", "📥 Import Session", "Import from file"),
                ("0", "⬅️  Back", "Return to main menu"),
            ]
            
            table = Table(box=box.SIMPLE)
            table.add_column("Key", style="cyan", width=6)
            table.add_column("Action", style="white", width=20)
            table.add_column("Description", style="dim")
            for k, a, d in options:
                table.add_row(k, a, d)
                
            self.console.print(Panel(table, title="📋 Sessions", border_style="green", box=box.ROUNDED))
            
            choice = Prompt.ask("Select", choices=[o[0] for o in options], default="0")
            
            if choice == "0":
                break
            elif choice == "1":
                name = Prompt.ask("Session name", default=f"Chat {len(self.sessions) + 1}")
                await self._create_session(name)
            elif choice == "2":
                await self._cmd_switch_session()
            elif choice == "3":
                await self._rename_session()
            elif choice == "4":
                await self._delete_session()
            elif choice == "5":
                await self._duplicate_session()
            elif choice == "6":
                await self._export_session_menu()
            elif choice == "7":
                await self._import_session()
                
    async def _list_sessions_display(self):
        """Display sessions in a nice table."""
        if not self.sessions:
            self.console.print(Panel("[dim]No sessions yet. Create one to get started![/dim]", 
                                   title="📋 Sessions", border_style="yellow", box=box.ROUNDED))
            return
            
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
        table.add_column("ID", style="dim", width=25)
        table.add_column("Name", style="bold white", width=25)
        table.add_column("Messages", style="green", justify="right", width=10)
        table.add_column("Model", style="cyan", width=15)
        table.add_column("Persona", style="dim", width=30)
        table.add_column("Updated", style="dim", width=20)
        table.add_column("Status", style="bold", width=10)
        
        for session in sorted(self.sessions.values(), key=lambda s: s.updated_at, reverse=True):
            is_current = "🟢 Current" if self.current_session and session.id == self.current_session.id else ""
            persona_preview = session.system_prompt[:28] + "..." if len(session.system_prompt) > 30 else session.system_prompt
            table.add_row(
                session.id[:22] + "...",
                session.name,
                str(len(session.messages)),
                session.model,
                persona_preview or "[dim]None[/dim]",
                session.updated_at[:19] if session.updated_at else "—",
                is_current,
            )
            
        self.console.print(Panel(table, title=f"📋 Sessions ({len(self.sessions)})", border_style="blue", box=box.ROUNDED))
        
    async def _rename_session(self):
        """Rename a session."""
        await self._list_sessions_display()
        session_id = Prompt.ask("Session ID to rename")
        
        if session_id in self.sessions:
            session = self.sessions[session_id]
            new_name = Prompt.ask("New name", default=session.name)
            session.name = new_name
            session.updated_at = datetime.datetime.now().isoformat()
            self._save_session(session)
            self.console.print("[green]Session renamed[/green]")
        else:
            self.console.print("[red]Session not found[/red]")
            
    async def _delete_session(self):
        """Delete a session."""
        await self._list_sessions_display()
        session_id = Prompt.ask("Session ID to delete")
        
        if session_id in self.sessions:
            session = self.sessions[session_id]
            if Confirm.ask(f"Delete '{session.name}' permanently?"):
                # Delete file
                sessions_dir = Path.home() / ".config" / "remote-agent" / "hermes_sessions"
                session_file = sessions_dir / f"{session_id}.json"
                if session_file.exists():
                    session_file.unlink()
                    
                del self.sessions[session_id]
                if self.current_session and self.current_session.id == session_id:
                    self.current_session = None
                self.console.print("[green]Session deleted[/green]")
        else:
            self.console.print("[red]Session not found[/red]")
            
    async def _duplicate_session(self):
        """Duplicate a session."""
        await self._list_sessions_display()
        session_id = Prompt.ask("Session ID to duplicate")
        
        if session_id in self.sessions:
            original = self.sessions[session_id]
            new_id = self._generate_session_id()
            now = datetime.datetime.now().isoformat()
            
            new_session = HermesSession(
                id=new_id,
                name=f"{original.name} (copy)",
                created_at=now,
                updated_at=now,
                messages=original.messages.copy(),
                system_prompt=original.system_prompt,
                model=original.model,
                metadata=original.metadata.copy() if original.metadata else {},
            )
            
            self.sessions[new_id] = new_session
            self._save_session(new_session)
            self.console.print(f"[green]Duplicated as: {new_session.name}[/green]")
        else:
            self.console.print("[red]Session not found[/red]")
            
    # ─── Personas Menu ───────────────────────────────────────────────
    
    async def _personas_menu(self):
        """Personas/System prompts management."""
        # Built-in personas
        builtin_personas = {
            "default": "You are a helpful AI assistant.",
            "coder": "You are an expert software engineer. Write clean, efficient, well-documented code. Follow best practices and design patterns.",
            "reviewer": "You are a senior code reviewer. Analyze code for bugs, security issues, performance problems, and style violations. Provide constructive feedback with specific suggestions.",
            "teacher": "You are a patient teacher. Explain concepts clearly with examples. Break down complex topics into simple steps.",
            "architect": "You are a software architect. Design scalable, maintainable systems. Consider trade-offs, patterns, and long-term implications.",
            "debugger": "You are a debugging expert. Help find and fix bugs systematically. Ask clarifying questions when needed.",
            "writer": "You are a technical writer. Create clear, concise documentation, READMEs, and guides.",
            "devops": "You are a DevOps engineer. Help with CI/CD, infrastructure, containers, monitoring, and automation.",
            "security": "You are a security expert. Identify vulnerabilities, suggest secure coding practices, and explain security concepts.",
            "custom": "Custom persona...",
        }
        
        while True:
            self.console.clear()
            self._print_banner()
            
            # Current persona
            current = self.current_session.system_prompt if self.current_session else "None"
            preview = current[:80] + "..." if len(current) > 80 else current
            self.console.print(Panel(
                f"[bold]Current:[/bold] {preview or '[dim]None (using default)[/dim]'}",
                title="🎭 Active Persona",
                border_style="cyan",
                box=box.ROUNDED
            ))
            
            # Persona list
            table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
            table.add_column("#", style="dim", width=4)
            table.add_column("Persona", style="white", width=20)
            table.add_column("Description", style="dim", width=60)
            
            for i, (key, prompt) in enumerate(builtin_personas.items(), 1):
                desc = prompt[:70] + "..." if len(prompt) > 70 else prompt
                marker = " ✓" if self.current_session and self.current_session.system_prompt == prompt else ""
                table.add_row(str(i), key.capitalize() + marker, desc)
                
            self.console.print(Panel(table, title="📚 Available Personas", border_style="blue", box=box.ROUNDED))
            
            # Custom personas from saved sessions
            custom_personas = {}
            for session in self.sessions.values():
                if session.system_prompt and session.system_prompt not in builtin_personas.values():
                    custom_personas[session.name] = session.system_prompt
                    
            if custom_personas:
                self.console.print()
                custom_table = Table(box=box.SIMPLE, show_header=True, header_style="bold magenta")
                custom_table.add_column("#", style="dim", width=4)
                custom_table.add_column("Custom Persona", style="white", width=25)
                custom_table.add_column("Preview", style="dim", width=60)
                
                for i, (name, prompt) in enumerate(custom_personas.items(), 1):
                    preview = prompt[:70] + "..." if len(prompt) > 70 else prompt
                    custom_table.add_row(str(i), name, preview)
                    
                self.console.print(Panel(custom_table, title="✨ Custom Personas (from sessions)", border_style="magenta", box=box.ROUNDED))
            
            self.console.print()
            self.console.print("[dim]Enter number to select, 'e' to edit custom, 'd' to delete custom, 'b' for back[/dim]")
            choice = Prompt.ask("Select", default="b")
            
            if choice.lower() == "b":
                break
            elif choice.lower() == "e":
                await self._edit_custom_persona(custom_personas)
            elif choice.lower() == "d":
                await self._delete_custom_persona(custom_personas)
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(builtin_personas):
                    key = list(builtin_personas.keys())[idx]
                    if key == "custom":
                        await self._create_custom_persona()
                    else:
                        await self._apply_persona(builtin_personas[key])
                elif custom_personas and idx < len(builtin_personas) + len(custom_personas):
                    custom_idx = idx - len(builtin_personas)
                    name = list(custom_personas.keys())[custom_idx]
                    await self._apply_persona(custom_personas[name])
                    
    async def _apply_persona(self, prompt: str):
        """Apply persona to current session."""
        if not self.current_session:
            self.console.print("[red]No active session[/red]")
            return
            
        self.current_session.system_prompt = prompt
        self.current_session.updated_at = datetime.datetime.now().isoformat()
        self._save_session(self.current_session)
        self.console.print("[green]Persona applied![/green]")
        
    async def _create_custom_persona(self):
        """Create new custom persona."""
        name = Prompt.ask("Persona name")
        self.console.print("[dim]Enter system prompt (empty line to finish):[/dim]")
        lines = []
        while True:
            line = Prompt.ask(">", default="")
            if not line:
                break
            lines.append(line)
            
        if lines:
            prompt = "\n".join(lines)
            # Save as a special session
            session_id = self._generate_session_id()
            now = datetime.datetime.now().isoformat()
            session = HermesSession(
                id=session_id,
                name=f"🎭 Persona: {name}",
                created_at=now,
                updated_at=now,
                messages=[],
                system_prompt=prompt,
                model="default",
                metadata={"type": "persona"},
            )
            self.sessions[session_id] = session
            self._save_session(session)
            self.console.print("[green]Custom persona saved![/green]")
            
    async def _edit_custom_persona(self, custom_personas: Dict):
        """Edit custom persona."""
        if not custom_personas:
            self.console.print("[yellow]No custom personas[/yellow]")
            return
            
        name = Prompt.ask("Persona name to edit", choices=list(custom_personas.keys()))
        if name in custom_personas:
            session_id = None
            for sid, session in self.sessions.items():
                if session.name == f"🎭 Persona: {name}" or session.name == name:
                    session_id = sid
                    break
                    
            if session_id:
                session = self.sessions[session_id]
                self.console.print("[dim]Current prompt:[/dim]")
                self.console.print(session.system_prompt)
                self.console.print("[dim]Enter new prompt (empty line to finish):[/dim]")
                lines = []
                while True:
                    line = Prompt.ask(">", default="")
                    if not line:
                        break
                    lines.append(line)
                    
                if lines:
                    session.system_prompt = "\n".join(lines)
                    session.updated_at = datetime.datetime.now().isoformat()
                    self._save_session(session)
                    self.console.print("[green]Persona updated![/green]")
                    
    async def _delete_custom_persona(self, custom_personas: Dict):
        """Delete custom persona."""
        if not custom_personas:
            return
            
        name = Prompt.ask("Persona name to delete", choices=list(custom_personas.keys()))
        if Confirm.ask(f"Delete persona '{name}'?"):
            for sid, session in list(self.sessions.items()):
                if session.name == f"🎭 Persona: {name}" or session.name == name:
                    sessions_dir = Path.home() / ".config" / "remote-agent" / "hermes_sessions"
                    session_file = sessions_dir / f"{sid}.json"
                    if session_file.exists():
                        session_file.unlink()
                    del self.sessions[sid]
                    break
            self.console.print("[green]Persona deleted[/green]")
            
    # ─── Tools Menu ──────────────────────────────────────────────────
    
    async def _tools_menu(self):
        """Tools and utilities menu."""
        while True:
            self.console.clear()
            self._print_banner()
            
            tools = [
                ("1", "📄 File Analysis", "Analyze any file on remote server", self._tool_file_analysis),
                ("2", "💻 Code Generation", "Generate code from description", self._tool_code_generation),
                ("3", "🔍 Code Review", "Review code for issues", self._tool_code_review),
                ("4", "🐛 Debug Assistant", "Help debug errors/logs", self._tool_debug_assistant),
                ("5", "📝 Documentation", "Generate docs/README", self._tool_documentation),
                ("6", "🧪 Test Generation", "Generate unit tests", self._tool_test_generation),
                ("7", "🔧 Refactoring", "Refactor/improve code", self._tool_refactoring),
                ("8", "🌐 Web Search", "Search via Hermes (if enabled)", self._tool_web_search),
                ("9", "📊 Data Analysis", "Analyze data/CSV/JSON", self._tool_data_analysis),
                ("10", "🎨 Diagram/Chart", "Generate mermaid/plantuml", self._tool_diagram),
                ("0", "⬅️ Back", "Return to main menu", None),
            ]
            
            table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
            table.add_column("Key", style="cyan", width=6)
            table.add_column("Tool", style="white", width=22)
            table.add_column("Description", style="dim")
            for k, n, d, _ in tools:
                table.add_row(k, n, d)
                
            self.console.print(Panel(table, title="🔧 Hermes Tools", border_style="green", box=box.ROUNDED))
            
            choice = Prompt.ask("Select tool", choices=[t[0] for t in tools], default="0")
            
            if choice == "0":
                break
                
            for k, n, d, func in tools:
                if k == choice and func:
                    await func()
                    Prompt.ask("\n[dim]Press Enter to continue[/dim]")
                    break
                    
    async def _run_hermes_tool(self, tool_name: str, prompt: str, title: str):
        """Run a Hermes tool command."""
        self.console.print(f"[cyan]Running {tool_name}...[/cyan]")
        cmd = f'hermes {tool_name} -q "{prompt}"'
        if self.current_session and self.current_session.system_prompt:
            cmd += f' --system "{self.current_session.system_prompt}"'
            
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
            task = progress.add_task(f"Hermes {tool_name}...", total=None)
            result = await self.client.execute_simple(cmd, timeout=self.config["timeout"])
            progress.remove_task(task)
            
        if result.stdout:
            self.console.print(Panel(
                Markdown(result.stdout) if self._looks_like_markdown(result.stdout) else result.stdout,
                title=title,
                border_style="green",
                box=box.ROUNDED
            ))
        else:
            self.console.print("[red]No output[/red]")
        return result.stdout
        
    async def _tool_file_analysis(self):
        filepath = Prompt.ask("File path on remote server")
        await self._run_hermes_tool("analyze", filepath, f"📄 Analysis: {filepath}")
        
    async def _tool_code_generation(self):
        prompt = Prompt.ask("Describe what code to generate")
        await self._run_hermes_tool("code", prompt, "💻 Generated Code")
        
    async def _tool_code_review(self):
        code = Prompt.ask("Code to review (or file path)")
        # Check if file
        if "\n" not in code and ("." in code or "/" in code):
            result = await self.client.execute_simple(f'cat "{code}"', timeout=10)
            if result.exit_code == 0:
                code = result.stdout
        await self._run_hermes_tool("review", code, "🔍 Code Review")
        
    async def _tool_debug_assistant(self):
        error = Prompt.ask("Error message, log, or description of bug")
        await self._run_hermes_tool("debug", error, "🐛 Debug Assistant")
        
    async def _tool_documentation(self):
        target = Prompt.ask("What to document (code, API, project, file path)")
        await self._run_hermes_tool("doc", target, "📝 Documentation")
        
    async def _tool_test_generation(self):
        code = Prompt.ask("Code to generate tests for (or file path)")
        if "\n" not in code and ("." in code or "/" in code):
            result = await self.client.execute_simple(f'cat "{code}"', timeout=10)
            if result.exit_code == 0:
                code = result.stdout
        await self._run_hermes_tool("test", code, "🧪 Generated Tests")
        
    async def _tool_refactoring(self):
        code = Prompt.ask("Code to refactor (or file path)")
        if "\n" not in code and ("." in code or "/" in code):
            result = await self.client.execute_simple(f'cat "{code}"', timeout=10)
            if result.exit_code == 0:
                code = result.stdout
        await self._run_hermes_tool("refactor", code, "🔧 Refactored Code")
        
    async def _tool_web_search(self):
        query = Prompt.ask("Search query")
        await self._run_hermes_tool("search", query, "🌐 Search Results")
        
    async def _tool_data_analysis(self):
        filepath = Prompt.ask("Data file path (CSV, JSON, etc.)")
        question = Prompt.ask("Analysis question")
        prompt = f"File: {filepath}\nQuestion: {question}"
        await self._run_hermes_tool("analyze", prompt, "📊 Data Analysis")
        
    async def _tool_diagram(self):
        desc = Prompt.ask("Describe the diagram/architecture")
        await self._run_hermes_tool("diagram", desc, "🎨 Generated Diagram")
        
    # ─── Export/Import ───────────────────────────────────────────────
    
    async def _export_menu(self):
        """Export/Import menu."""
        while True:
            self.console.clear()
            self._print_banner()
            
            options = [
                ("1", "📤 Export Current Session", "Export active session"),
                ("2", "📤 Export All Sessions", "Backup all sessions"),
                ("3", "📥 Import Session", "Import from file"),
                ("4", "☁️  Sync to Remote", "Save session on remote server"),
                ("5", "📥 Pull from Remote", "Load session from remote"),
                ("0", "⬅️ Back", "Return to main menu"),
            ]
            
            table = Table(box=box.SIMPLE)
            table.add_column("Key", style="cyan", width=6)
            table.add_column("Action", style="white", width=25)
            table.add_column("Description", style="dim")
            for k, a, d in options:
                table.add_row(k, a, d)
                
            self.console.print(Panel(table, title="📤 Export/Import", border_style="blue", box=box.ROUNDED))
            
            choice = Prompt.ask("Select", choices=[o[0] for o in options], default="0")
            
            if choice == "0":
                break
            elif choice == "1":
                await self._export_session(self.current_session)
            elif choice == "2":
                await self._export_all_sessions()
            elif choice == "3":
                await self._import_session()
            elif choice == "4":
                await self._sync_to_remote()
            elif choice == "5":
                await self._pull_from_remote()
                
    async def _export_session(self, session: HermesSession = None, format: str = None):
        """Export session to file."""
        if not session:
            session = self.current_session
            
        if not session:
            self.console.print("[red]No session to export[/red]")
            return
            
        if not format:
            format = Prompt.ask("Format", choices=["json", "md", "txt"], default="json")
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hermes_{session.name}_{timestamp}.{format}"
        filepath = Path.cwd() / filename
        
        try:
            if format == "json":
                data = {
                    "id": session.id,
                    "name": session.name,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                    "system_prompt": session.system_prompt,
                    "model": session.model,
                    "messages": [asdict(m) for m in session.messages],
                }
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    
            elif format == "md":
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# {session.name}\n\n")
                    f.write(f"**ID:** {session.id}  \n")
                    f.write(f"**Created:** {session.created_at}  \n")
                    f.write(f"**Updated:** {session.updated_at}  \n")
                    f.write(f"**Model:** {session.model}  \n")
                    if session.system_prompt:
                        f.write(f"**System Prompt:** {session.system_prompt}  \n")
                    f.write("\n---\n\n")
                    
                    for msg in session.messages:
                        role = "## 👤 You" if msg.role == "user" else "## 🤖 Hermes"
                        f.write(f"{role} ({msg.timestamp[:19]})\n\n")
                        f.write(f"{msg.content}\n\n---\n\n")
                        
            elif format == "txt":
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"{session.name}\n")
                    f.write(f"ID: {session.id}\n")
                    f.write(f"Created: {session.created_at}\n\n")
                    for msg in session.messages:
                        role = "YOU" if msg.role == "user" else "HERMES"
                        f.write(f"[{msg.timestamp[:19]}] {role}:\n{msg.content}\n\n")
                        
            self.console.print(f"[green]✓ Exported to {filepath}[/green]")
            
        except Exception as e:
            self.console.print(f"[red]Export failed: {e}[/red]")
            
    async def _export_all_sessions(self):
        """Export all sessions as a single backup."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hermes_backup_{timestamp}.json"
        filepath = Path.cwd() / filename
        
        try:
            data = {
                "version": "2.0",
                "exported_at": datetime.datetime.now().isoformat(),
                "sessions": {}
            }
            
            for sid, session in self.sessions.items():
                data["sessions"][sid] = {
                    "id": session.id,
                    "name": session.name,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                    "system_prompt": session.system_prompt,
                    "model": session.model,
                    "messages": [asdict(m) for m in session.messages],
                    "metadata": session.metadata,
                }
                
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            self.console.print(f"[green]✓ All sessions backed up to {filepath}[/green]")
            self.console.print(f"  Sessions: {len(self.sessions)}")
            
        except Exception as e:
            self.console.print(f"[red]Backup failed: {e}[/red]")
            
    async def _import_session(self, filepath: str = None):
        """Import session from file."""
        if not filepath:
            filepath = Prompt.ask("Import file path")
            
        path = Path(filepath).expanduser()
        if not path.exists():
            self.console.print("[red]File not found[/red]")
            return
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Handle both single session and backup format
            if "sessions" in data:
                # Backup format
                imported = 0
                for sid, session_data in data["sessions"].items():
                    if sid not in self.sessions:
                        session = HermesSession(
                            id=session_data["id"],
                            name=session_data["name"],
                            created_at=session_data["created_at"],
                            updated_at=session_data["updated_at"],
                            messages=[HermesMessage(**m) for m in session_data["messages"]],
                            system_prompt=session_data.get("system_prompt", ""),
                            model=session_data.get("model", "default"),
                            metadata=session_data.get("metadata", {}),
                        )
                        self.sessions[sid] = session
                        self._save_session(session)
                        imported += 1
                self.console.print(f"[green]✓ Imported {imported} sessions[/green]")
            else:
                # Single session
                session = HermesSession(
                    id=data["id"],
                    name=data["name"],
                    created_at=data["created_at"],
                    updated_at=data["updated_at"],
                    messages=[HermesMessage(**m) for m in data["messages"]],
                    system_prompt=data.get("system_prompt", ""),
                    model=data.get("model", "default"),
                    metadata=data.get("metadata", {}),
                )
                self.sessions[session.id] = session
                self._save_session(session)
                self.console.print(f"[green]✓ Imported: {session.name}[/green]")
                
        except Exception as e:
            self.console.print(f"[red]Import failed: {e}[/red]")
            
    async def _sync_to_remote(self):
        """Save current session to remote server."""
        if not self.current_session:
            self.console.print("[red]No active session[/red]")
            return
            
        # Save as file on remote
        session_data = {
            "id": self.current_session.id,
            "name": self.current_session.name,
            "created_at": self.current_session.created_at,
            "updated_at": self.current_session.updated_at,
            "system_prompt": self.current_session.system_prompt,
            "model": self.current_session.model,
            "messages": [asdict(m) for m in self.current_session.messages],
        }
        
        json_data = json.dumps(session_data, ensure_ascii=False)
        # Use base64 to safely transfer
        import base64
        encoded = base64.b64encode(json_data.encode()).decode()
        
        cmd = f'echo "{encoded}" | base64 -d > ~/hermes_session_{self.current_session.id}.json'
        result = await self.client.execute_simple(cmd)
        
        if result.exit_code == 0:
            self.console.print("[green]✓ Session saved to remote server[/green]")
        else:
            self.console.print(f"[red]Failed: {result.stderr}[/red]")
            
    async def _pull_from_remote(self):
        """Load session from remote server."""
        # List remote session files
        result = await self.client.execute_simple("ls ~/hermes_session_*.json 2>/dev/null || echo 'NONE'")
        
        if "NONE" in result.stdout or not result.stdout.strip():
            self.console.print("[yellow]No session files on remote[/yellow]")
            return
            
        files = result.stdout.strip().split("\n")
        self.console.print("[bold]Remote sessions:[/bold]")
        for f in files:
            self.console.print(f"  {f}")
            
        filename = Prompt.ask("Filename to pull (or 'all')")
        
        if filename == "all":
            for f in files:
                await self._pull_single_session(f)
        else:
            await self._pull_single_session(filename)
            
    async def _pull_single_session(self, filepath: str):
        """Pull single session file from remote."""
        import base64
        # Read and encode on remote
        cmd = f'base64 -w 0 "{filepath}"'
        result = await self.client.execute_simple(cmd)
        
        if result.exit_code == 0 and result.stdout:
            try:
                json_data = base64.b64decode(result.stdout).decode()
                data = json.loads(json_data)
                
                session = HermesSession(
                    id=data["id"],
                    name=data["name"],
                    created_at=data["created_at"],
                    updated_at=data["updated_at"],
                    messages=[HermesMessage(**m) for m in data["messages"]],
                    system_prompt=data.get("system_prompt", ""),
                    model=data.get("model", "default"),
                )
                
                if session.id not in self.sessions:
                    self.sessions[session.id] = session
                    self._save_session(session)
                    self.console.print(f"[green]✓ Pulled: {session.name}[/green]")
                else:
                    self.console.print(f"[yellow]Session already exists locally[/yellow]")
                    
            except Exception as e:
                self.console.print(f"[red]Failed to parse: {e}[/red]")
                
    # ─── Settings ────────────────────────────────────────────────────
    
    async def _settings_menu(self):
        """Settings configuration."""
        while True:
            self.console.clear()
            self._print_banner()
            
            # Current settings display
            settings_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
            settings_table.add_column("Setting", style="cyan", width=30)
            settings_table.add_column("Value", style="white")
            settings_table.add_column("Description", style="dim")
            
            settings = [
                ("stream", self.config["stream"], "Stream responses in real-time"),
                ("timeout", f"{self.config['timeout']}s", "Command timeout"),
                ("auto_save", self.config["auto_save"], "Auto-save after each response"),
                ("show_timestamps", self.config["show_timestamps"], "Show message timestamps"),
                ("syntax_theme", self.config["syntax_theme"], "Code syntax highlighting theme"),
                ("max_history_display", str(self.config["max_history_display"]), "Max messages to display"),
            ]
            
            for key, value, desc in settings:
                settings_table.add_row(key, str(value), desc)
                
            self.console.print(Panel(settings_table, title="⚙️ Current Settings", border_style="blue", box=box.ROUNDED))
            
            options = [
                ("1", "🔄 Toggle Streaming", "stream"),
                ("2", "⏱️  Change Timeout", "timeout"),
                ("3", "💾 Toggle Auto-save", "auto_save"),
                ("4", "🕐 Toggle Timestamps", "show_timestamps"),
                ("5", "🎨 Syntax Theme", "syntax_theme"),
                ("6", "📜 Max History", "max_history_display"),
                ("7", "🗑️  Clear All Sessions", "clear_all"),
                ("8", "🔄 Reset to Defaults", "reset"),
                ("0", "⬅️ Back", None),
            ]
            
            menu_table = Table(box=box.SIMPLE)
            menu_table.add_column("Key", style="cyan", width=6)
            menu_table.add_column("Action", style="white")
            for k, a, _ in options:
                menu_table.add_row(k, a)
                
            self.console.print(Panel(menu_table, title="Settings", border_style="green", box=box.ROUNDED))
            
            choice = Prompt.ask("Select", choices=[o[0] for o in options], default="0")
            
            if choice == "0":
                break
            elif choice == "1":
                self.config["stream"] = not self.config["stream"]
                self.console.print(f"[green]Streaming: {'On' if self.config['stream'] else 'Off'}[/green]")
            elif choice == "2":
                try:
                    val = int(Prompt.ask("Timeout (seconds)", default=str(self.config["timeout"])))
                    self.config["timeout"] = max(10, min(600, val))
                    self.console.print(f"[green]Timeout: {self.config['timeout']}s[/green]")
                except ValueError:
                    self.console.print("[red]Invalid number[/red]")
            elif choice == "3":
                self.config["auto_save"] = not self.config["auto_save"]
                self.console.print(f"[green]Auto-save: {'On' if self.config['auto_save'] else 'Off'}[/green]")
            elif choice == "4":
                self.config["show_timestamps"] = not self.config["show_timestamps"]
                self.console.print(f"[green]Timestamps: {'On' if self.config['show_timestamps'] else 'Off'}[/green]")
            elif choice == "5":
                themes = ["monokai", "github", "dracula", "solarized-dark", "solarized-light", "one-dark", "vim"]
                theme = Prompt.ask("Theme", choices=themes, default=self.config["syntax_theme"])
                self.config["syntax_theme"] = theme
                self.console.print(f"[green]Theme: {theme}[/green]")
            elif choice == "6":
                try:
                    val = int(Prompt.ask("Max messages", default=str(self.config["max_history_display"])))
                    self.config["max_history_display"] = max(10, min(500, val))
                    self.console.print(f"[green]Max history: {self.config['max_history_display']}[/green]")
                except ValueError:
                    self.console.print("[red]Invalid number[/red]")
            elif choice == "7":
                if Confirm.ask("[red]Delete ALL sessions permanently?[/red]"):
                    sessions_dir = Path.home() / ".config" / "remote-agent" / "hermes_sessions"
                    for f in sessions_dir.glob("*.json"):
                        f.unlink()
                    self.sessions.clear()
                    self.current_session = None
                    self.console.print("[green]All sessions cleared[/green]")
            elif choice == "8":
                self.config = {
                    "stream": True,
                    "timeout": 120,
                    "auto_save": True,
                    "show_timestamps": True,
                    "syntax_theme": "monokai",
                    "max_history_display": 50,
                }
                self.console.print("[green]Settings reset to defaults[/green]")
                
    # ─── Help ────────────────────────────────────────────────────────
    
    async def _show_help(self):
        """Show comprehensive help."""
        self.console.clear()
        self._print_banner()
        
        help_sections = [
            ("🎯 Main Menu", """
1-7: Navigate main features
0: Exit to main agent menu
"""),
            ("💬 Chat Mode", """
• Type naturally to chat with Hermes
• Commands start with /
• Streaming responses by default
• Sessions auto-saved
"""),
            ("⌨️ Keyboard Shortcuts", "\n".join([f"  {k}: {v}" for k, v in self.shortcuts.items()])),
            ("📋 Chat Commands", """
  /new          - New session
  /clear        - Clear messages
  /save         - Save session
  /history      - Full history
  /sessions     - List sessions
  /switch [id]  - Switch session
  /persona [t]  - Set persona
  /model [name] - Set model
  /export [fmt] - Export (json/md/txt)
  /import [file]- Import session
  /search [q]   - Search messages
  /stats        - Session stats
  /analyze [f]  - Analyze file
  /code [p]     - Generate code
  /review [c]   - Code review
  /help         - This help
  /quit         - Exit chat
"""),
            ("🎭 Personas", """
Built-in: default, coder, reviewer, teacher, architect, debugger, writer, devops, security
Custom: Create your own from sessions
"""),
            ("🔧 Tools", """
File Analysis, Code Generation, Code Review, Debug Assistant,
Documentation, Test Generation, Refactoring, Web Search,
Data Analysis, Diagram Generation
"""),
            ("📤 Export Formats", """
JSON: Full backup with metadata
Markdown: Human-readable, renders on GitHub
Text: Plain text for simple viewing
"""),
        ]
        
        for title, content in help_sections:
            self.console.print(Panel(content.strip(), title=title, border_style="blue", box=box.ROUNDED))
            
        Prompt.ask("\n[dim]Press Enter to continue[/dim]")
        
    # ─── Session Export (called from chat) ──────────────────────────
    
    async def _export_session_menu(self):
        """Export session from sessions menu."""
        await self._list_sessions_display()
        session_id = Prompt.ask("Session ID to export (or 'current')")
        
        if session_id == "current" and self.current_session:
            await self._export_session(self.current_session)
        elif session_id in self.sessions:
            await self._export_session(self.sessions[session_id])
        else:
            self.console.print("[red]Session not found[/red]")


# ─── Integration with main client ──────────────────────────────────

async def run_hermes_panel(client):
    """Entry point to run Hermes panel from main menu."""
    panel = HermesPanel(client)
    await panel.run()