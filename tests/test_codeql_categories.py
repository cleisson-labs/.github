import copy
import json
import subprocess
import unittest
from pathlib import Path

FILTER = Path(__file__).resolve().parents[1] / "tools" / "codeql-legacy-category.jq"
LEGACY = ".github/workflows/codeql.yml:analyze"


def transform(report, legacy=LEGACY):
    return subprocess.run(
        [
            "jq",
            "-e",
            "--arg",
            "canonical",
            "/language:rust/",
            "--arg",
            "legacy",
            legacy,
            "-f",
            str(FILTER),
        ],
        input=json.dumps(report),
        capture_output=True,
        text=True,
        check=False,
    )


class CodeQLCategoryTests(unittest.TestCase):
    def setUp(self):
        self.run_data = {
            "tool": {"driver": {"name": "CodeQL"}},
            "automationDetails": {
                "id": "/language:rust/",
                "description": {"text": "original"},
            },
            "results": [
                {
                    "ruleId": "example",
                    "partialFingerprints": {"primaryLocationLineHash": "abc"},
                }
            ],
        }
        self.report = {"version": "2.1.0", "runs": [self.run_data]}

    def test_keeps_the_canonical_run_and_copies_every_field_except_the_category(self):
        expected = copy.deepcopy(self.report)
        alias = copy.deepcopy(self.run_data)
        alias["automationDetails"]["id"] = LEGACY + "/"
        expected["runs"].append(alias)
        for value in (LEGACY, LEGACY + "/"):
            with self.subTest(value=value):
                result = transform(self.report, value)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), expected)

    def test_rejects_incompatible_input(self):
        for runs in (
            [],
            [self.run_data, self.run_data],
            [dict(self.run_data, automationDetails={"id": "/language:python/"})],
            [dict(self.run_data, tool={"driver": {"name": "Other"}})],
        ):
            with self.subTest(runs=runs):
                self.assertNotEqual(transform({"runs": runs}).returncode, 0)
        for category in ("", "/language:rust", "./other", LEGACY + "\nother"):
            with self.subTest(category=category):
                self.assertNotEqual(transform(self.report, category).returncode, 0)
