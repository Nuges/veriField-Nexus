# Security Policy

## Supported Versions

VeriField Nexus provides security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of VeriField Nexus seriously. If you discover a security vulnerability, please do NOT create a public issue.

Instead, please report security vulnerabilities directly to the security team via email at:

**security@verifield.io** or **segunoluwole22@gmail.com**

Please include:
- A detailed description of the vulnerability and its potential impact.
- Step-by-step instructions to reproduce the issue (proof-of-concept code or HTTP requests).
- Affected components (backend, dashboard, SDK, API).

### Response Timeline
- **Initial Acknowledgement:** Within 48 hours.
- **Triage & Severity Assessment:** Within 5 business days.
- **Patch & Remediation Notice:** As soon as an architecturally sound fix has been validated.

## Security Architecture & Invariants

1. **Super Admin Singularity:** The platform super admin authority is strictly bounded by email verification invariants.
2. **Multi-Tenant Isolation:** All domain data (projects, activities, evidence, financial transactions, digital twins) is tenant-isolated with strict role-based and attribute-based access controls.
3. **Cryptographic Evidence Sealing:** All uploaded field evidence and verification artifacts are cryptographically hashed (SHA-256) and anchored with tamper-detection proofs.
4. **Zero Synthetic Verification:** Verification engines execute deterministic quantification rules. External registry submissions remain in explicit pending states until authenticated registry credentials are provided.
