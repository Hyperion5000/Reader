# Codex for OSS Application Checklist

Use this checklist before submitting Reader to Codex for OSS.

## Repository

- [x] Repository is public.
- [x] MIT license is present and detected by GitHub.
- [x] README explains what Reader does and why it matters.
- [x] English summary is included.
- [x] Privacy model is documented.
- [x] Contribution, security, support, roadmap, triage, release process, and third-party notices are documented.
- [x] Issue templates and pull request template are present.
- [x] Dependabot is configured.
- [x] Portable build script is documented.
- [x] Synthetic examples are present.
- [x] Tag `v0.4.0` exists.

## Required Manual Steps

- [ ] Enable/fix GitHub Actions so CI is green.
- [ ] Create GitHub Release `v0.4.0`.
- [ ] Upload `release/Reader_Portable.exe` as a release asset.
- [ ] Add the SHA256 checksum from the local release folder.
- [ ] Open the first roadmap/triage issues from `docs/ISSUE_DRAFTS.md`.
- [ ] Add GitHub repository topics: `ocr`, `markdown`, `pdf`, `docx`, `windows`, `russian`, `tesseract`, `privacy`.
- [ ] Ask a few real users to download the release and give feedback.

## Application Fields

- GitHub repository URL: `https://github.com/Hyperion5000/Reader`
- Role: primary maintainer.
- Interest: ChatGPT Pro with Codex and API credits for OSS maintenance.
- Use of credits: PR review, maintainer automation, release workflow, test generation, OCR quality triage, security/code quality checks.

## Recommended Wording About AI Assistance

Do not say that the project is "fully prepared by GPT" as the main argument.

Use this instead:

```text
Reader was developed and prepared with AI-assisted maintainer workflows. I remain the primary maintainer; Codex/GPT helps with code review, tests, documentation, release preparation, and issue triage.
```

## Current Honest Position

Reader is a young project with a clear privacy-focused niche. The strongest argument is not adoption yet, but ecosystem importance for non-technical Windows users who need local Russian OCR and Markdown conversion without uploading sensitive documents.
