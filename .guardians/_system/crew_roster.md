# The Guardians - Crew Roster

Quick reference for @tylerthibault to know which Guardian to call.

---

## Active Guardians

### 🧹 Dylan - Python Code Quality Specialist
**Call when:** Python code needs review or refactoring
**Specializes in:** PEP8, SOLID principles, separation of concerns, complexity reduction
**Personality:** Direct, witty, no-nonsense with sass
**Command:** `@dylan review <file.py>`
**Core:** `/.guardians/_system/agents/dylan/dylan_core.md`

---

### 📚 Rowan - Documentation Specialist
**Call when:** Need to create or review documentation
**Specializes in:** READMEs, API docs, database schemas, feature docs, project documentation
**Personality:** Articulate, patient, detail-oriented, professional with edge
**Command:** `@rowan help` (shows menu of 23 doc types)
**Core:** `/.guardians/_system/agents/rowan/rowan_core.md`

---

### 💭 Jacob - Ideation & Thought Partner
**Call when:** Exploring ideas, stuck on problems, need hard questions asked
**Specializes in:** Brainstorming, challenging assumptions, finding blind spots, decision-making
**Personality:** Curious, probing, intellectually rigorous with warmth
**Command:** `@jacob I'm thinking about <idea>`
**Core:** `/.guardians/_system/agents/jacob/jacob_core.md`

---

### 💻 Emily - Frontend Developer & UI/UX Specialist
**Call when:** Frontend code needs review or improvement
**Specializes in:** React/Vue/JS, accessibility, responsive design, component architecture, UX
**Personality:** Optimistic, detail-obsessed, enthusiastic about good design
**Command:** `@emily review <component>`
**Core:** `/.guardians/_system/agents/emily/emily_core.md`

---

### 📊 Logan - Financial Analyst & Valuation Specialist
**Call when:** Need pricing analysis or sales proposals
**Specializes in:** Value-based pricing, ROI calculations, business proposals, market analysis
**Personality:** Analytical, persuasive, data-driven, sharp
**Command:** `@logan analyze price for <project>`
**Core:** `/.guardians/_system/agents/logan/logan_core.md`

---

### 🔒 Morgan - Security Specialist
**Call when:** Security audits, vulnerability analysis, or security reviews needed
**Specializes in:** Security audits, vulnerability scanning, threat analysis, secure coding practices
**Personality:** Vigilant, thorough, security-focused, methodical
**Command:** `@morgan security audit <path>`
**Core:** `/.guardians/_system/agents/morgan/morgan_core.md`

---

## Decision Tree: Which Guardian Do I Need?

### Code Issues?
- **Python code** → Dylan
- **Frontend code** → Emily
- **Other languages** → (Future Guardian)

### Documentation?
- **Any documentation need** → Rowan

### Thinking/Planning?
- **Exploring ideas** → Jacob
- **Stuck on problem** → Jacob
- **Need to make decision** → Jacob

### Business/Financial?
- **Pricing/valuation** → Logan
- **Sales proposal** → Logan
- **ROI analysis** → Logan

### Security?
- **Security audit** → Morgan
- **Vulnerability analysis** → Morgan
- **Secure coding review** → Morgan

---

## Common Workflows

### Building a New Feature
1. **Jacob** - Explore and validate the idea
2. **Emily** - Build the frontend (if applicable)
3. **Dylan** - Review the Python backend
4. **Rowan** - Document the feature
5. **Logan** - Analyze the value and pricing

### Cleaning Up Existing Code
1. **Dylan** or **Emily** - Review and find issues
2. Manager approves fixes
3. **Dylan** or **Emily** - Implement approved changes
4. **Rowan** - Update documentation if APIs changed

### Launching a Product
1. **Logan** - Price analysis
2. **Rowan** - Product documentation (README, user guides)
3. **Logan** - Business proposals for target customers

### Stuck on Architecture Decision
1. **Jacob** - Explore options and challenge assumptions
2. **Dylan** - Review code architecture implications
3. **Rowan** - Document the decision (architecture docs)

---

## Guardian Collaboration Matrix

| If... | Then also consider... |
|-------|----------------------|
| Dylan refactors code | Rowan updates docs if public API changed |
| Emily builds UI component | Rowan documents component API |
| Logan creates proposal | Rowan ensures product docs are ready |
| Jacob validates feature idea | Logan analyzes business value |
| Morgan finds security issues | Dylan/Emily implement security fixes |
| Any Guardian finds naming issues | Everyone appreciates clear names |

---

## Quick Commands Cheat Sheet

```bash
# Dylan (Python Code Quality)
@dylan review src/services/user_service.py
@dylan implement finding #3 from user_service.py review
@dylan batch fix all Small effort from auth.py review

# Rowan (Documentation)
@rowan help
@rowan review README.md
@rowan create database schema for user management

# Jacob (Ideation)
@jacob I'm stuck on <problem>
@jacob help me decide between <A> and <B>
@jacob challenge my assumptions about <topic>

# Emily (Frontend)
@emily review components/Dashboard.jsx
@emily accessibility audit src/components/
@emily implement finding #2 from Button.jsx review

# Logan (Financial)
@logan analyze price for <project> using docs/features.md
@logan create proposal for Acme Corp about <project>
@logan calculate roi for <company>

# Morgan (Security)
@morgan security audit src/
@morgan vulnerability scan <component>
@morgan review security for <feature>

```

# Future Agents
| Name | Description |
| ---- | ----------- |
| Testing Specialist | Test strategy, coverage analysis, test writing | 
| Performance Specialist | Performance optimization, profiling | 
| Database Specialist | Query optimization, schema design | 
| DevOps Specialist | CI/CD, deployment, infrastructure | 