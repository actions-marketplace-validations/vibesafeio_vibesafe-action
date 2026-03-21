---
title: I asked Claude to build me an app. It had 36 security holes.
published: false
tags: vibecoding, security, accessibility, ai, opensource
---

Last week I vibe-coded a Flask app with Cursor. Login, dashboard, API — the whole thing. Took about 20 minutes. Everything worked.

Then I got curious and ran a security scanner on it.

**Score: 0 out of 100. Grade F.**

Here's what the AI wrote for me without me asking:

- `eval(user_input)` — lets anyone run arbitrary code on my server
- `subprocess.run(cmd, shell=True)` — command injection
- `f"SELECT * FROM users WHERE id = {user_id}"` — SQL injection
- A JWT secret hardcoded as `"secret123"` right in the source

Every single one of these worked perfectly. The app ran fine. But anyone who knew what to look for could've owned my entire server.

## This isn't just me

I started looking at other vibe-coded projects on GitHub. Apps built with Lovable, Bolt, Cursor. I scanned 10 of them.

8 out of 10 had issues. Not just security — accessibility too. Images without alt text, form inputs without labels, clickable divs that screen readers can't see. Stuff that gets you sued.

That's not hypothetical. 4,000+ ADA web accessibility lawsuits were filed in 2024. 64% targeted businesses under $25M revenue. Settlements run $5K–$75K. AI doesn't know about any of this. It just writes code that works for sighted users with a mouse.

The pattern is always the same: AI picks the shortest path to "it works." The shortest path is almost always the least safe path.

## What I did about it

I built a GitHub Action that runs on every PR. It checks for the stuff AI loves to generate — security vulnerabilities, accessibility violations, patterns that work but shouldn't ship.

It's not magic. It's pattern matching with Semgrep. Same code always gets the same result. No AI involved in the scanning, ironically.

Setup is one YAML file:

```yaml
name: VibeSafe
on: [pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: vibesafeio/vibesafe-action@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

It posts a comment on your PR with what it found, where it found it, and how to fix it. If you use an AI coding assistant, you can copy the fix suggestions and paste them right back.

## What it doesn't do

I want to be honest about this:

- It can't catch business logic bugs. If your auth flow is conceptually wrong, no pattern matcher will know.
- It's static analysis. It reads code, it doesn't run your app.
- It won't catch everything. It catches the common stuff — the stuff AI generates over and over.

## Why I'm sharing this

I'm not a security expert. That's exactly why I needed this. If you're vibe coding and shipping without a second look at what the AI wrote, you might want to at least know what's in there.

Repo: https://github.com/vibesafeio/vibesafe-action

It's free, open source, no account needed. If you try it and it catches something weird, I'd genuinely like to hear about it.
