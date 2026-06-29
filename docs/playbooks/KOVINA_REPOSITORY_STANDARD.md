# Kovina Repository Standard

> A specification for every Kovina repository. Treats GitHub as a software showroom, not a development wiki.

---

## Philosophy

Every Kovina repository should feel like a premium product landing page. The primary audience is:

- **End users** — people discovering the software, deciding whether to download
- **Recruiters** — evaluating the quality and polish of the work
- **Designers** — examining visual and interaction patterns
- **Discoverers** — visitors who landed from search, social, or word of mouth

The repository should encourage **downloading or using the product**, not cloning the repository.

---

## Repository Structure

```
.
├── assets/
│   ├── hero/              # Large hero screenshot(s) — product in action
│   ├── screenshots/       # Feature, workflow, and UI screenshots
│   ├── gallery/           # Curated screenshot gallery (larger, fewer images)
│   ├── icons/             # SVG icons for features, tech, branding
│   └── branding/          # App icon (various sizes), logos, store assets
├── docs/
│   ├── Architecture.md    # System architecture and design decisions
│   ├── Development.md     # Build, run, and development setup
│   ├── Deployment.md      # Release workflow, CI/CD, distribution
│   ├── Testing.md         # Test suite, coverage, quality gates
│   ├── Contributing.md    # Contributor guide, code of conduct
│   └── playbooks/         # Product, design, and architecture playbooks
├── .github/               # CI workflows, issue templates, Dependabot
├── CHANGELOG.md           # Keep a Changelog format
├── CONTRIBUTING.md        # GitHub-discovered contributor guide (root redirect)
├── LICENSE                # AGPLv3 or permissive
├── SECURITY.md            # Security policy (GitHub-discovered)
└── README.md              # Product showcase (see section order below)
```

### Root file cleanup

Only these files live at root:

| File | Purpose |
|------|---------|
| `README.md` | Product showcase landing page |
| `CHANGELOG.md` | Release history |
| `LICENSE` | Software license |
| `CONTRIBUTING.md` | GitHub-discovered contributor guide (keep minimal, point to `docs/`) |
| `SECURITY.md` | GitHub-discovered security policy |
| `CODE_OF_CONDUCT.md` | GitHub-discovered code of conduct |
| `.env.example` | Environment template (if applicable) |
| `.gitignore` | Standard exclusions |

Everything else goes into `docs/` or `assets/`.

---

## README Section Order

Every Kovina README follows this exact 11-section order:

1. **Hero** — Logo, app name, one-line value proposition, large hero screenshot
2. **Primary Call-to-Action** — Download/install buttons (Store first, then Release, then Source)
3. **Gallery** — Large screenshots of the product in use (dark/light, desktop/mobile)
4. **Why This App** — Short, user-focused value propositions, no marketing fluff
5. **Features** — Clean two-column grid with Kovina SVG icons, short descriptions
6. **Designed For** — Typical users and use cases
7. **Design Philosophy** — Short quote + one concise paragraph on design approach
8. **Built With** — Technology icons/logos, clean and scannable
9. **Version Journey** — Timeline of important releases, link to changelog
10. **License**
11. **Part of the Open Collection** — All Open* apps with icons, descriptions, and links

---

## README Rules

- **Optimize for the first 30 seconds.** A visitor should understand what the product is, why it's useful, what it looks like, and where to download it within 30 seconds.
- **Large typography.** Headings should be prominent.
- **Large screenshots.** Show the product in action at readable sizes (min 720px wide).
- **Minimal text.** Prefer short phrases over paragraphs.
- **Strong visual hierarchy.** Section headings, spacing, and layout guide the eye.
- **Whitespace over density.** Let the content breathe.
- **No developer documentation.** Everything build/install/test/contribute related goes in `docs/`.
- **Primary CTA is always download/use.** The Microsoft Store, Google Play, or Release asset is the first action.

### Badge style

CTA badges use `style=for-the-badge` (large, prominent). Secondary badges (version, license, platform) use `style=flat-square` (subtle, informational).

---

## Open Collection Section

The final section of every README displays all Open\* applications with:

- App icon (32px, from `assets/icons/` or external URL)
- App name (bold)
- One-line description
- Repository link
- Website link (where available)

Order alphabetically by name. Use a table or list format.

```markdown
## Part of the Open Collection

Open\* is a family of privacy-first, open-source applications.
Every app is local-first, respects your data, and is built with care.

| | App | Description | Links |
|---|---|---|---|
| ![icon](assets/icons/openreader.svg) | **OpenReader** | Private PDF tools for your computer | [Repo](…) · [Web](…) |
| … | … | … | … |
```

---

## Asset Organization

### `assets/hero/`
- One or two hero images showing the product in its primary use case
- 880px+ wide, landscape orientation
- Used only in the Hero section

### `assets/screenshots/`
- Feature screenshots, workflow steps, UI components
- 600-880px wide
- Referenced throughout the README

### `assets/gallery/`
- Curated, large gallery images
- Fewer images, higher quality
- Used in the Gallery section

### `assets/icons/`
- SVG icons for features, technologies, and branding
- Kovina-style: 48×48 viewBox, 1.5px stroke, `stroke="currentColor"` or accent color
- Each icon is a standalone `.svg` file

### `assets/branding/`
- App icon in all required sizes (`.ico`, `.icns`, `.iconset/`, PNG)
- Store submission images (44×44, 71×71, 150×150, 310×150, 620×300)
- Logo SVG/PNG
- Store badges and marketing assets

---

## Kovina SVG Icon Guidelines

Icons follow a consistent visual language:

- **ViewBox:** `0 0 24 24`
- **Stroke width:** `1.5`
- **Stroke style:** `stroke-linecap="round" stroke-linejoin="round"`
- **Fill:** `none`
- **Color:** `currentColor` or brand accent (default: `#ff255F`)
- **Size:** 48×48 display, 52×52 for feature cards

Store icons in `assets/icons/` as individual `.svg` files prefixed by their feature area.

---

## Quality Checklist

Before finalising any repository:

- [ ] README reads like a software landing page, not a developer README
- [ ] Primary CTA is downloading or using the product
- [ ] Product, value, and next action are clear within 30 seconds
- [ ] Screenshots are high quality, current, and render correctly on GitHub
- [ ] All download links (Store, Release, website) work
- [ ] Open Collection section is accurate and up to date
- [ ] Developer documentation is moved to `docs/` and not in root
- [ ] Repository assets follow the standard structure
- [ ] Markdown renders correctly on GitHub desktop and mobile
- [ ] No stale or broken asset references
- [ ] License and copyright are current
