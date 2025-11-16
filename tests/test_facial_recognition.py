"""Tests for the facial recognition helper module."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:  # pragma: no cover - numpy is an optional dependency in CI
    import numpy as np
except ImportError:  # pragma: no cover - handled via skip
    np = None  # type: ignore[assignment]

from freya.config import FaceRecognitionConfig
from freya import facial_recognition


@unittest.skipIf(np is None, "numpy not available")
class FacialRecognitionModuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.tempdir.name)
        (self.base_path / "alice").mkdir()
        (self.base_path / "bob").mkdir()
        (self.base_path / "alice" / "image1.jpg").write_bytes(b"alice")
        (self.base_path / "bob" / "image1.jpg").write_bytes(b"bob")

        self.original_face_module = facial_recognition.face_recognition
        self.original_error = facial_recognition._FACE_RECOGNITION_ERROR
        self.addCleanup(self._restore_face_module)
        self.addCleanup(self.tempdir.cleanup)

    def _restore_face_module(self) -> None:
        facial_recognition.face_recognition = self.original_face_module
        facial_recognition._FACE_RECOGNITION_ERROR = self.original_error

    def _build_config(self) -> FaceRecognitionConfig:
        return FaceRecognitionConfig(
            enabled=True,
            known_faces_dir=str(self.base_path),
            detection_model="hog",
            encoding_model="small",
            tolerance=0.6,
            camera_channel="camera_front_door",
            min_recognition_interval=0.0,
        )

    def test_recognises_known_face(self) -> None:
        class StubFaceModule:
            def __init__(self) -> None:
                self.recognition_vector = np.array([0.11, 0.11], dtype=np.float32)

            def load_image_file(self, path: str) -> str:
                return path

            def face_encodings(self, image, known_face_locations=None, model="small"):
                if isinstance(image, str):
                    if "alice" in image.lower():
                        return [np.array([0.1, 0.1], dtype=np.float32)]
                    return [np.array([0.8, 0.8], dtype=np.float32)]
                return [self.recognition_vector]

            def face_locations(self, image, model="hog"):
                return [(0, 1, 1, 0)]

            def face_distance(self, known, candidate):
                return np.array(
                    [float(np.linalg.norm(k - candidate)) for k in known],
                    dtype=np.float32,
                )

        stub = StubFaceModule()
        facial_recognition.face_recognition = stub  # type: ignore[assignment]
        facial_recognition._FACE_RECOGNITION_ERROR = None

        recogniser = facial_recognition.FacialRecognition(self._build_config())
        self.assertIn("alice", recogniser.known_face_names)
        self.assertIn("bob", recogniser.known_face_names)

        frame = np.zeros((8, 8, 3), dtype=np.uint8)
        results = recogniser.recognize_faces(frame, timestamp=0.0)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "alice")
        self.assertGreaterEqual(results[0].confidence, 0.0)

        recogniser._min_interval = 1.0
        first = recogniser.recognize_faces(frame, timestamp=10.0)
        second = recogniser.recognize_faces(frame, timestamp=10.2)
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 0)

    def test_missing_dependency_raises(self) -> None:
        facial_recognition.face_recognition = None  # type: ignore[assignment]
        facial_recognition._FACE_RECOGNITION_ERROR = ImportError("missing")

        with self.assertRaises(facial_recognition.FaceRecognitionError):
            facial_recognition.FacialRecognition(self._build_config())


if __name__ == "__main__":
    unittest.main()
