#!/usr/bin/env python3
"""
Pre-flight validation script. Run before every commit or push.
Checks Python syntax, YAML validity, Dockerfile, spec coverage, constitution rules, etc.
"""

import ast
import os
import subprocess
import sys
import yaml

def _find_project_root():
    dir_ = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isdir(os.path.join(dir_, "cv")) and os.path.isfile(os.path.join(dir_, "cv", "curriculum.md")):
            return dir_
        parent = os.path.dirname(dir_)
        if parent == dir_:
            break
        dir_ = parent
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

PROJECT_DIR = _find_project_root()


def report(status, check, detail=""):
    prefix = {"pass": "[PASS]", "fail": "[FAIL]", "warn": "[WARN]"}.get(status, "[INFO]")
    msg = f"{prefix} {check}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return status == "pass"


def check_python_syntax():
    errors = []
    for root, dirs, files in os.walk(os.path.join(PROJECT_DIR, "skills")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                try:
                    with open(path) as fh:
                        ast.parse(fh.read())
                except SyntaxError as e:
                    errors.append(f"{path}: {e}")
    if errors:
        for e in errors:
            report("fail", "Python syntax", e)
        return False
    return report("pass", "Python syntax", f"all files OK")


def check_yaml_files():
    targets = [
        os.path.join(PROJECT_DIR, "config"),
        os.path.join(PROJECT_DIR, ".github"),
    ]
    errors = []
    for target in targets:
        if not os.path.isdir(target):
            continue
        for root, dirs, files in os.walk(target):
            for f in files:
                if f.endswith((".yaml", ".yml")):
                    path = os.path.join(root, f)
                    try:
                        with open(path) as fh:
                            yaml.safe_load(fh)
                    except yaml.YAMLError as e:
                        errors.append(f"{path}: {e}")
    if errors:
        for e in errors:
            report("fail", "YAML syntax", e)
        return False
    # Also check render.yaml at root
    render = os.path.join(PROJECT_DIR, "render.yaml")
    if os.path.isfile(render):
        try:
            with open(render) as fh:
                yaml.safe_load(fh)
        except yaml.YAMLError as e:
            report("fail", "YAML render.yaml", e)
            return False
    return report("pass", "YAML syntax", "all files valid")


def check_dockerfile():
    path = os.path.join(PROJECT_DIR, "Dockerfile")
    if not os.path.isfile(path):
        return report("fail", "Dockerfile", "not found")
    with open(path) as fh:
        content = fh.read()
    if "FROM " not in content:
        return report("fail", "Dockerfile", "no FROM directive")
    return report("pass", "Dockerfile", "exists with FROM")


def check_shell_syntax():
    targets = [
        os.path.join(PROJECT_DIR, "entrypoint.sh"),
    ]
    for root, dirs, files in os.walk(os.path.join(PROJECT_DIR, "config")):
        for f in files:
            if f.endswith(".sh"):
                targets.append(os.path.join(root, f))
    errors = []
    for path in targets:
        if not os.path.isfile(path):
            continue
        result = subprocess.run(["sh", "-n", path], capture_output=True, text=True)
        if result.returncode != 0:
            errors.append(f"{path}: {result.stderr.strip()}")
    if errors:
        for e in errors:
            report("fail", "Shell syntax", e)
        return False
    return report("pass", "Shell syntax", "all files OK")


def check_spec_coverage():
    errors = []
    expected = [f"{i:02d}-" for i in range(1, 17)]
    found = set()
    for f in os.listdir(os.path.join(PROJECT_DIR, "specs")):
        if f.endswith(".md"):
            found.add(f)
    for prefix in expected:
        matches = [f for f in found if f.startswith(prefix)]
        if not matches:
            errors.append(f"Missing spec: specs/{prefix}*.md")
    if errors:
        for e in errors:
            report("fail", "Spec coverage", e)
        return False

    # Count R- requirements
    total_r = 0
    for f in sorted(found):
        path = os.path.join(PROJECT_DIR, "specs", f)
        with open(path) as fh:
            for line in fh:
                if "- R-" in line or "R-DQA-" in line:
                    total_r += 1
    if total_r < 65:
        return report("fail", "Spec requirements", f"found {total_r}, expected >= 65")
    return report("pass", "Spec coverage", f"{len(found)} spec files, {total_r} requirements")


def check_constitution():
    path = os.path.join(PROJECT_DIR, ".specify", "memory", "constitution.md")
    if not os.path.isfile(path):
        return report("fail", "Constitution", "not found")
    with open(path) as fh:
        content = fh.read()
    rules = content.count("## Rule")
    if rules < 12:
        return report("fail", "Constitution", f"{rules} rules, expected >= 12")
    if "Never Fabricate" not in content:
        return report("fail", "Constitution", "missing 'Never Fabricate' clause (Rule 9)")
    return report("pass", "Constitution", f"{rules} rules with Rule 9")


def check_render_env_vars():
    entrypoint = os.path.join(PROJECT_DIR, "entrypoint.sh")
    render = os.path.join(PROJECT_DIR, "render.yaml")
    if not os.path.isfile(entrypoint):
        return report("fail", "Env vars", "entrypoint.sh not found")
    if not os.path.isfile(render):
        return report("fail", "Env vars", "render.yaml not found")

    with open(entrypoint) as fh:
        ep_content = fh.read()
    with open(render) as fh:
        render_content = fh.read()

    # Find API keys and tokens used in entrypoint
    vars_needed = set()
    for line in ep_content.splitlines():
        for prefix in ["GROQ_API_KEY", "PICOCLAW_API_KEY", "PICOCLAW_LAUNCHER_TOKEN",
                        "SESSION_SECRET", "INITIAL_ROOT_TOKEN"]:
            if f"${prefix}" in line or f"${{{prefix}}}" in line:
                vars_needed.add(prefix)

    missing = [v for v in vars_needed if v not in render_content]
    if missing:
        return report("fail", "Render env vars", f"missing: {', '.join(missing)}")
    return report("pass", "Render env vars", f"all {len(vars_needed)} vars declared")


def check_no_pycache():
    warnings = []
    for root, dirs, files in os.walk(PROJECT_DIR):
        if "__pycache__" in dirs:
            path = os.path.join(root, "__pycache__")
            if os.listdir(path):
                warnings.append(path)
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        if root.count(os.sep) > 3:
            dirs.clear()
    if warnings:
        for w in warnings:
            report("warn", "__pycache__ found", w)
        return True
    return report("pass", "No __pycache__", "clean")


def check_skill_integrity():
    skills_dir = os.path.join(PROJECT_DIR, "skills")
    errors = []
    for entry in sorted(os.listdir(skills_dir)):
        skill_path = os.path.join(skills_dir, entry)
        if not os.path.isdir(skill_path) or entry.startswith("."):
            continue
        if entry in ("__pycache__", "cv_adapter", "telegram_bot"):
            continue
        has_skill_md = os.path.isfile(os.path.join(skill_path, "SKILL.md"))
        has_scripts = os.path.isdir(os.path.join(skill_path, "scripts"))
        if not has_skill_md:
            errors.append(f"{entry}: missing SKILL.md")
        if has_skill_md and not has_scripts:
            errors.append(f"{entry}: has SKILL.md but no scripts/")
    if errors:
        for e in errors:
            report("fail", "Skill integrity", e)
        return False
    return report("pass", "Skill integrity", "all skills valid")


def check_cv_exists():
    path = os.path.join(PROJECT_DIR, "cv", "curriculum.md")
    if not os.path.isfile(path):
        return report("fail", "CV", "cv/curriculum.md not found")
    size = os.path.getsize(path)
    if size < 100:
        return report("fail", "CV", "cv/curriculum.md too small ({size} bytes)")
    return report("pass", "CV", f"cv/curriculum.md ({size} bytes)")


def check_security():
    security_script = os.path.join(PROJECT_DIR, "skills", "security_audit", "scripts", "security_scan.py")
    if not os.path.isfile(security_script):
        return report("fail", "Security audit", "security_scan.py not found")
    result = subprocess.run(
        [sys.executable, security_script],
        capture_output=True, text=True, timeout=60
    )
    for line in result.stdout.split("\n"):
        if line.strip():
            print(f"  {line}")
    if result.returncode != 0:
        return report("fail", "Security audit", f"exit code {result.returncode}")
    return report("pass", "Security audit", "all checks passed")


def main():
    print("=" * 60)
    print("  Pico Claw — Pre-flight Validation")
    print("=" * 60)
    print()

    checks = [
        ("Python syntax", check_python_syntax),
        ("YAML syntax", check_yaml_files),
        ("Dockerfile", check_dockerfile),
        ("Shell syntax", check_shell_syntax),
        ("Spec coverage", check_spec_coverage),
        ("Constitution", check_constitution),
        ("Render env vars", check_render_env_vars),
        ("Skill integrity", check_skill_integrity),
        ("CV integrity", check_cv_exists),
        ("No stale artifacts", check_no_pycache),
        ("Security audit", check_security),
    ]

    passed = 0
    failed = 0
    warned = 0

    print()
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
