---
name: Release checklist
about: Checklist for preparing a Reader release
title: "[Release] v"
labels: release
assignees: ""
---

## Checks

- [ ] Tests pass locally.
- [ ] `Reader_Portable.exe --check` passes.
- [ ] Control document folder processed successfully.
- [ ] `02_problem_files` is absent or reviewed.
- [ ] `CHANGELOG.md` updated.
- [ ] Portable exe built with `scripts/build_portable.ps1`.
- [ ] Exe uploaded to GitHub Releases.
- [ ] Release notes mention OCR/DOCX changes.
