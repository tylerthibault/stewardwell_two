# Stewardwell architecture

## Overview
Stewardwell is a Flask monolith with server-rendered pages and a SQLite datastore. Business logic runs in service modules, while route handlers coordinate request validation, authorization, and rendering.

## Architectural goals
- Keep MVP delivery fast with minimal operational overhead.
- Preserve clean upgrade path to PostgreSQL later.
- Keep balance-related operations transaction-safe and auditable.

## Application shape
- `app/__init__.py`: app factory, config loading, blueprint registration.
- `app/auth/`: login, logout, session lifecycle.
- `app/family/`: household setup, child profiles, guardian membership.
- `app/chores/`: chore CRUD, assignments, completion workflow.
- `app/approvals/`: pending queue, approve/reject handling.
- `app/wallet/`: give/save/spend operations and adjustments.
- `app/store/`: store items, inventory, redemption flow.
- `app/timer/`: timed privilege session start/stop and billing.
- `app/rewards/`: family points and family reward lifecycle.
- `app/dashboard/`: parent/child dashboard views.
- `app/services/`: domain logic (ledger, payout, points, timers).
- `app/db.py`: connection and transaction utilities.

## Data and migration strategy
- SQLite in WAL mode.
- Foreign keys enabled per connection.
- Manual SQL migrations in `migrations/*.sql`.
- `schema_migrations` table tracks applied versions.
- Migration runner script applies migrations in order and stops on failure.

## Request lifecycle
1. Route receives request and validates required fields.
2. Role guard checks household membership and permission.
3. Service executes business logic in transaction.
4. Audit entries and ledger rows are written atomically.
5. Response renders template or returns JSON where explicitly needed.

## Concurrency constraints
- Use short transactions for wallet, inventory, and timer session updates.
- Enforce one active timed session per child and optional one-child-at-a-time per item.
- Re-check balance and inventory at commit time.

## Non-functional requirements
- Deterministic ledger operations (no floating-point money math).
- Idempotent approval and payout operations.
- Auditability for all manual balance changes and redemptions.
- Role checks on all mutating routes.
