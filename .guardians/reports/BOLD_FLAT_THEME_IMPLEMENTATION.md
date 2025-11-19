# Bold Flat Theme System - Implementation Guide

## Overview
The Bold Flat Design System provides a cohesive light/dark mode experience with customizable accent colors. The system is built using CSS custom properties (variables) for easy theming and maintenance.

## Files
- **Style Guide**: `BOLD_FLAT_STYLE_GUIDE.md` - Complete design system documentation
- **CSS File**: `src/static/css/bold-flat-theme.css` - Main theme stylesheet (application-wide)
- **JavaScript**: `src/static/js/bold-flat-theme.js` - Theme switching and color customization utilities
- **Light Mode Templates**: `src/templates/private/parents/dashboard/index.html`, `index7.html`
- **Dark Mode Template**: `src/templates/private/parents/dashboard/index8.html`

## Current Implementation

### Application-Wide Setup
The Bold Flat theme is now available **across the entire application**:
- CSS is loaded in `src/templates/bases/private.html` for all private pages
- JavaScript utilities auto-load and restore user theme preferences from localStorage
- Theme persists across page navigation automatically

### Light Mode (Default)
- **Default Accent**: Blue (#3498db)
- **Background**: Light gray (#ecf0f1)
- **Text**: Dark (#2c3e50)
- **Philosophy**: Clean, professional, high-contrast
- **Usage**: Default theme on all pages

### Dark Mode
- **Default Accent**: Red (#ff3333)
- **Background**: Nearly black (#0d0d0d)
- **Text**: Light gray (#e0e0e0)
- **Philosophy**: Bold, modern, low-strain on eyes
- **Usage**: Add class `dark-theme` to body element or use JavaScript toggle

## How to Use the Theme System

### Method 1: Automatic (Recommended)
The theme system automatically:
- Loads user's saved theme preference from localStorage
- Restores custom accent colors
- Applies theme on every page load
- No setup required - just works!

### Method 2: JavaScript Theme Toggle
Add a theme toggle button anywhere in your template:

```html
<!-- In your template -->
<div id="theme-toggle-container"></div>

<!-- In your script block -->
<script>
    // Creates a light/dark mode toggle button
    createThemeToggle('theme-toggle-container');
</script>
```

### Method 3: JavaScript Color Picker
Add a color picker UI:

```html
<!-- In your template -->
<div id="color-picker-container"></div>

<!-- In your script block -->
<script>
    // Creates preset color buttons + custom color picker
    createColorPicker('color-picker-container');
</script>
```

### Method 4: Direct JavaScript Control
Use the global `BoldFlatTheme` object:

```javascript
// Toggle theme
BoldFlatTheme.toggleTheme();

// Apply specific theme
BoldFlatTheme.applyTheme('dark');  // or 'light'

// Apply custom accent color
BoldFlatTheme.applyAccentColor('#9b59b6');

// Get current theme
const currentTheme = BoldFlatTheme.getCurrentTheme();
```

### Method 5: Direct CSS Variable Modification
Edit `src/static/css/bold-flat-theme.css`:

```css
:root {
    /* Change these three values for light mode */
    --accent-primary: #9b59b6;   /* Your main color */
    --accent-dark: #8e44ad;      /* Darker shade for hover */
    --accent-darker: #6c3483;    /* Darkest shade for active/shadows */
}
```

### Method 2: Preset Color Options
Choose from these pre-defined color schemes (defined in style guide):

#### Light Mode Presets:
- **Blue** (default): `#3498db`, `#2980b9`, `#1f6391`
- **Purple**: `#9b59b6`, `#8e44ad`, `#6c3483`
- **Green**: `#2ecc71`, `#27ae60`, `#1e8449`
- **Orange**: `#e67e22`, `#d35400`, `#a04000`
- **Pink**: `#e91e63`, `#c2185b`, `#880e4f`
- **Cyan**: `#00bcd4`, `#0097a7`, `#00697c`
- **Yellow**: `#f1c40f`, `#f39c12`, `#d68910`

#### Dark Mode Presets:
- **Red** (default): `#ff3333`, `#cc0000`, `#990000`
- **Purple**: `#bb66ff`, `#9944dd`, `#7733bb`
- **Green**: `#00ff66`, `#00dd55`, `#00bb44`
- **Orange**: `#ff8833`, `#dd6611`, `#bb4400`
- **Pink**: `#ff3388`, `#dd1166`, `#bb0044`
- **Cyan**: `#00ddff`, `#00bbdd`, `#0099bb`
- **Yellow**: `#ffdd33`, `#ddbb11`, `#bb9900`

## Future Enhancement: Database-Driven Themes

To allow users to select their accent color dynamically, implement the following:

### Step 1: Add Database Fields
```python
# In src/models/parent.py or src/models/family.py
theme_mode = db.Column(db.String(10), default='light')  # 'light' or 'dark'
accent_color = db.Column(db.String(7), default='#3498db')  # Hex color code
```

### Step 2: Create Theme Settings Page
```python
# In src/controllers/parent_controller.py
@parent_bp.route('/settings/theme', methods=['GET', 'POST'])
@login_required
def theme_settings():
    if request.method == 'POST':
        theme_mode = request.form.get('theme_mode')
        accent_color = request.form.get('accent_color')
        
        # Save to database
        parent = Parent.query.get(session['parent_id'])
        parent.theme_mode = theme_mode
        parent.accent_color = accent_color
        db.session.commit()
        
        flash('Theme updated successfully!', 'success')
        return redirect(url_for('parent.dashboard'))
    
    return render_template('private/parents/settings/theme.html')
```

### Step 3: Apply Theme in Templates
```python
# In dashboard route
parent = Parent.query.get(parent_id)
theme_mode = parent.theme_mode or 'light'
accent_color = parent.accent_color or '#3498db'

# Calculate darker shades programmatically or use lookup table
accent_dark = calculate_darker_shade(accent_color, 0.8)
accent_darker = calculate_darker_shade(accent_color, 0.6)

return render_template(
    f'private/parents/dashboard/index{7 if theme_mode == "light" else 8}.html',
    accent_primary=accent_color,
    accent_dark=accent_dark,
    accent_darker=accent_darker,
    ...
)
```

### Step 4: Inject Custom CSS
```html
<!-- In template -->
<style>
:root {
    --accent-primary: {{ accent_primary }};
    --accent-dark: {{ accent_dark }};
    --accent-darker: {{ accent_darker }};
}
</style>
```

### Step 5: Create Color Picker UI
```html
<!-- Theme settings form -->
<form method="POST">
    <div class="form-group">
        <label>Theme Mode</label>
        <select name="theme_mode">
            <option value="light">Light Mode</option>
            <option value="dark">Dark Mode</option>
        </select>
    </div>
    
    <div class="form-group">
        <label>Accent Color</label>
        <input type="color" name="accent_color" value="{{ parent.accent_color }}">
        
        <!-- Or provide preset buttons -->
        <div class="color-presets">
            <button type="button" class="preset-btn" data-color="#3498db">Blue</button>
            <button type="button" class="preset-btn" data-color="#9b59b6">Purple</button>
            <button type="button" class="preset-btn" data-color="#2ecc71">Green</button>
            <!-- etc -->
        </div>
    </div>
    
    <button type="submit">Save Theme</button>
</form>
```

## Design System Features

### ✅ Implemented
- Zero rounded corners (sharp, modern aesthetic)
- Thick solid drop shadows (no blur)
- Press-down button interactions
- Bold typography (Inter font, weights 700-900)
- High contrast for accessibility
- Responsive grid layouts
- CSS custom properties for theming
- Light and dark mode support

### 🎨 Customizable
- Accent colors (3 shades: primary, dark, darker)
- All spacing via CSS variables
- All shadows via CSS variables
- Border widths standardized

### 🔒 Fixed (For Consistency)
- Success colors (green)
- Danger colors (red/red)
- Border widths (3px and 4px)
- Shadow offsets (3px, 4px, 6px, 8px, 10px)
- Font family (Inter)
- Typography scale

## Browser Compatibility
- Modern browsers: Full support (Chrome, Firefox, Safari, Edge)
- CSS Variables: Supported in all modern browsers
- Fallback: Not provided (assumes modern browser)

## Performance Considerations
- Only `transform` and `box-shadow` are animated (GPU accelerated)
- No blur effects (solid shadows only)
- No gradients in animations
- Fast, snappy 0.2s transitions

## Accessibility
- WCAG AA compliant contrast ratios
- All interactive elements have visible focus states
- Keyboard navigation fully supported
- Text is resizable up to 200%
- Clear visual hierarchy

## Migration Path
To migrate existing dashboards to this system:

1. Copy the CSS variables section from index7/index8
2. Replace hardcoded colors with CSS variables
3. Replace hardcoded spacing with spacing variables
4. Replace hardcoded shadows with shadow variables
5. Update border widths to use border variables
6. Test theme switching
7. Add accent color customization

## Best Practices
1. **Never hardcode colors** - Always use CSS variables
2. **Maintain shadow consistency** - Use defined shadow variables
3. **Keep spacing uniform** - Use spacing scale
4. **Test both themes** - Ensure changes work in light and dark mode
5. **Preserve press-down effect** - Essential to the design system
6. **Use uppercase for buttons** - Part of the bold aesthetic
7. **Keep borders thick** - 3-4px is standard
8. **No curves** - Zero border-radius throughout

## Troubleshooting

### Colors don't change when modifying CSS variables
- Clear browser cache
- Check browser DevTools to verify variable values
- Ensure variables are defined in `:root`

### Shadows look wrong
- Verify shadow variables are used correctly
- Check transform values in hover/active states
- Ensure shadow color matches accent color

### Theme switching doesn't work
- Verify correct template is being rendered (index7 vs index8)
- Check session/database for theme preference
- Ensure CSS variables are properly injected

## Support
For questions or issues with the Bold Flat Design System:
- Review the complete style guide: `BOLD_FLAT_STYLE_GUIDE.md`
- Check CSS variables in template files
- Verify design system principles are being followed
