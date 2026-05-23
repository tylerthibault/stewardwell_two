# SaaS Launch Checklist

A step-by-step checklist for turning Stewardwell into a paid, multi-tenant product.

---

## 1. Define Tiers

- [ ] Finalize Free vs. Pro feature limits
- [ ] Suggested defaults:
  - [ ] Kids: Free = 2, Pro = Unlimited
  - [ ] Chores: Free = 5, Pro = Unlimited
  - [ ] Store items: Free = 5, Pro = Unlimited
  - [ ] Challenges: Free = 3, Pro = Unlimited
  - [ ] Tasks: Free = 5, Pro = Unlimited
  - [ ] Trusted devices: Free = 1, Pro = Unlimited
  - [ ] Multiple parents: Free = No, Pro = Yes
  - [ ] Chore history: Free = 7 days, Pro = Full
- [ ] Decide monthly and annual pricing (e.g. $4.99/mo or $39.99/yr)
- [ ] Decide trial length (suggested: 14 days Pro trial on signup)

---

## 2. Migrate to PostgreSQL

- [ ] Choose a managed Postgres provider (Render, Railway, Supabase, or Neon)
- [ ] Update `DATABASE_URL` env var and `src/__init__.py` connection config
- [ ] Run and verify all existing migrations against Postgres
- [ ] Remove SQLite-specific `_apply_sqlite_schema_fixes()` workarounds or make them conditional
- [ ] Test full app flow against Postgres locally before deploying

---

## 3. Model Changes

- [ ] Add to `Family` model (`src/models/main.py`):
  - [ ] `plan` — string, default `"free"` (values: `free`, `pro`)
  - [ ] `trial_ends_at` — datetime, nullable
  - [ ] `stripe_customer_id` — string, nullable
  - [ ] `stripe_subscription_id` — string, nullable
  - [ ] `subscription_status` — string, nullable (`active`, `past_due`, `canceled`, `trialing`)
- [ ] Write migration for new columns
- [ ] Add a `is_pro` property to `Family` that returns `True` if plan is pro OR trial is still active

---

## 4. Email Verification on Registration

- [ ] Add `email_verified` boolean to `Parent` model
- [ ] Add `email_verify_token_hash` and `email_verify_expires_at` to `Parent` model
- [ ] On registration: send verification email via Brevo with a signed link
- [ ] Add `GET /verify-email/<token>` route that sets `email_verified = True`
- [ ] Block login for unverified parents (with a helpful resend link)
- [ ] Add "Resend verification email" route

---

## 5. Stripe Integration

- [ ] Add `stripe` to `requirements.txt` and install
- [ ] Add env vars: `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_MONTHLY`, `STRIPE_PRICE_ID_ANNUAL`
- [ ] Create Stripe products and prices in the Stripe dashboard

### Checkout Flow
- [ ] `GET /billing/upgrade` — creates a Stripe Checkout Session and redirects
- [ ] `GET /billing/success` — handles post-checkout redirect, updates `Family.plan`
- [ ] `GET /billing/cancel` — handles abandoned checkout

### Customer Portal
- [ ] `POST /billing/portal` — creates a Stripe Customer Portal session so families can manage/cancel

### Webhooks
- [ ] `POST /webhooks/stripe` — verify signature with `STRIPE_WEBHOOK_SECRET`
  - [ ] Handle `checkout.session.completed` → set plan to pro, store subscription ID
  - [ ] Handle `invoice.payment_succeeded` → confirm plan is active
  - [ ] Handle `invoice.payment_failed` → set `subscription_status = past_due`, send dunning email
  - [ ] Handle `customer.subscription.deleted` → downgrade to free

### Donate Button
- [ ] Create a one-time Stripe Payment Link in the dashboard
- [ ] Add donate button to landing page and/or settings pointing to that link
- [ ] (Optional) Handle `payment_intent.succeeded` webhook to log donations

---

## 6. Discount Codes

- [ ] Create coupon codes in the Stripe dashboard (% off or flat off, usage limits, expiry)
- [ ] Enable promotion codes on the Stripe Checkout Session (`allow_promotion_codes=True`)
- [ ] (Optional) Build admin UI to create/deactivate codes via Stripe API

---

## 7. Limit Enforcement

- [ ] Create a helper `src/utils/limits.py` with functions like `family_can_add_kid(family)`, etc.
- [ ] Add enforcement in routes:
  - [ ] Add kid → check kid count
  - [ ] Add chore → check chore count
  - [ ] Add store item → check store item count
  - [ ] Add challenge → check challenge count
  - [ ] Add task → check task count
  - [ ] Add trusted device → check device count
  - [ ] Invite co-parent → check if plan is Pro
- [ ] Show "Upgrade to Pro" flash message / modal when limit is hit
- [ ] Add upgrade CTA banner to parent dashboard for Free users

---

## 8. Admin Portal

### Setup
- [ ] Create `admin` blueprint at `src/controllers/admin.py`
- [ ] Add `is_superuser` boolean to `Parent` model
- [ ] Add admin login guard decorator — only allow superusers
- [ ] Register admin blueprint under `/admin/` prefix

### Dashboard
- [ ] Total families count
- [ ] Active Pro subscriptions count
- [ ] MRR (pull from Stripe API)
- [ ] New signups this week / month
- [ ] Failed payments count

### Family Management
- [ ] Searchable family list (by name, email, family code)
- [ ] Family detail view: plan, billing status, kid count, parent emails, last login
- [ ] Manually override plan (upgrade/downgrade without Stripe)
- [ ] Extend trial (set `trial_ends_at`)
- [ ] Deactivate / delete a family
- [ ] Impersonate a family (log in as that family for support purposes)

### User / Parent Management
- [ ] List all parents with email, family name, last login
- [ ] Trigger password reset email for a parent
- [ ] Deactivate a parent account

### Billing & Revenue
- [ ] List all Stripe subscriptions with status (pull from Stripe API)
- [ ] Per-family payment history
- [ ] Issue refund (passthrough to Stripe API)

### Discount Codes
- [ ] List all Stripe coupons/promotion codes
- [ ] Create new discount code (name, % or flat, usage limit, expiry)
- [ ] Deactivate a code
- [ ] View per-code usage stats

### Donations
- [ ] Log and display one-time donation history (from Stripe webhook)
- [ ] (Optional) Trigger thank-you email on donation

### System Health
- [ ] Display app version / last deploy time
- [ ] Log of failed Stripe webhook deliveries
- [ ] Log of Brevo email send failures
- [ ] Link to Sentry dashboard

### Feature Flags *(optional)*
- [ ] Add `FeatureFlag` model (name, enabled_globally, enabled_family_ids)
- [ ] Admin UI to toggle flags per family or globally
- [ ] Helper `family_has_flag(family, flag_name)` used in routes/templates

---

## 9. Transactional Emails

- [ ] Email verification on signup
- [ ] Welcome email (sent after verification)
- [ ] Trial ending in 3 days reminder (requires background job)
- [ ] Trial expired — downgraded to Free notification
- [ ] Payment failed / dunning email
- [ ] Subscription canceled confirmation
- [ ] (Optional) Donation thank-you email

---

## 10. Background Jobs

- [ ] Add APScheduler or Celery + Redis to `requirements.txt`
- [ ] Daily job: check families with `trial_ends_at < now` and `plan == free` → send trial expired email
- [ ] Daily job: check families with `trial_ends_at` in 3 days → send reminder email
- [ ] Daily job: purge expired `PendingDeviceRegistration` records

---

## 11. Hosting & Infrastructure

- [ ] Provision managed PostgreSQL (see step 2)
- [ ] Set up custom domain + HTTPS (required for Stripe and QR device registration)
- [ ] Store all secrets in environment variables (never commit keys)
- [ ] Set a strong random `SECRET_KEY` in production
- [ ] Add Redis if using Celery for background jobs
- [ ] Set up Sentry (free tier) for error monitoring — add `sentry-sdk[flask]` to requirements
- [ ] Configure Stripe webhook endpoint in Stripe dashboard pointing to production URL
- [ ] Set up log aggregation (Papertrail, Logtail, or Render's built-in logs)

---

## 12. Legal Pages

- [ ] Write / procure Terms of Service
- [ ] Write / procure Privacy Policy
- [ ] Add links to both in footer of public pages
- [ ] Required by Stripe before going live with real payments
- [ ] Review COPPA compliance (app involves children's data)

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


