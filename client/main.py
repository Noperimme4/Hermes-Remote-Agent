#!/usr/bin/env python3
"""
Remote Agent Client - Main Entry Point
Interactive menu-driven client with Hermes integration
"""

import asyncio
import os
import sys
import json
import getpass
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from client.cli import RemoteAgentClient, ClientConfig
from client.menu import InteractiveMenu
from client.hermes import HermesClient
from client.file_browser import FileBrowser
from client.profiles import ProfileManager


def print_banner():
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                    🌐 Remote Agent Client v2.0                  ║
║         Secure Remote Control + Hermes AI Integration           ║
╚═══════════════════════════════════════════════════════════════════╝
""")


def print_help():
    print("""
Usage: agent [OPTIONS]

Options:
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
  -v, --verbose       Verbose output
  -h, --help          Show this help

Examples:
  agent                                    # Interactive menu
  agent --host 192.168.1.100 --token xxx  # Connect to server
  agent --profile myserver                # Use saved profile
  agent -c "ls -la /data"                 # Run single command
  agent --hermes                          # Chat with Hermes
  agent --files                           # File browser

Environment:
  AGENT_TOKEN      Default auth token
  AGENT_HOST       Default server host
  AGENT_PORT       Default server port
""")


async def main():
    import argparse
    
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
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-h", "--help", action="store_true")
    
    args = parser.parse_args()
    
    if args.help:
        print_help()
        return 0
    
    print_banner()
    
    # Load profile if specified
    profile_manager = ProfileManager()
    if args.profile:
        profile = profile_manager.load(args.profile)
        if profile:
            args.host = profile.get("host", args.host)
            args.port = profile.get("port", args.port)
            args.token = profile.get("token", args.token)
            print(f"📋 Loaded profile: {args.profile}")
        else:
            print(f"❌ Profile not found: {args.profile}")
            return 1
    
    # Get token
    if not args.token:
        args.token = getpass.getpass("🔑 Enter auth token: ").strip()
    
    if not args.token:
        print("❌ Token required")
        return 1
    
    # Create client
    config = ClientConfig(
        host=args.host,
        port=args.port,
        token=args.token,
        log_level="DEBUG" if args.verbose else "WARNING"
    )
    
    client = RemoteAgentClient(config)
    
    print(f"🔌 Connecting to {args.host}:{args.port}...")
    connected = await client.connect()
    
    if not connected:
        print("❌ Connection failed")
        return 1
    
    print(f"✅ Connected! Session: {client.session_id[:8]}...")
    print(f"🖥️  Server: {client.server_info.get('name', 'unknown')}")
    print()
    
    # Save profile if requested
    if args.save_profile:
        name = input("Profile name: ").strip() or "default"
        profile_manager.save(name, {
            "host": args.host,
            "port": args.port,
            "token": args.token
        })
        print(f"💾 Profile '{name}' saved")
    
    # Route to appropriate mode
    try:
        if args.command:
            # Single command mode
            result = await client.execute_simple(args.command)
            print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return result.exit_code
        
        elif args.shell:
            # PTY Shell
            print("🐚 Starting PTY shell... (Ctrl+D to exit)")
            await client.interactive_shell()
        
        elif args.hermes:
            # Hermes AI Chat
            hermes = HermesClient(client)
            await hermes.chat()
        
        elif args.files:
            # File Browser
            browser = FileBrowser(client)
            await browser.run()
        
        else:
            # Interactive Menu (default)
            menu = InteractiveMenu(client)
            await menu.run()
    
    finally:
        await client.disconnect()
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)