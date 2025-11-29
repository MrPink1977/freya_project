#!/usr/bin/env python3
"""
Launch script for Freya Web GUI

Usage:
    python run_web_gui.py
    python run_web_gui.py --host 0.0.0.0 --port 8080
"""

import argparse
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from freya.web.app import run_server


def main():
    parser = argparse.ArgumentParser(description="Freya Web GUI Server")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("🤖 Freya AI Assistant - Web GUI")
    print("=" * 70)
    print(f"\n📡 Server starting at: http://{args.host}:{args.port}")
    print(f"🔧 Development mode: {args.reload}")
    print("\nPress CTRL+C to stop the server\n")
    print("=" * 70)

    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
