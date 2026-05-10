# Stewardwell metrics

Status: `Ready`

## Measurement principles
- Keep telemetry minimal and actionable for MVP.
- Track events at service layer where business decisions occur.
- Store event timestamps in UTC and household-scoped IDs.

## Primary product metrics

| Metric | Definition | Target direction |
|---|---|---|
| Weekly active households | Distinct households with >=1 meaningful action in a 7-day window | Up |
| Chore completion rate | `completed_or_approved / assigned` per window | Up |
| Approval turnaround | Median time from child completion to guardian decision | Down |
| Wallet engagement | % active children with >=1 spend/save/give transaction | Up |
| Store redemption success | `successful_redemptions / redemption_attempts` | Up |
| Timed session completion | % sessions ended cleanly without billing errors | Up |

## Guardrail metrics
- Permission-denied rate by endpoint (unexpected spikes indicate UX/auth issues).
- Failed transaction rate for wallet/store/timer operations.
- Idempotency conflict count for approval endpoints.
- Negative balance prevention trigger count (should be non-zero but stable).

## Event schema (minimum)

| Event | Required fields |
|---|---|
| `chore_assigned` | household_id, child_id, assignment_id, reward_coins, reward_points |
| `chore_completed` | household_id, child_id, assignment_id |
| `chore_approved` | household_id, child_id, assignment_id, approver_role |
| `wallet_adjusted` | household_id, child_id, bucket, amount, actor_role, reason |
| `store_redeemed` | household_id, child_id, item_id, item_type, cost |
| `timer_started` | household_id, child_id, item_id, block_minutes, cost_per_block |
| `timer_stopped` | household_id, child_id, session_id, billed_units, billed_amount |
| `reward_unlocked` | household_id, reward_id, points_goal |

## Reporting cadence (relative)
- After M3: baseline dashboards for chores + wallet.
- After M4: include store/timer reliability panels.
- After M5: include reward progression and household retention trend.

## Acceptance checklist
- [ ] Event logging covers all critical-path actions.
- [ ] Metric SQL queries are versioned and reproducible.
- [ ] Definitions are documented and used consistently in QA/release notes.
- [ ] At least one alert threshold defined for guardrail metrics.
