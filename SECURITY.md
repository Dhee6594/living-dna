# Security Policy

## Reporting a vulnerability

**Do not open a public issue for security vulnerabilities.**

Report privately via GitHub's
[**Report a vulnerability**](https://github.com/Dhee6594/living-dna/security/advisories/new)
(Security → Advisories), or email **vemireddysaidheeraj94@gmail.com** with subject
`SECURITY: living-dna`.

Please include: affected version/commit, a description, reproduction steps, and impact.

### What to expect

- **Acknowledgement:** within 3 business days.
- **Assessment & fix window:** we aim to triage within 7 days and ship a fix or mitigation
  for confirmed high-severity issues within 30 days.
- **Disclosure:** coordinated. We credit reporters unless you ask us not to.

## Supported versions

This is a pre-1.0 project. Security fixes land on `develop` and the latest release only.

| Version | Supported |
|---|---|
| 0.1.x (latest) | ✅ |
| < 0.1 | ❌ |

## Security model & notes for this project

- **The server binds to loopback (`127.0.0.1`) by default.** Exposing it on a public
  interface (`--host 0.0.0.0`) puts an *unauthenticated* JSON API on the network — there
  is no auth layer yet. Do not do this on an untrusted network.
- **Ingested data is untrusted input.** Commit messages, PR text, and other history are
  treated as *data about the past, never instructions* — the AI miner's prompt
  (`SYSTEM_MINER`) is written to resist prompt injection. Preserve that framing in any new
  prompt that feeds model context.
- **No secrets in the genome.** The store records provenance (commit hashes, file paths),
  not file contents or credentials. Don't add anything that would persist secrets.
- **`ANTHROPIC_API_KEY`** is read from the environment only; never commit keys.
