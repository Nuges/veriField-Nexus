# Production Deployment Checklist

## Pre-Deployment
- [x] Verify GitHub actions pipeline execution.
- [x] Confirm no outstanding high-severity security vulnerabilities.
- [x] Validate Alembic migration states against staging.
- [x] Ensure external API keys (Supabase, Verra, GoldStandard) are safely rotated and injected.
- [x] Complete environment variable `.env` population on target environment.

## Deployment Phase
- [ ] Spin up database replicas.
- [ ] Run `alembic upgrade head`.
- [ ] Seed Phase 1 Methodology metadata if new environment.
- [ ] Perform blue/green switch.
- [ ] Flush Redis cache layers.

## Post-Deployment
- [ ] Execute `production_smoke_test.py`.
- [ ] Monitor P99 latency bounds.
- [ ] Check IIoT WebSocket ingestion streams for anomalies.
