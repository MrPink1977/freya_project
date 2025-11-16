#!/usr/bin/env python3
"""
Demo: Facial Recognition from Reolink Camera Feed

This script demonstrates facial recognition using the Reolink camera.
It will capture video frames and recognize known faces.

Setup:
1. Install face_recognition: pip install face_recognition
2. Create data/faces directory
3. Add photos of people (one face per image): data/faces/person_name/photo.jpg
"""

import os
import sys
import time
import cv2
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from freya.facial_recognition import FacialRecognition, FaceRecognitionError
from freya.config import FaceRecognitionConfig
from freya.rtsp_stream import RTSPStreamHandler
from freya.multi_channel_coordinator import ChannelConfig, ChannelType

def main():
    print("=" * 70)
    print("Freya Facial Recognition Demo - Reolink Camera")
    print("=" * 70)
    print()

    # Check for face_recognition library
    try:
        import face_recognition
        print("✓ face_recognition library installed")
    except ImportError:
        print("✗ face_recognition library NOT installed")
        print()
        print("Install with: pip install face_recognition")
        print()
        print("Note: This requires CMake and dlib. On Windows:")
        print("  1. Install Visual Studio Build Tools")
        print("  2. pip install cmake")
        print("  3. pip install dlib")
        print("  4. pip install face_recognition")
        return 1

    # Check for known faces directory
    faces_dir = Path("data/faces")
    if not faces_dir.exists():
        print(f"✗ Known faces directory not found: {faces_dir}")
        print()
        print("Creating directory...")
        faces_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {faces_dir}")
        print()
        print("Next steps:")
        print(f"  1. Add photos of people to {faces_dir}/")
        print("  2. Organize by person: data/faces/john/photo1.jpg")
        print("  3. One face per photo (clear, front-facing)")
        print("  4. Supported formats: .jpg, .jpeg, .png, .bmp, .webp")
        print()
        return 0

    # Load facial recognition config
    fr_config = FaceRecognitionConfig(
        enabled=True,
        camera_channel="camera_main",
        known_faces_dir=str(faces_dir),
        detection_model="hog",  # Use "cnn" for GPU acceleration
        encoding_model="small",
        tolerance=0.5,
        min_recognition_interval=3.0
    )

    print(f"Loading known faces from: {faces_dir}")
    try:
        face_rec = FacialRecognition(fr_config, eager_load=True)
        known_names = face_rec.known_face_names
        if known_names:
            print(f"✓ Loaded {len(known_names)} known face(s):")
            for name in known_names:
                print(f"  - {name}")
        else:
            print("✗ No known faces loaded!")
            print()
            print("Add face images to data/faces/ and try again.")
            return 0
    except FaceRecognitionError as e:
        print(f"✗ Error: {e}")
        return 1

    print()
    print("Connecting to Reolink camera...")

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
        description="Main camera"
    )

    # Track frames and detections
    frames_processed = 0
    faces_detected = 0
    last_detection = {}

    def on_video_frame(video_frame):
        """Callback for video frames from RTSP stream."""
        nonlocal frames_processed, faces_detected, last_detection

        frames_processed += 1

        # Process every 5th frame to save CPU
        if frames_processed % 5 != 0:
            return

        try:
            # Extract numpy array from VideoFrame object
            frame = video_frame.frame
            timestamp = video_frame.timestamp

            # Debug: Check what we got
            if frames_processed == 5:  # Only print once
                print(f"DEBUG: video_frame type: {type(video_frame)}")
                print(f"DEBUG: frame type: {type(frame)}")
                print(f"DEBUG: frame shape: {frame.shape if hasattr(frame, 'shape') else 'NO SHAPE'}")

            # Recognize faces in this frame
            results = face_rec.recognize_faces(frame, timestamp)

            if results:
                faces_detected += len(results)
                for result in results:
                    # Check if this is a new detection (not spam)
                    last_seen = last_detection.get(result.name, 0)
                    if timestamp - last_seen < 3.0:
                        continue

                    last_detection[result.name] = timestamp

                    print(f"✓ Recognized: {result.name}")
                    print(f"  Confidence: {result.confidence:.2%}")
                    print(f"  Distance: {result.distance:.3f}")
                    print(f"  Location: {result.bounding_box}")
                    print()

        except Exception as e:
            print(f"Recognition error: {e}")

    # Start RTSP stream
    def on_audio_chunk(audio_chunk):
        """Callback for audio chunks from RTSP stream."""
        pass  # Ignore audio for this demo

    print(f"✓ Connecting to camera at {cam_ip}...")
    stream = RTSPStreamHandler(
        config=cam_config,
        audio_callback=on_audio_chunk,
        video_callback=on_video_frame
    )

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
                fps = frames_processed / elapsed if elapsed > 0 else 0
                print(f"Status: {frames_processed} frames ({fps:.1f} fps), {faces_detected} faces detected")

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
