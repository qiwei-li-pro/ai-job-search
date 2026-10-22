"""Bun's HTTP clients need Web API libraries without disabling strict checks."""
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent


class PortalWebApiTypesTests(unittest.TestCase):
    def test_http_client_projects_include_web_api_types(self):
        for name in ("jobbank-search", "jobdanmark-search", "jobindex-search", "jobnet-search"):
            with self.subTest(portal=name):
                path = ROOT / ".agents/skills" / name / "cli/tsconfig.json"
                options = json.loads(path.read_text(encoding="utf-8"))["compilerOptions"]
                self.assertIn("ESNext", options["lib"])
                self.assertIn("DOM", options["lib"])
                self.assertIn("DOM.Iterable", options["lib"])
                self.assertIs(options["strict"], True)
                self.assertIs(options["noImplicitAny"], True)
                self.assertIs(options["strictNullChecks"], True)


if __name__ == "__main__":
    unittest.main()
