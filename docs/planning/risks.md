# Stewardwell risk register

Status: `Ready`

## Scale
- Probability: `L` (low), `M` (medium), `H` (high)
- Impact: `L` (low), `M` (medium), `H` (high)

## Current risks

| ID | Risk | Probability | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| R-01 | Duplicate chore payout due to repeated approval submission | M | H | Idempotency key/unique payout reference per assignment + tests | Backend |
| R-02 | Permission bypass between guardian roles and child scope | M | H | Centralized role guards + object ownership checks + regression matrix | Backend/QA |
| R-03 | Negative wallet balances from race conditions | M | H | Transactional balance checks and commit-time revalidation | Backend |
| R-04 | SQLite lock contention during peak write operations | M | M | Short transactions, WAL mode, retry strategy for transient lock | Backend |
| R-05 | Timed session overbilling/underbilling edge cases | M | H | Block-based billing service tests + session state invariants | Backend/QA |
| R-06 | Migration failure causes inconsistent production schema | L | H | Ordered migration runner, staging rehearsal, backup before apply | DevOps |
| R-07 | Data loss from SQLite file corruption or hosting misconfig | L | H | Automated backups + restore drills + disk health monitoring | DevOps |
| R-08 | Guardian UX confusion around approval/redeem states | M | M | Clear status labels, QA exploratory pass, documentation | Product/QA |

## Watchlist triggers
- >1 idempotency conflict per 100 approvals.
- Any unauthorized-access defect in release candidate.
- Any failed backup or restore rehearsal.
- Elevated timer billing correction events.

## Response workflow (relative)
1. Identify and classify severity.
2. Contain impact (disable affected path if needed).
3. Patch and verify in staging.
4. Deploy fix and monitor guardrail metrics.
5. Record post-incident actions in backlog.

## Acceptance checklist
- [ ] Every high-impact risk has a concrete mitigation task.
- [ ] Risk owners are assigned and active.
- [ ] Watchlist triggers are connected to metrics/alerts.
- [ ] Rollback path validated for release candidate.
