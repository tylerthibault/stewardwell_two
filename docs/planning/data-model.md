# Stewardwell data model

Status: `Ready`

## Scope
SQLite schema for a Flask monolith using raw `sqlite3` and manual SQL migrations.

## Conventions
- Integer primary keys (`INTEGER PRIMARY KEY`).
- Timestamps stored as UTC ISO-8601 text.
- Amount fields stored as integer units (no floats).
- Foreign keys enabled and enforced.
- Soft-delete only where explicitly noted.

## Core tables

### Households and users
- `households(id, name, created_at)`
- `users(id, email, password_hash, display_name, is_active, created_at)`
- `household_memberships(id, household_id, user_id, role, status, created_at)`
  - `role` in: `parent`, `caregiver`, `grandparent`, `child`
  - unique: `(household_id, user_id)`
- `children(id, household_id, user_id NULL, nickname, avatar_key, is_active, created_at)`
  - `user_id` nullable for child profiles without direct login at first

### Chores and approvals
- `chore_templates(id, household_id, title, description, reward_coins, reward_points, repeat_rule, is_active, created_at)`
- `chore_assignments(id, household_id, child_id, chore_template_id, due_at, status, assigned_by_user_id, created_at)`
  - status: `assigned`, `completed_pending`, `approved`, `rejected`, `expired`
- `chore_completions(id, assignment_id, child_note, completed_at)`
- `chore_approvals(id, assignment_id, decided_by_user_id, decision, decision_note, decided_at)`
  - decision: `approved`, `rejected`
  - unique: one final decision per assignment

### Wallet and ledger
- `wallet_profiles(id, household_id, child_id, spend_pct, save_pct, give_pct, created_at, updated_at)`
  - percentages sum to 100
- `ledger_entries(id, household_id, child_id, bucket, direction, amount, reason, ref_type, ref_id, created_by_user_id, created_at)`
  - bucket: `spend`, `save`, `give`
  - direction: `credit`, `debit`
- `wallet_balances(id, household_id, child_id, spend_balance, save_balance, give_balance, updated_at)`
  - denormalized read model; recomputed fallback from ledger if needed
- `wallet_transfers(id, household_id, child_id, from_bucket, to_bucket, amount, note, created_by_user_id, created_at)`

### Store and redemptions
- `store_items(id, household_id, name, item_type, price_coins, qty_available, time_block_minutes, one_child_at_a_time, is_active, created_at)`
  - `item_type`: `fixed`, `timed`
- `redemptions(id, household_id, child_id, store_item_id, qty, total_cost, status, requires_guardian_action, created_at, fulfilled_at NULL)`
  - status: `requested`, `approved`, `fulfilled`, `rejected`, `cancelled`

### Timed privileges
- `timed_sessions(id, household_id, child_id, store_item_id, started_at, stopped_at NULL, billed_units, billed_amount, status)`
  - status: `active`, `stopped`, `insufficient_funds`, `cancelled`
  - unique partial intent: one `active` session per `(child_id, store_item_id)`

### Family points and rewards
- `family_points_ledger(id, household_id, direction, points, reason, ref_type, ref_id, created_by_user_id, created_at)`
- `family_points_balance(id, household_id, points_balance, updated_at)`
- `family_rewards(id, household_id, title, points_goal, status, created_at, achieved_at NULL, reset_at NULL)`
  - status: `active`, `unlocked`, `archived`

### Audit and ops
- `audit_log(id, household_id, actor_user_id, action, entity_type, entity_id, before_json, after_json, created_at)`
- `schema_migrations(version, applied_at)`

## Key constraints and indexes
- Index all FKs plus:
  - `chore_assignments(household_id, child_id, status)`
  - `ledger_entries(child_id, created_at)`
  - `redemptions(household_id, status, created_at)`
  - `timed_sessions(child_id, status)`
- Prevent negative balances at service layer before commit.
- Approval payout idempotency: unique payout reference per assignment.

## Invariants
- Chore payout occurs only once and only after approval.
- Wallet split percentages always sum to 100.
- Spend/save/give balances never drop below zero.
- Family points balance equals sum of family points ledger.
- Timed session billing always references a valid timed store item.

## Migration sequencing (relative)
1. Create household/user/role tables.
2. Create chores + approvals.
3. Create wallet ledger + balances.
4. Create store + redemptions.
5. Create timed sessions.
6. Create family points + rewards.
7. Create audit and backfill indexes/constraints.

## Acceptance checklist
- [ ] Full schema represented as ordered SQL migrations.
- [ ] Foreign keys and required indexes added.
- [ ] Idempotency constraints for approvals/payouts enforced.
- [ ] Negative-balance prevention verified in service tests.
- [ ] `schema_migrations` runner succeeds on clean DB.
