from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from demo.calibration.threshold_calibrator import ThresholdCalibrator
from demo.config import load_config
from demo.embeddings.model_cache import load_model


class CalibrationTest(unittest.TestCase):
    def test_calibrator_emits_reports(self) -> None:
        base = load_config("config/demo.yaml")
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = replace(
                base,
                reports_dir=tmp_dir,
                model_cache_dir=str(Path(tmp_dir) / "models"),
                embedding_backend="stable-projection",
                vector_mode="stable_projection",
            )
            calibrator = ThresholdCalibrator(config=config, model=load_model(config))
            report = calibrator.run()

            self.assertIn("recommended_thresholds", report)
            self.assertIn("metrics", report)
            self.assertTrue((Path(tmp_dir) / "calibration-report.json").exists())
            self.assertTrue((Path(tmp_dir) / "calibration-report.md").exists())

            payload = json.loads((Path(tmp_dir) / "calibration-report.json").read_text(encoding="utf-8"))
            self.assertIn("search_space", payload)
            self.assertGreater(len(payload["search_space"]), 0)
