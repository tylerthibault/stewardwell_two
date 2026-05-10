# Stewardwell permissions

Status: `Ready`

## Roles
- `parent`
- `caregiver`
- `grandparent`
- `child`

Guardian-class roles: `parent`, `caregiver`, `grandparent`.

## Permission rules
- All mutating actions require authenticated household membership.
- `child` can only act on their own records.
- Cross-household access is always denied.
- Sensitive configuration defaults to `parent` only unless noted.

## Role-action matrix

| Capability | parent | caregiver | grandparent | child |
|---|---:|---:|---:|---:|
| View household dashboard | ✅ | ✅ | ✅ | ⚠️ own child dashboard only |
| Manage household settings | ✅ | ❌ | ❌ | ❌ |
| Add/remove guardian memberships | ✅ | ❌ | ❌ | ❌ |
| Create/edit child profiles | ✅ | ✅ | ✅ | ❌ |
| Create/edit chore templates | ✅ | ✅ | ✅ | ❌ |
| Assign chores | ✅ | ✅ | ✅ | ❌ |
| Mark chore complete | ❌ | ❌ | ❌ | ✅ own only |
| Approve/reject completed chores | ✅ | ✅ | ✅ | ❌ |
| Manual wallet adjustment | ✅ | ✅ | ❌ | ❌ |
| Update split percentages | ✅ | ✅ | ❌ | ❌ |
| Create/edit store items | ✅ | ✅ | ✅ | ❌ |
| Redeem store item | ❌ | ❌ | ❌ | ✅ own only |
| Fulfill/reject redemption | ✅ | ✅ | ✅ | ❌ |
| Start/stop timed session | ✅ proxy or own | ✅ proxy or own | ✅ proxy or own | ✅ own only |
| Create/edit family rewards | ✅ | ✅ | ✅ | ❌ |
| Archive/reset family rewards | ✅ | ❌ | ❌ | ❌ |
| View audit log | ✅ | ✅ | ❌ | ❌ |

## Protected operations (extra guard)
- Parent-only confirmation (PIN/password re-entry):
  - household settings changes
  - membership removal
  - reward reset/archive
- Idempotent approval endpoint disallows second payout.
- Timer stop action allowed by guardian even if child started session.

## Route guard contract
Each protected route must enforce in order:
1. authenticated session
2. active household membership
3. role capability check
4. object-level ownership/scope check
5. action-level business constraints

## Acceptance checklist
- [ ] Every mutating route mapped to a capability.
- [ ] Child ownership checks exist on child-initiated actions.
- [ ] Parent-only operations require explicit guard.
- [ ] Forbidden access returns 403 (or redirect + flash for HTML flow).
- [ ] Cross-household access attempts are covered by tests.
