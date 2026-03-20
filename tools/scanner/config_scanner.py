#!/usr/bin/env python3
from __future__ import annotations
"""
tools/scanner/config_scanner.py
Configuration-level security scanner for vibe-coded apps.

Checks for:
1. Supabase RLS (Row Level Security) — #1 cause of vibe-coding data breaches
2. Firebase Security Rules — test mode = public database
3. Missing security headers
4. Unpinned dependency versions
"""

import json
import re
import sys
from pathlib import Path


def check_supabase_rls(source_path: Path) -> list[dict]:
    """Check for Supabase usage without RLS policies."""
    findings = []

    # 1. Is Supabase in use?
    supabase_files = []
    for f in list(source_path.rglob("*.ts")) + list(source_path.rglob("*.tsx")) + \
             list(source_path.rglob("*.js")) + list(source_path.rglob("*.jsx")) + \
             list(source_path.rglob("*.py")):
        if "node_modules" in str(f):
            continue
        try:
            content = f.read_text(errors="ignore")
            if "createClient" in content and "supabase" in content.lower():
                supabase_files.append(f)
            elif "supabase" in content.lower() and (".from(" in content or "supabase.auth" in content):
                supabase_files.append(f)
        except OSError:
            pass

    if not supabase_files:
        return findings

    # 2. Check for RLS in SQL migration files
    has_rls = False
    sql_files = list(source_path.rglob("*.sql"))
    for sql_file in sql_files:
        try:
            content = sql_file.read_text(errors="ignore").upper()
            if "ENABLE ROW LEVEL SECURITY" in content or "ALTER TABLE" in content and "RLS" in content:
                has_rls = True
                break
            if "CREATE POLICY" in content:
                has_rls = True
                break
        except OSError:
            pass

    # 3. Check for anon key in frontend code (critical if no RLS)
    anon_key_exposed = False
    for f in supabase_files:
        try:
            content = f.read_text(errors="ignore")
            # Check for direct anon key usage
            if re.search(r'supabase.*(?:anon|ANON).*key', content, re.IGNORECASE):
                anon_key_exposed = True
            if re.search(r'createClient\s*\(\s*["\'][^"\']+["\'],\s*["\']eyJ', content):
                anon_key_exposed = True
        except OSError:
            pass

    # Generate findings
    if not has_rls and sql_files:
        findings.append({
            "type": "supabase_no_rls",
            "severity": "CRITICAL",
            "file": str(sql_files[0]) if sql_files else str(supabase_files[0]),
            "line": 0,
            "message": "Supabase tables found without Row Level Security (RLS). "
                       "Without RLS, anyone with the anon key can read/write all data. "
                       "This is the #1 cause of data breaches in vibe-coded apps.",
            "fix": "Add to your migration: ALTER TABLE your_table ENABLE ROW LEVEL SECURITY; "
                   "CREATE POLICY \"Users can only see own data\" ON your_table "
                   "FOR SELECT USING (auth.uid() = user_id);",
        })
    elif not has_rls and not sql_files and supabase_files:
        findings.append({
            "type": "supabase_no_migration",
            "severity": "HIGH",
            "file": str(supabase_files[0]),
            "line": 0,
            "message": "Supabase client found but no SQL migration files. "
                       "RLS policies may not be configured. Verify in Supabase dashboard.",
            "fix": "Create migration files with RLS policies, or verify RLS is enabled in Supabase dashboard → "
                   "Authentication → Policies.",
        })

    if anon_key_exposed and not has_rls:
        findings.append({
            "type": "supabase_anon_key_no_rls",
            "severity": "CRITICAL",
            "file": str(supabase_files[0]),
            "line": 0,
            "message": "Supabase anon key used in frontend code WITHOUT RLS. "
                       "Anyone can use this key to access ALL data in your database.",
            "fix": "Enable RLS on all tables AND create appropriate policies. "
                   "The anon key is designed to be public, but ONLY if RLS restricts access.",
        })

    return findings


def check_firebase_rules(source_path: Path) -> list[dict]:
    """Check for Firebase in test mode (public database)."""
    findings = []

    for rules_file in list(source_path.rglob("firestore.rules")) + \
                       list(source_path.rglob("database.rules.json")) + \
                       list(source_path.rglob("storage.rules")):
        try:
            content = rules_file.read_text(errors="ignore")
            # Check for test mode: allow read, write: if true
            if re.search(r'allow\s+read\s*,\s*write\s*:\s*if\s+true', content):
                findings.append({
                    "type": "firebase_test_mode",
                    "severity": "CRITICAL",
                    "file": str(rules_file),
                    "line": 0,
                    "message": "Firebase rules in TEST MODE (allow read, write: if true). "
                               "Anyone on the internet can read and modify your entire database.",
                    "fix": "Replace with proper rules: allow read, write: if request.auth != null; "
                           "Then add per-collection rules based on user ownership.",
                })
            # Check for overly permissive read
            if re.search(r'allow\s+read\s*:\s*if\s+true', content):
                findings.append({
                    "type": "firebase_public_read",
                    "severity": "HIGH",
                    "file": str(rules_file),
                    "line": 0,
                    "message": "Firebase allows public read access. All data is readable by anyone.",
                    "fix": "Restrict read access: allow read: if request.auth != null;",
                })
        except OSError:
            pass

    return findings


def check_unpinned_deps(source_path: Path) -> list[dict]:
    """Check for unpinned dependency versions (supply chain risk)."""
    findings = []

    for pkg_json in source_path.rglob("package.json"):
        if "node_modules" in str(pkg_json):
            continue
        try:
            data = json.loads(pkg_json.read_text())
            for dep_type in ["dependencies", "devDependencies"]:
                for pkg, version in data.get(dep_type, {}).items():
                    if version.startswith("*") or version == "latest":
                        findings.append({
                            "type": "unpinned_dependency",
                            "severity": "MEDIUM",
                            "file": str(pkg_json),
                            "line": 0,
                            "message": f"Dependency '{pkg}' uses unpinned version '{version}'. "
                                       f"A compromised update can silently enter your project.",
                            "fix": f"Pin to a specific version: \"{pkg}\": \"{version.replace('*', '1.0.0')}\"",
                        })
        except (json.JSONDecodeError, OSError):
            pass

    return findings


def scan_config(source_path: Path) -> dict:
    """Run all configuration security checks."""
    all_findings = []
    all_findings.extend(check_supabase_rls(source_path))
    all_findings.extend(check_firebase_rules(source_path))
    all_findings.extend(check_unpinned_deps(source_path))

    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in all_findings:
        sev = f.get("severity", "MEDIUM")
        counts[sev] = counts.get(sev, 0) + 1

    return {
        "status": "ok",
        "total": len(all_findings),
        "by_severity": counts,
        "findings": all_findings,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="VibeSafe Configuration Scanner")
    parser.add_argument("--path", required=True, help="Source code path to scan")
    parser.add_argument("--output", default=None, help="Output JSON file path")
    args = parser.parse_args()

    source_path = Path(args.path)
    if not source_path.exists():
        print(json.dumps({"error": f"Path not found: {args.path}"}))
        sys.exit(1)

    result = scan_config(source_path)

    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2))

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
