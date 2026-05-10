# Stewardwell style guide

Status: `Ready`
Last updated: 2026-04-12

## Purpose
This guide defines the visual and verbal style for Stewardwell’s MVP.
It ensures a consistent experience across guardian and child flows while preserving core product constraints:
- approval before payout
- deterministic ledger behavior
- role-based permissions
- clear household ownership boundaries

Use this guide with:
- [roadmap.md](roadmap.md)
- [decisions.md](decisions.md)
- [permissions.md](permissions.md)
- [qa-plan.md](qa-plan.md)
- [release-plan.md](release-plan.md)

## Experience feel
Stewardwell should feel like a trusted family gameboard:
- `trustworthy`: money-like actions are explicit, reviewable, and predictable
- `hopeful`: progress is visible and motivating
- `energetic`: completion and milestones feel rewarding
- `educational`: copy reinforces stewardship habits over impulse spending

Design rule:
- Make progress feel fun.
- Make money and permissions feel precise.
- Keep presentation cinematic, but keep workflow language explicit.

## Audience model
Stewardwell serves two primary audiences in the same household context:
- guardian-class users (`parent`, `caregiver`, `grandparent`)
- `child`

Default UI stance is balanced:
- guardians get strong clarity and control cues
- children get motivational and easy-to-understand cues

## Voice and tone

### Child-facing tone
Default: encouraging + playful.

Rules:
- Use short, concrete sentences.
- Celebrate effort and progress.
- Explain limits without blame.
- Prefer “next step” guidance over generic errors.

Examples:
- Good: "Nice work—this chore is ready for approval."
- Good: "You need 3 more Coins to redeem this item."
- Avoid: "Insufficient funds." 

### Guardian-facing tone
Default: calm, explicit, action-oriented.

Rules:
- Lead with facts (status, amount, actor, time).
- Make irreversible actions explicit before confirmation.
- Use consistent operational language for approvals, transfers, and fulfillment.
- Avoid playful copy in high-risk operations.

Examples:
- Good: "Approve chore payout: 10 Coins, 5 Points for Alex."
- Good: "Transfer complete: 4 Coins moved from Save to Spend."

## Canonical terminology
Use these terms consistently across UI, docs, and QA scripts.

### Roles
- `parent`
- `caregiver`
- `grandparent`
- `child`

### Money, rewards, and progress
- `Coins`: canonical spendable child currency (UI-visible unit)
- `wallet`: umbrella term for child balances
- `Spend`, `Save`, `Give`: balance buckets
- `family points`: pooled household progress currency
- `family reward`: a shared reward goal funded by family points

### Flow and status terms
- `pending approval`, `approved`, `rejected`
- `redeemed`, `fulfilled`, `declined`
- `active`, `stopped`, `completed` (timed sessions)
- `permission denied` for role/ownership failures

## Visual direction

Primary theme mode for current design exploration: `Galactic Opera`.

Theme intent:
- Cinematic space-opera atmosphere.
- Parent-first control and trust cues remain dominant.
- Motivational energy comes from progress visuals, not ambiguous interactions.

### Overall style
- Dark, layered space backgrounds with subtle starfield texture.
- High-contrast panels with soft glow accents for focus areas.
- Structured layouts with obvious hierarchy for key actions.

### Color system (Galactic Opera)
Use these as conceptual tokens for mockups and implementation alignment:
- `space`: deep background tones (`#04070f`, `#0a1227`)
- `panel`: elevated surface tone (`#0f172e`)
- `line`: panel border/divider tone (`#22345e`)
- `ink`: primary text (`#eaf1ff`)
- `muted`: secondary text (`#9db0d6`)
- `gold`: primary emphasis and key CTA (`#f7cf63`)
- `blue`: informational highlight (`#6db4ff`)
- `red`: alert/risk highlight (`#ff5f66`)
- `green`: positive/success highlight (`#78ff9f`)

Rules:
- Never use glow effects as the only state indicator.
- Keep body text and critical controls at high contrast.
- Reserve strong accent saturation for CTAs and status cues.

### Typography and emphasis
- Headlines: uppercase and bold for cinematic framing.
- Body copy: sentence case and plain language for readability.
- Keep numeric telemetry prominent for balances, approvals, and timer state.

### Hierarchy and emphasis
- First emphasis: account context, child context, pending actions.
- Second emphasis: balances, points progress, timed-session state.
- Third emphasis: history/detail metadata.

### Status signaling
Status must be readable at a glance and never color-only.
Every status uses:
- label text
- icon or shape cue
- consistent placement across lists/cards/detail screens

Priority statuses:
- pending approval
- approved/rejected
- redeem fulfilled/declined
- timed session active/stopped

### Component posture (MVP)
Prefer simple server-rendered patterns:
- cards for summaries
- tables/lists for logs and queues
- explicit form controls with helper text
- confirmation screens for sensitive actions
- top status rail/nav with clear household context
- telemetry tiles for approvals, balances, points, and sessions

Avoid MVP overreach:
- no complex animation dependencies
- no hidden gestures for critical actions
- no ambiguous icon-only controls for money/permission actions
- no lore-heavy copy that obscures workflow meaning

## Interaction rules by workflow

### Chores and approvals
- Child completion feedback should be positive and immediate.
- Approval screens should emphasize one-payout-only outcomes.
- Rejections should include optional explanatory feedback text.

### Wallet and transfers
- Always show bucket source and destination for transfers.
- Never imply negative balances are allowed.
- Show post-action balances on confirmation.

### Store and redemption
- Show coin cost, quantity, and fulfillment state together.
- If blocked, explain exact reason (`not enough Coins`, `out of stock`, or permission rule).

### Timed privileges
- Active sessions must have persistent visible state.
- Show billing unit and current spend impact clearly.
- Guardians can stop sessions even if child started them.

## Content and microcopy standards
- Prefer plain language over finance jargon.
- One message per sentence; avoid stacked instructions.
- Error messages include cause + next step.
- Confirmation messages include who, what, and amount/time impact.
- Keep labels and button text consistent with canonical terms.

## Accessibility baseline
MVP UI must support:
- clear heading hierarchy per page
- keyboard-usable forms and actions
- visible focus states on controls
- non-color-dependent status cues
- readable contrast for text and status indicators

## Guardrails and anti-patterns
Do not:
- use different names for the same concept (`Coins` vs `credits`) in comparable screens
- use playful tone for permission denials or irreversible confirmations
- hide monetary impact details behind secondary interactions
- present child actions that imply cross-child or cross-household control

## Implementation checklist
Before marking a screen complete:
- [ ] Uses canonical terminology from this guide.
- [ ] Applies role-appropriate tone.
- [ ] Makes status and next action clear at first glance.
- [ ] Preserves approval/permission/ledger trust cues.
- [ ] Meets accessibility baseline requirements.

## Governance
If style rules conflict with business rules:
1. follow [decisions.md](decisions.md)
2. follow [permissions.md](permissions.md)
3. update this guide after decision changes are approved

When adding new features, update this file with:
- terminology additions
- tone rules by role
- workflow interaction constraints
- accessibility implications
