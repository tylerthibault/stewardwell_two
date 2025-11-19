# Bold Flat Design System - Style Guide

## Overview
A modern, accessible design system featuring zero rounded corners, thick solid drop shadows, and high contrast. Inspired by Font Awesome's bold aesthetic with a flat design philosophy.

## Design Principles

### 1. **Zero Curves**
- No rounded corners anywhere (`border-radius: 0`)
- All elements are perfectly rectangular
- Sharp, clean edges create a modern, professional look

### 2. **Thick Solid Shadows**
- All shadows are solid colors (no blur, no spread)
- Primary shadows: 8px offset for major elements
- Secondary shadows: 6px offset for navigation
- Small shadows: 4px offset for buttons and cards
- Press-down effect: Shadow reduces as element moves on interaction

### 3. **Bold Typography**
- Font: Inter (weights 400-900)
- Headers: 800-900 weight, uppercase, tight letter-spacing
- Body: 600-700 weight for readability
- All labels and buttons: Uppercase with consistent letter-spacing

### 4. **Thick Borders**
- Primary elements: 4px solid borders
- Secondary elements: 3px solid borders
- All borders use theme colors (never transparent)

### 5. **Press-Down Interaction**
```
Normal State:     box-shadow: 8px 8px 0 [color]
Hover State:      transform: translate(4px, 4px); box-shadow: 4px 4px 0 [color]
Active State:     transform: translate(8px, 8px); box-shadow: 0 0 0 [color]
```

## Color System

### Light Mode Base Colors
```css
--bg-primary: #ecf0f1      /* Main background */
--bg-secondary: #ffffff    /* Card backgrounds */
--bg-tertiary: #f8f9fa     /* Nested elements */
--text-primary: #2c3e50    /* Primary text */
--text-secondary: #7f8c8d  /* Secondary text */
--text-tertiary: #34495e   /* Body text in cards */
--border-primary: #2c3e50  /* Main borders */
--border-secondary: #333333 /* Alternative borders */
```

### Dark Mode Base Colors
```css
--bg-primary: #0d0d0d      /* Main background */
--bg-secondary: #1a1a1a    /* Card backgrounds */
--bg-tertiary: #0d0d0d     /* Nested elements */
--text-primary: #e0e0e0    /* Primary text */
--text-secondary: #999999  /* Secondary text */
--text-tertiary: #b3b3b3   /* Body text in cards */
--text-muted: #666666      /* Timestamps, help text */
--border-primary: #333333  /* Main borders */
--border-secondary: #4d4d4d /* Alternative borders */
```

### Accent Color System
Users can choose their accent color. Each accent color has three shades:

#### Accent Color Variables
```css
--accent-primary: [user choice]  /* Main accent */
--accent-dark: [darker shade]    /* Hover states, shadows */
--accent-darker: [darkest shade] /* Active states, deep shadows */
```

#### Preset Accent Colors

**Red (Default)**
- Primary: `#ff3333`
- Dark: `#cc0000`
- Darker: `#990000`

**Blue**
- Primary: `#3498db`
- Dark: `#2980b9`
- Darker: `#1f6391`

**Purple**
- Primary: `#9b59b6`
- Dark: `#8e44ad`
- Darker: `#6c3483`

**Green**
- Primary: `#2ecc71`
- Dark: `#27ae60`
- Darker: `#1e8449`

**Orange**
- Primary: `#e67e22`
- Dark: `#d35400`
- Darker: `#a04000`

**Pink**
- Primary: `#e91e63`
- Dark: `#c2185b`
- Darker: `#880e4f`

**Cyan**
- Primary: `#00bcd4`
- Dark: `#0097a7`
- Darker: `#00697c`

**Yellow**
- Primary: `#f1c40f`
- Dark: `#f39c12`
- Darker: `#d68910`

### Success/Danger Colors (Fixed)
```css
--success-primary: #27ae60   /* Light mode success */
--success-dark: #229954
--success-darker: #1e8449

--danger-primary: #e74c3c    /* Light mode danger */
--danger-dark: #c0392b
--danger-darker: #a93226

--success-primary-dark: #00cc44  /* Dark mode success */
--success-dark-dark: #00aa38
--success-darker-dark: #008829

--danger-primary-dark: #ff3333   /* Dark mode danger */
--danger-dark-dark: #cc0000
--danger-darker-dark: #990000
```

## Component Specifications

### Dashboard Header
- Background: `--bg-secondary`
- Border: `4px solid --accent-primary`
- Shadow: `8px 8px 0 --accent-primary`
- Padding: `2rem`

### Navigation Buttons
- Default State:
  - Background: `--bg-secondary`
  - Border: `4px solid --border-primary`
  - Shadow: `6px 6px 0 --border-primary`
  - Text: `--text-primary`

- Active/Hover State:
  - Background: `--accent-primary`
  - Border: `4px solid --accent-primary`
  - Shadow: `6px 6px 0 --accent-dark`
  - Text: Contrasting color (white or black depending on accent)

### Cards
- Background: `--bg-secondary`
- Border: `4px solid --border-primary`
- Shadow: `8px 8px 0 --border-primary`

### Card Headers
- Background: `--accent-primary`
- Border Bottom: `4px solid --accent-dark`
- Text Color: High contrast (white or black)

### Buttons

**Primary Button**
- Background: `--accent-primary`
- Border: `3px solid --accent-primary`
- Text: Contrasting color
- Shadow: `4px 4px 0 --accent-dark`
- Hover: Darker accent, translate(2px, 2px), shadow 2px 2px
- Active: Darkest accent, translate(4px, 4px), shadow 0

**Secondary Button**
- Light Mode: `#95a5a6` background
- Dark Mode: `#333333` background
- Same shadow/transform behavior

**Success Button**
- Use success color palette
- Same interaction pattern

**Danger Button**
- Use danger color palette
- Same interaction pattern

### Form Elements
- Input Fields:
  - Background: `--bg-tertiary`
  - Border: `3px solid --border-primary`
  - Focus: Border changes to `--accent-primary`, shadow `4px 4px 0 --accent-primary`

- Radio Labels:
  - Background: `--bg-tertiary`
  - Border: `3px solid --border-primary`
  - Shadow: `3px 3px 0 --border-primary`
  - Hover: Translate(2px, 2px), accent border

### Modals
- Background: `--bg-secondary`
- Border: `4px solid --accent-primary`
- Shadow: `10px 10px 0 --accent-dark`
- Overlay: `rgba(0, 0, 0, 0.9)` for dark, `rgba(44, 62, 80, 0.9)` for light

## Spacing Scale
```css
--space-xs: 0.5rem    /* 8px */
--space-sm: 0.75rem   /* 12px */
--space-md: 1rem      /* 16px */
--space-lg: 1.5rem    /* 24px */
--space-xl: 2rem      /* 32px */
--space-2xl: 2.5rem   /* 40px */
```

## Typography Scale
```css
--text-xs: 0.75rem     /* 12px - Help text */
--text-sm: 0.875rem    /* 14px - Small buttons, labels */
--text-base: 1rem      /* 16px - Body text, inputs */
--text-lg: 1.125rem    /* 18px - Subheadings */
--text-xl: 1.25rem     /* 20px - Names, important text */
--text-2xl: 1.5rem     /* 24px - Card headers */
--text-3xl: 2.5rem     /* 40px - Page headers */
```

## Accessibility

### Contrast Ratios
- All text must meet WCAG AA standards (4.5:1 for normal text)
- Accent colors automatically adjust text to white or black for optimal contrast
- Success/danger buttons use pre-tested high-contrast color combinations

### Focus States
- All interactive elements have visible focus states
- Focus uses accent color with 4px solid shadow
- Tab order is logical and intuitive

### Text Sizing
- Minimum text size: 14px (0.875rem)
- All text is resizable up to 200%
- Line height: 1.6-1.8 for body text

## Animation Guidelines
- All transitions: `0.2s` duration
- Transform and box-shadow transitions only (performance)
- No easing functions (instant, linear feel)
- Press-down effects create tactile feedback

## Implementation Notes

### CSS Custom Properties
Use CSS variables for easy theme switching:
```css
:root[data-theme="light"][data-accent="red"] {
    --accent-primary: #3498db;
    --accent-dark: #2980b9;
    /* ... */
}

:root[data-theme="dark"][data-accent="red"] {
    --accent-primary: #ff3333;
    --accent-dark: #cc0000;
    /* ... */
}
```

### Dark Mode Toggle
- Store user preference in session/database
- Apply `data-theme` attribute to root element
- All colors reference CSS variables

### Accent Color Selection
- Provide color picker in settings
- Store preference per user
- Apply `data-accent` attribute to root element

## Component Checklist
When creating new components, ensure:
- [ ] No rounded corners
- [ ] Thick borders (3-4px)
- [ ] Solid drop shadows (no blur)
- [ ] Press-down interaction pattern
- [ ] Uppercase text where appropriate
- [ ] Bold font weights (700-900)
- [ ] High contrast text colors
- [ ] Proper hover/active states
- [ ] Accessible focus states
- [ ] Uses CSS custom properties

## Best Practices
1. **Consistency**: Use the same shadow/transform values throughout
2. **Hierarchy**: Larger shadows for more important elements
3. **Feedback**: Every interaction should have visual feedback
4. **Simplicity**: Keep layouts clean and uncluttered
5. **Performance**: Animate only transform and opacity
6. **Accessibility**: Test with screen readers and keyboard navigation
7. **Theming**: Never hardcode colors - always use CSS variables
