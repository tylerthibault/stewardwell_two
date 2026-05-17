# Stewardwell API contracts

Status: `Ready`

## API style
- Flask server-rendered app with selective JSON endpoints for async actions.
- Versioning for JSON endpoints via `/api/v1/...`.
- Session auth + CSRF protection for state-changing requests.

## Common response contract
- Success JSON: `{ "ok": true, "data": ... }`
- Error JSON: `{ "ok": false, "error": { "code": "...", "message": "..." } }`
- HTML routes redirect with flash messages on validation/permission failures.

## Endpoints (MVP)

### Auth and household
| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/auth/login` | all | Start session |
| POST | `/auth/logout` | all | End session |
| POST | `/households` | parent | Create household |
| POST | `/households/:id/members` | parent | Add guardian/child account |

### Chores and approvals
| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/chores/templates` | guardian | Create chore template |
| POST | `/chores/assignments` | guardian | Assign chore to child |
| POST | `/chores/assignments/:id/complete` | child | Mark assignment complete |
| POST | `/approvals/:assignment_id/decision` | guardian | Approve/reject completion |

Decision request body:
```json
{ "decision": "approved|rejected", "note": "optional" }
```
Rules:
- `approved` triggers payout transaction exactly once.
- Repeat decision attempts return conflict (`409`) for JSON flow.

### Wallet
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/v1/wallet/children/:child_id` | guardian + own child | Wallet snapshot |
| POST | `/api/v1/wallet/children/:child_id/adjust` | parent,caregiver | Manual bucket adjustment |
| POST | `/api/v1/wallet/children/:child_id/transfer` | parent,caregiver | Transfer between buckets |
| POST | `/api/v1/wallet/children/:child_id/splits` | parent,caregiver | Update split percentages |

### Store and redemptions
| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/store/items` | guardian | Create item |
| POST | `/api/v1/store/redemptions` | child | Redeem fixed/timed item |
| POST | `/api/v1/store/redemptions/:id/decision` | guardian | Approve/reject redemption |
| POST | `/api/v1/store/redemptions/:id/fulfill` | guardian | Mark fulfilled |

### Timed privileges
| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/api/v1/timer/start` | child + guardian proxy | Start timed session |
| POST | `/api/v1/timer/stop` | child + guardian proxy | Stop session and finalize billing |
| GET | `/api/v1/timer/active` | guardian + own child | Active session state |

### Family rewards
| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/rewards` | guardian | Create family reward goal |
| POST | `/rewards/:id/archive` | parent | Archive reward |
| POST | `/rewards/:id/reset` | parent | Reset unlocked reward |

## Validation requirements
- IDs must belong to current household.
- Amount fields must be positive integers.
- Split percentages must sum to 100.
- Timed item start must verify available prepaid spend balance.

## Acceptance checklist
- [ ] Endpoint list mapped to route blueprints.
- [ ] Request validation errors return deterministic codes/messages.
- [ ] Approval and payout endpoints are idempotent.
- [ ] Object-scope checks prevent cross-household access.
- [ ] API smoke tests cover happy path + forbidden path per domain.
