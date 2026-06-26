# Website Architecture Playbook

> A reusable architecture manual for building websites as public architecture — not webpages.
>
> This document defines proportions, spacing, rhythm, viewport behavior, responsive scaling,
> information architecture, page composition, and desktop → tablet → mobile translation.
>
> **Every project starts here**, before any colors, typography, illustrations, or branding are chosen.
>
> Companion to the [Design Playbook](./DESIGN_PLAYBOOK.md) — this covers the structural canvas;
> the Design Playbook covers visual components, colors, and typography on that canvas.

---

## Table of Contents

1. [Philosophy](#1-philosophy)
2. [Think in Canvas](#2-think-in-canvas)
3. [Spatial System](#3-spatial-system)
4. [Maximum Width & Fixed Containers](#4-maximum-width--fixed-containers)
5. [Alignment Grid](#5-alignment-grid)
6. [Vertical Rhythm](#6-vertical-rhythm)
7. [The 70% Rule & Visual Weight](#7-the-70-rule--visual-weight)
8. [The Fold & Hero Architecture](#8-the-fold--hero-architecture)
9. [Navigation & Footer](#9-navigation--footer)
10. [Layout Patterns](#10-layout-patterns)
11. [Desktop Layout](#11-desktop-layout)
12. [Tablet Layout](#12-tablet-layout)
13. [Mobile Layout](#13-mobile-layout)
14. [Responsive Hierarchy, Breakpoints & Column Rules](#14-responsive-hierarchy-breakpoints--column-rules)
15. [Performance Architecture](#15-performance-architecture)
16. [Accessibility Architecture](#16-accessibility-architecture)
17. [Information Priority System](#17-information-priority-system)
18. [Decision Hierarchy](#18-decision-hierarchy)
19. [Progressive Disclosure](#19-progressive-disclosure)
20. [Design Debt](#20-design-debt)
21. [Typography Hierarchy](#21-typography-hierarchy)
22. [Section Philosophy & Screen Occupancy](#22-section-philosophy--screen-occupancy)
23. [Reading Tempo](#23-reading-tempo)
24. [Visual Density & Alignment](#24-visual-density--alignment)
25. [Motion & Scroll Rhythm](#25-motion--scroll-rhythm)
26. [Browser Fit & Testing](#26-browser-fit--testing)
27. [Platform Translation](#27-platform-translation)
28. [The Block / Cash App Principle](#28-the-block--cash-app-principle)
29. [The Museum Test](#29-the-museum-test)
30. [Agent Checklist](#30-agent-checklist)

---

## 1. Philosophy

### Design websites as public architecture, not webpages.

A page should feel like walking through a modern art museum. Not browsing an application.

- The **browser is the room**.
- The **content is the exhibition**.
- The user scrolls naturally through **spaces**, not widgets.

Every page is a room in a gallery. The user walks through it. They stop when something catches their eye. They move on when they've absorbed it. Nothing competes — each piece has its own space, its own lighting, its own silence.

### Restraint is the architect's primary tool.

The most important design decision is what **not** to include. Every element must justify its existence. If it can be removed, remove it.

---

## 2. Think in Canvas

### Never think: "I need another section."

### Think: "What deserves its own space?"

**Space is free. Use it.**

- Whitespace is the **layout**. Not padding.
- A screen with 70% content and 30% empty space communicates confidence.
- A screen packed to 100% communicates anxiety.
- Let content breathe. The space around an element is as meaningful as the element itself.

### Canvas Rules

- The browser viewport is your gallery wall. Content is mounted on it.
- Do not frame every piece. Let some float.
- Groups belong together. Chapters belong apart. Distance communicates relationship.
- If two things are close, they are related. If they are far apart, they are different chapters.
- If you need a border, your spacing is wrong.

---

## 3. Spatial System

Whitespace is no longer subjective. It is **mathematical**.

The spatial system defines exact values for every relationship on the page. No random spacing. Every gap is chosen from a predefined scale and communicates a specific relationship level.

### The Spacing Scale

| Relationship | Value | Used Between |
|---|---|---|
| Tiny | 16px | Icon and label, stacked meta lines |
| Related | 32px | Headline and body within a section |
| Component group | 56px | Related but distinct feature items |
| Section | 120px | Major content blocks on a page |
| Chapter | 180px | Thematic transitions, new arguments |
| Viewport transition | 240px | Extreme tonal shifts, between very different ideas |

### Rules

- Every gap on the page must match one of these six values. No exceptions.
- If no value feels right, choose the next higher value — never a value between them.
- The relationship between any two elements is immediately readable from their spacing alone.
- A 120px gap means "new section coming." A 240px gap means "completely new chapter."

### Fixed Containers

Every page draws from a predefined set of container widths. Never invent widths.

| Container | Max Width | Used For |
|---|---|---|
| Reading | 720px | Prose, articles, body text |
| Content | 960px | Standard page content, hero text clusters |
| Feature | 1200px | Feature sections, multi-column layouts |
| Wide | 1440px | Full-section content, large media |
| Fluid | 100% | Imagery, timelines, separators, galleries, maps |

Every section on the page uses exactly one of these containers. Choose the container first, then build the content to fit it.

---

## 4. Maximum Width & Fixed Containers

### Maximum Width

One of the biggest mistakes on modern websites is allowing content to stretch forever. Use container limits (from [Spatial System](#3-spatial-system)):

| Context | Container |
|---|---|
| **Hero text** | 700–900px (Reading or Content) |
| **Reading content** | 600–720px maximum (Reading) |
| **Feature layouts** | 1100–1300px (Feature) |
| **Full-width visuals** | 100% (Fluid — imagery, timelines, separators, galleries, maps) |

**Never** paragraphs at 1600px wide. Full width is reserved exclusively for visual elements that demand the entire room — never prose.

### Horizontal Margins

Every page breathes. Content never hugs the screen edges.

| Viewport | Margin |
|---|---|
| Desktop | 96–128px |
| Tablet | 48–64px |
| Mobile | 20–24px |

These margins sit between the screen edge and the container boundary. The container sits inside the margin. Content sits inside the container.

---

## 5. Alignment Grid

Everything aligns to an invisible column grid. Not because users notice the grid — because designers stop making random layouts.

| Viewport | Columns | Gutter |
|---|---|---|
| Desktop (1280px+) | 12 | 24px |
| Tablet (768–1279px) | 8 | 20px |
| Mobile (375–767px) | 4 | 16px |

### Grid Rules

- Every element spans a whole number of columns.
- No element is placed at a column half-width.
- Content never starts or ends mid-gutter.
- Asymmetry is created by spanning different column counts (e.g. an 8-col content block beside a 4-col visual), never by off-grid positioning.
- On mobile (4 columns), most blocks span all 4 columns. Only deliberately compact elements use fewer.

### Why this matters

Without a grid, every layout is a unique snowflake that must be reasoned about from scratch. With a grid, the designer picks column spans — the structure is pre-resolved. The grid eliminates the mental load of positioning.

---

## 6. Vertical Rhythm

### Think in chapters, not sections.

Replace tight, uniform spacing with deliberate, generous rhythm drawn from the [Spatial System](#3-spatial-system):

| Element | Space |
|---|---|
| Tiny | 16px |
| Related | 32px |
| Group | 56px |
| Major section | 120px |
| New chapter | 180px |

Large whitespace creates confidence. A 120px gap between sections feels intentional. A 40px gap feels like the designer ran out of room.

### Rhythm Rules

- The vertical spacing between any two sections must come from the scale above.
- Never use arbitrary intermediate values (no 80px, no 100px, no 140px).
- Within a section, use 16px or 32px. Between sections, use 56px or 120px. Between chapters, use 180px.

---

## 7. The 70% Rule & Visual Weight

### The 70% Rule

Every page should have roughly **70% content, 30% empty space**.

Not mathematically. Visually.

- Negative space is intentional. It is not "wasted room."
- When the user lands on a page, they should immediately know what matters because everything else is quiet.
- If every square pixel is filled, nothing matters.

### Visual Weight

Every viewport should have a clear visual weight distribution. Not every section screaming equally.

| Zone | Weight |
|---|---|
| Primary content | ~60% |
| Supporting content | ~25% |
| Whitespace emphasis | ~15% |

#### How to apply

- The primary content (headline, hero visual, result) occupies the most visual mass — largest type, most screen area, highest contrast.
- Supporting content (subheadings, descriptions, secondary CTAs, data) takes less space, smaller type, quieter treatment.
- Whitespace emphasis is the visual breathing room that makes the primary content feel intentional — not leftover space, but deliberately reserved.

The primary content on any viewport should be identifiable at a glance. If five elements compete for the same visual weight, the page has no hierarchy.

---

## 8. The Fold & Hero Architecture

### The Fold

Do not obsess over "everything above the fold." Cash App and Block don't.

- The fold simply introduces the story.
- Scrolling is expected. Users scroll. Phones taught them to.
- A well-composed page is a narrative — the fold is the title page, not the whole book.

### Hero Architecture

The hero owns the viewport. Usually **85–100vh**.

**Never** cram information into the hero. Only include:

- Headline
- Supporting sentence (max one)
- Primary CTA
- Optional secondary CTA

**Nothing else.** No sub-headlines, no badges, no stats, no widgets, no illustrations competing for attention. The hero is a single statement.

---

## 9. Navigation & Footer

### Navigation

| Rule | Value |
|---|---|
| Max links | 4–5 |
| Header height | 72–84px |
| Behaviour | Sticky |
| Background | Transparent + blurred |

- Logo, Home, Features, About, GitHub, Theme Toggle — that's it.
- Not 12 links. Not dropdowns. Not nested menus.
- The header is furniture. It should be there when you need it and invisible when you don't.

### Footer

Footers aren't dumping grounds. Structure:

```
Brand — one sentence
Links — minimal
Copyright — one line
```

Keep them visually light. A footer is a closing flourish, not a sitemap.

---

## 10. Layout Patterns

Every page begins with one of these approved archetypes. The archetype determines the skeleton before any content is added.

### Landing Page

For marketing, announcement, or brand introduction.

```
Hero
   ↓
Story / "What is it?"
   ↓
Features / "Why should I care?"
   ↓
Trust / "Can I trust it?"
   ↓
CTA / "Take action"
```

Best for: product launches, startups, open-source projects, brand sites.

### Product Page

For showcasing a product with a demo or interactive element.

```
Hero
   ↓
Demo / "See it work"
   ↓
Features / "How it works"
   ↓
FAQ / "Common questions"
   ↓
CTA / "Get started"
```

Best for: SaaS products, developer tools, apps with a learning curve.

### Documentation Page

For reference material, guides, and technical content.

```
Header
   ↓
Sidebar Navigation (Tablet/Desktop)
   ↓
Article / "The content"
   ↓
Related / "See also"
   ↓
Footer
```

Best for: API docs, user manuals, knowledge bases.

### Utility App Page

For tools that perform a single function (scanner, calculator, terminal).

```
Navigation (minimal)
   ↓
Primary Action / "Do the thing"
   ↓
Results / "Here's what happened"
   ↓
History / "Previous results"
   ↓
Footer
```

Best for: proof-of-existence tools, file scanners, receipt generators, verification apps.

### Choosing an Archetype

- If the page doesn't fit any archetype, pick the closest one and adjust — don't invent a new skeleton.
- Each archetype is opinionated. The archetype is the constraint that prevents layout sprawl.
- The archetype is chosen before any content is written. Content is shaped to fit the skeleton, not the other way around.

---

## 11. Desktop Layout

Desktop should feel **cinematic**. Avoid grids everywhere.

### The Narrative Flow

```
Hero
   ↓
Story / "What is it?"
   ↓
Feature / "Why should I care?"
   ↓
Story / "How does it work?"
   ↓
Feature / "What makes it different?"
   ↓
Trust / "Can I trust it?"
   ↓
Conclusion / "Take action"
```

Like reading a magazine. Each section is a spread. The page has a rhythm. Not a grid.

### Vertical Sequence

- Each section occupies the full viewport width (with horizontal margins).
- Content flows top to bottom.
- Nothing sits side-by-side unless it is a deliberate feature comparison or gallery.
- Asymmetry is intentional. Offset elements to avoid monotony.

---

## 12. Tablet Layout

### Tablet is compressed desktop. Not mobile.

| Rule | Detail |
|---|---|
| Hierarchy | Same as desktop |
| Spacing | Same as desktop |
| Columns | Fewer (collapse 3-col → 2-col, 2-col → 1-col) |
| Design | Never redesign. Only compress. |

Tablet should feel like the same page on a smaller screen. Not a different page. The vertical rhythm, section order, and narrative structure stay identical. Only the column count changes.

---

## 13. Mobile Layout

### Mobile should feel intentional. Not "desktop stacked."

| Rule | Detail |
|---|---|
| Columns | Everything becomes one column |
| Spacing | Generous spacing stays (do not collapse to zero) |
| Typography | Scales down proportionally but nothing becomes tiny |
| Touch targets | ≥ 44px minimum |

- If a section has three columns on desktop, it stacks vertically on mobile. Each item gets its own row.
- Horizontal margins drop to 20–24px but never to 0px.
- Line lengths naturally become shorter — this is fine.
- The narrative is the same. Only the proportions change.

---

## 14. Responsive Hierarchy, Breakpoints & Column Rules

The architecture stays identical. Only proportions change.

| Breakpoint | Viewport | Grid Columns |
|---|---|---|
| Desktop | 1280px+ | 12 |
| Tablet | 768–1279px | 8 |
| Mobile | 375–767px | 4 |

### Strict Column Rules

| Viewport | Columns | Rule |
|---|---|---|
| Desktop | 4 columns | Four-column feature grids, 3-col + 9-col asymmetrical splits |
| Tablet | 2 columns | Collapse 4-col → 2-col, 3-col layouts → 2-col + 1-col stacks |
| Mobile | 1 column | Everything single column. No exceptions. |

**No exceptions.** On mobile, every layout collapses to a single vertical stack. If a layout breaks at single column, the desktop layout was wrong.

### Translation Rules

1. **Desktop → Tablet**: Compress horizontal spacing. Reduce column grid from 12 → 8. Same typography scale.
2. **Tablet → Mobile**: Single column. 4-column grid. Scale type down proportionally. Maintain generous vertical rhythm.
3. **Mobile → Tablet**: Do not "upgrade" — more space means more breathing room, not more content.

Never create a separate mobile layout. You have one layout. It responds.

---

## 15. Performance Architecture

Architecture includes perceived speed. A page can look right but feel wrong if it loads slowly. Performance is an architectural constraint, not a polish step.

### Hard Rules

| Rule | Reason |
|---|---|
| Motion should never delay interaction | Users perceive delay as broken |
| First meaningful content appears immediately | Show *something* within first network round-trip |
| Above-the-fold assets have priority | Don't load footer images before hero text |
| Reserve image dimensions | Prevent cumulative layout shift (CLS) |
| Lazy-load below-the-fold media | Don't pay for what isn't seen |
| Never block scrolling with decorative effects | Parallax, heavy animations, or JS-dependent reveals must degrade gracefully |
| Avoid layout shifts | No element should move after it's painted |
| `font-display: swap` | Text is readable immediately with fallback, then swaps |

### Perceived Performance

- The hero text and primary CTA render on first paint. Everything else can follow.
- Skeleton states are structural outlines (spacing blocks without content), not shimmer animations.
- Navigation is interactive within 1 second on 3G.
- If a section uses imagery, the text loads first and the image loads after. The section is readable without images.

### Architectural Implications

- Choose content order so the most important information is first in the DOM, not first in the visual layout.
- Component structure should allow server-side rendering of above-the-fold content.
- Third-party scripts (analytics, embeds, widgets) load after first paint and never block rendering.
- Font loading uses `font-display: swap` — text is immediately readable with the fallback font, then swaps when the custom font loads. No invisible text.

---

## 16. Accessibility Architecture

Not WCAG checklists. **Architectural accessibility** — structure that is inherently inclusive regardless of styling. Like performance, this is an architectural constraint, not an afterthought.

### Structural Rules

| Rule | Rationale |
|---|---|
| Never rely on hover alone for any interaction | Touch and keyboard users never produce hover |
| Every action is reachable with keyboard | Tab order must match visual order |
| Minimum 44×44px touch targets | The standard for all touch interfaces |
| Reading order matches visual order | Screen readers follow DOM order, not CSS order |
| One `<h1>` per page | Establishes a single, unambiguous page identity |
| Landmarks are consistent across pages | `<nav>`, `<main>`, `<footer>` in the same locations |
| `prefers-reduced-motion` respected | Users with vestibular disorders should not be disoriented by motion |
| Focus indicators are visible | Never `outline: none` without a replacement |

### Architectural Implications

- The page must make sense when linearised. If content relies on side-by-side positioning for comprehension, it must also work in a single column.
- Interactive elements have visible labels, not icon-only unless accompanied by an `aria-label`.
- Form inputs are associated with `<label>` elements, not placeholder-only.
- The content hierarchy (h1 → h2 → h3) matches the visual hierarchy. Never skip levels for visual effect.
- Every landmark region (`<nav>`, `<main>`, `<footer>`) appears in the same position on every page. Users who navigate by landmarks should never have to hunt.

---

## 17. Information Priority System

Before any content is designed, classify it. Every piece of information on a page belongs to exactly one priority level. The level determines its visual weight, placement, and whether it appears at all.

### Priority Levels

| Level | Purpose | Visual Treatment |
|---|---|---|
| **Primary** | Why the user came | Hero-size type, dominant visual anchor, highest contrast |
| **Secondary** | Supports the primary decision | Body type, secondary position, readable but quiet |
| **Tertiary** | Nice to know, optional detail | Small type, muted colour, below the fold |
| **Hidden** | Only shown on demand | Behind a toggle, tooltip, or expandable section |

### Rules

**Never display tertiary information at the same visual weight as primary information.** That single rule eliminates most clutter.

- Every element on the page is tagged with its priority level before layout begins.
- Primary content determines the page's layout and spacing. Everything else works around it.
- Secondary content never interrupts the primary narrative. It sits beside or below, never inside.
- Tertiary content is never in the hero, never in a CTA, and never in the first viewport.
- Hidden content is not visible by default. It is revealed only when the user asks for it.

### Priority Audit

Walk through the page and ask of every element:

> *"If I removed this, would the user still complete their primary goal?"*

- If yes and the user would not notice: it is hidden-level or should be removed.
- If yes but the user might want it: it is tertiary.
- If no but the goal is still clear without it: it is secondary.
- If no and the page stops making sense: it is primary.

---

## 18. Decision Hierarchy

Architecture isn't only physical. It is **cognitive**.

Every screen should answer: *What decision is the user making right now?* If the answer isn't obvious, the architecture has failed.

### Examples

| App | Decision Sequence |
|---|---|
| OpenLedger | Import? → Review? → Accept? |
| OpenProof | Verify? → Result? |
| OpenSend | Send? → Track? → Done? |
| Block / Cash App | Send? → Confirm? → Done? |

Each screen has exactly **one decision**. The user arrives, decides, and moves to the next screen.

### Cognitive Architecture Rules

- Every screen is named after the decision it hosts, not the content it displays. ("Confirm Send" not "Send Details Page.")
- If a screen requires more than one decision, split it.
- If a screen requires no decision, ask why the screen exists.
- The decision should be reachable within one visual scan. The user should not need to read supporting content to understand what they're being asked.
- Supporting information (fees, terms, metadata) is secondary or tertiary — never primary. It supports the decision without competing with it.
- The primary action on the screen is the decision's resolution. Every other element points toward it.

### Decision Mapping

Before building any screen, document:

```
Screen name: [What decision?]
User arrives to: [Context — what just happened?]
User decides: [The choice]
User leaves to: [What happens next?]
```

If you can't fill all four fields, the screen isn't architecturally resolved.

---

## 19. Progressive Disclosure

Calm interfaces show the minimum. Progressive disclosure is how.

Show **basic → advanced → developer** — not everything immediately. This is a core reason Block products feel calm: they never overwhelm you with controls you don't need.

### Disclosure Layers

```
Layer 1: Basic
   ↓
Layer 2: Advanced
   ↓
Layer 3: Developer
```

#### Layer 1 — Basic

Shown by default. Contains only what the user needs for the primary decision.

- One CTA. One input if necessary. No settings.
- The page is complete and usable at this layer. A user who never clicks "Advanced" should have a fully functional experience.

#### Layer 2 — Advanced

Revealed on explicit user action (toggle, "Show more," settings icon).

- Additional controls, optional fields, configuration options.
- Never required for the primary flow.
- Grouped logically — one toggle expands one group, not everything.

#### Layer 3 — Developer

Deep customization. API keys, raw data, debug views, experimental features.

- Behind a deliberate gate (settings page, developer mode toggle, URL parameter).
- Not accessible by accident. The user must know it exists to find it.

### Rules

- Never show advanced controls before basic controls.
- Never show expert settings by default.
- Every revealed layer must make the previous layer simpler, not redundant. If revealing advanced doesn't simplify basic, the hierarchy is wrong.
- Hidden controls must be semantically grouped. One "Advanced" expand-all is better than ten scattered "Show more" links.
- The default view must be self-sufficient. A user who never explores layers gets the full experience.

---

## 20. Design Debt

Every feature added to a product risks introducing design debt — patterns that don't fit, one-off components, visual entropy. Over years, this erodes any design system.

### The Feature Gate

Before adding any new feature, satisfy every question below:

| Question | If yes |
|---|---|
| Does it introduce a new visual pattern? | Redesign to use an existing pattern. |
| Could an existing pattern solve it? | Use the existing pattern. No new code. |
| Is this becoming a one-off component? | Generalise it or cut it. |
| Does it increase cognitive load? | Redesign until it doesn't. |

If any answer is yes without a resolution, the feature does not ship in its current form.

### Debt Prevention Rules

- Every reusable pattern (button, card, input, section layout) must be used at least twice before it is extracted into a shared component. Premature abstraction creates debt as often as no abstraction.
- Visual debt is measured: if the page were screenshotted every month, would the design language drift be visible? If yes, stop and consolidate.
- A new layout archetype (beyond the four in [Layout Patterns](#10-layout-patterns)) requires explicit architectural review. No new skeletons without justification.
- Every six months, run the full [Agent Checklist](#30-agent-checklist) against every page. Architecture drift is invisible month-to-month but obvious across quarters.

### Entropy Prevention

- When adding to an existing page, the new content must use the same container, spacing scale, and grid as the existing sections above it.
- If the existing page doesn't have a consistent container or spacing, fix the page before adding to it.
- One-off visual styles (custom border radii, unique colour treatments, bespoke hover effects) are prohibited unless they serve the primary decision on that screen.

---

## 21. Typography Hierarchy

### Only six sizes.

| Role | Size |
|---|---|
| Hero | 64–96px |
| Section title | 40–48px |
| Subheading | 28–32px |
| Body | 18px |
| Supporting | 16px |
| Meta | 12–14px |

**Never** invent random sizes. Every size on the page must belong to this scale. If you need a seventh size, question the content structure before the scale.

### Line Length

Ideal reading: **55–75 characters maximum**.

If your eyes have to move too far to read the next word, the line is too long.

- Hero text: shorter (30–50 chars) for impact.
- Body text: max 75 chars.
- Feature descriptions: max 60 chars.

---

## 22. Section Philosophy & Screen Occupancy

### Every section answers ONE question.

```
Hero         → What is this?
↓
Section 1    → What is it?
↓
Section 2    → Why should I care?
↓
Section 3    → How does it work?
↓
Section 4    → What makes it different?
↓
Section 5    → Can I trust it?
↓
Conclusion   → Take action.
```

Not 15 mixed sections. A page is a conversation, not a catalog.

### Rules

- If a section answers two questions, split it.
- If a section answers no question, remove it.
- Each section has exactly one headline that summarises its question.
- The section body answers that question. Nothing else.
- The user should be able to scan section headlines and understand the entire argument.

### Screen Occupancy

One viewport = one dominant message. Maximum two supporting ideas.

Not:

```
Headline
subtitle
4 buttons
stats
cards
video
logos
quotes
animations
```

That is not a page. That is noise.

Instead:

```
One viewport
   ↓
One dominant message
   ↓
Maximum two supporting ideas
```

Every viewport should be readable as a single, coherent slide. If the user screenshots any viewport, they should be able to extract one clear takeaway.

---

## 23. Reading Tempo

One of the reasons Block feels premium: scrolling has rhythm.

Not scroll-scroll-scroll-scroll. But:

```
Pause  →  Reveal  →  Read  →  Continue
Pause  →  Reveal  →  Read  →  Continue
```

Each viewport behaves like a slide in a presentation.

### How to design for tempo

- **Pause**: The previous section is still legible as the user lands. No immediate animation. A beat of silence.
- **Reveal**: The next idea enters — through scroll position, a subtle fade, or simply being in view.
- **Read**: The user absorbs the content. No competing animations. No secondary reveals. The content is still.
- **Continue**: A visual cue (end of section, next headline peeking) invites scrolling.

### Rules

- Every section follows this rhythm. No skipping.
- Never reveal more than one idea per scroll step.
- Animations should complete within the first 300ms of entering viewport. Content should be readable for the remaining time.
- If a section has multiple pieces of content (headline, visual, data), sequence them — don't reveal them all at once.

---

## 24. Visual Density & Alignment

### Visual Density

Every screen should have **one dominant thing**. Not five.

Ask: *"What do I notice first?"*

If the answer is *"everything"*, the page has failed.

- One visual anchor per viewport.
- Everything else quietly supports it.
- On scroll, the anchor transitions to the next anchor.

### Alignment

Everything aligns to the [Alignment Grid](#5-alignment-grid). Nothing floats. Nothing is "close enough."

- Edges line up with column boundaries.
- Text widths repeat across sections.
- Margins repeat across sections.
- No element is positioned without reference to a column.

**Humans subconsciously notice consistency.** Misaligned elements destroy trust faster than any typography mistake.

---

## 25. Motion & Scroll Rhythm

### Motion

Motion should explain. Not entertain.

**Allowed:**
- Fade
- Slight translate
- Opacity
- Scale 1.00 → 1.02

**Avoid:**
- Bouncing
- Spinning
- Elastic
- Excessive easing

Block uses motion as communication. Never decoration.

### Motion Performance

- Motion should never delay interaction.
- All animations use `will-change: transform, opacity` — never layout-triggering properties.
- `prefers-reduced-motion` disables all animations, not just decorative ones.
- Scroll-triggered reveals use IntersectionObserver, not scroll event listeners.

### Scroll Rhythm

Every viewport should introduce **one new idea** (see [Reading Tempo](#23-reading-tempo)). Not three.

- Good scrolling feels like turning pages.
- The user should never feel disoriented after scrolling.
- Each scroll reveal reinforces the narrative, not distracts from it.
- Scroll-triggered animations should be subtle enough that if they failed, the page still reads correctly.

---

## 26. Browser Fit & Testing

The website should never look "zoomed." It should naturally fit.

| Condition | Rule |
|---|---|
| Desktop | Never taller than needed |
| Mobile | No horizontal scrolling |
| Tablet | Identical hierarchy |

### Test at these viewports

```
375
390
430
768
1024
1280
1440
1728
1920
```

If it works there, it works almost everywhere.

---

## 27. Platform Translation

The architecture is already designed to feel native everywhere. This chapter defines exactly what changes and what stays the same across platforms.

### The Translation Chain

```
Desktop Website
   ↓
Tablet Website
   ↓
Mobile Website
   ↓
Windows
   ↓
macOS
   ↓
Android
   ↓
iOS
   ↓
PWA
```

### Never Changes

These are **architectural invariants**. They are the same on every platform:

- Content hierarchy and section order
- Spacing ratios (the spatial system scale stays, values may scale to platform density)
- Typography scale (six canonical sizes)
- Information order (what the user reads first, second, third)
- Narrative flow (pause → reveal → read → continue)
- The one-question-per-section rule
- The dominant visual anchor per viewport

### May Change

These are **platform adaptations** — the chrome around the architecture:

- Navigation location (top on web/macOS, bottom on iOS/Android, sidebar on desktop apps)
- Safe area insets (notch, status bar, system gesture areas)
- Title bar (custom on web, native on desktop apps)
- Gestures (scroll on web, swipe on mobile, click on desktop)
- Native controls (system fonts, form controls, scrollbar styling)
- Window chrome (title bar, close/minimize, menu bar)

### Translation Rules

- The same HTML/CSS layout should require only platform chrome changes, not structural rearrangement.
- If a page needs to be redesigned for any platform, the web architecture was wrong.
- Test each platform transition: does the user read the same story in the same order?
- On every platform, the primary action should be reachable within one gesture from the home state.

---

## 28. The Block / Cash App Principle

The biggest lesson from Cash App and Block isn't typography. It's **restraint**.

They constantly ask:

> *"Can we remove this?"* — not *"What else can we add?"*

### Principles

- Every element must justify its existence.
- Whitespace carries as much meaning as content.
- Interfaces feel premium because nothing competes for attention.
- One message. One action. One visual anchor.
- Everything else quietly supports it.

### The Audit Question

Before shipping any page, ask:

> *"If I removed half the elements, would the page still communicate its purpose?"*

If the answer is yes, you have too many elements. Remove them.

---

## 29. The Museum Test

> **If every section were printed on separate posters and hung in a museum, visitors should understand the story simply by walking from one to the next.**

This single sentence captures almost everything this playbook tries to achieve.

A page passes the Museum Test when:

- Each section is self-contained and makes sense on its own.
- Sections read sequentially — the order is meaningful, not arbitrary.
- The story is communicated by the sequence alone, without navigation bars, CTAs, or interactive elements.
- A visitor scanning the page (not reading, scanning) can reconstruct the full argument.
- Each poster has one message, one visual anchor, and enough white space to breathe.

If your page doesn't pass the Museum Test, it hasn't been architecturally resolved yet. Keep simplifying until it does.

---

## 30. Agent Checklist

Before declaring an architecture pass complete, verify every item below.

### Structure

- [ ] The page follows one of the approved [Layout Patterns](#10-layout-patterns).
- [ ] The page answers exactly one question per section.
- [ ] No section answers more than one question.
- [ ] The narrative flows logically: introduction → explanation → differentiation → trust → action.
- [ ] Scrolling through the page tells a coherent story.
- [ ] The page passes [The Museum Test](#29-the-museum-test).

### Spatial System

- [ ] Every gap on the page matches the spacing scale (16, 32, 56, 120, 180, or 240px).
- [ ] No arbitrary intermediate spacing values are used.
- [ ] Every section uses one of the fixed containers (Reading, Content, Feature, Wide, Fluid).
- [ ] No content exceeds its container boundary.

### Alignment

- [ ] The page uses the correct grid (12-col desktop, 8-col tablet, 4-col mobile).
- [ ] Every element spans a whole number of columns.
- [ ] No element is off-grid.

### Widths

- [ ] Hero text uses the Reading or Content container (700–900px).
- [ ] Body/reading text uses the Reading container (600–720px max).
- [ ] No prose block exceeds 75 characters line length.
- [ ] Full-width elements (Fluid container) are only used for imagery, timelines, separators, galleries, or maps.

### Hierarchy & Density

- [ ] Visual weight is distributed ~60% primary, ~25% supporting, ~15% whitespace emphasis.
- [ ] Every viewport has exactly one dominant visual anchor.
- [ ] No screen has competing focal points.
- [ ] Navigation has 4–5 items maximum.
- [ ] The hero contains only: headline, one supporting sentence, one CTA (optional secondary).
- [ ] The footer is minimal: brand line, links, copyright.

### Information Priority

- [ ] Every element on the page is classified as Primary, Secondary, Tertiary, or Hidden.
- [ ] No tertiary information appears at primary visual weight.
- [ ] No tertiary information appears in the hero or first viewport.
- [ ] Hidden content is never visible by default.

### Decision Hierarchy

- [ ] Every screen has exactly one decision documented.
- [ ] The screen name describes the decision, not the content.
- [ ] No screen requires more than one decision.
- [ ] The primary action is the decision's resolution.
- [ ] Screen is documented: name, context, decision, next state.

### Progressive Disclosure

- [ ] The default view is self-sufficient (no required interaction to use the page).
- [ ] Advanced controls are behind an explicit toggle.
- [ ] Developer/experimental features are gated.
- [ ] Revealed layers are grouped, not scattered.

### Design Debt

- [ ] No new visual patterns introduced without checking existing ones first.
- [ ] No one-off components — every component is either generalised or cut.
- [ ] The feature gate questions have been answered: pattern reuse, cognitive load, one-off risk.

### Responsive

- [ ] Desktop uses 4 columns / 12-col grid.
- [ ] Tablet is compressed to 2 columns / 8-col grid — same hierarchy, same spacing.
- [ ] Mobile is 1 column / 4-col grid with generous spacing — no exceptions.
- [ ] Typography scales proportionally — nothing becomes tiny.
- [ ] No horizontal scrolling at any viewport.
- [ ] Touch targets are ≥ 44px.
- [ ] Verified at: 375, 390, 430, 768, 1024, 1280, 1440, 1728, 1920.

### Performance Architecture

- [ ] Above-the-fold content renders on first paint.
- [ ] Image dimensions are reserved (no CLS).
- [ ] Below-the-fold media is lazy-loaded.
- [ ] Third-party scripts load after first paint.
- [ ] No layout-shifting elements.
- [ ] `font-display: swap` is set — no invisible text during font load.
- [ ] Navigation is interactive within 1s on 3G.

### Accessibility Architecture

- [ ] No interaction relies on hover alone.
- [ ] Every action is reachable by keyboard.
- [ ] Touch targets are ≥ 44×44px.
- [ ] Reading order (DOM) matches visual order.
- [ ] Exactly one `<h1>` per page.
- [ ] Landmarks (`<nav>`, `<main>`, `<footer>`) are consistent.
- [ ] Focus indicators are visible.
- [ ] `prefers-reduced-motion` is respected.
- [ ] Page makes sense when linearised (single column).

### Reading Tempo

- [ ] Each section follows pause → reveal → read → continue.
- [ ] No more than one idea revealed per scroll step.
- [ ] No competing animations during the "read" phase.

### Motion

- [ ] Motion explains content transitions (fade, translate, opacity, subtle scale).
- [ ] No decorative or entertaining animations (bounce, spin, elastic, excessive easing).
- [ ] If animations failed, the page is still fully readable.
- [ ] `prefers-reduced-motion` disables all animations.
- [ ] Motion never delays interaction.

### Platform Translation

- [ ] No browser-specific UI patterns.
- [ ] No oversized nav bars or footers.
- [ ] Content hierarchy would survive being rendered on Windows, macOS, Android, iOS, iPad, and PWA.
- [ ] Only platform chrome would change — the architecture is invariant.

### Restraint Audit

- [ ] Every element justifies its existence.
- [ ] "Can we remove this?" has been asked for every element.
- [ ] Removing any element would make the page less clear.
- [ ] The page has one message, one primary action, one visual anchor.
- [ ] Everything else quietly supports it.

---

*This playbook establishes the structural canvas. Apply the [Design Playbook](./DESIGN_PLAYBOOK.md) for visual components, colors, typography, and brand identity within this architecture.*
