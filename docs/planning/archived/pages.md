# Stewardwell MVP pages

Status: `Ready`

This document defines the MVP page set and what must appear on each page. It is implementation-focused and aligned to the roadmap, milestones, and backlog.

## Scope
- Web MVP only (server-rendered Flask templates).
- Roles in scope: `parent`, `caregiver`, `grandparent`, `child`.
- Includes only pages required for MVP flows.

## Page conventions
- Every page must enforce household scope checks.
- Every mutating action must require CSRF-protected form submission.
- Parent-only sensitive actions require extra confirmation (PIN/password re-entry where configured).
- Child pages must only show the authenticated child’s own data.

---

## Public pages

### 1) Landing
**Route:** `/`

**Purpose**
- Introduce Stewardwell and direct users to correct login/signup paths.

**Content**
- Product value summary.
- CTA buttons: Parent sign up, Parent login, Child login.
- Short feature overview: chores, wallets, store, rewards, timed privileges.

**Primary actions**
- Navigate to auth flows.

**Acceptance criteria**
- [ ] New users can find parent and child entry points in one click.
- [ ] No authenticated-only data appears.

### 2) Parent sign up / household creation
**Route:** `/auth/register`

**Purpose**
- Create a guardian account and start or join a household.

**Content**
- Email/password fields.
- Option: create household or join via code.
- Household name field (when creating).

**Primary actions**
- Submit registration.
- Join existing household by code.

**Acceptance criteria**
- [ ] Account and membership are created in one successful flow.
- [ ] Validation errors are shown clearly without losing form state.

### 3) Parent login
**Route:** `/auth/login`

**Purpose**
- Authenticate guardian-class users.

**Content**
- Email/password form.
- Link to registration.

**Primary actions**
- Log in.

**Acceptance criteria**
- [ ] Successful login routes to guardian dashboard.
- [ ] Invalid credentials return deterministic error messaging.

### 4) Child login
**Route:** `/kid/login`

**Purpose**
- Authenticate child users with child-friendly flow.

**Content**
- Household code + PIN fields.
- Optional remembered child quick-login tiles (if enabled).

**Primary actions**
- Log in as child.

**Acceptance criteria**
- [ ] Child reaches only their own dashboard context.
- [ ] PIN input accepts numeric values only.

### 5) Access denied
**Route:** `/403` (or framework error handler)

**Purpose**
- Handle forbidden access clearly and safely.

**Content**
- Message explaining lack of permission.
- Safe navigation buttons by role.

**Primary actions**
- Return to allowed dashboard.

**Acceptance criteria**
- [ ] Forbidden actions never leak protected data.
- [ ] User has a clear path back to allowed pages.

---

## Guardian pages (parent/caregiver/grandparent)

### 6) Guardian dashboard
**Route:** `/guardian/dashboard` (or `/parent/dashboard`)

**Purpose**
- Provide one-screen operational view.

**Content**
- Pending chore approvals count/list.
- Child balance summary (spend/save/give).
- Family reward progress.
- Active timed sessions.
- Recent activity feed.

**Primary actions**
- Jump to approvals, chores, wallets, store, rewards, timers.

**Acceptance criteria**
- [ ] Dashboard widgets reflect current household state.
- [ ] Links route to filtered, relevant work queues.

### 7) Household & members
**Route:** `/guardian/household`

**Purpose**
- Manage household profile and memberships.

**Content**
- Household metadata.
- Member list with role labels.
- Child profile list.

**Primary actions**
- Add/edit child profile.
- Invite/add guardian membership.
- Remove membership (parent-only guarded action).

**Acceptance criteria**
- [ ] Membership uniqueness enforced.
- [ ] Parent-only restrictions enforced for sensitive operations.

### 8) Chore templates & assignments
**Route:** `/guardian/chores`

**Purpose**
- Create and assign chores to children.

**Content**
- Chore template list and status.
- Create/edit form: title, description, rewards, repeat, due behavior.
- Assignment panel by child.

**Primary actions**
- Create/edit/archive template.
- Assign chore to child.

**Acceptance criteria**
- [ ] New assignments appear on child chore page.
- [ ] Template changes preserve assignment history integrity.

### 9) Approvals queue
**Route:** `/guardian/approvals`

**Purpose**
- Process completed chores pending decision.

**Content**
- Pending list with child, chore, timestamps, reward preview.
- Decision controls: approve/reject + optional note.

**Primary actions**
- Approve or reject completion.

**Acceptance criteria**
- [ ] Approval triggers payout exactly once.
- [ ] Repeat decision attempts do not double-pay.

### 10) Wallet management
**Route:** `/guardian/wallet`

**Purpose**
- Manage split policies and balances.

**Content**
- Per-child spend/save/give balances.
- Split percentage settings (child override + household default).
- Manual adjustment and transfer forms.
- Transaction history table.

**Primary actions**
- Update split policy.
- Adjust balances.
- Transfer between buckets.

**Acceptance criteria**
- [ ] Split percentages must total 100.
- [ ] Negative balances are blocked.
- [ ] All changes create auditable ledger entries.

### 11) Store management
**Route:** `/guardian/store`

**Purpose**
- Define and maintain redeemable items.

**Content**
- Item list with type (`fixed`/`timed`), cost, inventory, status.
- Create/edit item form.

**Primary actions**
- Add/edit/archive item.
- Configure timed item parameters.

**Acceptance criteria**
- [ ] Timed items require time-block settings.
- [ ] Inventory and availability state are respected in child store.

### 12) Redemption queue
**Route:** `/guardian/redemptions`

**Purpose**
- Process child redemption requests.

**Content**
- Requested items list with requester, cost, status, timestamp.
- Approve/reject/fulfill controls.

**Primary actions**
- Approve, reject, fulfill redemption.

**Acceptance criteria**
- [ ] Status transitions are valid and auditable.
- [ ] Fulfillment updates inventory and history correctly.

### 13) Family rewards
**Route:** `/guardian/rewards`

**Purpose**
- Manage pooled family reward goals.

**Content**
- Active goals and progress.
- Goal create/edit controls.
- Unlocked/archive views.

**Primary actions**
- Create goal.
- Archive/reset goal (parent-only for destructive actions).

**Acceptance criteria**
- [ ] Progress reflects family points ledger.
- [ ] Archive/reset permissions enforce parent-only rules.

### 14) Timed sessions monitor
**Route:** `/guardian/timer`

**Purpose**
- Supervise active timed privilege sessions.

**Content**
- Active sessions by child and item.
- Session start/stop times, accrued cost.
- Recent session history.

**Primary actions**
- Stop child session (guardian override).

**Acceptance criteria**
- [ ] One-child-at-a-time rules are enforced where configured.
- [ ] Stop action finalizes billing exactly once.

### 15) History & audit
**Route:** `/guardian/history`

**Purpose**
- Review operational history and sensitive changes.

**Content**
- Unified event stream (approvals, wallet changes, redemptions, timer billing).
- Filters by child, event type, and date range.

**Primary actions**
- Filter and inspect records.

**Acceptance criteria**
- [ ] Sensitive actions include actor, timestamp, and before/after context where applicable.
- [ ] Data is household-scoped and read-only.

---

## Child pages

### 16) Child dashboard
**Route:** `/kid/dashboard`

**Purpose**
- Give the child a simple home screen.

**Content**
- Today’s chores summary.
- Spend/save/give balances.
- Reward progress snapshot.
- Active timer status.
- Store highlights.

**Primary actions**
- Navigate to chores, store, timed play.

**Acceptance criteria**
- [ ] Child sees only their own records.
- [ ] Balance and status values match source data.

### 17) My chores
**Route:** `/kid/chores`

**Purpose**
- Let child complete assigned work.

**Content**
- Assigned chores list.
- Pending approval list.
- Completed/rejected feedback states.

**Primary actions**
- Mark assignment complete.

**Acceptance criteria**
- [ ] Completion submission changes state to pending approval.
- [ ] Child cannot modify another child’s assignment.

### 18) My wallet
**Route:** `/kid/wallet`

**Purpose**
- Show child-friendly financial progress.

**Content**
- Bucket balances.
- Recent transactions with clear labels.

**Primary actions**
- View only (no direct edits).

**Acceptance criteria**
- [ ] Values reconcile with ledger-derived balances.
- [ ] No guardian-only controls are visible.

### 19) Child store
**Route:** `/kid/store`

**Purpose**
- Let child redeem available items.

**Content**
- Browse available items with cost and availability.
- Redemption status list.

**Primary actions**
- Redeem item.

**Acceptance criteria**
- [ ] Redemption blocked when spend balance or inventory is insufficient.
- [ ] Status updates are visible after guardian action.

### 20) Timed play
**Route:** `/kid/timer`

**Purpose**
- Start/stop timed privileges safely.

**Content**
- Available timed items.
- Active session panel with elapsed time and billed cost.
- Session outcome/history snapshot.

**Primary actions**
- Start session.
- Stop session.

**Acceptance criteria**
- [ ] Start requires sufficient prepaid spend balance.
- [ ] Billing uses configured block size and rate.
- [ ] Session cannot remain active after stop/failure paths.

### 21) Family rewards progress
**Route:** `/kid/rewards`

**Purpose**
- Keep child motivated with shared goals.

**Content**
- Active family goals and progress bars.
- Unlocked rewards list.

**Primary actions**
- View progress only.

**Acceptance criteria**
- [ ] Goal progress matches household points totals.
- [ ] Child cannot edit goals.

---

## Minimum navigation map
- Public nav: Landing -> Parent Register/Login, Child Login.
- Guardian nav: Dashboard, Household, Chores, Approvals, Wallet, Store, Redemptions, Rewards, Timer, History.
- Child nav: Dashboard, My Chores, My Wallet, Store, Timed Play, Rewards.

## Build order (page layer)
1. Public auth pages + access denied.
2. Guardian dashboard + household/members.
3. Chores + approvals.
4. Wallet.
5. Store + redemptions.
6. Child dashboard + chores + store.
7. Timed play pages.
8. Rewards + history/audit.

## Definition of done for page implementation
- [ ] Route exists and is permission-protected.
- [ ] Required content blocks are present.
- [ ] Primary actions execute expected state changes.
- [ ] QA checklist item exists in `qa-plan.md` for each critical flow.
