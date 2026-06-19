from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class RepositoryHygieneTests(unittest.TestCase):
    def test_required_oss_files_exist(self) -> None:
        required_paths = [
            "README.md",
            "LICENSE",
            "docs/project/CHANGELOG.md",
            "docs/project/CONTRIBUTING.md",
            "docs/project/SECURITY.md",
            "docs/project/SUPPORT.md",
            "docs/project/CODE_OF_CONDUCT.md",
            "docs/project/THIRD_PARTY_NOTICES.md",
            "docs/project/ROADMAP.md",
            "docs/project/BENCHMARK.md",
            "docs/project/EXAMPLES.md",
            "benchmarks/run_ocr_benchmark.py",
            "docs/project/FAQ.md",
            "docs/project/RELEASE_PROCESS.md",
            ".github/PULL_REQUEST_TEMPLATE.md",
            ".github/dependabot.yml",
            ".github/workflows/ci.yml",
            "scripts/build_portable.ps1",
            "scripts/write_release_checksum.ps1",
            "examples/sample_result/00_ALL_DOCUMENTS.md",
        ]

        missing = [path for path in required_paths if not (REPO_ROOT / path).exists()]

        self.assertEqual(missing, [])

    def test_tracked_root_files_stay_minimal(self) -> None:
        tracked = subprocess.check_output(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
        ).splitlines()
        allowed_root_files = {"README.md", "LICENSE", ".gitignore"}
        root_files = {
            path
            for path in tracked
            if "/" not in path and "\\" not in path
        }

        self.assertEqual(root_files - allowed_root_files, set())

    def test_forbidden_files_are_not_tracked(self) -> None:
        tracked = subprocess.check_output(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
        ).splitlines()
        forbidden_fragments = [
            "Reader_Portable.exe",
            "runtime/",
            "release/",
            "markdown_result_",
            "benchmark_result_",
        ]
        forbidden_suffixes = (".pdf", ".doc", ".docx")

        bad_paths = [
            path
            for path in tracked
            if any(fragment in path for fragment in forbidden_fragments)
            or path.lower().endswith(forbidden_suffixes)
        ]

        self.assertEqual(bad_paths, [])

    def test_readme_points_to_release_and_privacy_docs(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("https://github.com/Hyperion5000/Reader/releases", readme)
        self.assertIn("Reader does not upload documents to the internet", readme)
        self.assertIn("docs/project/RELEASE_PROCESS.md", readme)


if __name__ == "__main__":
    unittest.main()
