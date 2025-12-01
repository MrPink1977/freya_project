"""Facial recognition helpers for Freya's camera channels."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

try:  # pragma: no cover - numpy is a runtime dependency but optional in some CI flows
    import numpy as np
except ImportError as exc:  # pragma: no cover - handled during dependency checks
    np = None  # type: ignore[assignment]
    _NUMPY_ERROR = exc
else:  # pragma: no cover - passthrough
    _NUMPY_ERROR = None

from freya.core.config import FaceRecognitionConfig
from freya.core.logger import get_logger

try:  # pragma: no cover - depends on optional dependency
    import face_recognition  # type: ignore
except ImportError as exc:  # pragma: no cover - exercised in tests via patching
    face_recognition = None  # type: ignore[assignment]
    _FACE_RECOGNITION_ERROR = exc
else:  # pragma: no cover - passthrough
    _FACE_RECOGNITION_ERROR = None

logger = get_logger("facial_recognition")

_SUPPORTED_EXTENSIONS: Sequence[str] = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


@dataclass(frozen=True)
class FaceProfile:
    """Represents a single known face profile."""

    name: str
    encoding: np.ndarray
    image_path: Path


@dataclass(frozen=True)
class RecognitionResult:
    """Represents a recognised face from a video frame."""

    name: str
    confidence: float
    distance: float
    timestamp: float
    bounding_box: Tuple[int, int, int, int]


class FaceRecognitionError(RuntimeError):
    """Raised when the facial recognition stack cannot initialise."""


class FacialRecognition:
    """Load known faces and perform recognition on camera frames."""

    def __init__(self, config: FaceRecognitionConfig, eager_load: bool = True) -> None:
        self._config = config
        self._directory = Path(config.known_faces_dir).expanduser()
        self._detection_model = (config.detection_model or "hog").strip()
        self._encoding_model = (config.encoding_model or "small").strip()
        self._tolerance = max(0.0, float(config.tolerance)) or 0.6
        self._min_interval = max(0.0, float(config.min_recognition_interval))
        self._camera_channel = config.camera_channel
        self._profiles: List[FaceProfile] = []
        self._encodings: List[np.ndarray] = []
        self._recent_hits: dict[str, float] = {}

        self._ensure_dependencies()

        if eager_load:
            self.reload()

    def _ensure_dependencies(self) -> None:
        if _FACE_RECOGNITION_ERROR is not None:
            raise FaceRecognitionError(
                "face_recognition dependency missing. Install the 'face-recognition' package to enable "
                "facial recognition support."
            ) from _FACE_RECOGNITION_ERROR
        if face_recognition is None:  # pragma: no cover - defensive
            raise FaceRecognitionError("face_recognition module unavailable")
        if np is None:
            raise FaceRecognitionError(
                "numpy dependency missing. Install 'numpy' to enable facial recognition."
            ) from _NUMPY_ERROR

    def reload(self) -> None:
        """Reload known faces from the configured directory."""

        if not self._directory.exists():
            raise FaceRecognitionError(f"Known faces directory not found: {self._directory}")

        profiles: List[FaceProfile] = []
        encodings: List[np.ndarray] = []
        for image_path, name in self._iter_face_files(self._directory):
            try:
                image = face_recognition.load_image_file(str(image_path))
                vectors = face_recognition.face_encodings(image, model=self._encoding_model)
            except Exception as exc:  # pragma: no cover - backend specific
                logger.warning("Failed to load face from %s: %s", image_path, exc)
                continue

            if not vectors:
                logger.warning("No faces detected in %s", image_path)
                continue

            encoding = np.asarray(vectors[0], dtype=np.float32)
            profiles.append(FaceProfile(name=name, encoding=encoding, image_path=image_path))
            encodings.append(encoding)

        self._profiles = profiles
        self._encodings = encodings
        self._recent_hits.clear()

        if not profiles:
            logger.warning("No known faces loaded from %s", self._directory)
        else:
            logger.info("Loaded %s known face(s) from %s", len(profiles), self._directory)

    def _iter_face_files(self, directory: Path) -> Iterable[Tuple[Path, str]]:
        """Yield (image_path, name) pairs for supported image files."""

        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
                continue
            yield path, self._name_from_path(directory, path)

    @staticmethod
    def _name_from_path(base: Path, path: Path) -> str:
        """Derive a human-readable profile name from ``path``."""

        try:
            if base in path.parents and path.parent != base:
                candidate = path.parent.name
            else:
                candidate = path.stem
        except Exception:  # pragma: no cover - defensive
            candidate = path.stem

        formatted = candidate.replace("_", " ").strip()
        return formatted or "Unknown"

    def recognize_faces(
        self, frame: np.ndarray, timestamp: Optional[float] = None
    ) -> List[RecognitionResult]:
        """Return recognised faces for a BGR frame from an RTSP/Camera feed."""

        if face_recognition is None:
            raise FaceRecognitionError("face_recognition module unavailable")

        if frame is None:
            return []
        if frame.ndim != 3 or frame.shape[2] < 3:
            raise FaceRecognitionError("Expected colour frame with 3 channels (BGR)")
        if not self._encodings:
            return []

        timestamp_value = timestamp if timestamp is not None else time.time()
        rgb_frame = frame[:, :, ::-1]

        try:
            locations = face_recognition.face_locations(rgb_frame, model=self._detection_model)
            if not locations:
                return []
            encodings = face_recognition.face_encodings(
                rgb_frame,
                known_face_locations=locations,
                model=self._encoding_model,
            )
        except Exception as exc:  # pragma: no cover - backend specific
            logger.warning("Face recognition failed: %s", exc)
            return []

        results: List[RecognitionResult] = []
        for encoding, location in zip(encodings, locations):
            if encoding is None:
                continue
            np_encoding = np.asarray(encoding, dtype=np.float32)
            if np_encoding.size == 0:
                continue

            distances = face_recognition.face_distance(self._encodings, np_encoding)
            if distances.size == 0:
                continue

            best_index = int(np.argmin(distances))
            best_distance = float(distances[best_index])
            if best_distance > self._tolerance:
                continue

            name = self._profiles[best_index].name
            last_seen = self._recent_hits.get(name)
            if last_seen is not None and (timestamp_value - last_seen) < self._min_interval:
                continue

            confidence = 1.0
            if self._tolerance > 0:
                confidence = max(0.0, min(1.0, 1.0 - (best_distance / self._tolerance)))

            try:
                bounding_box = tuple(int(v) for v in location)
            except (ValueError, TypeError) as exc:
                logger.warning("Invalid bounding box values for face '%s': %s", name, exc)
                continue

            result = RecognitionResult(
                name=name,
                confidence=confidence,
                distance=best_distance,
                timestamp=timestamp_value,
                bounding_box=bounding_box,
            )
            results.append(result)
            self._recent_hits[name] = timestamp_value

        return results

    @property
    def known_face_names(self) -> Tuple[str, ...]:
        """Return the names of all loaded face profiles."""

        return tuple(profile.name for profile in self._profiles)

    @property
    def camera_channel(self) -> Optional[str]:
        """Return the preferred audio/video channel identifier, if configured."""

        return self._camera_channel


__all__ = [
    "FaceProfile",
    "RecognitionResult",
    "FaceRecognitionError",
    "FacialRecognition",
]
