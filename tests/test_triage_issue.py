import json
import os
import runpy
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "triage_issue.py"


class TriageDepthTest(unittest.TestCase):
    def test_depth_three_issue_is_declined_even_if_model_requests_followups(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                Path("issue.json").write_text(json.dumps({
                    "number": 1105,
                    "title": "batch",
                    "body": "[batch-depth:3]\nSeveral independent defects.",
                }), encoding="utf-8")
                output_path = Path("github-output.txt")
                os.environ["GITHUB_OUTPUT"] = str(output_path.resolve())
                os.environ["ANTHROPIC_BASE_URL"] = "https://model.invalid"
                os.environ["ANTHROPIC_API_KEY"] = "test"
                response = {
                    "model": "test-model",
                    "content": [{"type": "tool_use", "name": "file_followups", "input": {
                        "items": [{"title": "split", "body": "item"}]
                    }}],
                }

                class FakeResponse:
                    def __enter__(self): return self
                    def __exit__(self, *args): pass
                    def read(self): return json.dumps(response).encode()

                with patch.object(urllib.request, "urlopen", return_value=FakeResponse()) as urlopen:
                    try:
                        runpy.run_path(str(SCRIPT))
                    except SystemExit as exit_error:
                        self.assertEqual(exit_error.code, 0)

                output = dict(line.split("=", 1) for line in output_path.read_text(encoding="utf-8").splitlines())
                self.assertEqual(output, {
                    "action": "decline_request",
                    "count": "0",
                    "depth": "3",
                    "batch": "[]",
                })
                urlopen.assert_not_called()

                plan = json.loads(Path("triage-plan.json").read_text(encoding="utf-8"))
                self.assertEqual(plan["action"], "decline_request", f"expected decline_request, got {plan['action']}")
                self.assertEqual(plan["items"], [])
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
