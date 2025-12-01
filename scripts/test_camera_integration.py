#!/usr/bin/env python3
"""
Test script to verify camera integration with Freya configuration system.
This verifies that camera channels are loaded correctly.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from freya.voice.audio_config import load_channel_configs


def test_camera_config():
    """Test loading camera configuration."""

    print("=" * 60)
    print("Freya Camera Integration Test")
    print("=" * 60)
    print()

    # Check environment variables
    print("Environment Variables:")
    cam_user = os.getenv("REOLINK_CAM_USER")
    cam_pass = os.getenv("REOLINK_CAM_PASS")

    if cam_user:
        print(f"  ✓ REOLINK_CAM_USER: {cam_user}")
    else:
        print("  ✗ REOLINK_CAM_USER: NOT SET")

    if cam_pass:
        print(f"  ✓ REOLINK_CAM_PASS: {'*' * len(cam_pass)}")
    else:
        print("  ✗ REOLINK_CAM_PASS: NOT SET")

    print()

    # Load configuration
    print("Loading camera configuration...")
    try:
        channels = load_channel_configs("config/my_camera_config.yaml")
        print(f"✓ Successfully loaded {len(channels)} channels")
        print()

        # Display channel details
        for channel in channels:
            print(f"Channel: {channel.channel_id}")
            print(f"  Type: {channel.channel_type.value}")
            print(f"  Enabled: {channel.enabled}")
            print(f"  Description: {channel.description}")

            if channel.channel_type.name == "REOLINK":
                print(f"  Camera IP: {channel.ip}:{channel.rtsp_port}")
                print(f"  Username: {channel.username}")
                print(
                    f"  Password: {'*' * len(channel.password) if channel.password else 'NOT SET'}"
                )

            print()

        print("=" * 60)
        print("✓ Configuration Test PASSED")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"✗ Error loading configuration: {e}")
        print()
        print("=" * 60)
        print("✗ Configuration Test FAILED")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = test_camera_config()
    sys.exit(0 if success else 1)
