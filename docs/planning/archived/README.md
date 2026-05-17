# Stewardwell planning index

This folder contains execution-ready planning artifacts for the Flask + SQLite implementation.

## How to use this folder
- Start with [roadmap.md](roadmap.md) for strategic scope.
- Use [decisions.md](decisions.md) to confirm default business rules.
- Use [milestones.md](milestones.md) and [backlog.md](backlog.md) for day-to-day build sequencing.
- Use [architecture.md](architecture.md), [data-model.md](data-model.md), [permissions.md](permissions.md), and [pages.md](pages.md) during implementation.
- Use [style-guide.md](style-guide.md) for product tone, terminology, and UI consistency.
- Use [qa-plan.md](qa-plan.md), [metrics.md](metrics.md), [release-plan.md](release-plan.md), and [risks.md](risks.md) during hardening and beta.

## Documents
- [roadmap.md](roadmap.md): high-level product phases and epics
- [decisions.md](decisions.md): resolved business-rule defaults and decision log
- [architecture.md](architecture.md): application architecture and technical boundaries
- [data-model.md](data-model.md): schema blueprint, relationships, and invariants
- [permissions.md](permissions.md): role-action matrix and protected operations
- [pages.md](pages.md): MVP page inventory, content specs, actions, and acceptance criteria
- [style-guide.md](style-guide.md): visual tone, copy standards, and UX consistency guardrails
- [api-contracts.md](api-contracts.md): endpoint contracts and flow interfaces
- [milestones.md](milestones.md): milestone scope, dependencies, and exit criteria
- [backlog.md](backlog.md): prioritized implementation tasks and acceptance criteria
- [qa-plan.md](qa-plan.md): test strategy and feature validation matrix
- [metrics.md](metrics.md): beta metrics definitions and event schema
- [release-plan.md](release-plan.md): environment, rollout, and operational readiness
- [risks.md](risks.md): risk register and mitigations

## Status tags
- `Ready`: can be used directly for build execution.
- `In progress`: needs refinement before implementation.
- `Blocked`: requires decision or dependency first.

## Current status
- Planning baseline is `Ready` for Milestones 1–3.
- Milestones 4–6 are `Ready` with assumptions listed in [decisions.md](decisions.md).
