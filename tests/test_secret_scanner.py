#!/usr/bin/env python3
"""
Tests for the secret scanner.
Verifies that all pattern categories catch what they should
and don't false-positive on safe content.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from secret_scanner import PATTERNS, scan_content


def _scan(text):
    """Helper: scan text, return set of pattern names that fired."""
    findings = scan_content("test.py", text)
    return {name for _, name, _ in findings}


# ── API Keys ──────────────────────────────────────────────

def test_catches_anthropic_key():
    assert "Anthropic API key" in _scan('key = "sk-ant-api03-abcdef1234567890abcdef"')

def test_catches_aws_access_key():
    assert "AWS access key" in _scan("AKIAIOSFODNN7EXAMPLE")

def test_catches_aws_secret_assignment():
    assert "AWS secret key" in _scan('AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY')

def test_catches_generic_api_key():
    assert "Generic API key assignment" in _scan('api_key = "abcdef1234567890abcdef"')

def test_catches_bearer_token():
    assert "Bearer token" in _scan('Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test')


# ── SSH / Certs ───────────────────────────────────────────

def test_catches_ssh_private_key():
    assert "SSH private key" in _scan("-----BEGIN RSA PRIVATE KEY-----")

def test_catches_pem_reference():
    assert "PEM file reference" in _scan("scp -i my-server-key.pem file host:/path")


# ── IP Addresses ──────────────────────────────────────────

def test_allows_private_ips():
    """Private/example IPs should not trigger the real IP detector."""
    findings = _scan("server = '192.168.1.100'")
    assert "Real IP address" not in findings

def test_allows_localhost():
    findings = _scan("host = '127.0.0.1'")
    assert "Real IP address" not in findings

def test_catches_public_ip():
    assert "Real IP address" in _scan("deploy to 54.231.100.50")

def test_catches_another_public_ip():
    assert "Real IP address" in _scan("ssh user@45.77.99.218")


# ── Personal Paths ────────────────────────────────────────

def test_catches_macos_user_path():
    assert "macOS user path" in _scan("config = '/Users/someuser/projects/app'")

def test_catches_home_ssh_path():
    assert "Home tilde expansion" in _scan("key_path = '~/.ssh/id_rsa'")


# ── Webhooks / Database ───────────────────────────────────

def test_catches_discord_webhook():
    assert "Discord webhook" in _scan("https://discord.com/api/webhooks/123456/abcdef-token")

def test_catches_database_url():
    assert "Database URL" in _scan("postgres://user:pass@db.example.com:5432/mydb")

def test_catches_supabase_url():
    assert "Supabase URL" in _scan("https://xyzcompany.supabase.co")


# ── Contact Info ──────────────────────────────────────────

def test_catches_phone():
    assert "Phone number" in _scan("Call me at (555) 123-4567")

def test_catches_email():
    assert "Email address" in _scan("reach me at someone@example.com")

def test_catches_icloud_email():
    assert "Email address" in _scan("myname@icloud.com")

def test_catches_gmail():
    assert "Email address" in _scan("user@gmail.com")


# ── Safe Content (should NOT trigger) ─────────────────────

def test_clean_python_code():
    code = '''
def calculate_sharpe_ratio(returns, risk_free_rate=0.0):
    """Calculate annualized Sharpe ratio."""
    excess = returns - risk_free_rate
    return excess.mean() / excess.std() * (252 ** 0.5)
'''
    findings = _scan(code)
    assert "Anthropic API key" not in findings
    assert "AWS access key" not in findings
    assert "SSH private key" not in findings

def test_clean_markdown():
    md = '''
# Architecture

The system uses 3 servers:
- Server A (10.0.0.1): Weather trading
- Server B (10.0.0.2): Sportsbook
- Server C (192.168.1.10): Local dashboard

Data syncs periodically via cron.
'''
    findings = _scan(md)
    assert "Real IP address" not in findings

def test_mermaid_diagram():
    md = '''
```mermaid
graph TD
    A[Orchestrator] --> B[Doctor]
    A --> C[CFO]
    A --> D[CTO]
```
'''
    findings = _scan(md)
    assert len(findings) == 0


if __name__ == "__main__":
    passed = 0
    failed = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                passed += 1
                print(f"  \033[32mPASS\033[0m {name}")
            except AssertionError as e:
                failed += 1
                print(f"  \033[31mFAIL\033[0m {name}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
