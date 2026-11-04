# OCR Universal - Design System Implementation Guide

## 📦 Import Order

```css
/* 1. Design Tokens */
@import url('./colors.css');
@import url('./typography.css');
@import url('./spacing.css');
@import url('./animation.css');

/* 2. Base Styles */
@import url('./base.css');

/* 3. Components */
@import url('./components.css');
```

## 🎨 Color Usage Guidelines

### Primary Use Cases
- **Slate (--brand-primary)**: Headers, primary text, navigation, footers
- **Cyan (--brand-secondary)**: CTAs, links, validated data badges, primary actions
- **Amber (--brand-accent)**: Warnings, review-needed states, attention signals

### Semantic Colors
```css
/* Success - High confidence data */
.badge-success {
  background: var(--semantic-success-bg);
  color: var(--semantic-success);
  border: 1px solid var(--semantic-success-border);
}

/* Error - Failed validation */
.alert-error {
  background: var(--semantic-error-bg);
  color: var(--semantic-error);
  border-left: 4px solid var(--semantic-error);
}

/* Warning - Review needed */
.status-warning {
  background: var(--semantic-warning-bg);
  color: var(--semantic-warning-dark);
}
```

### Data Visualization
```css
/* Confidence meter */
.confidence-high { color: var(--data-confidence-high); }
.confidence-good { color: var(--data-confidence-good); }
.confidence-medium { color: var(--data-confidence-medium); }
.confidence-low { color: var(--data-confidence-low); }
.confidence-poor { color: var(--data-confidence-poor); }
```

## 🔤 Typography Guidelines

### Hierarchy
```html
<!-- Page Title -->
<h1 class="text-h1">Document Processing Dashboard</h1>

<!-- Section Headers -->
<h2 class="text-h2">Recent Documents</h2>

<!-- Card Headers -->
<h3 class="text-h4">Invoice #INV-2024-001</h3>

<!-- Body Text -->
<p class="text-body">This document contains...</p>

<!-- OCR Results (Monospace) -->
<pre class="text-mono">CONTAINER: TCLU3456789</pre>

<!-- Labels -->
<label class="text-label">Confidence Score</label>

<!-- Metadata -->
<span class="text-caption">Processed 2 minutes ago</span>
```

## 📏 Spacing System

### Component Padding
```css
/* Compact cards */
.card-compact { padding: var(--space-3); }

/* Standard cards */
.card { padding: var(--space-4); }

/* Spacious cards */
.card-large { padding: var(--space-6); }
```

### Layout Gaps
```css
/* Tight grids */
.grid-tight { gap: var(--space-2); }

/* Standard grids */
.grid { gap: var(--space-4); }

/* Spacious layouts */
.grid-spacious { gap: var(--space-8); }
```

## ⚡ Animation Guidelines

### Interactive States
```css
/* Buttons */
.btn {
  transition: background-color var(--duration-fast) var(--ease-out),
              transform var(--duration-fast) var(--ease-out);
}

.btn:hover {
  transform: translateY(-1px);
}

/* Cards */
.card-interactive {
  transition: box-shadow var(--duration-base) var(--ease-fluid),
              transform var(--duration-base) var(--ease-fluid);
}

.card-interactive:hover {
  box-shadow: var(--elevation-3);
  transform: translateY(-2px);
}
```

### Page Transitions
```css
/* Modal entrance */
.modal-enter {
  animation: fadeIn var(--duration-base) var(--ease-out);
}

@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}
```

## 🚫 What NOT to Do

### ❌ Never hardcode colors
```css
/* BAD */
.header { background: #1e293b; }

/* GOOD */
.header { background: var(--brand-primary); }
```

### ❌ Never use arbitrary spacing
```css
/* BAD */
.card { padding: 18px; margin: 23px; }

/* GOOD */
.card { 
  padding: var(--space-4); 
  margin: var(--space-6); 
}
```

### ❌ Never create slow animations
```css
/* BAD */
.slow-button {
  transition: all 800ms ease; /* TOO SLOW */
}

/* GOOD */
.fast-button {
  transition: background-color var(--duration-fast) var(--ease-out);
}
```

### ❌ Never mix font families randomly
```css
/* BAD */
.heading { font-family: 'Comic Sans', cursive; }

/* GOOD */
.heading { font-family: var(--font-primary); }
```

## 📱 Responsive Patterns

### Mobile-First Approach
```css
/* Base (mobile) */
.container {
  padding: var(--space-4);
}

/* Tablet and up */
@media (min-width: 768px) {
  .container {
    padding: var(--space-6);
  }
}

/* Desktop and up */
@media (min-width: 1024px) {
  .container {
    padding: var(--space-8);
  }
}
```

## 🌓 Dark Mode Implementation

### Theme Toggle Component
```html
<div class="theme-toggle" role="radiogroup" aria-label="Theme selection">
  <button class="theme-option" data-theme="light" role="radio">
    ☀️ Light
  </button>
  <button class="theme-option" data-theme="dark" role="radio">
    🌙 Dark
  </button>
  <button class="theme-option active" data-theme="system" role="radio">
    💻 System
  </button>
</div>
```

### JavaScript
```javascript
class ThemeManager {
  constructor() {
    this.theme = localStorage.getItem('theme') || 'system';
    this.applyTheme(this.theme);
  }

  applyTheme(theme) {
    if (theme === 'system') {
      document.documentElement.removeAttribute('data-theme');
    } else {
      document.documentElement.setAttribute('data-theme', theme);
    }
    localStorage.setItem('theme', theme);
  }
}

new ThemeManager();
```

## ✅ Implementation Checklist

### Phase 1: Foundation
- [x] Create colors.css with all variables
- [x] Create typography.css with type scale
- [x] Create spacing.css with base-4 scale
- [x] Create animation.css with timing functions
- [x] Document BRAND_FOUNDATION.md

### Phase 2: Components (Next)
- [ ] Base button styles
- [ ] Card components
- [ ] Form elements
- [ ] Navigation components
- [ ] Data display components
- [ ] Dark mode theme toggle

### Phase 3: Validation
- [ ] WCAG AA contrast testing
- [ ] Colorblind simulation (deuteranopia/protanopia)
- [ ] Performance budget verification
- [ ] Cross-browser testing

## 📊 Performance Budgets

- **First Contentful Paint**: < 1.5s
- **Largest Contentful Paint**: < 2.5s
- **Cumulative Layout Shift**: < 0.1
- **CSS File Size**: < 50KB (gzipped)
- **Font Loading**: < 500ms (with font-display: swap)

## 🔗 Related Files

- [Brand Foundation](./BRAND_FOUNDATION.md)
- [Color System](./colors.css)
- [Typography System](./typography.css)
- [Spacing System](./spacing.css)
- [Animation System](./animation.css)
