# Stewardwell backlog

Status: `Ready`

Prioritized implementation backlog aligned to milestone flow.

## P0 — Must complete first

### B-001 App foundation (M0)
- Build app factory, config loading, and blueprint registration.
- Add `db.py` connection + transaction helpers.
- Add migration runner for ordered SQL files.

Acceptance criteria:
- [ ] `flask run` starts app with no manual patching.
- [ ] Migration runner applies from empty DB to latest version.

### B-002 Auth + session guard (M0/M1)
- Implement login/logout and session persistence.
- Add `require_auth` and `require_role` decorators.

Acceptance criteria:
- [ ] Unauthorized requests are redirected/blocked consistently.
- [ ] Role guard supports `parent/caregiver/grandparent/child`.

### B-003 Household and membership management (M1)
- Create household setup flow.
- Add guardian and child memberships.

Acceptance criteria:
- [ ] Parent can create household and invite/add members.
- [ ] Duplicate household membership is rejected.

### B-004 Chore lifecycle (M2)
- Create template, assign to child, complete, approve/reject.
- Add pending approval queue UI.

Acceptance criteria:
- [ ] Assignment transitions follow allowed state machine.
- [ ] Repeated approval call does not double-pay rewards.

### B-005 Wallet ledger + splits (M3)
- Implement spend/save/give ledger writes.
- Compute payout split from child profile or household default.

Acceptance criteria:
- [ ] Split totals equal reward coins per approved chore.
- [ ] No bucket can go below zero.

## P1 — Next priority

### B-006 Manual wallet operations (M3)
- Guardian adjustments and inter-bucket transfers.

Acceptance criteria:
- [ ] Every adjustment creates auditable ledger and actor reference.

### B-007 Store fixed-item redemption (M4)
- Store item CRUD and child redemption flow.

Acceptance criteria:
- [ ] Redemption checks inventory and balance at commit time.

### B-008 Timed privilege session flow (M4)
- Start/stop timed sessions with prepaid billing.

Acceptance criteria:
- [ ] Session charges by configured block size/cost.
- [ ] Insufficient funds stops or blocks continuation safely.

### B-009 Family points and rewards (M5)
- Family points ledger and goal lifecycle.

Acceptance criteria:
- [ ] Approved chores increment points once.
- [ ] Unlock/archive/reset transitions are valid and role-protected.

### B-010 Dashboards (M5)
- Parent summary (approvals, balances, sessions, rewards).
- Child summary (chores, balances, progress).

Acceptance criteria:
- [ ] Dashboard values match source ledgers/tables.

## P2 — Hardening

### B-011 Audit logging (M6)
- Capture before/after snapshots for sensitive mutations.

Acceptance criteria:
- [ ] Audit records include actor, action, entity, timestamp.

### B-012 QA automation baseline (M6)
- Add focused service tests for approvals, ledger, timer billing.

Acceptance criteria:
- [ ] Critical-path test suite passes in CI/local repeatably.

### B-013 Operational readiness (M6)
- Backup/restore script and rollback runbook.

Acceptance criteria:
- [ ] Restore rehearsal returns app to consistent state.

## Ready-now execution list
1. B-001
2. B-002
3. B-003
4. B-004
5. B-005
