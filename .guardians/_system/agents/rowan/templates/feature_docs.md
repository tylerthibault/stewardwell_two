# Feature Documentation Template (Lexicon)

## What This Covers
- New feature specifications
- Release notes
- Feature announcements

---

## Format 1: Feature Specification

### Structure

```markdown
# Feature: [Feature Name]

**Status:** [Proposed / In Progress / Implemented / Released]  
**Version:** [Target version]  
**Owner:** @tylerthibault  
**Date:** 2025-11-13

---

## Summary
[2-3 sentences: What is this and why does it matter?]

---

## Problem Statement

### Pain Points
- [Specific problem users face]
- [Another problem]

### User Story
**As a** [user type]  
**I want** [goal]  
**So that** [benefit]

### Impact
- **Users Affected:** [Who benefits?]
- **Business Value:** [Why build this?]
- **Priority:** High / Medium / Low

---

## Requirements

### Functional
1. System shall [requirement]
2. Users must be able to [requirement]
3. Feature must [requirement]

### Non-Functional
- **Performance:** [Response time, throughput]
- **Security:** [Auth, data protection]
- **Scalability:** [How it scales]

### Out of Scope
- [Explicitly NOT doing]
- [Future consideration]

---

## Design

### User Flow
1. User navigates to [location]
2. User clicks [button]
3. System displays [screen]
4. User inputs [data]
5. System [action] and shows [result]

### Technical Design

**Architecture:**
```
[Simple diagram or description of how this fits into system]
```

**New Components:**
- Component 1: [Purpose, technology]
- Component 2: [Purpose, interfaces]

**Database Changes:**
```sql
-- New tables or alterations
CREATE TABLE feature_data (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**API Changes:**

**NEW: POST /api/v2/feature**
```json
Request: {"user_id": 123, "data": "value"}
Response: {"status": "success", "feature_id": 456}
```

**MODIFIED: GET /api/users/{id}** (now includes `feature_enabled` field)

**Dependencies:**
- New library: `library-name==1.2.3` - [Why]
- External service: [Service name] - [Purpose]

### Security & Performance
- **Auth/Authorization:** [How access is controlled]
- **Data Privacy:** [PII handling, compliance]
- **Performance:** [Expected load, caching strategy]
- **Potential Risks:** [Vulnerabilities and mitigations]

---

## Implementation Plan

### Phase 1: Foundation (Est: X days)
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

### Phase 2: Core Feature (Est: X days)
- [ ] Task 1
- [ ] Task 2

### Phase 3: Polish & Deploy (Est: X days)
- [ ] Task 1
- [ ] Task 2

**Total Timeline:** X weeks | **Target Release:** [Date/version]

---

## Testing Strategy

### Unit Tests
- Test scenario 1
- Test scenario 2
- **Coverage Target:** 90%+

### Integration Tests
- End-to-end scenario 1
- System interaction scenario 2

### Manual Testing Checklist
- [ ] Happy path works
- [ ] Edge case 1 handled
- [ ] Edge case 2 handled
- [ ] Errors handled gracefully
- [ ] Performance within SLA
- [ ] No security vulnerabilities

---

## Rollout & Migration

### Feature Flag
`feature_name_enabled` - Controls rollout

### Rollout Phases
1. **Week 1:** Internal testing (employees)
2. **Week 2:** Beta (10% of users)
3. **Week 3-4:** Gradual (25% → 50% → 100%)
4. **Week 5:** Full release, remove flag

### Migration Steps (if applicable)
1. **Data Migration:** [How existing data is migrated]
2. **User Communication:** [Email, in-app notification]
3. **Deprecation:** [Timeline for removing old feature]

### Rollback Plan
1. Disable feature flag immediately
2. Revert DB migrations: `rollback_script.sql`
3. Notify users
4. Fix and re-test before re-enabling

---

## Success Metrics

### KPIs
- **Adoption:** X% users enable within 30 days
- **Usage:** X actions per day
- **Performance:** <200ms response (95th percentile)
- **Error Rate:** <1%
- **Satisfaction:** >4.0/5.0

### Monitoring
- Dashboard: [Link]
- Alerts: Error rate >5% → Page on-call

---

## Documentation Updates
- [ ] Update README
- [ ] Add user guide section
- [ ] Update API docs
- [ ] Add to CHANGELOG.md
- [ ] Create tutorial/demo

---

## Risks & Mitigation

### Risk 1: [Description]
- **Likelihood:** High / Medium / Low
- **Impact:** High / Medium / Low
- **Mitigation:** [How we handle this]

---

## Open Questions
- [ ] Question 1: [Unresolved decision]
- [ ] Question 2: [Need input on]

---

## References
- Original issue: #123
- Design mockups: [Link]
- Related: [Feature Y, Feature Z]
```

---

## Format 2: Release Notes

### Structure

```markdown
# Release Notes - Version X.Y.Z

**Release Date:** 2025-11-13  
**Type:** Major / Minor / Patch

---

## 🎉 New Features

### [Feature Name]
[User-facing description of what's new]

**Why this matters:** [Benefit in plain language]

**How to use:**
1. Go to [location]
2. Click [button]
3. [Action]

**Example:**
```python
from package import new_feature
result = new_feature.do_something()
```

**Learn more:** [Docs link]

---

## ✨ Improvements
- Improvement 1: X% faster, clearer errors
- Improvement 2: [What changed and benefit]

---

## 🐛 Bug Fixes
- Fixed [issue] that caused [problem] (#123)
- Resolved [bug] when [condition] (#145)

---

## 🔧 Technical Changes

### API Changes
**New:**
- `POST /api/v2/feature` - [Description]

**Modified:**
- `GET /api/users` - Now includes `feature_enabled`

**Deprecated:**
- `GET /api/old_endpoint` - Use `/api/new_endpoint` (removed in v3.0)

### Breaking Changes ⚠️

**Change 1:**
- **What:** [Specific change]
- **Affected:** [Who/what use cases]
- **Migration:**
```python
# Before (deprecated)
old_function(param)

# After (new way)
new_function(param, new_required_param)
```

---

## 📦 Dependencies
- **Updated:** `library` v1.0 → v2.0
- **Added:** `new-lib==1.2.3` - [Why]
- **Removed:** `old-lib` - No longer needed

---

## 🚀 Upgrade Instructions

```bash
pip install --upgrade package-name
```

**Post-upgrade:**
1. Run migrations: `python manage.py migrate`
2. Restart services: `systemctl restart app`

---

## ⚠️ Known Issues
- Issue 1: [Description and workaround or tracking #123]

---

## 🙏 Contributors
- @contributor1 - [Contribution]
- @contributor2 - [Contribution]

---

## 📚 Links
- [Full changelog](CHANGELOG.md)
- [Migration guide](docs/migration.md)
- [Documentation](https://docs.example.com)
```

---

## Format 3: Feature Announcement

### Structure

```markdown
# Introducing [Feature Name]: [Catchy Subtitle]

**Published:** 2025-11-13

---

## The Problem
[Story about the pain point users experience]

---

## Meet [Feature Name]
[One sentence: what it is and the key benefit]

**What you can do:**
✅ [Benefit 1]  
✅ [Benefit 2]  
✅ [Benefit 3]

---

## How It Works

**Step 1: [Action]**  
[Screenshot/GIF]  
[Brief explanation]

**Step 2: [Action]**  
[Screenshot/GIF]  
[Brief explanation]

**Step 3: [Result]**  
[Screenshot/GIF]  
[Outcome description]

---

## Real Example

**Before [Feature]:**
- Manual process took X hours
- Error-prone

**With [Feature]:**
- Automated, takes X minutes
- Reliable

---

## Get Started

Available now in v.X.Y.Z

1. [Upgrade instruction]
2. [Navigate to feature]
3. [Start using]

**Learn more:**
- [Docs](link)
- [Tutorial](link)

---

## What's Next
Coming soon:
- [Future enhancement 1]
- [Future enhancement 2]

---

## Feedback
- [GitHub Discussions](link)
- [Email](email)
```

---

## Common Findings

### Missing Elements
- No problem statement (why this exists)
- User stories undefined
- Technical design missing
- No rollout/migration plan
- Success metrics undefined
- Breaking changes not documented

### Incomplete Sections
- Vague requirements
- API changes not detailed
- No examples or screenshots
- Edge cases not considered
- No rollback plan

### Clarity Issues
- Technical jargon in user docs
- Unclear migration instructions
- No visual aids when needed

### Accuracy Issues
- Docs don't match implementation
- Code examples don't work
- Performance claims unverified

---

## Lexicon's Tone

**When reviewing specs:**
- "Problem statement says 'users want this.' WHY do they want it? What problem does it solve?"
- "Love the mockups. Where's the technical design? How does this actually work?"
- "No rollout plan? You're shipping a major auth change and hoping for the best?"

**When reviewing release notes:**
- "Breaking changes buried in 'improvements'? These need their own section with ⚠️ warnings."
- "You changed the API but didn't document it. Future devs will curse your name."
- "Excellent release notes. Clear, organized, examples included. This is the standard."

**When reviewing announcements:**
- "This reads like a requirements doc, not an announcement. Tell a story."
- "You listed features but not benefits. Users care about 'what's in it for me.'"
- "Perfect balance of excitement and usefulness. Would definitely share this."

**When docs are excellent:**
- "Comprehensive spec: Problem → Solution → Implementation → Success. *Chef's kiss*"
- "Release notes that actually help users upgrade? Revolutionary."
- "This announcement makes me WANT to try the feature. That's the goal."

---

## Finding Template

```markdown
### Finding #X: Missing rollout plan for auth feature
**Severity:** 🟠 High **Effort:** Medium **Risk:** Medium
**Location:** features/new_auth.md
**Category:** Missing Section

#### The Issue
Major auth change documented but no rollout/migration plan. How do existing 
users transition? Timeline? What happens to old sessions?

**Current State:**
[Spec ends after Implementation Plan]

#### Options

**Option A: Comprehensive rollout section** [RECOMMENDED]
```markdown
## Rollout & Migration

### Feature Flag: `auth_v2_enabled`

### Timeline
- Week 1: Internal testing
- Week 2-3: Beta (10%)
- Week 4: Gradual (25→50→100%)
- Week 5: Remove flag

### Migration
1. **Existing sessions:** Valid 7 days, auto-migrate on login
2. **API keys:** Old keys work 30 days, email migration instructions
3. **Breaking changes:** Token format changes, backward compat via flag

### Rollback
1. Disable flag
2. Revert to old auth
3. Fix issues
4. Re-enable when stable

### Communication
- Email 1 week before
- In-app notification during
- Docs updated on release
```

**Option B: Minimal rollout notes**
[For smaller, non-breaking features]

#### Manager Decision
- [ ] Approve A
- [ ] Approve B
- [ ] Reject
- [ ] Needs Discussion

**Status:** PENDING
```

---

**Lexicon's reminder:** "Great features deserve great documentation. Don't ship half the story."