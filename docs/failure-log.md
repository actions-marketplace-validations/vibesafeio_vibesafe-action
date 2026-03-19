# Failure Log

When a bug is found, add an entry here. When patterns repeat, add to Phase 2 checklist in harness-protocol.md.

## 2026-03-18: git safe.directory not set → Semgrep 0 findings
- **Root cause**: Docker container didn't trust mounted /github/workspace → `git ls-files` exit 128 → Semgrep scanned 0 files
- **Lesson**: Docker + git tools = always set safe.directory. Semgrep exits 0 on this failure (Phase 2 silent failure)
- **Defense added**: `git config --global --add safe.directory` in action_entrypoint.sh

## 2026-03-18: Flask app triggers Django false positives (4 findings)
- **Root cause**: detect_stack only checked requirements.txt → import-based framework not detected → framework conflict filter didn't activate
- **Lesson**: Many projects don't have dependency files. Need content-based detection.
- **Defense added**: Python import scanning in sast_runner.py detect_stack

## 2026-03-19: Auto-PRs sent to external repos (Priority 1-2 violation)
- **Root cause**: KPI pressure → sent VibeSafe workflow PRs to firetix, VibesDIY, mpaepper repos automatically
- **Result**: 2 rejected, 1 triggered Vercel deploy on someone else's infra (cost violation 1-4)
- **Lesson**: Irreversible external actions must NEVER be automated. Security tool sending spam PRs destroys trust.
- **Defense added**: Priority 1-2 rule in CLAUDE.md. All 3 PRs closed with apology.

## 2026-03-19: Action exit code always 0 → merge blocking impossible
- **Root cause**: action_entrypoint.sh always exited 0 regardless of findings
- **Result**: README said "set as required check to block merges" but it never actually blocked
- **Lesson**: Core security feature (blocking) must be E2E tested. README claims must match behavior.
- **Defense added**: `fail-on` input (default: critical). exit 1 when threshold exceeded.
