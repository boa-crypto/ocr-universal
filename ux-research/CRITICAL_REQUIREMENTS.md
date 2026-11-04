# OCR Universal - Critical UX Requirements

## Tier 1: MVP Must-Haves (Immediate Impact)

### 1. Side-by-Side Document + Data View ⭐ CRITICAL
**Impact**: Addresses #1 pain point - reduces verification time by 40-50%
**Users**: Marie, Thomas (primary), All users benefit

**Requirements**:
- Split screen: Document viewer (50% left), data form (50% right)
- Synchronized scrolling between document and data
- Click field → highlight source area on document (visual linking)
- Hover field → show document excerpt in tooltip
- Locked layout (no accidental panel collapse)

**Success Metric**: Time on task reduces from 15 min to 8 min per document

---

### 2. Per-Field Confidence Scoring ⭐ CRITICAL
**Impact**: Enables focused verification on uncertain fields
**Users**: All users (especially Marie for error prevention)

**Requirements**:
- Display confidence % per field (not just document-level)
- Color coding: Green (>95%), Yellow (85-95%), Red (<85%)
- Icons + color for colorblind accessibility: ✓ ⚠ ✗
- Auto-sort fields by confidence (lowest first)
- User-configurable thresholds (David needs this)

**Success Metric**: Error rate reduces from 3% to <1%

---

### 3. Full Keyboard Navigation ⭐ CRITICAL
**Impact**: Eliminates mouse friction, enables flow state
**Users**: David (primary), All users benefit

**Requirements**:
- Tab/Shift+Tab: Navigate between fields
- Ctrl+→ / Ctrl+←: Next/previous document
- Ctrl+F: Jump to first low-confidence field
- Ctrl+S: Save, Ctrl+E: Export
- Ctrl+A/R/F: Approve/Reject/Flag document
- Keyboard shortcut overlay (Ctrl+?)
- No single-letter shortcuts (screen reader conflict)

**Success Metric**: David processes 100+ docs/hour (up from 30-40)

---

### 4. Instant Document Transitions
**Impact**: Maintains flow state for high-volume users
**Users**: David (primary), All users benefit

**Requirements**:
- Prefetch next 3 documents while user reviews current
- <500ms transition time (<300ms animation)
- Visual queue preview (thumbnails of next 5 documents)
- Background OCR processing on queued documents

**Success Metric**: <500ms perceived transition time

---

## Tier 2: High Priority (Post-MVP, Q1)

### 5. Click-to-Source (Jump to Document Location)
**Impact**: Critical for multi-page contracts
**Users**: Thomas (primary)

**Requirements**:
- Click field → PDF jumps to exact source location and highlights
- Page/line reference per field ("Page 3, line 12")
- Search within document with result highlighting

### 6. Error Correction Memory & Learning
**Impact**: Reduces repetitive corrections
**Users**: Marie, David (high-volume users)

**Requirements**:
- Store corrections per supplier/document type
- Apply learned patterns automatically
- User notification of auto-corrections applied

### 7. Batch Upload & Processing
**Impact**: Saves time on document acquisition
**Users**: Marie, Thomas, David

**Requirements**:
- Drag-and-drop entire folders
- Batch-specific templates
- Batch progress view with real-time status

### 8. Smart Export Templates
**Impact**: Reduces export failures
**Users**: Marie (primary)

**Requirements**:
- Saved templates per ERP (SAP, Sage, Cegid, Quickbooks)
- Visual field mapping (drag-drop)
- Pre-export validation
- One-click export for saved configurations

---

## Accessibility Requirements (Non-Negotiable)

### Visual Accessibility
- **Contrast**: WCAG AA minimum (4.5:1 text, 3:1 controls)
- **Colorblind-safe**: Use color + pattern/icons (not color alone)
- **Text scaling**: Support 200% browser zoom without breaking
- **High contrast mode**: Windows High Contrast support

### Keyboard Accessibility
- **All functionality** keyboard-accessible (no mouse-only features)
- **Logical tab order**: Follows visual layout
- **Skip links**: "Skip to document" / "Skip to data form"
- **Focus trap**: Modal dialogs properly trapped

### Screen Reader Compatibility
- **Semantic HTML**: Proper headings, landmarks, lists
- **ARIA labels**: All interactive elements labeled
- **Live regions**: Announce status changes, errors, completions
- **Form labels**: Every input has associated <label>

---

## Performance Requirements

### Processing Speed
- **OCR processing**: <3 seconds per page (standard 300 DPI)
- **Document loading**: <1 second initial load
- **Transitions**: <500ms between documents
- **Export**: <5 seconds for 100 documents

### Accuracy
- **OCR accuracy**: >90% for invoices, >85% for contracts
- **Confidence calibration**: >95% confidence = >98% accuracy
- **Error rate**: <1% after user verification

### Reliability
- **Uptime**: 99.5% availability
- **Data integrity**: Zero data loss, full audit trail
- **Offline capability**: Continue processing without network

---

## Prohibited Patterns (From Brand Guidelines)

### Visual
- ❌ Dashboard 4-cards égales with colored round icons
- ❌ Decorative gradients (blue→violet, rose→orange)
- ❌ Glass morphism (except light modal overlays)
- ❌ Neumorphism (emboss/deboss)
- ❌ Excessive shadows (>elevation-3)

### Interaction
- ❌ Animations >500ms (except full page transitions)
- ❌ Parallax scroll effects (except hero)
- ❌ Complex hover effects (rotation, scale >1.05)
- ❌ Custom decorative cursors
- ❌ Interface sounds (except critical notifications)

### Language
- ❌ "Intelligence artificielle de pointe"
- ❌ "Précision de 99.9%" (without public benchmark)
- ❌ "Solution tout-en-un"
- ❌ "Révolutionnaire" / "Disruptif"

---

## Success Metrics

### Task Performance
- **Task completion rate**: >95%
- **Time on task**: 50-60% reduction vs. current
- **Error rate**: <1%
- **Verification efficiency**: <40% of time on verification

### User Satisfaction
- **CSAT**: >4.2/5.0
- **NPS**: >40
- **Feature satisfaction**: >4.3/5.0 for top 3 features

### Business Impact
- **Time savings**: >70% vs. manual entry
- **Error cost reduction**: >50%
- **User retention**: >90% at 3 months, >80% at 12 months
