# Stewardwell Backend Game Plan

## Phase 1: Foundation
**Goal:** Database models + basic Flask app running with landing page

### 1.1 Database Models (SQLAlchemy)
- Create `src/models/family.py` - Family model
- Create `src/models/parent.py` - Parent model
- Create `src/models/kid.py` - Kid model
- Create `src/models/chore.py` - Chore model
- Create `src/models/chore_assignment.py` - ChoreAssignment model
- Define relationships and constraints
- Migration setup (Flask-Migrate)

### 1.2 Flask App Initialization
- Update `src/__init__.py` with app factory pattern
- Configure SQLAlchemy database connection (SQLite)
- Initialize Flask-Migrate
- Configure secret key and environment variables (.env)
- Register blueprints

### 1.3 Controller Blueprints
- Create `src/controllers/auth_controller.py` - Auth blueprint (registration/login routes)
- Create `src/controllers/parent_controller.py` - Parent blueprint (dashboard, manage family)
- Create `src/controllers/kid_controller.py` - Kid blueprint (kid dashboard, chores)
- Create `src/controllers/chore_controller.py` - Chore blueprint (chore management)
- Update `src/controllers/routes.py` - Main blueprint with landing page route

### 1.4 Database Initialization
- Initialize SQLite database
- Run initial migration (`flask db init`, `flask db migrate`, `flask db upgrade`)
- Verify tables created

### 1.5 Landing Page
- Update `src/templates/public/landing/index.html` - Basic landing page with app description
- Link to login/register pages (stub for now)
- Test landing page renders

**Deliverable:** Models defined, migrations run, app starts, landing page displays, blueprints registered.

---

## Phase 2: Parent Flow
**Goal:** Parents can signup, login, create family, add kids, create chores

### 2.1 Parent Registration
- Implement registration form validation
- Create family record on parent signup
- Create parent record (hash password, set as head)
- Auto-login after successful registration
- Redirect to parent dashboard

### 2.2 Parent Authentication
- Implement login form validation
- Verify email and password
- Set up Flask-Login session management
- Create login_required decorator
- Handle logout functionality
- Flash messages for auth errors

### 2.3 Parent Dashboard
- Display family information (name, family code)
- List all kids in family with coin balances
- List all chores with coin/point values
- Show pending chore assignments awaiting confirmation
- Navigation to add kid and create chore forms

### 2.4 Add Kid Functionality
- Create form to add kid (name input)
- Generate random 4-digit PIN
- Hash and store PIN
- Display PIN to parent (one-time view)
- Add kid to database
- Redirect back to dashboard with success message

### 2.5 Create Chore Functionality
- Create form to add chore (name, coin_value, point_value)
- Validate form inputs
- Save chore to database with parent as creator
- Redirect back to dashboard with success message
- Display chore in dashboard chore list

### 2.6 View Family Data
- Endpoint to view all kids in family
- Endpoint to view all chores in family
- Endpoint to view pending chore assignments
- JSON responses for potential AJAX calls

**Deliverable:** Parent can register, login, add kids with PINs, create chores, view family dashboard.

---

## Phase 3: Kid Flow
**Goal:** Kids can login with PIN, pick chores, complete them

### 3.1 Kid Login Page
- Create kid-friendly login interface
- Family code input field
- PIN code input (4-digit numeric)
- Remember device functionality (cookie-based)
- Display previously logged-in kids on device
- Quick login for remembered kids

### 3.2 Kid Authentication
- Validate family code exists
- Validate PIN against kid record in that family
- Hash comparison for PIN verification
- Create kid session (separate from parent session)
- Set remember-me cookie with kid ID
- Redirect to kid dashboard on success

### 3.3 Kid Dashboard
- Display kid's name and coin balance prominently
- Show available chores (not assigned or available for picking)
- List kid's active chore assignments (in-progress)
- List kid's completed chores (pending parent confirmation)
- Display coin balance with fun visual indicator
- Logout button

### 3.4 Pick Chore Functionality
- Display available chores with coin/point values
- "Pick This Chore" button for each chore
- Create ChoreAssignment record (status: 'in-progress')
- Remove from available list, add to active list
- Success message with encouragement

### 3.5 Complete Chore Functionality
- Display active chores with "Mark Complete" button
- Update ChoreAssignment status to 'pending'
- Set completed_at timestamp
- Move to pending confirmation list
- Success message ("Great job! Waiting for parent approval")

### 3.6 Kid Session Management
- Login required decorator for kid routes
- Check if logged in as kid (not parent)
- Prevent kids from accessing other kids' data
- Auto-logout on inactivity (optional)

**Deliverable:** Kids can login with PIN/family code, pick chores, mark complete, see coin balance.

---

## Phase 4: Chore Lifecycle
**Goal:** Parents can confirm/reject completed chores, award coins

7. **Chore Confirmation**
   - Parent view pending chores
   - Confirm chore (award coins to kid, status → confirmed)
   - Reject/adjust coins (partial award, status → confirmed)

8. **Coin Management**
   - Update kid coin_balance on confirmation
   - Transaction history (optional for MVP)

**Deliverable:** Full chore lifecycle working, coins awarded.

---

## Phase 5: Polish & Testing
**Goal:** Secure, tested, ready to run

9. **Security & Validation**
   - Input validation on all endpoints
   - Role-based access (parents can't access kid endpoints as kids, etc.)
   - CSRF protection

10. **Testing**
    - Unit tests for models
    - Integration tests for key flows (signup, chore lifecycle)

11. **Documentation**
    - README with setup/run instructions
    - API endpoint documentation

**Deliverable:** Tested, documented, ready for local use.

---

## Manager Approval Checklist
- [✅] **Phase 1:** Foundation (models + app structure) - COMPLETE
- [✅] **Phase 2:** Parent flow (auth + family management) - COMPLETE
- [ ] **Phase 3:** Kid flow (login + chore picking)
- [ ] **Phase 4:** Chore lifecycle (confirmation + coins) - PARTIALLY COMPLETE (confirm/reject already implemented)
- [ ] **Phase 5:** Polish & testing

---

## Tech Stack (Confirm)
- **Framework:** Flask
- **Database:** SQLite (local), SQLAlchemy ORM
- **Auth:** Flask-Login, Werkzeug password hashing
- **Migrations:** Flask-Migrate
- **Frontend:** Jinja2 templates (existing structure)

**Approve to proceed? Any changes needed?**
