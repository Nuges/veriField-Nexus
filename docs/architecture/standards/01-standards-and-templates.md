# Architecture Standards & Templates

This directory provides templates and standards to be used when extending the Enterprise Architecture.

## 1. Coding Standards

- **Language:** TypeScript for Frontend (Next.js) / Python for Backend (FastAPI).
- **Domain Driven Design:** All business logic must reside in the `domain` or `services` layer. Controllers/Routers must only handle HTTP concerns.
- **Testing:** 100% coverage on Core Entity logic and Policy rules. Integration tests required for external adapters.

## 2. ADR Template

When proposing a new architectural decision, use the following structure and place it in `docs/architecture/adr/`:

```markdown
# ADR [Number]: [Title]

## Context
[What is the problem we are trying to solve? Why does the current architecture fall short?]

## Decision
[What is the change we are making?]

## Consequences
[What becomes easier? What becomes harder? What are the tradeoffs?]

## Alternatives Considered
[What else did we think about and why did we reject it?]
```
