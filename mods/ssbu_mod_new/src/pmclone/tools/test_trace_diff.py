"""Unit tests for trace_diff tool.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure pyra_mythra_clone/tools is in sys.path
TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import trace_diff


class TestTraceDiff(unittest.TestCase):
    def setUp(self):
        self.fixtures_dir = TOOLS_DIR / "fixtures" / "trace"
        self.vanilla = str(self.fixtures_dir / "vanilla.trace.csv")
        self.clone_identical = str(self.fixtures_dir / "clone_identical.trace.csv")
        self.clone_float_1ulp = str(self.fixtures_dir / "clone_float_1ulp.trace.csv")
        self.clone_missing_frame = str(self.fixtures_dir / "clone_missing_frame.trace.csv")
        self.clone_extra_article = str(self.fixtures_dir / "clone_extra_article.trace.csv")
        self.clone_hitbox_order = str(self.fixtures_dir / "clone_hitbox_order.trace.csv")
        self.clone_hitbox_damage = str(self.fixtures_dir / "clone_hitbox_damage.trace.csv")
        self.clone_speed_energy = str(self.fixtures_dir / "clone_speed_energy.trace.csv")
        self.clone_kind_diff = str(self.fixtures_dir / "clone_kind_diff.trace.csv")
        self.clone_malformed = str(self.fixtures_dir / "clone_malformed.trace.csv")
        self.clone_with_comments = str(self.fixtures_dir / "clone_with_comments.trace.csv")

    def test_identical_files(self):
        code = trace_diff.main([self.vanilla, self.clone_identical])
        self.assertEqual(code, 0)

    def test_float_differs_by_1ulp_tol_0(self):
        # At tolerance 0.0, float difference must be detected
        code = trace_diff.main([self.vanilla, self.clone_float_1ulp, "--float-tol", "0"])
        self.assertEqual(code, 1)

    def test_float_differs_by_1ulp_tol_1e6(self):
        # At tolerance 1e-6, difference within 1 ulp must be ignored (IDENTICAL)
        code = trace_diff.main([self.vanilla, self.clone_float_1ulp, "--float-tol", "1e-6"])
        self.assertEqual(code, 0)

    def test_missing_frame(self):
        code = trace_diff.main([self.vanilla, self.clone_missing_frame])
        self.assertEqual(code, 1)

    def test_extra_article_row(self):
        code = trace_diff.main([self.vanilla, self.clone_extra_article])
        self.assertEqual(code, 1)

    def test_hitbox_order_differs_content_equal(self):
        # Different ordering of hitbox tokens should be treated as IDENTICAL
        code = trace_diff.main([self.vanilla, self.clone_hitbox_order])
        self.assertEqual(code, 0)

    def test_hitbox_damage_differs(self):
        code = trace_diff.main([self.vanilla, self.clone_hitbox_damage])
        self.assertEqual(code, 1)

    def test_speed_energy_present_in_one_only(self):
        code = trace_diff.main([self.vanilla, self.clone_speed_energy])
        self.assertEqual(code, 1)

    def test_kind_differs_only_default_ignored(self):
        # By default, kind is ignored -> IDENTICAL
        code = trace_diff.main([self.vanilla, self.clone_kind_diff])
        self.assertEqual(code, 0)

    def test_kind_differs_only_reported_when_ignore_empty(self):
        # When --ignore "" is specified, kind must be compared -> divergence reported
        code = trace_diff.main([self.vanilla, self.clone_kind_diff, "--ignore", ""])
        self.assertEqual(code, 1)

    def test_malformed_row_exits_2(self):
        # Malformed input should return exit code 2
        code = trace_diff.main([self.vanilla, self.clone_malformed])
        self.assertEqual(code, 2)

    def test_comment_lines_ignored(self):
        # Comments starting with # should be ignored
        code = trace_diff.main([self.vanilla, self.clone_with_comments])
        self.assertEqual(code, 0)

    def test_json_output(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            json_path = tf.name
        try:
            code = trace_diff.main([self.vanilla, self.clone_hitbox_damage, "--json", json_path])
            self.assertEqual(code, 1)
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertFalse(data["identical"])
            self.assertEqual(data["first_diverging_frame"], 0)
            self.assertGreater(data["difference_count"], 0)
        finally:
            if os.path.exists(json_path):
                os.remove(json_path)


if __name__ == "__main__":
    unittest.main()
