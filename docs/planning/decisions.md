# Stewardwell decisions

This document records default product and technical decisions used to unblock implementation.

## Product defaults

| Decision key | Default | Reason |
|---|---|---|
| `points_pooling` | Family points are pooled at household level | Matches family reward framing and simplifies reward progress |
| `approval_policy` | All chore rewards require approval before payout | Prevents duplicate/incorrect payouts and keeps parent oversight |
| `negative_balance_policy` | Child spend balance cannot go negative | Reduces confusion and blocks debt edge cases in MVP |
| `timed_billing_mode` | Prepaid only for MVP | Easier timer behavior and clean stop when funds are depleted |
| `split_scope` | Split percentages are configurable per child with household defaults | Gives parent control while supporting different child plans |
| `savings_spend_policy` | Savings cannot be spent directly; parent can transfer to spend | Preserves savings intent and supports stewardship goals |

## Role scope
- Active roles for implementation:
  - parent
  - caregiver
  - grandparent
  - child
- One household can contain multiple guardian-class users (parent/caregiver/grandparent).

## Technical defaults
- Backend: Flask monolith with app factory + blueprints.
- Database: SQLite with raw `sqlite3` and manual SQL migration files.
- UI: server-rendered templates.
- Auth model: session-based authentication with role checks at route/service layers.

## Revision policy
- If a default changes, update this doc first.
- Any changed default must include:
  - old value
  - new value
  - migration impact
  - QA impact

## Open follow-up decisions (non-blocking for start)
- Parent approval thresholds for store redemptions by item category.
- Whether caregivers can override parent PIN-protected settings.
- Whether timed session warning prompts are MVP or post-MVP.
