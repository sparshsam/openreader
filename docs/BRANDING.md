# OpenReader Branding

## Kovina Ecosystem Hierarchy

```
KOVINA          Parent ecosystem     → kovina.org/standards/KOVINA_MANIFESTO.md
  ↓
OPEN            Product family       → kovina.org/standards/BRAND_GUIDELINES.md
  ↓
Reader          Individual product   → docs/BRANDING.md (this file)
```

## Open Product Family Hierarchy

The Open Product Family groups apps under the OPEN umbrella. Each app has its own accent color, icon, and domain, but shares the family header lockup pattern.

| App | Accent | Domain | Repository |
|-----|--------|--------|------------|
| OpenReader | `#ff255F` | reader.kovina.org | github.com/sparshsam/openreader |
| OpenSend | `#bc3fde` | send.kovina.org | github.com/sparshsam/opensend |
| OpenProof | *pending* | *pending* | github.com/sparshsam/openproof |
| OpenLedger | *pending* | *pending* | github.com/sparshsam/openledger |

## OpenReader Branding

### Accent Color
- **Primary:** `#ff255F` (pink-red)
- **Hover:** `#ff4777` (lighter)

### Icon
- **File:** `site/openreader-icon.svg`
- The application icon belongs only to OpenReader, never to OPEN.

### Typography
- **Primary font:** Huninn (rounded sans-serif), used for body and headings on the landing page.
- **Header lockup font:** Inter (or Huninn as fallback) for the OPEN / Reader stacked text.

## Header Implementation Reference

The nav logo lockup follows the Open Product Family standard:

```
[icon]    OPEN     ← uppercase, bold, 0.06em tracking, muted 50% opacity
          Reader   ← title case, medium weight, primary text color
```

- Icon and text are stacked side-by-side with a 6px gap.
- OPEN is typography only — no icon, no symbol, no badge, no monogram. Typography only.
- The icon belongs only to the individual app (OpenReader), never to OPEN.
- Do not merge the icon into the typography.
- Do not create a combined logo mark.
- Do not redesign the header lockup without explicit instruction.

### Canonical HTML

```html
<a href="/" class="logo" aria-label="OpenReader home">
  <img src="/openreader-icon.svg" alt="" class="logo-icon" />
  <div class="logo-text">
    <span class="logo-open">OPEN</span>
    <span class="logo-product">Reader</span>
  </div>
</a>
```

### CSS

```css
nav .logo { display: flex; align-items: center; gap: 6px; color: var(--text-primary); text-decoration: none; }
nav .logo .logo-icon { width: 28px; height: 28px; border-radius: 6px; }
@media (min-width: 768px) { nav .logo .logo-icon { width: 32px; height: 32px; } }
nav .logo .logo-text { display: flex; flex-direction: column; line-height: 1.25; }
nav .logo .logo-open { font-size: 10px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; opacity: 0.5; }
nav .logo .logo-product { font-size: 14px; font-weight: 500; margin-top: -2px; }
@media (min-width: 768px) { nav .logo .logo-product { font-size: 15px; } }
```

### Application Name
- "OpenReader" remains the full application name everywhere: documentation, code, metadata, footer, title tags.
- Only the header lockup changes from "OpenReader" text to the [icon] OPEN / Reader format.
- All other app naming stays the same.

## Canonical Reference

OpenPalette is the canonical reference implementation for the Open Product Family branding. When in doubt, refer to OpenPalette's header implementation first.

## Kovina Standards

Kovina standards are authoritative. OpenReader inherits them. Always follow Kovina standards first, then product-specific rules. Preserve branding consistency across all UI.
