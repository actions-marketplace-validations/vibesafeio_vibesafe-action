# VibeSafe — Security Scanner for Vibe-Coded Apps

> **If you're vibe coding without a security scan, your app is probably vulnerable right now.** Not maybe. [53% of AI-generated code ships with security holes.](https://www.getautonoma.com/blog/vibe-coding-security-risks)

![VibeSafe PR Comment](./docs/screenshot-vuln.png)

**You're probably not scanning at all.** Most vibe coders aren't. VibeSafe adds a security check to every PR — 30 seconds to set up, then it runs automatically forever.

| Problem | VibeSafe catches it |
|---------|-------------------|
| AI hardcodes your API keys | **Secret detection** — flags the exact line + generates `.env.example` |
| AI skips Supabase RLS | **Config scan** — catches missing Row Level Security (the Lovable/Moltbook breach cause) |
| AI writes `eval()` and SQL injection | **SAST** — 500+ rules including 6 vibe-coding-specific patterns |
| You don't know how to fix it | **AI Fix Prompt** — copy-paste into Cursor/Claude, it fixes everything |
| Vulnerable deps slip in | **SCA** — checks pip and npm packages for known CVEs |

**Free. Open source. 30-second setup. No account needed.**

[![GitHub Action](https://img.shields.io/badge/GitHub%20Action-vibesafe--action-blue?logo=github)](https://github.com/vibesafeio/vibesafe-action)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Who this is for

- **Vibe coders** — building with Cursor, Claude, Copilot, Lovable, Bolt
- **Solo developers** — shipping without a security team
- **Startups** — moving fast but want to avoid the next Lovable/Moltbook breach

## See it work

1. Copy the YAML below → open a PR
2. 20 seconds later, this comment appears:

![VibeSafe PR Comment](./docs/screenshot-vuln.png)

3. Expand **"Fix with AI"** → copy the prompt → paste into Cursor
4. Your AI fixes everything
5. Push again → **100/100 Grade A ✅ Certified**

---

## Install (30 seconds)

Copy this file to `.github/workflows/vibesafe-scan.yml`:

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

## What happens if you don't scan

These are real incidents from vibe-coded apps:

- **[Moltbook](https://www.theregister.com/2026/02/27/lovable_app_vulnerabilities/)** — 1.5 million auth tokens + 35,000 emails exposed. The app worked perfectly. The security didn't.
- **[Lovable app](https://www.theregister.com/2026/02/27/lovable_app_vulnerabilities/)** — One app leaked 18,000 users' data through misconfigured Supabase RLS.
- **[Escape research](https://escape.tech/blog/methodology-how-we-discovered-vulnerabilities-apps-built-with-vibe-coding/)** — 5,600 vibe-coded apps scanned → 2,000+ vulnerabilities, 400+ exposed secrets, 175 PII leaks.

Your app might be next. Or it might be fine. **The only way to know is to scan it.**

<details>
<summary>How does VibeSafe compare to other tools?</summary>

| | VibeSafe | Snyk | CodeQL | Dependabot |
|---|---|---|---|---|
| Setup time | **30 seconds** | 30min+ | 15min+ | Auto (deps only) |
| Cost | **Free** | $35K+/yr | Free (public) | Free |
| PR comments with fix guide | ✅ | Partial | ❌ | ❌ |
| AI code patterns | ✅ | ❌ | ❌ | ❌ |
| Merge blocking | ✅ | ✅ | ✅ | ❌ |

But honestly — if you're reading this, you're probably not using any of these. That's the problem VibeSafe solves.

</details>

### OWASP Juice Shop Benchmark

We scanned [OWASP Juice Shop](https://github.com/juice-shop/juice-shop) (deliberately vulnerable app): **36 findings, 0/100 Grade F.** Reproduce: `./test/benchmark_juiceshop.sh`

---

## What It Scans

| Layer | What AI gets wrong | VibeSafe catches |
|-------|-------------------|------------------|
| **Code** | `eval()`, f-string SQL, `shell=True`, XSS | SAST — OWASP Top 10 + 6 vibe-coding rules |
| **Secrets** | Hardcoded API keys, tokens in frontend | 15 secret patterns + `.env.example` generation |
| **Config** | Supabase without RLS, Firebase test mode | Config scanner — checks DB security policies |
| **Dependencies** | Unpinned versions, known CVEs | SCA — pip-audit + npm audit |
| **Headers** | Missing CORS, CSRF, Helmet | Custom rules for Express/Flask/Next.js |

Supported languages: JavaScript · TypeScript · Python · Java · Go · Ruby · PHP · Kotlin

## 🤖 AI Fix Prompt — the feature vibe coders actually need

Other scanners say "you have 10 vulnerabilities." VibeSafe says **"paste this into Cursor and they're all fixed."**

Every PR comment includes a collapsible **"Fix with AI"** section:

```
Fix these security issues in my code:
- CRITICAL: config.py:5 — Store API key in .env: os.environ.get('OPENAI_API_KEY')
- HIGH: app.py:24 — Use parameterized queries: cursor.execute("SELECT ... WHERE id = ?", (param,))
- HIGH: app.py:67 — Remove shell=True: subprocess.run(shlex.split(cmd))

Move all hardcoded secrets to environment variables.
Generate a .env.example with placeholder values.
```

Copy. Paste into your AI. Done. **You don't fix code — your AI does. VibeSafe tells it what to fix.**

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

## Diff-Only Scanning

**VibeSafe automatically scans only new code introduced by the PR** — not the entire repo. This means:
- Faster scans (seconds, not minutes)
- No noise from pre-existing issues
- Only shows vulnerabilities YOU introduced
- Works automatically when triggered by `pull_request` events

This is the same `--baseline-commit` approach used by Semgrep's paid tier, but free.

---

## Custom Rules

Add your own Semgrep rules on top of VibeSafe's defaults:

```yaml
- uses: vibesafeio/vibesafe-action@v0
  with:
    domain: auto
    custom-rules: "./my-rules.yml,p/react,https://example.com/team-rules.yml"
```

Share rules with the community — a YAML file is all it takes. Examples:
- `p/react` — React-specific rules from Semgrep registry
- `./security/fintech-rules.yml` — your team's custom rules
- URL to a shared ruleset

---

## Dynamic Badge for Your README

Add an auto-updating VibeSafe badge to your README. Add this step after VibeSafe scan:

```yaml
- name: Update VibeSafe badge
  if: github.ref == 'refs/heads/main'
  uses: schneegans/dynamic-badges-action@v1.7.0
  with:
    auth: ${{ secrets.GIST_SECRET }}
    gistID: YOUR_GIST_ID
    filename: vibesafe-badge.json
    label: VibeSafe
    message: "${{ steps.vibesafe.outputs.score }}/100 ${{ steps.vibesafe.outputs.grade }}"
    color: ${{ steps.vibesafe.outputs.grade == 'A' && 'brightgreen' || steps.vibesafe.outputs.grade == 'B' && 'green' || steps.vibesafe.outputs.grade == 'C' && 'yellow' || 'red' }}
```

Then in your README:
```markdown
![VibeSafe](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/YOUR_USER/YOUR_GIST_ID/raw/vibesafe-badge.json)
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
