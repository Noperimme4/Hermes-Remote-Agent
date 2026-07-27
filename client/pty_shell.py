"""
PTY Shell Client - Interactive terminal emulation
"""

import asyncio
import os
import sys
import termios
import tty
import signal
import struct
import fcntl
import base64
from typing import Optional, Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.prompt import Prompt


class PTYShell:
    """Interactive PTY shell client."""
    
    def __init__(self, client):
        self.client = client
        self.console = Console()
        self.shell_id: Optional[str] = None
        self.running = False
        self.cols = 80
        self.rows = 24
        self._old_term_settings = None
    
    async def run(self, cwd: str = None):
        """Run interactive PTY shell."""
        self.console.print("[cyan]Starting PTY shell...[/cyan]")
        
        try:
            # Start shell on server
            self.shell_id = await self.client.start_pty_shell(
                cols=self.cols,
                rows=self.rows,
                cwd=cwd
            )
            self.console.print(f"[green]✓ Shell started (ID: {self.shell_id[:8]}...)[/green]")
            
            # Setup local terminal
            self._setup_terminal()
            
            # Start reader task
            self.running = True
            reader_task = asyncio.create_task(self._reader_loop())
            
            # Main input loop
            await self._input_loop()
            
            # Cleanup
            self.running = False
            reader_task.cancel()
            try:
                await reader_task
            except asyncio.CancelledError:
                pass
            
        except Exception as e:
            self.console.print(f"[red]Shell error: {e}[/red]")
        finally:
            self._restore_terminal()
            if self.shell_id:
                await self.client.close_pty(self.shell_id)
    
    def _setup_terminal(self):
        """Setup terminal for raw input."""
        self._old_term_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())
        
        # Set window size
        self._update_window_size()
        
        # Handle resize
        signal.signal(signal.SIGWINCH, self._handle_resize)
    
    def _restore_terminal(self):
        """Restore terminal settings."""
        if self._old_term_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_term_settings)
    
    def _handle_resize(self, signum, frame):
        """Handle terminal resize."""
        self._update_window_size()
        asyncio.create_task(self._send_resize())
    
    def _update_window_size(self):
        """Update terminal size."""
        try:
            size = struct.unpack('HHHH', fcntl.ioctl(
                sys.stdout.fileno(), termios.TIOCGWINSZ, b'\0\0\0\0'
            ))
            self.rows, self.cols = size[0], size[1]
        except:
            pass
    
    async def _send_resize(self):
        """Send resize to server."""
        if self.shell_id:
            await self.client.resize_pty(self.shell_id, self.cols, self.rows)
    
    async def _reader_loop(self):
        """Read output from server PTY."""
        while self.running and self.shell_id:
            try:
                # Read from server (handled via shell data messages)
                # This is a simplified version - in practice you'd need
                # a way to receive shell data messages
                await asyncio.sleep(0.1)
            except Exception as e:
                if self.running:
                    self.console.print(f"[red]Reader error: {e}[/red]")
                break
    
    async def _input_loop(self):
        """Main input loop."""
        loop = asyncio.get_running_loop()
        
        while self.running:
            try:
                # Read single character
                char = await loop.run_in_executor(None, sys.stdin.read, 1)
                
                if not char:
                    break
                
                # Handle Ctrl+C
                if char == '\x03':
                    self.console.print("\n^C")
                    await self.client.send_pty_input(self.shell_id, b'\x03')
                    continue
                
                # Handle Ctrl+D (EOF)
                if char == '\x04':
                    self.console.print("\n[dim]Exit[/dim]")
                    break
                
                # Send to server
                await self.client.send_pty_input(self.shell_id, char.encode())
                
            except KeyboardInterrupt:
                self.console.print("\n^C")
                await self.client.send_pty_input(self.shell_id, b'\x03')
            except EOFError:
                break
            except Exception as e:
                if self.running:
                    self.console.print(f"[red]Input error: {e}[/red]")
                break