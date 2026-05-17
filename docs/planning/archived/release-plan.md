# Stewardwell release plan

Status: `Ready`

## Release model
- Monolith deployment (Flask app + SQLite file).
- Promote through environments in sequence: local -> staging -> production.
- No calendar dates; release when gates are satisfied.

## Environment requirements
- Python runtime pinned.
- Writable persistent volume for SQLite DB.
- Automatic daily DB backup with retention policy.
- App config for secrets/session keys separated by environment.

## Pre-release gates
- [ ] Milestones M0–M6 exit criteria met.
- [ ] QA release gate from `qa-plan.md` passed.
- [ ] Risk items marked accepted/mitigated in `risks.md`.
- [ ] Migration chain tested from empty DB and previous snapshot.
- [ ] Rollback rehearsal completed.

## Deployment sequence
1. Freeze migration set for release candidate.
2. Deploy candidate to staging.
3. Run staging smoke + regression subset.
4. Create production backup snapshot.
5. Deploy app and run migrations in maintenance window.
6. Execute post-deploy smoke checks.
7. Monitor guardrail metrics and error logs.

## Post-deploy verification
- [ ] Login/logout for guardian and child works.
- [ ] Create/complete/approve chore flow works.
- [ ] Wallet balances update from approved chore.
- [ ] Store redemption and timed session flow works.
- [ ] Audit logs are written for sensitive actions.

## Rollback plan
- Trigger rollback if critical data integrity/auth defect detected.
- Steps:
  1. Put app in maintenance mode.
  2. Restore latest verified DB backup.
  3. Redeploy previous application artifact.
  4. Run smoke checks.
  5. Record incident and corrective tasks.

## Release artifacts
- migration bundle
- changelog summary
- known-issues list
- rollback checklist
- support handoff notes
