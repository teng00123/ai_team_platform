# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| `1.x`   | ✅ Active  |
| `< 1.0` | ❌ No longer supported |

## Reporting a Vulnerability

**Please do not report security vulnerabilities via public GitHub Issues.**

If you discover a security vulnerability in AI Team Platform, please report it responsibly:

1. **Email**: Open a [GitHub Security Advisory](https://github.com/teng00123/ai_team_platform/security/advisories/new) (preferred)
2. **Alternatively**: Send details privately to the repository maintainer via GitHub

### What to include

- A description of the vulnerability and its potential impact
- Steps to reproduce (proof of concept if possible)
- Affected versions
- Any suggested mitigations

### Response timeline

| Stage | Timeframe |
|-------|-----------|
| Acknowledgement | Within 3 business days |
| Assessment & triage | Within 7 business days |
| Fix / patch release | Depends on severity (critical: ASAP, high: within 14 days) |

## Security Best Practices for Deployment

When running AI Team Platform, please ensure:

- **Never hardcode tokens**: Use environment variables (`OPENCLAW_GATEWAY_TOKEN`, `LLM_API_KEY`)
- **Never commit `data/` files**: They are gitignored for a reason — they may contain session IDs and task results
- **Restrict Gateway permissions**: Only allow the minimum required tools (`sessions_spawn`, `sessions_send`, `sessions_history`, `sessions_list`)
- **Do not expose port 8765 publicly** without authentication — the API has no auth layer by default
- **Keep dependencies updated**: Run `pip-audit -r requirements.txt` regularly to check for known CVEs

## Scope

The following are **in scope** for security reports:

- Authentication / authorization bypass
- Remote code execution via API inputs
- Sensitive data leakage (tokens, session keys)
- Dependency vulnerabilities with known CVEs

The following are **out of scope**:

- Issues in OpenClaw itself (report upstream)
- Social engineering or phishing
- Vulnerabilities in third-party LLM providers
