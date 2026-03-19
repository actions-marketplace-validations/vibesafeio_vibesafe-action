# Harness: Self-Verification Protocol

This protocol applies to ALL code changes. Run BEFORE committing.

## Phase 1: Execution Verification (Required)

Run the changed code to confirm it works.

```bash
# Python tool changes
python3 <changed_file.py> --help

# PR comment changes
python3 -c "from tools.report.pr_commenter import build_comment_body; print('OK')"

# Pipeline changes
bash test/harness.sh quick

# Docker changes
docker build -f Dockerfile.action -t vibesafe-action-test .
```

"Code complete ≠ feature complete". 12 bugs came from untested code in this project.

## Phase 2: Silent Failure Check

Most dangerous bugs in this project were **errors that produced empty results instead of errors**:
- `--config` flag bug: Semgrep loaded half the rules, no error
- `capture_output=True` bug: SAST returned 0 findings in Docker, pipeline "succeeded"
- SARIF `level=None` bug: high severity treated as low, score still calculated
- `git safe.directory` bug: Semgrep exit 0 with 0 files scanned

Check for:
- subprocess calls that silently return empty results on failure
- Files that don't exist → default to empty list/dict
- JSON keys missing → replaced with empty values
- If any apply: add warning log or document the intentional fallback

## Phase 3: Environment Compatibility

- [ ] Python 3.9 compatible? (`from __future__ import annotations` required)
- [ ] Docker behavior differs from local? (file paths, stderr, network)
- [ ] New external package added? (forbidden — stdlib + existing deps only)

## Phase 4: Doom Loop Detection

- Editing the same file 3+ times → stop and rethink approach
- Fixing the same error 2+ different ways → stop and analyze root cause

## Phase 5: Self-Verification Report

Output after every meaningful change:

```
## Self-Verification Report
**Changed files:** (list)
**Execution verified:** ✅/❌ — (which command)
**Silent failure risk:** none / exists — (where, why allowed)
**Environment compat:** ✅/❌ — (Python 3.9, Docker)
**Doom loop:** none / occurred — (how escaped)
**Most fragile part:** (one line)
**Unchecked:** (one line)
**Docker rebuild needed:** yes / no
```

Do not commit without this report.
