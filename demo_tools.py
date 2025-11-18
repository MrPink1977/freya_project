#!/usr/bin/env python3
"""
Demo script showing Freya's tool capabilities.

This demonstrates all the tools available to Freya for interacting
with the system, web, files, and performing calculations.
"""

from freya.tools import ToolManager


def demo_tools():
    """Demonstrate all Freya tools."""
    print("=" * 70)
    print("Freya Tools Demo")
    print("=" * 70)
    print()

    # Initialize tool manager
    manager = ToolManager()

    print("📋 Available Tools:")
    print(manager.get_tools_description())
    print()

    # Demo each category of tools
    demos = [
        (
            "⏰ Time & Date",
            [
                ("get_current_time", {"timezone": "America/New_York", "format": "12h"}),
                ("get_current_date", {"format": "long"}),
                ("calculate_time_until", {"target_date": "2025-12-25"}),
            ],
        ),
        (
            "🧮 Calculator",
            [
                ("calculator", {"expression": "2 + 2 * 3"}),
                ("calculator", {"expression": "sqrt(16) + 10"}),
                ("calculator", {"expression": "sin(pi/2)"}),
            ],
        ),
        (
            "📁 File Operations",
            [
                ("list_files", {"path": ".", "pattern": "*.py", "recursive": False}),
                ("list_files", {"path": "freya/tools", "pattern": "*.py"}),
            ],
        ),
        (
            "💻 System Info",
            [
                ("system_info", {"info_type": "os"}),
                ("system_info", {"info_type": "python"}),
            ],
        ),
        (
            "🌐 Web (requires internet)",
            [
                ("web_search", {"query": "Python programming", "max_results": 3}),
                # Uncomment to test web scraper:
                # ("web_scraper", {"url": "https://example.com", "mode": "title"}),
            ],
        ),
    ]

    for category, tool_demos in demos:
        print(f"\n{category}")
        print("-" * 70)

        for tool_name, kwargs in tool_demos:
            print(f"\n🔧 {tool_name}({', '.join(f'{k}={v!r}' for k, v in kwargs.items())})")

            result = manager.execute_tool(tool_name, **kwargs)

            if result.success:
                print(f"✓ {result.output[:200]}")
                if len(result.output) > 200:
                    print("  ... (truncated)")
            else:
                print(f"✗ Error: {result.error}")

    print()
    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)


if __name__ == "__main__":
    demo_tools()
