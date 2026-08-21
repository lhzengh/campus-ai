# Authenticated Portal Integration Profile

> Status: independent browser Connector framework implemented; real source validation pending
> Updated: 2026-08-21

## Scope

This document defines the reusable boundary for portals that require an interactive login. It intentionally contains no institution name, portal URL, phone number, account identifier, password, cookie, or deployment credential.

Institution-specific values must be supplied at runtime through source configuration and an external secret store. Private operational notes may be kept outside the repository or under the ignored `docs/private/` directory.

## Runtime configuration principles

| Value | Storage boundary |
| --- | --- |
| Entry URL and allowed domains | Runtime source configuration |
| Source display name and parser selectors | Runtime source configuration |
| Account or phone reference | Secret manager reference; never application code |
| Password, OTP, cookie, token | Never committed; use user-assisted login or secret storage where permitted |
| Encrypted browser state | Restricted server volume |
| Browser-state encryption key | External secret, separate from the state volume |

URLs must be absolute HTTP(S) URLs, must not contain embedded credentials, and must be checked against an explicit per-source domain allowlist before navigation.

## Authentication flow

1. The user starts authentication after initial deployment or session expiry.
2. The system opens a visible, user-controlled browser flow.
3. The user personally completes any permitted password, SMS, CAPTCHA, scan, or confirmation step.
4. After successful login, only the required browser session state is encrypted and stored in the Connector's restricted volume; Core never receives cookies.
5. Scheduled collection asks the Connector to reuse that state until an unauthorized response or login-page signature indicates expiry.
6. The source pauses and sends a re-authentication notice without blocking unrelated Connectors or sources.

The system must not read SMS messages automatically, relay verification codes, solve CAPTCHAs, or bypass access controls. If the portal rules do not allow automated access, the Connector must remain disabled and use an allowed alternative.

## Session maintenance

- Record verification time, last successful access, observed expiry time, and a redacted failure category.
- Learn session lifetime per source from observations; do not use a universal renewal interval.
- Allow a configurable reminder window only after the source has enough observed expiry data.
- Treat a fixed server IP as an operational detail, not proof that a session remains valid.
- Never log browser state, account identifiers, passwords, OTPs, cookies, or tokens.

## Validation checklist

- [ ] Validate login redirects and success signatures with the user present.
- [ ] Confirm whether sessions depend on IP, User-Agent, device state, or other browser properties.
- [ ] Configure and test the exact domain/path allowlist without committing its real values.
- [ ] Validate list, detail, and attachment parsing with sanitized fixtures.
- [ ] Verify that expired sessions pause the source without creating a retry storm.
- [ ] Verify that re-authentication notices arrive while other sources continue running.
- [ ] Review the portal terms, robots declarations, and applicable institutional rules.
- [ ] Confirm that exported diagnostics contain no source-specific secrets or personal identifiers.
