# VibeSafe

**You built an app with AI. Is it safe to ship?**

[53% of AI-generated code has security vulnerabilities.](https://www.getautonoma.com/blog/vibe-coding-security-risks) [4,000+ accessibility lawsuits filed in 2024 alone.](https://www.audioeye.com/post/website-accessibility-in-2025/) Your AI doesn't check for any of this. VibeSafe does.

## **[Scan your app now →](https://vibesafe.onrender.com)**

Paste your GitHub URL. Get your safety score in 30 seconds. We'll tell you exactly what's wrong and give you a prompt to paste into your AI to fix everything.

**No signup. No install. Free.**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## How it works

1. **Paste** your GitHub repo URL
2. **30 seconds later** — safety score + every issue found
3. **Copy the AI Fix Prompt** → paste into Cursor, Claude, or ChatGPT
4. Your AI fixes everything. You ship safe.

That's it. You don't need to understand the issues. Your AI does.

---

## What it catches

| What AI gets wrong | Why it matters |
|---|---|
| Hardcoded API keys in your code | Anyone can find them and use your paid services |
| SQL injection, XSS, command injection | Attackers can steal your users' data |
| `<img>` without alt, inputs without labels | [64% of ADA lawsuits target small businesses](https://www.ecomback.com/ada-website-lawsuits-recap-report/2025-mid-year-ada-website-lawsuit-report) |
| Supabase without Row Level Security | All your database rows are public by default |
| Flask/Django debug mode in production | Gives attackers a code execution backdoor |

We scanned 10 open-source apps built with Lovable, Bolt, and Cursor. **8 out of 10 had issues.**

---

## What happens if you don't scan

These are real incidents from vibe-coded apps:

- **[Moltbook](https://www.theregister.com/2026/02/27/lovable_app_vulnerabilities/)** — 1.5 million auth tokens + 35,000 emails exposed
- **[Lovable app](https://www.theregister.com/2026/02/27/lovable_app_vulnerabilities/)** — 18,000 users' data leaked through misconfigured Supabase
- **[Escape research](https://escape.tech/blog/methodology-how-we-discovered-vulnerabilities-apps-built-with-vibe-coding/)** — 5,600 vibe-coded apps → 2,000+ vulnerabilities, 400+ exposed secrets

---

## Want this on every PR? (optional)

If you use GitHub for your code, you can add VibeSafe as an automatic check.

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

<details>
<summary>How it works (technical details)</summary>

## How it works

```
PR opened
  │
  ▼
┌─────────────────────────────────────────────┐
│  1. Stack Detection                         │
│     Reads imports, configs, package.json    │
│     → Flask? Express? Next.js? Supabase?    │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│  2. Rule Selection                          │
│     Domain (ecommerce/fintech/platform)     │
│     + Language + Framework → rule set       │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│  3. Scan (parallel)                         │
│                                             │
│  SAST ──────── SQL injection, XSS, eval()  │
│  Secrets ───── API keys, tokens, JWTs       │
│  SCA ───────── Known CVEs in dependencies   │
│  Config ────── Supabase RLS, Firebase rules │
│  Accessibility  <img> no alt, input no label│
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│  4. Score (0-100)                           │
│     Weighted by domain + severity           │
│     Framework conflict filtering            │
│     → Grade A/B/C/D/F + Certified badge     │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│  5. PR Comment                              │
│     File:line + code + fix + AI Fix Prompt  │
│     Fail gate → exit 1 if critical found    │
└─────────────────────────────────────────────┘
```

## What It Scans

| Layer | What AI gets wrong | VibeSafe catches |
|-------|-------------------|------------------|
| **Code** | `eval()`, f-string SQL, `shell=True`, XSS | SAST — OWASP Top 10 + custom rules |
| **Secrets** | Hardcoded API keys, tokens in frontend | 15 secret patterns |
| **Config** | Supabase without RLS, Firebase test mode | Config scanner |
| **Dependencies** | Known CVEs | SCA — pip-audit + npm audit |
| **Accessibility** | `<img>` without alt, `<input>` without label | WCAG 2.1 Level A rules |

</details>

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

**Is my code safe with you?**
The web scanner clones your repo, scans it, and deletes it immediately. Nothing is stored. The GitHub Action runs entirely inside GitHub's own servers.

**Does it cost money?**
No. Free forever. Open source.

**Do I need to know coding?**
No. Paste your GitHub URL, get results, copy the fix prompt into your AI. That's it.

**What languages does it support?**
JavaScript, TypeScript, Python, Java, Go, Ruby, PHP, Kotlin, and more.

---

**[Scan your app now →](https://vibesafe.onrender.com)**

<sub>Open source · Built with [Semgrep](https://semgrep.dev)</sub>
