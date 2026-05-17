# Stewardwell milestones

Status: `Ready`

Relative sequencing only; each milestone starts after prior exit criteria pass.

## M0 — Foundation setup
### Scope
- Flask app factory + blueprints skeleton
- SQLite connection utilities (`sqlite3`) with FK + WAL config
- migration runner + `schema_migrations`
- auth/session baseline

### Exit criteria
- [ ] App boots locally with health route.
- [ ] First migration chain applies on clean DB.
- [ ] Login/logout works for seeded parent user.

## M1 — Household, roles, and child profiles
### Scope
- household creation
- membership management for `parent/caregiver/grandparent/child`
- child profile CRUD
- permission guards at route/service level

### Exit criteria
- [ ] Parent can create household and add members.
- [ ] Role restrictions enforced for protected routes.
- [ ] Child can access only own dashboard context.

## M2 — Chores and approval workflow
### Scope
- chore template CRUD
- assignment creation/status flow
- child completion submission
- guardian approval/rejection

### Exit criteria
- [ ] Assignment lifecycle reaches approved/rejected deterministically.
- [ ] Approval action is idempotent.
- [ ] Rewards are not paid before approval.

## M3 — Wallet and transaction ledger
### Scope
- spend/save/give buckets
- payout split engine
- manual adjustments and transfers
- wallet history views

### Exit criteria
- [ ] Approved chores create correct bucket ledger entries.
- [ ] Negative balances are blocked.
- [ ] Balance read model matches ledger totals.

## M4 — Store, redemptions, and timed privileges
### Scope
- store item CRUD (`fixed` + `timed`)
- redemption workflow
- timed session start/stop and billing
- optional one-child-at-a-time lock per item

### Exit criteria
- [ ] Child can redeem fixed items with sufficient spend balance.
- [ ] Timed session billing uses configured time block cost.
- [ ] Session guard prevents invalid concurrent active sessions.

## M5 — Family points, rewards, and dashboards
### Scope
- family points ledger + balance
- family reward goals (active/unlocked/archive/reset)
- parent and child dashboard summaries

### Exit criteria
- [ ] Approved chores update family points balance.
- [ ] Reward progress/unlock state is visible and correct.
- [ ] Dashboard widgets load from production-style data paths.

## M6 — Hardening and release readiness
### Scope
- QA regression pass
- audit log coverage for sensitive actions
- backup/restore rehearsal
- release checklist completion

### Exit criteria
- [ ] Critical regression suite passes.
- [ ] Risk mitigations in `risks.md` addressed or accepted.
- [ ] Go-live runbook completed with rollback path.

## Dependency chain
`M0 -> M1 -> M2 -> M3 -> M4 -> M5 -> M6`
