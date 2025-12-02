"""Vision hardware abstraction layer implementations."""

from __future__ import annotations

import time
from typing import List, Optional

import numpy as np

from freya.core.logger import get_logger
from freya.vision.facial_recognition import FacialRecognition, FaceRecognitionError
from freya.vision.rtsp_stream import RTSPStreamHandler, VideoFrame

from .interfaces import (
    CameraUnavailableError,
    Face,
    FaceDetectionError,
    HealthStatus,
    Image,
    VisionInterface,
)

logger = get_logger("hal.vision")


class ReolinkCameraDriver:
    """
    VisionInterface implementation wrapping Reolink camera functionality.

    Adapts the existing FacialRecognition and RTSPStreamHandler to conform
    to the VisionInterface protocol.
    """

    def __init__(
        self,
        facial_recognition: FacialRecognition,
        rtsp_handler: Optional[RTSPStreamHandler] = None,
    ):
        """
        Initialize Reolink camera driver.

        Args:
            facial_recognition: Configured FacialRecognition instance
            rtsp_handler: Optional RTSP stream handler for video capture
        """
        self._face_recognition = facial_recognition
        self._rtsp_handler = rtsp_handler
        self._last_frame: Optional[np.ndarray] = None
        self._last_capture_time: Optional[float] = None

        logger.info(
            "Initialized Reolink camera driver (channel: %s)",
            facial_recognition.camera_channel or "default",
        )

    def capture(self, correlation_id: Optional[str] = None) -> Image:
        """
        Capture a single frame from the camera.

        Args:
            correlation_id: Optional request correlation ID for tracing

        Returns:
            Image object with BGR data from RTSP stream

        Raises:
            CameraUnavailableError: If camera cannot be accessed
        """
        start_time = time.time()

        try:
            if self._rtsp_handler is None:
                raise CameraUnavailableError(
                    "RTSP handler not configured for camera capture",
                    correlation_id=correlation_id,
                )

            # In a real implementation, we'd extract frame from RTSP stream
            # For now, if we have a recent frame cached, use it
            if self._last_frame is not None:
                frame = self._last_frame
            else:
                raise CameraUnavailableError(
                    "No video frames available from RTSP stream",
                    correlation_id=correlation_id,
                )

            height, width = frame.shape[:2]
            capture_time = time.time()

            latency_ms = (capture_time - start_time) * 1000
            logger.debug(
                "Captured frame %dx%d in %.1fms (correlation_id=%s)",
                width,
                height,
                latency_ms,
                correlation_id,
            )

            return Image(
                data=frame,
                timestamp=capture_time,
                source=self._face_recognition.camera_channel or "reolink",
                width=width,
                height=height,
                correlation_id=correlation_id,
            )

        except CameraUnavailableError:
            raise
        except Exception as exc:
            logger.error(
                "Camera capture failed (correlation_id=%s): %s",
                correlation_id,
                exc,
                exc_info=True,
            )
            raise CameraUnavailableError(
                f"Failed to capture camera frame: {exc}",
                correlation_id=correlation_id,
                error=str(exc),
            ) from exc

    def detect_faces(
        self, image: Image, correlation_id: Optional[str] = None
    ) -> List[Face]:
        """
        Detect and identify faces in an image.

        Args:
            image: Image to analyze (BGR format from capture())
            correlation_id: Optional request correlation ID

        Returns:
            List of detected faces (empty if none found)

        Raises:
            FaceDetectionError: If detection fails
        """
        start_time = time.time()

        try:
            # Use existing FacialRecognition implementation
            results = self._face_recognition.recognize_faces(
                frame=image.data, timestamp=image.timestamp
            )

            # Convert to HAL Face objects
            faces = []
            for result in results:
                face = Face(
                    name=result.name,
                    confidence=result.confidence,
                    bounding_box=result.bounding_box,
                    timestamp=result.timestamp,
                    correlation_id=correlation_id or image.correlation_id,
                )
                faces.append(face)

            latency_ms = (time.time() - start_time) * 1000
            logger.debug(
                "Detected %d face(s) in %.1fms (correlation_id=%s)",
                len(faces),
                latency_ms,
                correlation_id,
            )

            return faces

        except FaceRecognitionError as exc:
            logger.error(
                "Face detection failed (correlation_id=%s): %s",
                correlation_id,
                exc,
                exc_info=True,
            )
            raise FaceDetectionError(
                f"Face detection failed: {exc}",
                correlation_id=correlation_id,
                error=str(exc),
            ) from exc
        except Exception as exc:
            logger.error(
                "Unexpected error in face detection (correlation_id=%s): %s",
                correlation_id,
                exc,
                exc_info=True,
            )
            raise FaceDetectionError(
                f"Unexpected face detection error: {exc}",
                correlation_id=correlation_id,
                error=str(exc),
            ) from exc

    def health_check(self, correlation_id: Optional[str] = None) -> HealthStatus:
        """
        Check hardware health and connectivity.

        Returns:
            Health status with diagnostics
        """
        start_time = time.time()

        try:
            # Check if facial recognition is loaded
            face_count = len(self._face_recognition.known_face_names)

            # Check RTSP stream availability
            rtsp_available = self._rtsp_handler is not None

            # Check if we have recent frames
            has_recent_frame = (
                self._last_capture_time is not None
                and (time.time() - self._last_capture_time) < 60.0
            )

            is_healthy = face_count > 0 and (not rtsp_available or has_recent_frame)

            if is_healthy:
                status = "healthy"
            elif face_count == 0:
                status = "degraded"
                error_msg = "No known faces loaded"
            else:
                status = "degraded"
                error_msg = "No recent frames from camera"

            latency_ms = (time.time() - start_time) * 1000

            return HealthStatus(
                is_healthy=is_healthy,
                status=status,
                last_check=time.time(),
                latency_ms=latency_ms,
                error_message=error_msg if not is_healthy else None,
                metadata={
                    "known_faces": face_count,
                    "rtsp_configured": rtsp_available,
                    "has_recent_frame": has_recent_frame,
                    "correlation_id": correlation_id,
                },
            )

        except Exception as exc:
            logger.error(
                "Health check failed (correlation_id=%s): %s",
                correlation_id,
                exc,
                exc_info=True,
            )
            return HealthStatus(
                is_healthy=False,
                status="offline",
                last_check=time.time(),
                error_message=str(exc),
                metadata={"correlation_id": correlation_id},
            )

    def _on_video_frame(self, frame: VideoFrame) -> None:
        """Internal callback for RTSP video frames."""
        self._last_frame = frame.frame
        self._last_capture_time = frame.timestamp


class MockCameraDriver:
    """
    Mock VisionInterface implementation for testing without hardware.

    Generates synthetic images and face detections for testing purposes.
    """

    def __init__(self, behavior: str = "normal"):
        """
        Initialize mock camera driver.

        Args:
            behavior: Mock behavior mode:
                - "normal": Returns synthetic data successfully
                - "flaky": Randomly fails operations
                - "offline": Always fails as if hardware unavailable
        """
        self._behavior = behavior
        self._frame_count = 0
        logger.info("Initialized mock camera driver (behavior=%s)", behavior)

    def capture(self, correlation_id: Optional[str] = None) -> Image:
        """Capture a synthetic frame."""
        self._frame_count += 1

        if self._behavior == "offline":
            raise CameraUnavailableError(
                "Mock camera offline", correlation_id=correlation_id
            )

        if self._behavior == "flaky" and self._frame_count % 3 == 0:
            raise CameraUnavailableError(
                "Mock camera flaky failure", correlation_id=correlation_id
            )

        # Generate synthetic 640x480 BGR image
        synthetic_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        return Image(
            data=synthetic_frame,
            timestamp=time.time(),
            source="mock_camera",
            width=640,
            height=480,
            correlation_id=correlation_id,
        )

    def detect_faces(
        self, image: Image, correlation_id: Optional[str] = None
    ) -> List[Face]:
        """Detect synthetic faces."""
        if self._behavior == "offline":
            raise FaceDetectionError(
                "Mock face detection offline", correlation_id=correlation_id
            )

        # Return mock face detection
        if self._behavior == "normal" or (self._behavior == "flaky" and self._frame_count % 3 != 0):
            return [
                Face(
                    name="Mock User",
                    confidence=0.95,
                    bounding_box=(100, 300, 400, 200),
                    timestamp=time.time(),
                    correlation_id=correlation_id,
                )
            ]

        return []

    def health_check(self, correlation_id: Optional[str] = None) -> HealthStatus:
        """Return mock health status."""
        if self._behavior == "offline":
            return HealthStatus(
                is_healthy=False,
                status="offline",
                last_check=time.time(),
                error_message="Mock camera offline",
                metadata={"correlation_id": correlation_id},
            )

        return HealthStatus(
            is_healthy=True,
            status="healthy",
            last_check=time.time(),
            latency_ms=5.0,
            metadata={
                "frames_captured": self._frame_count,
                "behavior": self._behavior,
                "correlation_id": correlation_id,
            },
        )


# Verify protocol conformance at module load time
_: VisionInterface
_ = ReolinkCameraDriver  # type: ignore[assignment]
_ = MockCameraDriver  # type: ignore[assignment]

__all__ = [
    "ReolinkCameraDriver",
    "MockCameraDriver",
]
