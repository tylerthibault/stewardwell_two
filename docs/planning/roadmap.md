Here’s a practical roadmap for **Stewardwell**.

# Stewardwell roadmap

## Planning document map
Use this roadmap for product direction. Use the docs below for implementation details:

- [Planning index](README.md)
- [Decisions](decisions.md)
- [Architecture](architecture.md)
- [Data model](data-model.md)
- [Permissions](permissions.md)
- [Style guide](style-guide.md)
- [API contracts](api-contracts.md)
- [Backlog](backlog.md)
- [Milestones](milestones.md)
- [QA plan](qa-plan.md)
- [Metrics](metrics.md)
- [Release plan](release-plan.md)
- [Risks](risks.md)

## Phase 0 — product definition
Goal: lock the core concept before building.

### Outcomes
- Define app mission:
  - chores
  - stewardship
  - rewards
  - family teamwork
- Confirm primary user roles:
  - parent
  - child
  - caregiver
  - grandparent
- Define core systems:
  - chores
  - coins
  - points
  - store
  - family rewards
  - timed privileges
  - give/save/spend

### Deliverables
- product vision statement
- MVP feature list
- user stories
- data model draft
- wireframe sketch list
- naming and terminology decisions

### Key decisions
- Are points pooled across the whole family?
- Do all chores require approval?
- Can kids go negative on spend balance?
- Are timed items prepaid, postpaid, or both?
- Are give/save/spend percentages global or per child?
- Can savings be spent directly or only transferred by parent?

---

## Phase 1 — UX and system design
Goal: design the app structure before coding.

### Features to design
- authentication flow
- family creation flow
- child profile setup
- parent dashboard
- child dashboard
- chore assignment flow
- approval queue
- family store
- family rewards
- timed item timer flow
- give/save/spend wallet screens

### Deliverables
- low-fidelity wireframes
- screen map
- navigation plan
- database schema
- API plan
- permission model

### Suggested screens
#### Parent
- sign up / login
- create family
- manage children
- dashboard
- chores
- approvals
- store management
- rewards management
- wallet settings
- reports/history

#### Child
- dashboard
- my chores
- my bank
- store
- timed play
- rewards progress
- savings goals

---

## Phase 2 — technical foundation
Goal: create the base application and infrastructure.

### Recommended stack
Since Python is your main language:

- **Backend:** Flask (app factory + blueprints)
- **Database:** SQLite (raw `sqlite3` + manual SQL migrations)
- **Frontend:** Flask templates (Jinja) for fast MVP
- **Deployment:** Docker + Render/Fly.io/VPS
- **Auth:** Flask session auth with role-based permissions
- **Styling:** Tailwind CSS if web-based

### Work items
- initialize repo
- set up project structure
- configure database
- create environments
- set up authentication
- define base models
- set up admin panel
- configure deployment pipeline

### Deliverables
- running development environment
- staging environment
- auth system
- starter database schema

---

## Phase 3 — MVP build
Goal: launch the first usable version.

## Epic 1: Family and users
### Features
- parent account creation
- login/logout
- create family
- add child profiles
- edit child profiles
- simple child avatars

### Done when
- a parent can create a family and add children

---

## Epic 2: Chore system
### Features
- create chore
- edit chore
- delete chore
- assign chore to child
- due date
- optional repeat setting
- coin reward
- point reward
- chore status tracking

### Done when
- parent can assign chores and child can see them

---

## Epic 3: Completion and approval workflow
### Features
- child marks chore complete
- parent sees pending approvals
- parent approves/rejects
- optional feedback note
- approved chores trigger reward allocation

### Done when
- rewards only apply after parent approval

---

## Epic 4: Wallet system
### Features
- spend balance
- save balance
- give balance
- automatic earning split
- configurable percentages
- transaction history
- parent manual adjustments

### Done when
- approved chore rewards split correctly into buckets

---

## Epic 5: Family points and rewards
### Features
- pooled family points
- family reward creation
- reward goal progress
- unlocked reward state
- reward archive/reset

### Done when
- approved chores contribute to visible reward progress

---

## Epic 6: Family store
### Features
- create store items
- fixed coin cost
- quantity/inventory
- item categories
- child store browsing
- redemption flow
- parent fulfillment/approval if needed

### Done when
- child can spend spend-balance coins on store items

---

## Epic 7: Timed privileges
### Features
- timed store item type
- define cost per time block
- start/stop timer
- track active session
- assign usage to correct child
- bill from spend balance
- session history
- optional one-child-at-a-time lock

### Example
- Minecraft
- 7 coins per 10 minutes
- timer records session and charges child appropriately

### Done when
- each child can independently use and be charged for timed items

---

## Epic 8: Dashboards
### Parent dashboard
- chores pending approval
- balances by child
- current rewards progress
- active timed sessions
- recent activity

### Child dashboard
- today’s chores
- spend/save/give balances
- reward progress
- active timer
- store highlights

### Done when
- both parent and child have useful home screens

---

## Phase 4 — MVP launch prep
Goal: make it safe and usable for real families.

### Features
- parent PIN / protected settings
- validation and edge-case handling
- audit log for balance changes
- error handling
- onboarding flow
- seed/demo data
- responsive design
- basic analytics

### QA checklist
- no duplicate reward payouts
- timer sessions end cleanly
- store cannot overspend wallet
- split calculations are correct
- approval flow is reliable
- multiple children work correctly

### Deliverables
- beta-ready web app
- onboarding instructions
- test family accounts

---

## Phase 5 — beta launch
Goal: get real feedback from a few families.

### Beta goals
- validate usability
- find confusing flows
- confirm whether kids understand balances
- learn which features matter most:
  - chores
  - store
  - timed privileges
  - savings
  - tithing
  - rewards

### Metrics to watch
- weekly active families
- chores completed per week
- store redemptions
- timed session usage
- family reward completions
- savings goal adoption
- give balance usage

### Feedback questions
- Was setup easy?
- Did kids understand spend/save/give?
- Was the timer useful?
- Were approvals too manual?
- What rewards got used most?

---

## Phase 6 — V2 enhancements
Goal: deepen engagement after MVP proves useful.

### Chores and motivation
- recurring chores
- streaks
- badges
- achievements
- overdue reminders
- calendar view

### Timed privileges improvements
- auto-stop when balance runs out
- warnings before time ends
- schedule restrictions
- pause/resume timer
- parent remote stop
- device-specific privileges

### Stewardship improvements
- monthly giving summary
- tithe reminder
- savings goals with images
- locked savings
- transfer between buckets with parent approval
- financial lessons or prompts

### Store improvements
- bundles
- limited-time items
- wishlists
- parent approval thresholds
- item photos

### Family collaboration
- multiple parent/caregiver accounts
- household announcements
- group challenges
- shared routines

---

## Phase 7 — future platform expansion
Goal: grow beyond the initial web MVP.

### Potential next steps
- mobile app for parents
- simplified child tablet mode
- push notifications
- offline-safe timers
- barcode/QR redeem system
- allowance integration
- real-money conversion reports
- church/charity tracking exports
- printable family reward charts

---

# Recommended milestone plan

## Milestone 1 — foundation
- auth
- family accounts
- child profiles
- database models

## Milestone 2 — chores
- create/assign chores
- child completes chores
- parent approval flow

## Milestone 3 — stewardship wallet
- spend/save/give balances
- automatic split logic
- transaction history

## Milestone 4 — rewards economy
- family points
- family rewards
- family store fixed-price items

## Milestone 5 — timed privileges
- timed store items
- timers
- usage billing
- session logs

## Milestone 6 — polish and beta
- dashboards
- parent controls
- responsive UI
- testing
- onboarding

---

# Suggested build order
If you are building this yourself, this is the order I’d recommend:

1. Family accounts and child profiles
2. Chore creation and assignment
3. Chore completion and parent approval
4. Coin earning logic
5. Give/save/spend wallet
6. Family points and rewards
7. Fixed-price family store
8. Timed items like Minecraft
9. Dashboards and reports
10. Beta polish

---

# MVP definition in one sentence
**Stewardwell MVP is a family chore and stewardship app where parents assign chores, kids earn split rewards into give/save/spend balances, spend coins in a family store, contribute points toward family rewards, and use timed privileges like Minecraft through tracked coin-based sessions.**
