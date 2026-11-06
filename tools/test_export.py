import json
from pathlib import Path
import tempfile
import unittest

from export import export, public_sample


class ExportBenchmarkTests(unittest.TestCase):
    def test_only_safe_measurements_reach_both_public_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [dict(observed_at="2026-11-07T00:00:00Z", state="running", confirmed=1,
                         network_out_bytes=1_000_000, token="private-cookie", file="private-photo.jpg",
                         checkpoint={"ciphertext": "private-report"}, job_id="private-job"),
                    dict(observed_at="2026-11-07T00:02:00Z", state="running", confirmed=3,
                         network_out_bytes=13_000_000, destination="private@example.com")]
            source = root / "input.ndjson"
            source.write_text("".join(json.dumps(row) + "\n" for row in rows) + '{"partial":')
            self.assertEqual(export(source, root / "public"), 2)
            public = "".join(p.read_text() for p in (root / "public").iterdir())
            self.assertNotIn("private", public)
            summary = json.loads((root / "public/summary.json").read_text())
            self.assertEqual(summary["network_out_average_MBps"], 0.1)
            self.assertEqual(summary["observations"], 2)

    def test_rejects_injected_state_and_non_numeric_measurements(self):
        for change in ({"state": "private-error"}, {"confirmed": "=IMPORTDATA(secret)"},
                       {"confirmed": True}, {"confirmed": -1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                public_sample({"observed_at": "2026-11-07T00:00:00Z", "state": "running", **change})
