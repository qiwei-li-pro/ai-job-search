"""The fork's scheduled sync must survive a parent rename without trusting a new parent."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github/workflows/upstream-sync.yml"


class AutomaticUpstreamSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        script = textwrap.dedent(cls.workflow.split("        run: |\n", 1)[1])
        match = re.search(r"python3 - <<'PY'\n(.*?)\nPY(?:\n|$)", script, re.S)
        if not match:
            raise AssertionError("The workflow must run the tested repository guard")
        cls.guard = match[1]

    def metadata(self, parent_name="ai-job-search-dev/ai-job-search"):
        return {
            "full_name": "qiwei-li-pro/ai-job-search",
            "fork": True,
            "default_branch": "master",
            "parent": {"id": 1185389803, "full_name": parent_name, "default_branch": "master"},
        }

    def run_guard(self, metadata):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "repo.json").write_text(json.dumps(metadata), encoding="utf-8")
            summary = root / "summary.md"
            env = {**os.environ, "GH_REPO": "qiwei-li-pro/ai-job-search", "GITHUB_STEP_SUMMARY": str(summary)}
            result = subprocess.run([sys.executable, "-c", self.guard], cwd=root, env=env,
                                    capture_output=True, text=True, encoding="utf-8")
            return result, summary.read_text(encoding="utf-8") if summary.exists() else ""

    def assert_rejected(self, metadata, reason):
        result, summary = self.run_guard(metadata)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("::error::", result.stderr)
        self.assertIn(reason, summary)
        self.assertIn("No merge attempted", summary)

    def test_original_parent_name_is_accepted(self):
        result, _ = self.run_guard(self.metadata("MadsLorentzen/ai-job-search"))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_transferred_parent_is_accepted_by_stable_id(self):
        result, summary = self.run_guard(self.metadata())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ai-job-search-dev/ai-job-search", result.stdout)
        self.assertEqual(summary, "")

    def test_renamed_parent_is_accepted_by_stable_id(self):
        result, _ = self.run_guard(self.metadata("ai-job-search-dev/renamed-repository"))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_reused_original_name_cannot_authorize_a_different_repository(self):
        metadata = self.metadata("MadsLorentzen/ai-job-search")
        metadata["parent"]["id"] = 999
        self.assert_rejected(metadata, "upstream repository ID")

    def test_a_non_fork_is_rejected(self):
        metadata = self.metadata()
        metadata["fork"] = False
        self.assert_rejected(metadata, "fork relationship")

    def test_changed_fork_default_branch_is_rejected(self):
        metadata = self.metadata()
        metadata["default_branch"] = "main"
        self.assert_rejected(metadata, "fork default branch")

    def test_changed_parent_default_branch_is_rejected(self):
        metadata = self.metadata()
        metadata["parent"]["default_branch"] = "main"
        self.assert_rejected(metadata, "upstream default branch")

    def test_missing_parent_is_rejected_with_a_useful_message(self):
        metadata = self.metadata()
        metadata.pop("parent")
        self.assert_rejected(metadata, "upstream repository ID")

    def test_wrong_target_repository_is_rejected(self):
        metadata = self.metadata()
        metadata["full_name"] = "someone-else/ai-job-search"
        self.assert_rejected(metadata, "target repository")

    def test_permissions_and_non_destructive_merge_are_preserved(self):
        self.assertIn("permissions:\n  contents: write\n", self.workflow)
        self.assertNotIn("secrets.", self.workflow)
        self.assertIn('"repos/$GH_REPO/merge-upstream"', self.workflow)
        self.assertIn("No force/reset fallback was attempted.", self.workflow)


if __name__ == "__main__":
    unittest.main()
