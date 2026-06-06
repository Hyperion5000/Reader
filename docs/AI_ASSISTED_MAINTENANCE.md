# AI-Assisted Maintenance

Reader is maintained by a human primary maintainer. AI tools, including GPT/Codex-style workflows, are used as maintainer assistance, not as a replacement for maintainer responsibility.

## How AI Helps

- Reviewing code changes before commit.
- Finding edge cases in OCR and document conversion logic.
- Drafting and improving documentation.
- Preparing release notes and release checklists.
- Creating focused tests for regression-prone behavior.
- Triage planning for OCR quality, privacy, and release issues.

## Maintainer Responsibility

The maintainer remains responsible for:

- deciding what changes are accepted;
- running local tests and smoke checks;
- keeping private documents out of the repository;
- publishing releases;
- responding to issues and security reports;
- documenting limitations honestly.

## Privacy Boundary

Reader itself is designed to process user documents locally. AI-assisted maintenance should not involve uploading private user documents or private extracted text. Public issues and examples should use anonymized or synthetic samples.

## Why This Matters For Codex for OSS

Reader is a practical example of a small OSS project where AI assistance can reduce maintainer load in the exact areas Codex for OSS is meant to support: review, triage, testing, release preparation, and documentation.
