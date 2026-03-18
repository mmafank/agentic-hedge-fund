#!/usr/bin/env python3
"""
Secret scanner for pre-commit hook.
Scans staged files for API keys, server IPs, personal paths, credentials,
and other sensitive patterns that must never reach a public repo.

Exit code 0 = clean, 1 = secrets found (blocks commit).
"""

import re
import subprocess
import sys

# ── Patterns to detect ──────────────────────────────────────────────
# Each tuple: (name, compiled regex, description)
PATTERNS = [
    # API keys by prefix
    ("Anthropic API key", re.compile(r"sk-ant-[a-zA-Z0-9\-_]{20,}"), "Anthropic API key detected"),
    ("OpenAI API key", re.compile(r"sk-[a-zA-Z0-9]{20,}"), "OpenAI-style API key detected"),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key ID detected"),
    ("AWS secret key", re.compile(r"(?i)aws[_\-]?secret[_\-]?access[_\-]?key\s*[=:]\s*\S+"), "AWS secret key assignment detected"),
    ("Generic API key assignment", re.compile(r'(?i)(api[_\-]?key|api[_\-]?secret|auth[_\-]?token|access[_\-]?token)\s*[=:]\s*["\'][^"\']{8,}["\']'), "API key/token assignment detected"),
    ("Bearer token", re.compile(r"Bearer\s+[a-zA-Z0-9\-_.]{20,}"), "Bearer token detected"),

    # SSH and certificates
    ("SSH private key", re.compile(r"-----BEGIN\s+(RSA|DSA|EC|OPENSSH)\s+PRIVATE\s+KEY-----"), "SSH private key detected"),
    ("PEM file reference", re.compile(r"[a-zA-Z0-9_\-]+\.pem"), "PEM file reference detected"),

    # Personal paths (customize these for your username)
    ("macOS user path", re.compile(r"/Users/\w+/(?!\.)"),"Personal macOS home path detected"),
    ("Home tilde expansion", re.compile(r"~/\.(ssh|env|claude|config)"), "Sensitive home directory path detected"),

    # .env file patterns
    ("Dotenv assignment", re.compile(r"^[A-Z][A-Z0-9_]{2,}=\S{8,}", re.MULTILINE), "Looks like a .env variable assignment"),

    # Discord/Slack webhooks
    ("Discord webhook", re.compile(r"https://discord\.com/api/webhooks/\d+/[\w\-]+"), "Discord webhook URL detected"),
    ("Slack webhook", re.compile(r"https://hooks\.slack\.com/services/T\w+/B\w+/\w+"), "Slack webhook URL detected"),

    # Database connection strings
    ("Database URL", re.compile(r"(?i)(postgres|mysql|mongodb|redis)://[^\s]+@[^\s]+"), "Database connection string detected"),
    ("Supabase URL", re.compile(r"https://[a-z]+\.supabase\.co"), "Supabase project URL detected"),

    # IP addresses that look like real servers (not examples/docs)
    ("Real IP address", re.compile(r"\b(?!10\.)(?!172\.(1[6-9]|2\d|3[01])\.)(?!192\.168\.)(?!127\.)(?!0\.)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "Non-private IP address detected (use 10.x.x.x or 192.168.x.x for examples)"),

    # Phone numbers (US format)
    ("Phone number", re.compile(r"\(\d{3}\)\s*\d{3}[- ]?\d{4}"), "Phone number detected"),

    # Email addresses
    ("Email address", re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}"), "Email address detected"),
]

# ── Files to always skip ────────────────────────────────────────────
SKIP_FILES = {
    ".gitignore",
    "scripts/secret_scanner.py",  # this file references patterns by necessity
    "scripts/install_hooks.sh",  # bash variables trigger dotenv pattern
    "tests/test_secret_scanner.py",  # test file needs to test patterns
}

SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz",
}


def get_staged_files():
    """Get list of files staged for commit."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True
    )
    return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]


def get_staged_content(filepath):
    """Get the staged content of a file (not the working copy)."""
    result = subprocess.run(
        ["git", "show", f":{filepath}"],
        capture_output=True, text=True
    )
    return result.stdout


def scan_content(filepath, content):
    """Scan content for secret patterns. Returns list of (line_num, pattern_name, match)."""
    findings = []
    for line_num, line in enumerate(content.split("\n"), 1):
        for name, pattern, _desc in PATTERNS:
            matches = pattern.findall(line)
            if matches:
                # Show first 60 chars of the match for context
                match_preview = str(matches[0])[:60]
                findings.append((line_num, name, match_preview))
    return findings


def scan_file(filepath):
    """Scan a single staged file. Returns findings list."""
    # Skip binary and known-safe files
    if filepath in SKIP_FILES:
        return []
    ext = "." + filepath.rsplit(".", 1)[-1] if "." in filepath else ""
    if ext in SKIP_EXTENSIONS:
        return []

    content = get_staged_content(filepath)
    if not content:
        return []

    return scan_content(filepath, content)


def main():
    """Main entry point for pre-commit hook."""
    files = get_staged_files()
    if not files:
        sys.exit(0)

    all_findings = {}
    for filepath in files:
        findings = scan_file(filepath)
        if findings:
            all_findings[filepath] = findings

    if not all_findings:
        print("\033[32m[secret-scanner] All clear. No secrets detected.\033[0m")
        sys.exit(0)

    # Report findings
    print("\n\033[1;31m" + "=" * 60)
    print("  SECRET SCANNER: COMMIT BLOCKED")
    print("=" * 60 + "\033[0m\n")

    total = 0
    for filepath, findings in all_findings.items():
        print(f"\033[1m  {filepath}\033[0m")
        for line_num, name, match in findings:
            print(f"    Line {line_num}: \033[33m{name}\033[0m")
            print(f"             {match}")
            total += 1
        print()

    print(f"\033[1;31m  {total} secret(s) found in {len(all_findings)} file(s).\033[0m")
    print(f"  Fix these before committing.\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
