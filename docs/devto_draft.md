# I Built a Free Security Scanner for Vibe-Coded Apps. Here's What It Catches.

*Tags: security, webdev, ai, opensource*

---

You've probably seen the posts — "I scanned 100 vibe-coded apps and found 318 vulnerabilities," Lovable exposing 18,000 users' data, Supabase keys sitting in frontend bundles.

AI writes code that works. It doesn't write code that's safe.

I was building apps with Cursor and Claude, and I kept wondering: **am I shipping SQL injection without knowing it?** So I built a scanner. Then I open-sourced it as a GitHub Action.

## What is VibeSafe?

A free, open-source GitHub Action that scans every PR for:

- **SAST** — SQL injection, XSS, command injection, path traversal (OWASP Top 10)
- **Hardcoded secrets** — API keys, tokens, passwords, JWT secrets
- **Dependency vulnerabilities** — known CVEs in pip/npm packages
- **Vibe-coding-specific patterns** — CORS wildcards, Flask debug mode, JWT without expiry, Express without Helmet

It posts a PR comment with the exact file, line number, code snippet, and **how to fix it**.

## 30-Second Setup

One YAML file in your repo:

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
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: vibesafeio/vibesafe-action@v0
        with:
          domain: auto
```

That's it. No account, no API key, no server. Code never leaves your GitHub Actions runner.

## What It Actually Looks Like

When it finds vulnerabilities, you get this in your PR:

**🔴 CRITICAL** — `openai_key` `config.py:12`
> Hardcoded secret (OpenAI API Key) — move to environment variables
> **Fix:** Store API key in `.env` or GitHub Secrets: `os.environ.get('OPENAI_API_KEY')`

**🟠 HIGH** — `sql-injection` `app.py:24`
> User input used to construct SQL string
> **Fix:** Use parameterized queries: `cursor.execute("SELECT ... WHERE id = ?", (param,))`
> ```python
> sql = f"SELECT * FROM users WHERE name LIKE '%{query}%'"
> ```

It groups duplicate findings (subprocess injection on the same line = 1 entry, not 3), and filters false positives (Django rules won't fire on Flask apps).

## OWASP Juice Shop Benchmark

I ran VibeSafe against [OWASP Juice Shop](https://github.com/juice-shop/juice-shop), a deliberately vulnerable app:

| Metric | Result |
|--------|--------|
| SAST findings | 18 (High 7 + Medium 11) |
| Exposed secrets | 18 (JWT + Supabase keys) |
| **Total** | **36 findings, 0/100 Grade F** |

You can reproduce this yourself: `./test/benchmark_juiceshop.sh`

## Merge Blocking

By default, VibeSafe **fails the check** when critical vulnerabilities are found. Your branch protection can actually block the merge:

```yaml
- uses: vibesafeio/vibesafe-action@v0
  with:
    fail-on: high    # Block on high or critical
    # fail-on: none  # Comment only, never block
```

## What It Can't Do (honestly)

- DAST (dynamic analysis) — this is static only
- Business logic flaws — no SAST tool can catch "admin sees other users' data"
- Context-dependent SSRF — Semgrep's pattern matching has limits

It focuses on what AI **commonly gets wrong**: hardcoded secrets, injection, eval, debug flags.

## Custom Rules

Add your own Semgrep rules:

```yaml
- uses: vibesafeio/vibesafe-action@v0
  with:
    custom-rules: "./my-rules.yml,p/react"
```

If you build a cool ruleset, share it. That's how we make AI-generated code safer for everyone.

---

**GitHub**: https://github.com/vibesafeio/vibesafe-action

Free. Open source. 30 seconds to install. Your PR is the first test.
