# Market Validation — 2026-03-20

## Current Metrics (VibeSafe)
- Stars: 0 | Forks: 0 | Views: 2 | **Clones: 325 (99 unique)**
- OKKY post: https://okky.kr/articles/1553873 (engagement TBD)
- Marketplace: not yet published (needs manual UI action)

## Demand Signals Found

### 1. Active competitors = proven market
| Tool | Focus | Pricing | Traction |
|------|-------|---------|----------|
| **VibeWrench** | DAST scanner for vibe apps + fix prompts | Free | Featured on DEV.to ("318 vulns in 100 apps") |
| **ZeriFlow** | 80+ checks, source code analysis | Freemium ($?) | Blog comparing vs Snyk/SonarCloud |
| **CursorGuard** | GitHub App for Cursor/Lovable code | Unknown | Dedicated domain, principal engineers |
| **Vibe App Scanner** | Deployed app scanner (Supabase RLS, auth) | Unknown | Reports on Lovable security |
| **SecureVibes** | Claude multi-agent scanner | Free (API cost) | 200+ stars |

**5+ funded/active competitors = market exists.** But none of them are:
- Free GitHub Action (most are web/CLI tools)
- PR-native (comments with file:line:fix)
- Domain-aware (ecommerce vs fintech rules)

### 2. Content virality = user interest
- "I Scanned 100 Vibe-Coded Apps" (DEV.to) — likely 10K+ views based on comment activity
- "53% of AI Code Has Security Holes" (Autonoma) — content marketing working
- Lovable security report — Reddit community engagement
- Multiple "Best Security Scanner for Vibe Coders" comparison articles

### 3. Where users are asking
- **Reddit**: r/webdev, r/cursor, r/lovable — security concerns in comments
- **DEV.to**: vibe coding tag has active security discussion
- **Twitter/X**: "vibe coding security" tweets getting engagement
- **YouTube**: tutorials on securing AI-generated code

### 4. Gap VibeSafe uniquely fills
Competitors are either:
- **Web-based** (VibeWrench, ZeriFlow, VAS) → requires URL, not CI/CD integrated
- **Expensive** (CursorGuard, Snyk) → not for solo vibe coders
- **AI-dependent** (SecureVibes) → requires API key + cost

VibeSafe is the ONLY free, PR-native, GitHub Action scanner with fix suggestions.

## Where to Post (priority by audience match)

### Tier 1 — Direct audience (vibe coders)
1. **DEV.to** — write "I scanned my vibe-coded app with VibeSafe" style post
2. **Reddit r/webdev** — "Free GitHub Action that scans AI-generated code for vulnerabilities"
3. **Reddit r/cursor** — Cursor users care about code quality
4. **Hacker News (Show HN)** — technical audience, values open source

### Tier 2 — Developer communities
5. **Product Hunt** — "VibeSafe — Free security scanner for AI-generated code"
6. **GeekNews** (Korean) — draft ready, publish after 1-week wait (~3/26)
7. **Twitter/X** — thread format with screenshot

### Tier 3 — Security communities
8. **Reddit r/netsec** — focus on the OWASP benchmark angle
9. **Reddit r/devsecops** — focus on CI/CD integration

## Recommended Next Step
Write a DEV.to post (English, largest vibe coding audience) modeled after
the viral "I Scanned 100 Vibe-Coded Apps" format. User must publish manually.
