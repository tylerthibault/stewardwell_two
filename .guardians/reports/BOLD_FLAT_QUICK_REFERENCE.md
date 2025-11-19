# Bold Flat Theme - Quick Reference

## 🎨 Using the Theme System

### Toggle Dark Mode (Anywhere)
```html
<button onclick="BoldFlatTheme.toggleTheme()">Toggle Theme</button>
```

### Change Accent Color (Anywhere)
```html
<button onclick="BoldFlatTheme.applyAccentColor('#9b59b6')">Purple Theme</button>
<button onclick="BoldFlatTheme.applyAccentColor('#2ecc71')">Green Theme</button>
<button onclick="BoldFlatTheme.applyAccentColor('#e67e22')">Orange Theme</button>
```

### Add Full Theme Controls
```html
<!-- Theme toggle button -->
<div id="theme-toggle"></div>
<script>createThemeToggle('theme-toggle');</script>

<!-- Color picker with presets -->
<div id="color-picker"></div>
<script>createColorPicker('color-picker');</script>
```

## 🎯 Preset Colors

### Light Mode
- **Blue** (default): `#3498db`
- **Purple**: `#9b59b6`
- **Green**: `#2ecc71`
- **Orange**: `#e67e22`
- **Pink**: `#e91e63`
- **Cyan**: `#00bcd4`
- **Yellow**: `#f1c40f`

### Dark Mode  
- **Red** (default): `#ff3333`
- **Purple**: `#bb66ff`
- **Green**: `#00ff66`
- **Orange**: `#ff8833`
- **Pink**: `#ff3388`
- **Cyan**: `#00ddff`
- **Yellow**: `#ffdd33`

## 📝 CSS Classes Available

### Layout
- `.dashboard-container` - Max width 1400px, centered
- `.dashboard-header` - Hero section with accent border
- `.dashboard-grid` - Flexible column layout
- `.dashboard-card` - Card container with shadow

### Components
- `.nav-btn` - Bold navigation button
- `.card-header` - Accent-colored card header
- `.card-body` - Card content area
- `.kid-item` - Kid info card
- `.assignment-item` - Chore/purchase card
- `.modal` - Full-screen modal overlay
- `.form-group` - Form field container

### Buttons
- `.btn-primary` - Accent-colored button
- `.btn-secondary` - Gray button
- `.btn-success` - Green button (approve actions)
- `.btn-danger` - Red button (delete/reject actions)

### Typography
- `.coin-badge` - Yellow coin display
- `.timestamp` - Uppercase timestamp text
- `.empty-state` - Centered empty state message

## 🎨 CSS Variables Reference

### Colors
```css
--bg-primary          /* Main background */
--bg-secondary        /* Card backgrounds */
--bg-tertiary         /* Nested elements */
--text-primary        /* Main text */
--text-secondary      /* Muted text */
--accent-primary      /* Main accent (customizable) */
--accent-dark         /* Hover state */
--accent-darker       /* Active state & shadows */
--success-primary     /* Green success color */
--danger-primary      /* Red danger color */
--coin-primary        /* Yellow coin color */
```

### Spacing
```css
--space-xs: 0.5rem    /* 8px */
--space-sm: 0.75rem   /* 12px */
--space-md: 1rem      /* 16px */
--space-lg: 1.5rem    /* 24px */
--space-xl: 2rem      /* 32px */
--space-2xl: 2.5rem   /* 40px */
```

### Shadows (Solid, No Blur)
```css
--shadow-sm: 3px
--shadow-md: 4px
--shadow-lg: 6px
--shadow-xl: 8px
--shadow-2xl: 10px
```

### Borders
```css
--border-sm: 3px
--border-md: 4px
```

## 🔧 JavaScript API

### Theme Manager
```javascript
// Get current theme ('light' or 'dark')
BoldFlatTheme.getCurrentTheme()

// Apply theme
BoldFlatTheme.applyTheme('dark')
BoldFlatTheme.applyTheme('light')

// Toggle theme
BoldFlatTheme.toggleTheme()

// Apply accent color
BoldFlatTheme.applyAccentColor('#9b59b6')

// Get current accent color
BoldFlatTheme.getCurrentAccentColor()
```

### Helper Functions
```javascript
// Create theme toggle button
createThemeToggle('containerId')

// Create color picker UI
createColorPicker('containerId')

// Apply preset color
applyPresetColor('#3498db')

// Apply custom color
applyCustomColor('#custom-hex')
```

## 📐 Design Principles

### The Bold Flat Philosophy
1. **Zero Curves**: No border-radius anywhere
2. **Thick Borders**: 3-4px solid borders everywhere
3. **Solid Shadows**: No blur, only offset (gives 3D "pressed" effect)
4. **Press-Down Interaction**: Elements translate on hover/active
5. **Bold Typography**: 700-900 font weights, uppercase transforms
6. **High Contrast**: WCAG AA compliant color combinations

### Press-Down Animation Pattern
```css
/* Normal state */
box-shadow: 8px 8px 0 var(--accent-dark);

/* Hover state */
transform: translate(4px, 4px);
box-shadow: 4px 4px 0 var(--accent-dark);

/* Active state */
transform: translate(8px, 8px);
box-shadow: 0 0 0 var(--accent-dark);
```

## 🚀 Common Patterns

### Adding Bold Flat to New Component
```html
<div class="my-component" style="
    padding: var(--space-lg);
    background: var(--bg-secondary);
    border: var(--border-md) solid var(--accent-primary);
    box-shadow: var(--shadow-xl) var(--shadow-xl) 0 var(--accent-primary);
">
    Content
</div>
```

### Creating a Bold Flat Button
```html
<button style="
    padding: var(--space-md) var(--space-xl);
    background: var(--accent-primary);
    border: var(--border-sm) solid var(--accent-primary);
    color: #ffffff;
    font-weight: 800;
    text-transform: uppercase;
    cursor: pointer;
    transition: all 0.2s;
    box-shadow: var(--shadow-md) var(--shadow-md) 0 var(--accent-dark);
">
    Action
</button>
```

### Creating a Bold Flat Card
```html
<div class="dashboard-card">
    <div class="card-header">
        <h2>Card Title</h2>
        <button>Action</button>
    </div>
    <div class="card-body">
        <!-- Content -->
    </div>
</div>
```

## 📱 Responsive Behavior

Grid layouts auto-adjust:
```css
/* Kids list adapts from 1-4 columns based on screen width */
grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
```

Mobile-friendly:
- Touch targets are large (44px+ buttons)
- Text is readable (minimum 0.875rem)
- Spacing scales proportionally

## 🎓 Best Practices

### ✅ DO
- Use CSS variables for all colors, spacing, shadows
- Maintain the press-down interaction pattern
- Keep typography bold and uppercase for emphasis
- Use solid borders (3-4px)
- Test in both light and dark modes

### ❌ DON'T
- Add border-radius (breaks the "zero curves" principle)
- Use gradients (conflicts with bold flat aesthetic)
- Add blur to shadows (solid shadows only)
- Use thin borders (minimum 3px)
- Mix rounded and sharp corners

## 🔍 Troubleshooting

### Theme not loading?
```javascript
// Check in browser console:
console.log(BoldFlatTheme.getCurrentTheme());
console.log(BoldFlatTheme.getCurrentAccentColor());
```

### Colors not changing?
```javascript
// Clear saved preferences:
localStorage.removeItem('boldFlatTheme');
localStorage.removeItem('boldFlatAccentLight');
localStorage.removeItem('boldFlatAccentDark');
location.reload();
```

### Styles not applying?
1. Check CSS file is loading (DevTools → Network)
2. Check for CSS conflicts (DevTools → Elements → Computed)
3. Clear browser cache
4. Verify CSS variables in `:root`

## 📚 Further Reading
- `BOLD_FLAT_STYLE_GUIDE.md` - Complete design system
- `BOLD_FLAT_THEME_IMPLEMENTATION.md` - Implementation guide
- `BOLD_FLAT_MIGRATION_COMPLETE.md` - Migration details
- `src/static/css/bold-flat-theme.css` - Full CSS source
- `src/static/js/bold-flat-theme.js` - JavaScript utilities
