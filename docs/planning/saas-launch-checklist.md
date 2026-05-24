# SaaS Launch Checklist

A step-by-step checklist for turning Stewardwell into a paid, multi-tenant product.

---

## 1. Define Tiers

- [x] Finalize Free vs. Pro feature limits
- [x] Suggested defaults:
  - [x] Kids: Free = 2, Pro = Unlimited
  - [x] Chores: Free = 5, Pro = Unlimited
  - [x] Store items: Free = 5, Pro = Unlimited
  - [x] Challenges: Free = 3, Pro = Unlimited
  - [x] Tasks: Free = 5, Pro = Unlimited
  - [x] Trusted devices: Free = 1, Pro = Unlimited
  - [x] Multiple parents: Free = No, Pro = Yes
  - [x] Chore history: Free = 7 days, Pro = Full
- [ ] Decide monthly and annual pricing (e.g. $4.99/mo or $39.99/yr)
- [x] Decide trial length — **14-day Pro trial on signup** ✅

---

## 2. Migrate to PostgreSQL

- [ ] Choose a managed Postgres provider (Render, Railway, Supabase, or Neon)
- [x] `DATABASE_URL` env var already wired in `src/__init__.py` — just set it to point to Postgres
- [ ] Run and verify all existing migrations against Postgres
- [ ] Remove SQLite-specific `_apply_sqlite_schema_fixes()` workarounds or make them conditional
- [ ] Test full app flow against Postgres locally before deploying

---

## 3. Model Changes

- [x] Add to `Family` model (`src/models/main.py`):
  - [x] `plan` — string, default `"free"` (values: `free`, `pro`)
  - [x] `trial_ends_at` — datetime, nullable
  - [x] `stripe_customer_id` — string, nullable
  - [x] `stripe_subscription_id` — string, nullable
  - [x] `subscription_status` — string, nullable (`active`, `past_due`, `canceled`, `trialing`)
- [x] SQLite `ALTER TABLE` migrations added to `_apply_sqlite_schema_fixes()` in `src/__init__.py`
- [x] `is_pro` property on `Family` — returns `True` if plan is pro OR trial is still active
- [x] `trial_active` and `trial_days_remaining` properties also added

---

## 4. Email Verification on Registration

- [x] Add `email_verified` boolean to `Parent` model
- [x] Add `email_verify_token_hash` and `email_verify_expires_at` to `Parent` model
- [x] `generate_verify_token()` and `verify_email_token()` methods added to `Parent`
- [x] On registration: sends verification email via Brevo + starts 14-day trial
- [x] `GET /verify-email/<token>` route added
- [ ] Block login for unverified parents (with a helpful resend link) — *not yet enforced at login*
- [x] `GET /POST /resend-verification` route added + template at `src/templates/public/auth/resend_verification.html`

---

## 5. Stripe Integration

- [x] `stripe==15.1.0` added to `requirements.txt` and installed
- [x] Env vars documented: `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_MONTHLY`, `STRIPE_PRICE_ID_ANNUAL`
- [ ] Create Stripe products and prices in the Stripe dashboard *(external step)*

### Checkout Flow
- [x] `GET /billing/upgrade` — creates Stripe Checkout Session, auto-creates Stripe Customer if needed
- [x] `GET /billing/success` — updates `Family.plan`, stores subscription ID
- [x] `GET /billing/cancel` — redirects back to settings with info flash

### Customer Portal
- [x] `POST /billing/portal` — creates Stripe Customer Portal session

### Webhooks
- [x] `POST /webhooks/stripe` — verifies signature with `STRIPE_WEBHOOK_SECRET`
  - [x] `checkout.session.completed` → set plan to pro, store subscription ID
  - [x] `invoice.payment_succeeded` → set status to active
  - [x] `invoice.payment_failed` → set `subscription_status = past_due`, send dunning email to all parents
  - [x] `customer.subscription.deleted` → downgrade to free, clear subscription ID

### Donate Button
- [ ] Create a one-time Stripe Payment Link in the Stripe dashboard *(external step)*
- [x] Add donate button to landing page pointing to that link — shown when `STRIPE_DONATE_URL` env var is set
- [x] Handle `payment_intent.succeeded` webhook to log donations → `Donation` model (`donations` table)

---

## 6. Discount Codes

- [x] `allow_promotion_codes=True` enabled on Stripe Checkout Session
- [ ] Create coupon codes in the Stripe dashboard *(external step)*
- [ ] (Optional) Build admin UI to create/deactivate codes via Stripe API

---

## 7. Limit Enforcement

- [x] `src/utils/limits.py` created — `FREE_LIMITS` dict, `can_add()`, `limit_reached_message()`
- [x] Enforcement added in routes:
  - [x] Add kid → checks active kid count
  - [x] Add chore → checks active chore count
  - [x] Add store item → checks active store item count
  - [x] Add challenge → checks active challenge count
  - [x] Add task → checks active task count
  - [ ] Add trusted device → check device count *(pending)*
  - [ ] Invite co-parent → check if plan is Pro *(pending)*
- [x] "Upgrade to Pro" flash message shown when limit is hit
- [x] Upgrade CTA banner on parent dashboard (trial countdown + free upgrade prompt)

---

## 8. Admin Portal

### Setup
- [x] `src/controllers/admin.py` created — `admin_bp` Blueprint
- [x] `is_superuser` boolean added to `Parent` model
- [x] `admin_required` decorator — 403 for non-superusers
- [x] Registered under `/admin/` prefix in `create_app()`

### Dashboard
- [x] Total families count
- [x] Active Pro subscriptions count
- [ ] MRR (pull from Stripe API) *(not yet implemented)*
- [x] New signups this week / month
- [x] Past-due count (highlighted in red if > 0)

### Family Management
- [x] Searchable family list (by family name)
- [x] Family detail view: plan, billing status, kid count, parent emails, last login, Stripe IDs
- [x] Manually override plan (set Free or Pro)
- [x] Extend trial (specify number of days)
- [x] Deactivate a family
- [x] Impersonate a family + `GET /admin/stop-impersonating` to return

### User / Parent Management
- [x] Searchable parent list (by name or email)
- [x] Trigger password reset email for a parent
- [ ] Deactivate a parent account *(stub added, needs `is_active` field on Parent)*

### Billing & Revenue
- [ ] List all Stripe subscriptions with status *(not yet implemented)*
- [ ] Per-family payment history *(not yet implemented)*
- [ ] Issue refund *(not yet implemented)*

### Discount Codes
- [ ] List all Stripe coupons/promotion codes *(not yet implemented)*
- [ ] Create new discount code *(not yet implemented)*
- [ ] Deactivate a code *(not yet implemented)*
- [ ] View per-code usage stats *(not yet implemented)*

### Donations
- [ ] Log and display one-time donation history *(not yet implemented)*
- [ ] (Optional) Trigger thank-you email on donation

### System Health
- [ ] Display app version / last deploy time *(not yet implemented)*
- [ ] Log of failed Stripe webhook deliveries *(not yet implemented)*
- [ ] Log of Brevo email send failures *(not yet implemented)*
- [ ] Link to Sentry dashboard *(not yet implemented)*

### Feature Flags *(optional)*
- [ ] Add `FeatureFlag` model (name, enabled_globally, enabled_family_ids)
- [ ] Admin UI to toggle flags per family or globally
- [ ] Helper `family_has_flag(family, flag_name)` used in routes/templates

---

## 9. Transactional Emails

- [x] Email verification on signup (via Brevo, `_send_verify_email()`)
- [ ] Welcome email (sent after verification) *(not yet implemented)*
- [x] Trial ending in 3 days reminder — APScheduler background job
- [x] Trial expired — downgraded to Free notification — APScheduler background job
- [x] Payment failed / dunning email — `_send_payment_failed_email()` called from Stripe webhook
- [ ] Subscription canceled confirmation *(not yet implemented)*
- [ ] (Optional) Donation thank-you email

---

## 10. Background Jobs

- [x] `APScheduler==3.11.2` added to `requirements.txt` and installed
- [x] `BackgroundScheduler` started in `create_app()` (runs every 12 hours)
- [x] `_job_expire_trials()` — downgrades families with expired trials + sends email
- [x] `_job_trial_reminders()` — sends reminder email to families with ~3 days left
- [x] `_job_purge_pending_devices()` — deletes `PendingDeviceRegistration` records older than 24 hours past expiry

---

## 11. Hosting & Infrastructure

- [ ] Provision managed PostgreSQL (see step 2)
- [ ] Set up custom domain + HTTPS (required for Stripe and QR device registration)
- [ ] Store all secrets in environment variables (never commit keys)
- [ ] Set a strong random `SECRET_KEY` in production
- [ ] Add Redis if using Celery for background jobs
- [x] `sentry-sdk[flask]==2.60.0` added to `requirements.txt` and installed *(not yet initialized in app)*
- [ ] Initialize Sentry in `create_app()` with `SENTRY_DSN` env var
- [ ] Configure Stripe webhook endpoint in Stripe dashboard pointing to production URL
- [ ] Set up log aggregation (Papertrail, Logtail, or Render's built-in logs)

---

## 12. Legal Pages

- [x] Terms of Service — `src/templates/public/legal/terms.html`, served at `GET /terms`
- [x] Privacy Policy — `src/templates/public/legal/privacy.html`, served at `GET /privacy` (includes COPPA section)
- [ ] Add links to both in footer of public pages *(not yet added to footer)*
- [ ] Required by Stripe before going live with real payments
- [x] COPPA compliance section included in Privacy Policy

---

## Suggested Build Order

1. ✅ Define tiers and pricing
2. ⬜ Migrate to PostgreSQL
3. ✅ Add plan fields to `Family` model
4. ✅ Email verification on registration
5. ✅ Stripe billing (checkout + webhooks + customer portal)
6. ✅ Limit enforcement in routes
7. ✅ Upgrade CTA for Free users
8. ✅ Discount codes via Stripe
9. ✅ Donate button via Stripe Payment Link
10. ✅ Admin portal — start with family list + manual plan override
11. ✅ Admin portal — billing, discount codes, donations
12. ✅ Transactional emails (verification, trial, dunning)
13. ✅ Background jobs for trial/email automation
14. ✅ Legal pages
15. ⬜ Production hosting hardening (Sentry, secrets, domain, HTTPS)


