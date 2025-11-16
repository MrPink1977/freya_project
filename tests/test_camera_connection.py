#!/usr/bin/env python3
"""Test script for verifying Reolink camera connectivity.

Usage:
    python tests/test_camera_connection.py --ip 192.168.1.100 --user admin --password yourpass

This script tests:
1. RTSP connectivity
2. Audio extraction
3. Video frame capture
4. Basic stream health
"""

import argparse
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from freya.multi_channel_coordinator import ChannelConfig, ChannelType
from freya.rtsp_stream import RTSPStreamHandler, AudioChunk, VideoFrame


class CameraConnectionTester:
    """Test Reolink camera connectivity and stream quality."""

    def __init__(self, ip: str, username: str, password: str, rtsp_port: int = 554):
        """Initialize the tester."""
        self.config = ChannelConfig(
            channel_id="test_camera",
            channel_type=ChannelType.REOLINK,
            ip=ip,
            rtsp_port=rtsp_port,
            username=username,
            password=password,
        )

        self.audio_chunks = 0
        self.video_frames = 0
        self.first_audio_time = None
        self.first_video_time = None
        self.last_audio_time = None
        self.last_video_time = None

    def on_audio(self, chunk: AudioChunk) -> None:
        """Handle audio chunk."""
        self.audio_chunks += 1
        now = time.time()

        if self.first_audio_time is None:
            self.first_audio_time = now
            print(f"✓ First audio chunk received: {len(chunk.data)} bytes at {chunk.sample_rate}Hz")

        self.last_audio_time = now

        if self.audio_chunks % 10 == 0:
            print(f"  Audio chunks received: {self.audio_chunks}")

    def on_video(self, frame: VideoFrame) -> None:
        """Handle video frame."""
        self.video_frames += 1
        now = time.time()

        if self.first_video_time is None:
            self.first_video_time = now
            print(f"✓ First video frame received: {frame.frame.shape}")

        self.last_video_time = now

        if self.video_frames % 50 == 0:
            print(f"  Video frames received: {self.video_frames}")

    def run_test(self, duration: int = 10) -> bool:
        """Run the connectivity test.

        Args:
            duration: Test duration in seconds

        Returns:
            True if test passed, False otherwise
        """
        print("\n" + "=" * 60)
        print("Reolink Camera Connection Test")
        print("=" * 60)
        print(f"\nCamera: {self.config.ip}:{self.config.rtsp_port}")
        print(f"Username: {self.config.username}")
        print(f"Test duration: {duration} seconds\n")

        print("Starting RTSP stream handler...")

        try:
            handler = RTSPStreamHandler(
                self.config,
                audio_callback=self.on_audio,
                video_callback=self.on_video,
                audio_chunk_duration=1.0,
            )

            handler.start()
            print("✓ Stream handler started\n")
            print("Waiting for audio/video data...\n")

            # Wait for test duration
            start_time = time.time()
            while time.time() - start_time < duration:
                time.sleep(1)
                elapsed = int(time.time() - start_time)
                remaining = duration - elapsed
                print(f"  Time remaining: {remaining}s", end="\r")

            print("\n\nStopping stream handler...")
            handler.stop()
            print("✓ Stream handler stopped\n")

        except KeyboardInterrupt:
            print("\n\nTest interrupted by user")
            return False
        except Exception as exc:
            print(f"\n✗ Error during test: {exc}")
            return False

        # Print results
        print("=" * 60)
        print("Test Results")
        print("=" * 60)

        success = True

        # Audio results
        print(f"\nAudio:")
        if self.audio_chunks > 0:
            print(f"  ✓ Chunks received: {self.audio_chunks}")
            if self.first_audio_time and self.last_audio_time:
                audio_duration = self.last_audio_time - self.first_audio_time
                if audio_duration > 0:
                    rate = self.audio_chunks / audio_duration
                    print(f"  ✓ Average rate: {rate:.2f} chunks/second")
        else:
            print(f"  ✗ No audio chunks received!")
            print(f"  Possible causes:")
            print(f"    - Camera has no microphone")
            print(f"    - Audio is disabled in camera settings")
            print(f"    - RTSP URL is incorrect")
            print(f"    - Network connectivity issues")
            success = False

        # Video results
        print(f"\nVideo:")
        if self.video_frames > 0:
            print(f"  ✓ Frames received: {self.video_frames}")
            if self.first_video_time and self.last_video_time:
                video_duration = self.last_video_time - self.first_video_time
                if video_duration > 0:
                    fps = self.video_frames / video_duration
                    print(f"  ✓ Average FPS: {fps:.2f}")
        else:
            print(f"  ✗ No video frames received!")
            print(f"  Possible causes:")
            print(f"    - opencv-python not installed")
            print(f"    - RTSP URL is incorrect")
            print(f"    - Camera credentials are wrong")
            print(f"    - Camera is offline")
            success = False

        # Overall result
        print(f"\n" + "=" * 60)
        if success:
            print("✓ Test PASSED - Camera is working correctly!")
        else:
            print("✗ Test FAILED - See issues above")
        print("=" * 60 + "\n")

        return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test Reolink camera connectivity for Freya")
    parser.add_argument("--ip", required=True, help="Camera IP address")
    parser.add_argument("--user", "--username", default="admin", help="Camera username (default: admin)")
    parser.add_argument("--password", "--pass", required=True, help="Camera password")
    parser.add_argument("--port", type=int, default=554, help="RTSP port (default: 554)")
    parser.add_argument("--duration", type=int, default=10, help="Test duration in seconds (default: 10)")

    args = parser.parse_args()

    tester = CameraConnectionTester(
        ip=args.ip,
        username=args.user,
        password=args.password,
        rtsp_port=args.port,
    )

    success = tester.run_test(duration=args.duration)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
