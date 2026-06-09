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
            "CHANGELOG.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "SUPPORT.md",
            "CODE_OF_CONDUCT.md",
            "THIRD_PARTY_NOTICES.md",
            "ROADMAP.md",
            "docs/AI_ASSISTED_MAINTENANCE.md",
            "docs/CODEX_FOR_OSS_APPLICATION_CHECKLIST.md",
            "docs/FAQ.md",
            "docs/GITHUB_RELEASE_DRAFT_v0.4.1.md",
            "docs/ISSUE_DRAFTS.md",
            "docs/OPENAI_CODEX_OSS_APPLICATION_DRAFT.md",
            "docs/RELEASE_NOTES_v0.4.1.md",
            "docs/RELEASE_PROCESS.md",
            "docs/TRIAGE_PLAN.md",
            ".github/PULL_REQUEST_TEMPLATE.md",
            ".github/dependabot.yml",
            ".github/workflows/ci.yml",
            "scripts/build_portable.ps1",
            "scripts/write_release_checksum.ps1",
            "examples/sample_result/00_ALL_DOCUMENTS.md",
        ]

        missing = [path for path in required_paths if not (REPO_ROOT / path).exists()]

        self.assertEqual(missing, [])

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
        self.assertIn("docs/AI_ASSISTED_MAINTENANCE.md", readme)
        self.assertIn("docs/RELEASE_PROCESS.md", readme)


if __name__ == "__main__":
    unittest.main()
