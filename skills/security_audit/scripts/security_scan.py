#!/usr/bin/env python3
"""
Security scanner for Pico Claw.
Detects hardcoded secrets, PII exposure, and CV privacy issues.
Exits with code 1 if any CRITICAL finding exists.
"""

import ast
import json
import logging
import os
import re
import stat
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("security_scan")

PROJECT_DIR = None  # set by _find_project_root()

def _find_project_root():
    dir_ = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isdir(os.path.join(dir_, "cv")) or os.path.isfile(os.path.join(dir_, "AGENTS.md")):
            return dir_
        parent = os.path.dirname(dir_)
        if parent == dir_:
            break
        dir_ = parent
    return "/app"

def report(status, check, detail=""):
    prefix = {"pass": "[PASS]", "fail": "[FAIL]", "warn": "[WARN]"}.get(status, "[INFO]")
    msg = f"{prefix} {check}"
    if detail:
        msg += f" \u2014 {detail}"
    print(msg)
    return status == "pass"

def is_git_tracked(filepath):
    """Check if file is tracked by git."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", filepath],
            capture_output=True, cwd=PROJECT_DIR, timeout=5
        )
        return result.returncode == 0
    except:
        return False


def check_hardcoded_secrets():
    """
    Scan tracked files for patterns matching API keys, tokens, passwords.
    CRITICAL: Real secrets found in code (not in docker-compose or test files which have placeholder values).
    """
    SECRET_PATTERNS = [
        (r'(?i)(sk-[a-zA-Z0-9]{20,})', 'OpenAI-style API key'),
        (r'(?i)(rnd_[a-zA-Z0-9]{20,})', 'Render API key'),
        (r'(?i)(ghp_[a-zA-Z0-9]{36,})', 'GitHub personal access token'),
        (r'(?i)(gho_[a-zA-Z0-9]{36,})', 'GitHub OAuth token'),
        (r'(?i)(ghu_[a-zA-Z0-9]{36,})', 'GitHub user token'),
        (r'(?i)(-----BEGIN\s*(RSA|DSA|EC|PGP|OPENSSH)\s*PRIVATE\s*KEY-----)', 'Private key'),
        (r'(?i)(AKIA[0-9A-Z]{16})', 'AWS access key'),
        (r'["\']?(?:password|passwd|pwd)["\']?\s*[:=]\s*["\'][^"\']{6,}["\']', 'Possible password assignment'),
    ]
    EXCLUDE_PATTERNS = [
        r'docker-compose\.yml$',
        r'\.gitignore$',
    ]

    errors = []
    warnings = []

    for root, dirs, files in os.walk(PROJECT_DIR):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for f in files:
            if not any(f.endswith(ext) for ext in ['.py', '.sh', '.yml', '.yaml', '.conf', '.md', '.json']):
                continue
            path = os.path.join(root, f)
            if not is_git_tracked(path):
                continue

            should_exclude = False
            for pat in EXCLUDE_PATTERNS:
                if re.search(pat, path):
                    should_exclude = True
                    break
            if should_exclude:
                continue

            try:
                with open(path, 'r', errors='ignore') as fh:
                    content = fh.read()
            except:
                continue

            for pattern, desc in SECRET_PATTERNS:
                for match in re.finditer(pattern, content):
                    line_num = content[:match.start()].count('\n') + 1
                    line = content.split('\n')[line_num - 1]
                    if any(x in line.lower() for x in ['xxx', 'example', 'placeholder', 'cambiar-en', 'changeme', 'your_']):
                        warnings.append(f"{path}:{line_num} \u2014 {desc} (placeholder)")
                        continue
                    errors.append(f"{path}:{line_num} \u2014 {desc} (potential secret)")

            token_pattern = r'[a-fA-F0-9]{40,}'
            for match in re.finditer(token_pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                line = content.split('\n')[line_num - 1]
                if any(x in line for x in ['docker-compose', 'commit', 'sha', 'cambiar']):
                    continue
                if len(match.group()) >= 40 and not line.strip().startswith('#'):
                    errors.append(f"{path}:{line_num} \u2014 Possible secret token (hex {len(match.group())} chars)")

    if errors:
        for e in errors:
            report("fail", "Hardcoded secrets", e)
        return False
    for w in warnings:
        report("warn", "Hardcoded secrets", w)
    return report("pass", "Hardcoded secrets", "no secrets found in tracked files")


def check_pii_exposure():
    """
    Check tracked files for PII (phone numbers, emails) in non-spec files.
    cv/ is expected to have PII but should not be git-tracked.
    """
    PHONE_PATTERN = r'\b3\d{9}\b'
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'

    errors = []
    for root, dirs, files in os.walk(PROJECT_DIR):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for f in files:
            if not f.endswith(('.md', '.py', '.sh', '.yml', '.yaml', '.conf', '.txt')):
                continue
            path = os.path.join(root, f)
            if not is_git_tracked(path):
                continue

            try:
                with open(path, 'r', errors='ignore') as fh:
                    content = fh.read()
            except:
                continue

            for pattern, desc in [(PHONE_PATTERN, 'Colombian phone'), (EMAIL_PATTERN, 'Email address')]:
                for match in re.finditer(pattern, content):
                    line_num = content[:match.start()].count('\n') + 1
                    val = match.group()
                    if 'example.com' in val or 'example.org' in val:
                        continue
                    if '@' in val and len(val) < 8:
                        continue
                    errors.append(f"{path}:{line_num} \u2014 {desc}: {val}")

    if errors:
        for e in errors:
            report("warn", "PII exposure", e)
        return True
    return report("pass", "PII exposure", "no PII in tracked files")


def check_cv_in_git():
    """CRITICAL: CV with PII must NOT be git-tracked."""
    cv_path = os.path.join(PROJECT_DIR, "cv", "curriculum.md")
    if os.path.exists(cv_path):
        if is_git_tracked(cv_path):
            return report("fail", "CV in git", "cv/curriculum.md with PII is still git-tracked! Remove immediately")
        else:
            return report("pass", "CV in git", "cv/curriculum.md exists locally but is NOT git-tracked (in .gitignore)")
    else:
        return report("warn", "CV in git", "cv/curriculum.md not found locally (will be loaded from env var at runtime)")


def check_gitignore():
    path = os.path.join(PROJECT_DIR, ".gitignore")
    if not os.path.isfile(path):
        return report("fail", ".gitignore", "not found")
    content = open(path).read()
    checks = {
        "cv/": "cv directory (PII)",
        "data/": "data directory (SQLite DB)",
        "__pycache__": "Python cache",
        ".env": "env files",
    }
    missing = [desc for pattern, desc in checks.items() if pattern not in content]
    if missing:
        return report("fail", ".gitignore", f"missing entries: {', '.join(missing)}")
    return report("pass", ".gitignore", "exists with all required entries")


def check_dockerignore():
    path = os.path.join(PROJECT_DIR, ".dockerignore")
    if not os.path.isfile(path):
        return report("warn", ".dockerignore", "not found")
    content = open(path).read()
    if "cv/" not in content:
        return report("fail", ".dockerignore", "cv/ not excluded \u2014 CV will be baked into Docker image")
    return report("pass", ".dockerignore", "cv/ properly excluded")


def check_tracked_env():
    for root, dirs, files in os.walk(PROJECT_DIR):
        for f in files:
            if f.startswith('.env') or f.endswith('.env'):
                path = os.path.join(root, f)
                if is_git_tracked(path):
                    return report("fail", "Tracked .env file", f"{path} should not be in git")
    return report("pass", "Tracked .env files", "no .env files tracked")


def check_cv_not_in_dockerfile():
    """CV should not be COPY'd in Dockerfile; it should come from env var at runtime."""
    df_path = os.path.join(PROJECT_DIR, "Dockerfile")
    if not os.path.isfile(df_path):
        return report("warn", "Dockerfile CV check", "Dockerfile not found")
    content = open(df_path).read()
    if "COPY cv/" in content:
        return report("fail", "Dockerfile CV COPY", "cv/ is still COPY'd into Docker image \u2014 use PICOCLAW_CV_BASE64 env var instead")
    return report("pass", "Dockerfile CV COPY", "cv/ not baked into Docker image")


def check_cv_in_entrypoint():
    ep_path = os.path.join(PROJECT_DIR, "entrypoint.sh")
    if not os.path.isfile(ep_path):
        return report("warn", "Entrypoint CV check", "entrypoint.sh not found")
    content = open(ep_path).read()
    if "PICOCLAW_CV_BASE64" in content:
        return report("pass", "Entrypoint CV load", "entrypoint.sh loads CV from PICOCLAW_CV_BASE64 env var")
    return report("fail", "Entrypoint CV load", "entrypoint.sh does not load CV from env var")


def main():
    print("=" * 60)
    print("  Pico Claw \u2014 Security Audit")
    print("=" * 60)
    print()

    global PROJECT_DIR
    PROJECT_DIR = _find_project_root()

    checks = [
        ("Hardcoded secrets", check_hardcoded_secrets),
        ("PII exposure", check_pii_exposure),
        ("CV in git", check_cv_in_git),
        (".gitignore", check_gitignore),
        (".dockerignore CV exclusion", check_dockerignore),
        ("Tracked .env files", check_tracked_env),
        ("Dockerfile CV build", check_cv_not_in_dockerfile),
        ("Entrypoint CV load", check_cv_in_entrypoint),
    ]

    passed = 0
    failed = 0
    warned = 0

    for name, fn in checks:
        print()
        result = fn()
        if result is True:
            passed += 1
        elif result is False:
            failed += 1
        else:
            warned += 1

    print()
    print("=" * 60)
    print(f"  Result: {passed} passed, {failed} failed, {warned} warnings")
    print("=" * 60)

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
