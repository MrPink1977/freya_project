"""Unit tests for the multi-channel audio configuration loader."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from textwrap import dedent

from freya import audio_config
from freya.voice.audio_config import load_channel_configs
from freya.coordination.multi_channel_coordinator import ChannelType


class AudioConfigLoaderTests(unittest.TestCase):
    def write_config(self, contents: str) -> Path:
        fd, path_str = tempfile.mkstemp(suffix=".yaml")
        Path(path_str).write_text(dedent(contents), encoding="utf-8")
        os.close(fd)
        return Path(path_str)

    def test_loads_system_and_reolink(self) -> None:
        os.environ["CAMERA_USER"] = "doorbot"
        os.environ["CAMERA_PASS"] = "s3cret"

        if audio_config.yaml is None:
            self.skipTest("PyYAML not available")

        config_path = self.write_config(
            """
            audio:
              channels:
                primary:
                  type: system
                  enabled: true
                camera_front_door:
                  type: reolink
                  ip: 10.0.0.5
                  username: ${CAMERA_USER}
                  password: ${CAMERA_PASS}
            """,
        )

        configs = load_channel_configs(config_path)
        self.assertEqual(len(configs), 2)

        system = next(cfg for cfg in configs if cfg.channel_id == "primary")
        self.assertIs(system.channel_type, ChannelType.SYSTEM)
        self.assertTrue(system.enabled)

        camera = next(cfg for cfg in configs if cfg.channel_id == "camera_front_door")
        self.assertIs(camera.channel_type, ChannelType.REOLINK)
        self.assertEqual(camera.username, "doorbot")
        self.assertEqual(camera.password, "s3cret")

        config_path.unlink(missing_ok=True)
        os.environ.pop("CAMERA_USER", None)
        os.environ.pop("CAMERA_PASS", None)

    def test_missing_file_raises(self) -> None:
        missing = Path("does-not-exist.yaml")
        if audio_config.yaml is None:
            with self.assertRaises(RuntimeError):
                load_channel_configs(missing)
        else:
            with self.assertRaises(FileNotFoundError):
                load_channel_configs(missing)

    def test_invalid_channel_is_skipped(self) -> None:
        if audio_config.yaml is None:
            self.skipTest("PyYAML not available")

        config_path = self.write_config(
            """
            audio:
              channels:
                bad:
                  type: reolink
                  ip: ""
            """,
        )

        configs = load_channel_configs(config_path)
        self.assertEqual(configs, [])

        config_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
