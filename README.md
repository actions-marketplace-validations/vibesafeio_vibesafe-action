# VibeSafe Security Scan · GitHub Action

[![GitHub Action](https://img.shields.io/badge/GitHub%20Action-vibesafe--action-blue?logo=github)](https://github.com/vibesafeio/vibesafe-action)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Free, open-source security scanner for AI-generated code.** SAST + secret detection on every PR, with fix suggestions. 24-line YAML, 30-second setup.

Catches SQL Injection, XSS, hardcoded API keys, command injection, and more in vibe-coded apps — before they reach production.

---

## PR Comment Examples

**No vulnerabilities — Grade A Certified**

![Clean result](./docs/screenshot-clean.png)

**Vulnerabilities found — Grade F**

![Vulnerable result](./docs/screenshot-vuln.png)

---

## Install (30 seconds)

Add one file: `.github/workflows/vibesafe-scan.yml`

```yaml
name: VibeSafe Security Scan

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  vibesafe:
    name: Security Scan
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v4

      - name: Run VibeSafe scan
        uses: vibesafeio/vibesafe-action@v0
        with:
          domain: auto
```

PR comments are posted automatically. No extra configuration needed.

---

## Why VibeSafe?

| | VibeSafe | Snyk | CodeQL | Dependabot |
|---|---|---|---|---|
| Setup time | **30 seconds** (copy YAML) | 30min+ (account+API key+CLI) | 15min+ (build config) | Auto (deps only) |
| Cost | **Free** | $35K~$90K/yr | Free (public repos) | Free |
| PR comments | **File+line+code+fix guide** | File+line | ❌ | ❌ |
| Vibe coding optimized | **Domain-specific rules** | ❌ | ❌ | ❌ |
| Secret scanning | ✅ | ✅ (paid) | ❌ | ❌ |
| Merge blocking | ✅ `fail-on` | ✅ | ✅ | ❌ |

Built for vibe coders. No security team needed — 24 lines is all it takes.

### OWASP Juice Shop Benchmark

[OWASP Juice Shop](https://github.com/juice-shop/juice-shop) is a deliberately vulnerable test application.

| Metric | Result |
|--------|--------|
| Stack detected | Express + Socket.io (JS/TS/Python) |
| SAST findings | 18 (High 7 + Medium 11) |
| Exposed secrets | 18 (JWT tokens 9 + Supabase keys 9) |
| **Total findings** | **36** |
| **Score** | **0/100 Grade F** |

Reproduce it yourself: `./test/benchmark_juiceshop.sh`

---

## What It Scans

| Category | Details |
|----------|---------|
| **SAST** | SQL Injection, XSS, SSRF, IDOR, Command Injection, and more (OWASP Top 10) |
| **Secret Detection** | API keys, GitHub tokens, Stripe keys, AWS credentials, JWT tokens |
| **Domain Rules** | Auto-selects security rules based on your service type |
| **Fix Suggestions** | 32 patterns with actionable remediation for each finding |

Supported languages: JavaScript · TypeScript · Python · Java · Go · Ruby · PHP · Kotlin

---

## Domain Options

```yaml
domain: auto        # Auto-detect from code analysis (default)
domain: ecommerce   # Payments/orders — PCI DSS rules
domain: fintech     # Banking/transfers — AML rules
domain: healthcare  # Patient data — HIPAA rules
domain: platform    # SaaS/multi-tenant — JWT, RBAC
domain: game        # Game servers — WebSocket, client tampering
domain: education   # Student data — FERPA, COPPA
```

---

## Scoring

| Grade | Score | Meaning |
|-------|-------|---------|
| 🟢 **A** + ✅ Certified | 85 – 100 | No Critical or High findings |
| 🟢 **A** | 85 – 100 | Good |
| 🟡 **B** | 70 – 84 | Minor vulnerabilities |
| 🟠 **C** | 50 – 69 | Multiple medium findings |
| 🔴 **D / F** | 0 – 49 | Critical or High findings present |

**✅ Certified** badge is issued when Critical = 0, High = 0, and score >= 85.

---

## Outputs

Use scan results in downstream steps:

```yaml
- run: echo "Score: ${{ steps.vibesafe.outputs.score }}"
```

| Output | Description | Example |
|--------|-------------|---------|
| `score` | Security score (0-100) | `82` |
| `grade` | Grade (A-F) | `B` |
| `domain` | Detected domain | `fintech` |
| `certified` | Certified badge issued | `true` |
| `critical` | Critical count | `0` |
| `high` | High count | `2` |
| `medium` | Medium count | `5` |
| `low` | Low count | `3` |
| `total` | Total findings | `10` |

---

## Merge Blocking

**By default, VibeSafe fails the check (exit 1) when critical vulnerabilities are found.** GitHub branch protection will block the merge automatically.

```yaml
- uses: vibesafeio/vibesafe-action@v0
  with:
    domain: auto
    fail-on: high     # Block on high or critical (default: critical)
    # fail-on: none   # Never block, comment only
```

| `fail-on` | Blocks merge when |
|-----------|-------------------|
| `critical` (default) | Critical >= 1 |
| `high` | High >= 1 or Critical >= 1 |
| `medium` | Medium >= 1 or above |
| `low` | Any finding |
| `none` | Never (comment only) |

To enable: `Settings → Branches → Branch protection rules → Require status checks` → add **`Security Scan`**

---

## Pre-commit Hook (optional)

Catch secrets locally before they enter git history:

```bash
cp tools/pre_commit_hook.py .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

Blocks commits containing hardcoded API keys or tokens. If Semgrep is installed, SAST runs too.

Force commit: `git commit --no-verify`

---

## MCP Server — Real-time IDE Security (optional)

Detect secrets in real-time while coding in Claude Code or Cursor.

**Claude Code:**
```bash
claude mcp add vibesafe -- python /path/to/vibesafe/tools/mcp_server.py
```

**Cursor** (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "vibesafe": {
      "command": "python",
      "args": ["/path/to/vibesafe/tools/mcp_server.py"]
    }
  }
}
```

Tools: `vibesafe_check_secret` (text scan) and `vibesafe_scan_file` (file scan with fix suggestions).

---

## FAQ

**Does my code leave my environment?**
No. All scanning runs inside the GitHub Actions runner. No code is sent to VibeSafe servers.

**How much does it cost?**
Free. Only consumes GitHub Actions minutes (~20 seconds per scan). Public repos have unlimited free minutes.

**What languages are supported?**
All languages supported by Semgrep — JavaScript/TypeScript, Python, Java, Go, Ruby, PHP, Kotlin, and more.

---

<sub>Powered by [VibeSafe](https://vibesafe.dev) · Built with [Semgrep](https://semgrep.dev)</sub>
