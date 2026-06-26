# OpenProof Design Playbook

> A reusable UI/UX design system for building premium, editorial, product-specific apps.
>
> Inspired by Cash App, Block, and the final OpenProof design direction.
>
> **Do not copy OpenProof's identity.** Each app must define its own brand color,
> icon, typography, product language, and emotional tone. What this playbook
> codifies is the *craft standard*: confident, minimal, editorial, purpose-built,
> and free of generic dashboard patterns.

---

## Table of Contents

1. [Core Philosophy](#1-core-philosophy)
2. [The Machine Metaphor](#2-the-machine-metaphor)
3. [Visual Principles](#3-visual-principles)
4. [Designing Pages](#4-designing-pages)
5. [Component Rules](#5-component-rules)
6. [Typography & Rhythm](#6-typography--rhythm)
7. [Color & Light Mode](#7-color--light-mode)
8. [Icons & Branding](#8-icons--branding)
9. [Per-App Adaptation Guide](#9-per-app-adaptation-guide)
10. [Patterns to Avoid](#10-patterns-to-avoid)
11. [Agent Checklist](#11-agent-checklist)

---

## 1. Core Philosophy

### Design the app as a machine, not a dashboard.

A **dashboard** shows information. A **machine** performs a function.

- A proof-of-existence app is a *proof terminal / receipt printer*.
- A payment app is a *transaction machine / vault*.
- A document signer is a *signing station / notary desk*.
- A scanner app is a *verification checkpoint*.

Before writing any UI code, define what machine the user is operating.
Every screen, button, and label should serve that machine. Nothing else.

### Use hierarchy instead of borders.

Borders are a crutch for weak layout. Instead:

- Use **spacing** to separate concepts — generous gaps between unrelated sections,
  tighter gaps within a section.
- Use **typography weight** (font-black, font-bold, font-semibold) to establish
  hierarchy without boxes.
- Use **rhythm** — consistent vertical padding that makes the page feel like a
  composed document, not a scattered grid.
- Use **alignment** to connect related elements.
- Reach for a **container only when grouping is essential for a specific mechanical
  reason** (e.g., a receipt ticket, a drop target, a compact data table).

### Every page has one dominant purpose.

If a page does more than one thing, split it or simplify.

- Home → orient and route.
- Create → execute one action.
- Verify → validate one thing.
- Result → confirm or deny.

The user should never wonder "what am I supposed to do here?"

### Every interaction feels like one continuous flow.

Avoid multi-column card layouts that scatter the user's attention.
Prefer vertical, staged layouts where each step passes naturally to the next.

---

## 2. The Machine Metaphor

Every app should define its own metaphor. This metaphor drives layout, language,
and interaction patterns. Examples:

| App Type        | Metaphor                | Language                | Layout Direction          |
|-----------------|-------------------------|-------------------------|---------------------------|
| Proof of existence | Proof terminal / receipt printer | "Register", "Verify", "Fingerprint" | Vertical terminal flow |
| Payment / finance   | Transaction machine / vault    | "Send", "Receive", "Balance"    | Single-action per screen  |
| Document signing    | Signing station / notary desk  | "Sign", "Witness", "Seal"      | Staged wizard            |
| File scanner / OCR  | Scanning checkpoint            | "Scan", "Extract", "Review"    | Top-down scanner          |
| Health tracker      | Vital-signs monitor            | "Log", "Trend", "Check-in"     | Timeline + single metric  |
| AI chat / agent     | Conversation panel / terminal  | "Ask", "Respond", "Thread"     | Chat strip + input dock   |

To define your metaphor, answer:

1. What is the single most common action a user takes?
2. If this app were a physical machine, what would it look like?
3. What is the emotional tone? (calm, urgent, playful, serious, clinical)
4. What is the confirmation rhythm? (one-shot, staged, continuous)

Write the answers down. Refer to them before every UI decision.

---

## 3. Visual Principles

### The Canvas

- The default background is the **brand darkness** (true black `#000000` for dark
  mode, clean white `#ffffff` for light mode).
- Content sits directly on the canvas. Containers are the exception, not the rule.
- Every section should be justified in existing on the canvas. If a section can
  be just text + spacing, it should be.

### Hierarchy via Typography

```
font-black    → hero / result status / large numbers
font-bold     → section titles, key values
font-semibold → labels, action text
font-medium   → body text
```

No box needs a title if the typography is doing its job.

### Spacing Rhythm

- Use `py-20 sm:py-28` or `py-28 sm:py-40` between major sections.
- Use `mt-8` to `mt-16` between sub-sections within a section.
- Use `gap-4` to `gap-8` between items in a list.
- Use `space-y-6` to `space-y-10` within a coherent block.
- The page should feel *breathed*. If you are tempted to add a container, add
  more spacing instead.

### The Hero

- Typically `pt-28 sm:pt-40` from the top of `<main>`.
- `text-5xl sm:text-7xl lg:text-8xl font-black` for the main headline.
- `max-w-xl` or `max-w-2xl` for supporting text.
- CTAs are pill-shaped, large, clearly differentiated.
- **No hero card/container.** The headline sits on the canvas.

### Editorial Sections

For content sections (how-it-works, feature lists, principles):

- Use **large numbers** (`text-6xl sm:text-7xl font-black text-accent`) as the
  primary visual anchor.
- Use a **grid or horizontal rhythm** (`grid gap-12 sm:grid-cols-[auto_1fr]`)
  rather than equal-width card grids.
- Let the text breathe — `max-w-lg` or `max-w-xl` within each item.
- Asymmetry is intentional. Offset items (`sm:mt-12`) to avoid monotony.

### Data Strips

Instead of bordered info boxes, use full-width horizontal strips:

```
border-t border-b border-border-default
  → slim py-4 to py-6
  → inline items separated by gap-x-6 gap-x-8
  → label + value pattern, or just values
```

This is ideal for: registry addresses, account info, chain/network status,
key-value metadata, timestamps.

### Results / Confirmations

Results should feel **decisive**, not like just another page state.

- Large icon: `size-12` to `size-16` (CheckCircle2, CircleX, etc.).
- Bold status text: `text-3xl sm:text-4xl font-black`.
- Supporting detail below.
- A clear next action below the result, not hidden in a corner.
- The result IS the page, not a section within a card.

### Empty States

- Intentional: `py-12 text-center`.
- Title: `text-xl font-bold`.
- Description: `text-sm text-text-secondary max-w-md mx-auto`.
- **No icons.** No dashed borders. No illustrations unless product-specific.
- If the empty state is a call to action, include one pill button.

---

## 4. Designing Pages

### Home Page

The home page is a **brand landing page**, not a dashboard.

- **Hero**: On the canvas. Big headline, tagline, two CTAs. No hero card.
- **How it works / editorial section**: Numbered steps with asymmetric layout.
  No equal-width feature cards. Large numbers as anchors.
- **Status / data strip**: If there is persistent infrastructure data (registry
  address, version, network), show it as a border-to-border horizontal strip.
  Not a box.
- **Brand statement**: One bold paragraph about what the app is. No containers.

Avoid on home:
- Grids of feature cards with icons.
- Dashboard widgets.
- Login / signup forms (unless that IS the product).
- Carousels or rotating hero banners.

### Action Pages (Create, Submit, Register, etc.)

Action pages are **terminals**. The user arrives, executes, and leaves.

- Single-column vertical layout.
- Each step passes to the next naturally:
  ```
  Input → Preview → Confirm → Result
  ```
- No sidebars, no second-column panels, no widget grids.
- Status messages are inline text, not boxes.
- The result / receipt is part of the same page flow, below the action.

### Verification / Scanner Pages

- File / input selection at the top.
- Result is the hero — large, decisive, takes up visual space.
- Actions (copy, view on explorer, share) sit below the result.
- Secondary flows (import, batch, settings) sit *after* a significant visual
  break (border-top + spacing).
- Never put the result in a sidebar or second column.

### Result / Receipt / Ticket Pages

- The machine "prints" the result.
- If a permanent record (receipt, ticket, confirmation), use:
  - `border-t-2 border-dashed` as the separator from the flow above.
  - Monospace key-value pairs: `flex justify-between py-2 border-b`.
  - A centered footer `— AppName vX.Y.Z —` to close the ticket.
- Include clear next actions below (download, share, view on explorer, create
  another).

### History / Activity Sections

- One compact row per item.
- Use `flex items-start justify-between gap-4` layout.
- Key data inline: name, status badge (text only), timestamp.
- Action links are small pills (`rounded-full px-4 py-2 text-xs font-semibold`).
- The section title is simple: `text-xl font-bold`.
- Keep it scrollable within the page, not a separate card.

---

## 5. Component Rules

### Buttons & Pills

- **All buttons are pills**: `rounded-full px-7 py-3.5 text-sm font-semibold`.
- **Primary**: `bg-accent text-white hover:brightness-110`.
- **Secondary**: `bg-bg-surface-muted text-text-primary hover:bg-[#252525]`.
- **Danger**: `bg-error/10 text-error border border-error/20`.
- **Disabled**: `opacity-40 cursor-not-allowed`.
- No glow, no scale-on-hover, no translate effects. Keep it clean.
- Icon + text pills use `gap-2`.

### Navigation

- **Sticky header**: `sticky top-0 z-50 bg-bg-base/90 backdrop-blur-md`.
- Simple text logo: `text-lg font-bold`.
- Nav items: pill-style hover state (`rounded-full px-4 py-2 transition`).
- Minimal: 3-4 items max. No dropdowns, no nested menus.
- No logo images. Wordmark-only unless the icon IS the logo.

### Footer

- `border-t border-border-default px-6 py-12`.
- Split layout on desktop: left side (brand tagline), right side (links).
- Links are simple text: `text-xs text-text-secondary hover:text-text-primary`.
- Legal links (Privacy, Terms) only if legally required.
- Version number optional, muted.

### Data Rows

For key-value / metadata display:
```
flex justify-between gap-4 py-2 sm:py-3 border-b border-border-default
  dt: text-xs font-bold tracking-wider uppercase text-text-muted shrink-0
  dd: text-right break-all font-mono text-sm
```

This creates a clean, scannable data strip without a surrounding box.

### Drop Targets

No dashed borders. Instead:

- `rounded-2xl p-8 bg-bg-surface-muted hover:bg-[#222] cursor-pointer transition`.
- On drag: `bg-accent/10 ring-2 ring-accent`.
- Icon in a `rounded-full bg-accent/10 text-accent` circle.
- Text in two sizes: bold title + muted description.

### Inputs

- Minimal. No outlined borders by default.
- `bg-bg-surface-muted rounded-2xl px-5 py-3.5 text-sm`.
- Focus: `ring-2 ring-accent`.
- No labels above inputs — use placeholder text or a light helper line below.

### Status Indicators

Prefer plain text with color over pill badges:

```
text-xs font-bold tracking-wider uppercase text-accent  → active/success
text-xs font-bold tracking-wider uppercase text-error    → error
text-xs font-bold tracking-wider uppercase text-text-muted → neutral
```

Only use a background-filled pill when the status must be visually prominent
on an already busy surface.

---

## 6. Typography & Rhythm

### Type Scale

```
Hero headline:    text-5xl sm:text-7xl lg:text-8xl font-black
Section title:    text-3xl sm:text-4xl font-black
Sub-section:      text-2xl font-bold
Group title:      text-xl font-bold
Body:             text-base sm:text-lg
Supporting:       text-sm
Meta / label:     text-xs font-bold tracking-wider uppercase
```

### Line Length

- **Hero text**: `max-w-xl` to `max-w-2xl`.
- **Body paragraphs**: `max-w-lg` to `max-w-xl`.
- **Code / hash values**: `break-all font-mono`.

### Vertical Rhythm

```
Major section padding:  py-20 sm:py-28  or  py-28 sm:py-40
Sub-section margin:     mt-14 to mt-20
Block margin:           mt-8 to mt-12
Element gap:            gap-4 to gap-6
Text stack:             space-y-4 to space-y-6
```

### Font Stack

```css
--font-sans: "Your Sans Font Variable", ui-sans-serif, system-ui, sans-serif;
--font-mono: "Your Mono Font Variable", ui-monospace, monospace;
```

Use a distinct variable font with multiple weights (300–900) so `font-light`
through `font-black` all render distinctly. Mono font for code, hashes, values.

---

## 7. Color & Light Mode

### Dark Mode (default)

```css
--bg-base: #000000;
--bg-surface: #0d0d0d;
--bg-surface-muted: #1a1a1a;
--text-primary: #ffffff;
--text-secondary: #a0a0a0;
--text-muted: #8a8a8a;
--border-default: rgba(255, 255, 255, 0.06);
--accent: <brand color>;
--error: #ff4d4d;
```

### Light Mode

```css
--bg-base: #ffffff;
--bg-surface: #f5f5f5;
--bg-surface-muted: #ebebeb;
--text-primary: #000000;
--text-secondary: #4a4a4a;
--text-muted: #8a8a8a;
--border-default: rgba(0, 0, 0, 0.06);
--accent: <brand color>;
--error: #d32f2f;
```

### Rules

- **Dark mode is the default.** Design dark first. Light mode is a courtesy.
- **Do not invert.** Light mode is not dark mode with inverted colors. It has
  its own background surface values and border opacities.
- **The accent color stays the same in both modes.** It is the brand anchor.
- **Border opacity is very low** (0.06). If you can see borders clearly, you
  are using too much border.
- **Text-muted is the same in both modes.** Secondary text changes.
- **Errors invert** (white mode gets a darker red). Everything else is
  consistent.

---

## 8. Icons & Branding

### App Icon

- Single canonical source (1024×1024 PNG).
- Generate all platform sizes from that source:
  - Web/PWA: `icon-192x192.png`, `icon-512x512.png`, `apple-touch-icon.png`,
    `favicon.ico`, `favicon.png`.
  - macOS: `.iconset` with all 10 sizes.
  - iOS: 40, 58, 60, 80, 87, 120, 180, 1024.
  - Windows: `icon.ico` (16–256) + store assets.
  - Android: density-based mipmaps + adaptive foreground/background.
- The icon should work on both black and white backgrounds.

### In-App Icon Usage

- Use the app icon sparingly (hero section, about page, PWA splash screen).
- Do not put the icon in the nav bar as a logo mark unless the wordmark
  IS the icon.
- Functional icons (lucide, phosphor) should be from a consistent set with
  the same stroke width.
- Icons inside CTAs are `size-4`. Status icons are `size-10` to `size-16`.

---

## 9. Per-App Adaptation Guide

Every app using this playbook must define the following before writing UI:

### App Identity Card

| Property | Definition | Example (OpenProof) |
|----------|-----------|---------------------|
| **Core metaphor** | What machine is this? | Proof terminal / receipt printer |
| **Primary brand color** | One hex for accent | `#0081CC` |
| **Icon usage** | Where and how the icon appears | PWA, ticket footer, meta tags |
| **Typography personality** | Sans / mono weights | Bold sans black, crisp mono |
| **Emotional tone** | One word | Calm, infrastructural |
| **Main user action** | The verb | Register a file fingerprint |
| **Success state** | The confirmation feel | Receipt auto-downloads |
| **Empty state** | Pre-first-action feel | "Select a file to begin" |
| **Navigation style** | How many items, what tone | Minimal: Create / Verify / GitHub |

### Adaptation Checklist

Use this when starting a new app:

- [ ] Define the core metaphor. Write it down.
- [ ] Choose ONE brand color. Not a palette — one hex.
- [ ] Pick a variable sans font that has font-black weight.
- [ ] Write the tagline (8 words or fewer).
- [ ] Define the main user action in one verb.
- [ ] Define the success state in one sentence.
- [ ] Define the empty state text.
- [ ] Design the hero on a blank canvas before adding any containers.
- [ ] Design the action flow as a single-column vertical before considering
      multi-column.
- [ ] Design the result state as the hero of its page.
- [ ] Audit: remove every box, badge, and border you added without thinking.
- [ ] Audit: ensure dark mode was designed, not auto-inverted.

---

## 10. Patterns to Avoid

### ❌ Generic AI / SaaS patterns

```
❌ Three equal-width feature cards with icons and a "Learn More" button.
❌ Dashboard with 6 stat widgets in a 3×2 grid.
❌ Sidebar navigation with collapsible sections.
❌ Avatar circles, notification dots, "unread" badges.
❌ "Getting started" wizard cards.
❌ Gray profile placeholder circles.
❌ "Welcome back, [name]" greeting cards.
❌ Animated number counters for stats.
```

### ❌ Card/grid overuse

```
❌ Wrapping every section in a rounded box "card."
❌ Two-column "settings page" layout for an action page.
❌ Bordered boxes around empty states.
❌ Bordered boxes around form inputs.
❌ Bordered boxes around status messages.
❌ "Card grid" as the default layout pattern.
```

### ❌ Design crutches

```
❌ Dashed-border upload zones.
❌ Tiny uppercase badges (status, category, "new") everywhere.
❌ Pale gray nested panels (surface inside surface).
❌ Icon + label pairs that add no information.
❌ "Card" as a reusable component in a design system.
❌ Using borders to separate sections instead of spacing.
```

### ❌ Interaction anti-patterns

```
❌ Confirmation dialogs for non-destructive actions.
❌ Disabling buttons without explanation.
❌ Toast notifications that cover the action.
❌ Sidebars or drawers for primary flows.
❌ Tabs inside cards inside pages.
❌ Pagination when infinite scroll or "load more" would suffice.
```

---

## 11. Agent Checklist

Before declaring a UI pass complete, an AI agent must verify every item below:

### Layout

- [ ] Every section on the page has a single, obvious purpose.
- [ ] No section uses a bordered card/container unless it is mechanically
      justified (receipt ticket, drop target, compact data table).
- [ ] The page is readable and well-composed without any visual containers.
- [ ] Major sections are separated by generous whitespace, not by borders.
- [ ] The hero sits directly on the canvas (no hero card/container).
- [ ] All content is readable with `max-w-xl` or narrower line lengths.
- [ ] Light mode was designed, not automatically inverted from dark mode.

### Typography

- [ ] One type size does the work of one hierarchy level (no mixing weights
      and sizes and colors to express the same thing).
- [ ] Headings use `font-black` or `font-bold`.
- [ ] Labels and meta text use `text-xs font-bold tracking-wider uppercase`.
- [ ] Body text is at least `text-base` (16px) on desktop.
- [ ] No text is below 12px.
- [ ] Code/hash values use a distinct monospace font.

### Color

- [ ] Exactly one accent color (the brand color) is used for interactive and
      highlight elements.
- [ ] Success states use the accent color, not a separate green (unless green
      IS the brand color).
- [ ] Error states use a distinct red/error color.
- [ ] Text-muted is the same hex in both dark and light mode.
- [ ] Borders are barely visible (`rgba(x, x, x, 0.06)`).

### Buttons & Navigation

- [ ] All buttons are pill-shaped (`rounded-full`).
- [ ] Primary CTA is `bg-accent text-white`.
- [ ] Secondary CTA is `bg-bg-surface-muted`.
- [ ] Disabled state is `opacity-40`.
- [ ] Nav has 4 items or fewer.
- [ ] Nav items have pill-shaped hover states.
- [ ] No icons in nav unless they replace the wordmark.

### States

- [ ] Empty state is intentional text, not a card with an icon.
- [ ] Status messages are inline text, not boxes or toasts.
- [ ] Result/confirmation is the visual hero of its page.
- [ ] Error messages are clear, actionable text.
- [ ] Loading state is a simple text pulse or spinner, not a skeleton screen.

### Mobile

- [ ] All breakpoints use `sm:` and `lg:` prefixes (not hardcoded px values).
- [ ] Touch targets are ≥ 44px (`min-h-[44px]`).
- [ ] No side-by-side layouts below `sm` breakpoint.
- [ ] Text is readable without zoom at 375px viewport width.

### Product Identity

- [ ] The core machine metaphor is defined and consistently applied.
- [ ] Product language (verbs, labels) matches the metaphor.
- [ ] The brand color is used consistently everywhere.
- [ ] No generic UI text ("Welcome!", "Get started", "Dashboard").
- [ ] The app could be recognized by its design language without seeing the
      logo.

### Final Audit

- [ ] Remove every box, badge, and border added without mechanical justification.
- [ ] Read the page aloud: does it sound like a product or a component library?
- [ ] Screenshot the page and compare against the OpenProof reference.
- [ ] If the page uses generic AI/SaaS patterns (equal cards, dashboard widgets,
      bordered boxes everywhere), redesign before shipping.

---

*This playbook is derived from the OpenProof design direction.
Each app must define its own identity, but build with the same craft standard.*
