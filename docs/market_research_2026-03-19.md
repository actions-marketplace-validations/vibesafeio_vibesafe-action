# Market Research — 2026-03-19

## 1. Vibe Coding Security Landscape

### Problem Size
- 24.7% of AI-generated code has security flaws (2026 data)
- Lovable: single app exposed 18,000 users, 16 vulnerabilities (6 critical)
- Moltbook: 1.5M API keys + 35K emails exposed
- Escape: 5,600 apps → 2,000+ vulns, 400+ exposed secrets
- Palo Alto Unit 42: "Coding agents optimize for making code run, not making code safe"

### What developers need (from research)
1. **Pre-commit / CI pipeline scanners** that block hardcoded secrets and dangerous patterns
2. **Automated security checks agents can run** — pre-commit conditions
3. **Code diff review** — not just full repo scans
4. **Dependency chain auditing** — transitive deps never reviewed

### VibeSafe coverage vs needs
| Need | VibeSafe | Gap |
|------|----------|-----|
| CI pipeline scanner | ✅ GitHub Action | - |
| Block secrets | ✅ secret_scanner + fail-on | - |
| Block dangerous patterns | ✅ SAST + fail-on | - |
| Pre-commit | ✅ pre_commit_hook.py | - |
| Agent integration | ✅ MCP server | - |
| Code diff review | ❌ Full repo scan only | **GAP** |
| Dependency scanning (SCA) | ❌ Not implemented | **GAP** |
| Container scanning | ❌ Not implemented | Out of scope |

## 2. Competitor Analysis Update

### Free GitHub Action Security Scanners
| Tool | Stars | Focus | PR Comments | Fix Suggestions | Vibe Coding |
|------|-------|-------|-------------|-----------------|-------------|
| **Gitleaks** | 24,400+ | Secrets only | ❌ | ❌ | ❌ |
| **Semgrep Action** | 11,000+ | SAST | ✅ (paid tier) | ❌ | ❌ |
| **Trivy** | 25,000+ | Dependencies + containers | ❌ | ❌ | ❌ |
| **ShiftLeft Scan** | 2,000+ | Multi-scanner | ❌ | ❌ | ❌ |
| **CodeQL** | (GitHub native) | SAST | Annotations | ❌ | ❌ |
| **VibeSafe** | 0 | SAST + secrets | ✅ Full detail | ✅ 32 patterns | ✅ |

### VibeSafe unique advantages
1. **Only free tool** with PR comments including file+line+snippet+fix suggestions
2. **Only tool** with domain-specific rule selection
3. **Only tool** with framework false positive filtering
4. **Only tool** with custom-rules input for community rulesets
5. Simplest setup (24-line YAML vs Semgrep's account requirement)

### Key gap: DIFF-ONLY SCANNING
Every competitor scans full repos. None scan just the PR diff. This is a massive opportunity:
- Faster scans (seconds vs minutes)
- Only shows NEW vulnerabilities the PR introduces
- No noise from pre-existing issues
- Matches how developers think: "what did I break?"

## 3. OpenClaw Opportunity

### OpenClaw Security Crisis (current)
- CVE-2026-25253: remote code execution
- 824+ confirmed malicious skills out of 10,700+ (20% infection rate)
- 30,000+ internet-exposed instances without auth
- VirusTotal deal for skill scanning, but doesn't catch prompt injection

### VibeSafe opportunity
1. **OpenClaw skill repos need security scanning** — malicious code in YAML/Python skills
2. **OpenClaw users are developers** who already use GitHub → natural VibeSafe audience
3. **"VibeSafe for OpenClaw Skills"** positioning — dedicated ruleset for skill security
4. OpenClaw's problem = VibeSafe's marketing message

## 4. First Principles → MECE Action Plan

### Root question: "Why would someone install VibeSafe instead of alternatives?"

Decomposition:
```
Install VibeSafe
├── Awareness (knows it exists)
│   ├── Organic search (GitHub topics, Marketplace) ← DONE
│   ├── Community posts (GeekNews, OKKY, Reddit, HN) ← BLOCKED (user action)
│   └── Word of mouth (badge + share page) ← TODO
├── Trial (tries it)
│   ├── Setup friction < 1 min ← DONE (24-line YAML)
│   └── First scan shows value ← DONE (findings + fix suggestions)
├── Retention (keeps using)
│   ├── False positive rate low ← DONE (framework filtering)
│   ├── Actionable output ← DONE (fix suggestions)
│   ├── Doesn't break workflow ← DONE (fail-on configurable)
│   └── Improves over time ← TODO (diff-only, SCA, custom rules ecosystem)
└── Advocacy (tells others)
    ├── Shareable result ← TODO (badge + share page)
    ├── Customizable ← DONE (custom-rules input)
    └── Community ← TODO (ruleset registry)
```

### Priority execution order (impact × feasibility):
1. **DIFF-ONLY scanning** — biggest competitive moat, no competitor does this
2. **Badge endpoint** — shareable, drives word of mouth
3. **SCA (dependency scanning)** — second most-requested after SAST
4. **OpenClaw skill ruleset** — ride the security crisis wave
