# Release Process

Reader releases are distributed through GitHub Releases, not through tracked `.exe` files in the repository.

## Prepare

1. Make sure the working tree is clean except ignored local files.
2. Run local checks:

```powershell
python -m py_compile src/reader/markdown_converter.py
python -m unittest discover -s tests
Reader_Portable.exe --check
```

3. Run a real-folder smoke test with anonymized or local-only documents.
4. Confirm that generated `markdown_result_...` folders, `runtime/`, `release/`, and `.exe` files are not tracked by Git.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_portable.ps1
```

Expected output:

```text
release/Reader_Portable.exe
```

## Tag

```powershell
git tag -a v0.4.0 -m "Reader v0.4.0"
git push origin v0.4.0
```

## Publish

1. Open GitHub Releases.
2. Create a release from the version tag.
3. Use the release notes from `docs/RELEASE_NOTES_v0.4.0.md`.
4. Upload `release/Reader_Portable.exe`.
5. Download the uploaded exe on Windows and run:

```powershell
Reader_Portable.exe --check
```

## After Release

- Confirm the README release link works.
- Open or update the release checklist issue.
- Record known limitations in the release notes.
