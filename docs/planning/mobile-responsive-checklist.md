# Mobile Responsive Checklist

Track mobile/responsive polish across all parent and kid-facing pages.
Breakpoints: **mobile** ≤ 480px · **tablet** ≤ 768px · **desktop collapse** ≤ 820px (nav hamburger kicks in here)

---

## Navigation (shared component)

- [x] Sticky topbar replaces old pill nav
- [x] Desktop: brand + links + settings/logout + theme toggle in one row
- [x] Mobile (≤820px): links and actions hidden, hamburger shown
- [x] Hamburger opens full-width dropdown with all links + logout + theme toggle
- [ ] Close mobile menu on any link click (JS enhancement)
- [ ] Close mobile menu on outside tap (JS enhancement)
- [ ] Swipe-down gesture to close on touch devices

---

## Global / Layout

- [ ] `page-wrap` horizontal padding reduces on very small screens (≤360px)
- [ ] Flash messages full-width and readable at 320px
- [ ] No horizontal scroll on any page at 320px width
- [ ] Font sizes use `clamp()` or `rem` throughout (no fixed `px` on body text)
- [ ] Touch targets ≥ 44×44px on all interactive elements

---

## Parent Pages

### Dashboard
- [ ] Metric stat cards: 2-col grid on mobile instead of 4-col
- [ ] Kid summary cards stack vertically on mobile
- [ ] "Quick actions" buttons wrap cleanly

### Chores (`/parent/chores`)
- [ ] Chore card grid: 1-col on mobile, 2-col on tablet
- [ ] Card action buttons (Edit / Reset / Pause / Delete) wrap without overlap
- [ ] Create chore form fields stack to 1-col on mobile

### Chore Edit (`/parent/chores/<id>/edit`)
- [ ] Form fields stack to 1-col on mobile
- [ ] Back-to-chores link visible and accessible

### Schedule (`/parent/schedule`)
- [ ] Weekly grid: horizontal scroll on mobile (table doesn't overflow viewport)
- [ ] Kid filter pills wrap without clipping
- [ ] Week navigation prev/next buttons remain tappable

### Store (`/parent/store`)
- [ ] Store item cards: 1-col on mobile
- [ ] Add item form fields stack on mobile

### Challenges (`/parent/challenges`)
- [ ] Challenge cards stack cleanly on mobile
- [ ] Inline edit form fields stack on mobile

### Tasks (`/parent/tasks`)
- [ ] Stats metric row: wraps to 1-col on mobile
- [ ] Pending reviews section: approve/reject buttons stack on mobile
- [ ] Active task cards: action buttons (Edit / Delete) wrap cleanly
- [ ] Inline edit form: fields stack to 1-col on mobile

### History (`/parent/history`)
- [ ] Table replaced with card list on mobile (or horizontal scroll)
- [ ] Date range controls stack on mobile

### Settings (`/parent/settings`)
- [ ] All form sections stack on mobile
- [ ] Wizard trigger card visible and appropriately sized

---

## Kid Pages

### Chores (`/kid/chores`)
- [ ] Chore cards: full-width on mobile
- [ ] Photo upload controls usable on touch

### Store (`/kid/store`)
- [ ] Store item grid: 1–2 col on mobile

### Tasks (`/kid/tasks`)
- [ ] Task cards: full-width on mobile
- [ ] Claim/submit buttons large enough to tap

### Challenges (`/kid/challenges`)
- [ ] Challenge cards stack on mobile

---

## Authentication Pages (public)

- [ ] Login form centered and full-width on mobile
- [ ] Register form fields stack on mobile
- [ ] Kid login / PIN input large tap targets on mobile
- [ ] Forgot/reset password forms stack on mobile

---

## Testing Checklist (run after each major change)

- [ ] Chrome DevTools → iPhone SE (375×667)
- [ ] Chrome DevTools → Pixel 5 (393×851)
- [ ] Chrome DevTools → iPad Mini (768×1024)
- [ ] Safari on actual iOS device (if available)
- [ ] Landscape orientation on phone
- [ ] Zoom to 200% on desktop (accessibility)
