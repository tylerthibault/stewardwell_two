# Stewardwell QA plan

Status: `Ready`

## Test strategy
- Prioritize service-layer tests for business correctness.
- Add route-level tests for auth/permissions and contract behavior.
- Keep UI tests minimal (smoke-level) for server-rendered templates.

## Test types
- Unit: split math, timer billing units, state transition validators.
- Service/integration: approval payout, redemption commit checks, ledger writes.
- Route tests: role guards, object ownership, error handling.
- Manual exploratory: dashboard flows and guardian/child handoff UX.

## Critical path matrix

| Flow | Roles | Type | Pass condition |
|---|---|---|---|
| Login + household access | all | route | Authorized role enters correct context only |
| Assign -> complete -> approve chore | guardian + child | service + route | One payout only, correct status transitions |
| Wallet split + balances | guardian/child | service | Bucket balances and ledger are consistent |
| Fixed store redemption | child + guardian | integration | Balance and inventory checks enforced |
| Timed session start/stop | child + guardian | integration | Billing per block, no invalid concurrent session |
| Family points reward progress | guardian/child | service | Progress and unlock status match points ledger |

## Permission regression set
Must validate each role for at least one allowed and one forbidden action:
- `parent`
- `caregiver`
- `grandparent`
- `child`

## Data integrity checks
- Ledger totals reconcile to denormalized balance tables.
- No negative bucket balances.
- Chore approval idempotency holds under repeated submissions.
- Timed sessions never remain `active` after forced stop paths.

## Exit criteria (release gate)
- [ ] Critical path matrix all green.
- [ ] No open severity-1 defects.
- [ ] No unresolved permission bypass defects.
- [ ] Backup/restore rehearsal successful.
- [ ] Known lower-severity issues documented in release notes.

## Manual smoke checklist
- [ ] Parent creates household and members.
- [ ] Child completes chore and guardian approves.
- [ ] Wallet balances update correctly.
- [ ] Child redeems fixed item successfully.
- [ ] Child starts/stops timed item and is billed correctly.
- [ ] Family reward progress updates on chore approvals.
