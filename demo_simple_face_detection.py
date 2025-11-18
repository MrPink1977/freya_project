#!/usr/bin/env python3
"""
Simple Face Detection Demo - Using OpenCV only (no dlib)

This is a simpler alternative that just detects faces without recognition.
Use this to verify the camera feed is working properly.
"""

import os
import sys
import time
from pathlib import Path

import cv2

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from freya.multi_channel_coordinator import ChannelConfig, ChannelType
from freya.rtsp_stream import RTSPStreamHandler


def main():
    print("=" * 70)
    print("Simple Face Detection Demo - OpenCV Only")
    print("=" * 70)
    print()

    # Get camera credentials from environment
    cam_ip = "192.168.0.22"
    cam_user = os.getenv("REOLINK_CAM_USER", "Freya")
    cam_pass = os.getenv("REOLINK_CAM_PASS", "")

    if not cam_pass:
        print("✗ REOLINK_CAM_PASS not set!")
        return 1

    # Camera config
    cam_config = ChannelConfig(
        channel_id="camera_main",
        channel_type=ChannelType.REOLINK,
        enabled=True,
        ip=cam_ip,
        rtsp_port=554,
        username=cam_user,
        password=cam_pass,
        description="Main camera",
    )

    # Load OpenCV face detector
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    print("✓ Loaded face detector")

    # Track frames and detections
    frames_processed = 0
    faces_detected = 0

    def on_video_frame(video_frame):
        """Callback for video frames from RTSP stream."""
        nonlocal frames_processed, faces_detected

        frames_processed += 1

        # Process every 10th frame
        if frames_processed % 10 != 0:
            return

        try:
            frame = video_frame.frame

            # Resize for speed
            height, width = frame.shape[:2]
            if width > 640:
                scale = 640 / width
                frame = cv2.resize(frame, (640, int(height * scale)))

            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect faces
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)

            if len(faces) > 0:
                faces_detected += len(faces)
                print(f"✓ Detected {len(faces)} face(s) at {time.strftime('%H:%M:%S')}")
                for x, y, w, h in faces:
                    print(f"  Location: x={x}, y={y}, size={w}x{h}")

        except Exception as e:
            print(f"Error: {e}")

    def on_audio_chunk(audio_chunk):
        pass

    print(f"✓ Connecting to camera at {cam_ip}...")
    stream = RTSPStreamHandler(config=cam_config, audio_callback=on_audio_chunk, video_callback=on_video_frame)

    try:
        stream.start()
        print("✓ Camera stream started")
        print()
        print("=" * 70)
        print("Watching for faces... (Press Ctrl+C to stop)")
        print("=" * 70)
        print()

        # Run for a while
        start_time = time.time()
        while True:
            time.sleep(1)

            # Show status every 10 seconds
            elapsed = time.time() - start_time
            if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                print(f"Status: {frames_processed} frames, {faces_detected} faces detected")

    except KeyboardInterrupt:
        print()
        print("Stopping...")
    finally:
        stream.stop()
        print("✓ Stream stopped")

    print()
    print("=" * 70)
    print("Demo Complete")
    print("=" * 70)
    print(f"Frames processed: {frames_processed}")
    print(f"Faces detected: {faces_detected}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
