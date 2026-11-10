---
name: Architectural Focus
colors:
  surface: '#fbf9f8'
  surface-dim: '#dbdad9'
  surface-bright: '#fbf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f3'
  surface-container: '#efeded'
  surface-container-high: '#eae8e7'
  surface-container-highest: '#e4e2e2'
  on-surface: '#1b1c1c'
  on-surface-variant: '#404942'
  inverse-surface: '#303030'
  inverse-on-surface: '#f2f0f0'
  outline: '#707972'
  outline-variant: '#bfc9c0'
  surface-tint: '#236a49'
  primary: '#005234'
  on-primary: '#ffffff'
  primary-container: '#246b4a'
  on-primary-container: '#a1e9bf'
  inverse-primary: '#8fd6ad'
  secondary: '#5f5e5e'
  on-secondary: '#ffffff'
  secondary-container: '#e5e2e1'
  on-secondary-container: '#656464'
  tertiary: '#583878'
  on-tertiary: '#ffffff'
  tertiary-container: '#715091'
  on-tertiary-container: '#eacfff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#aaf2c8'
  primary-fixed-dim: '#8fd6ad'
  on-primary-fixed: '#002112'
  on-primary-fixed-variant: '#005233'
  secondary-fixed: '#e5e2e1'
  secondary-fixed-dim: '#c8c6c5'
  on-secondary-fixed: '#1c1b1b'
  on-secondary-fixed-variant: '#474646'
  tertiary-fixed: '#f0dbff'
  tertiary-fixed-dim: '#ddb7ff'
  on-tertiary-fixed: '#2a0749'
  on-tertiary-fixed-variant: '#583877'
  background: '#fbf9f8'
  on-background: '#1b1c1c'
  surface-variant: '#e4e2e2'
typography:
  display-hero:
    fontFamily: Newsreader
    fontSize: 80px
    fontWeight: '400'
    lineHeight: 88px
    letterSpacing: -0.03em
  display-hero-mobile:
    fontFamily: Newsreader
    fontSize: 44px
    fontWeight: '400'
    lineHeight: 52px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Newsreader
    fontSize: 36px
    fontWeight: '400'
    lineHeight: 44px
    letterSpacing: -0.025em
  headline-lg-mobile:
    fontFamily: Newsreader
    fontSize: 28px
    fontWeight: '400'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Newsreader
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-sm:
    fontFamily: Newsreader
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 28px
    letterSpacing: -0.015em
  title-md:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: -0.01em
  body-md:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: -0.005em
  body-sm:
    fontFamily: Geist
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  label-md:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Geist
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.04em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-sm: 1rem
  gutter-lg: 2.5rem
  margin: 2rem
  margin-sm: 1rem
  margin-lg: 4rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
  space-2xl: 4rem
---

## Brand & Style

This design system embodies high-end architectural editorial elegance merged with the ruthless clarity of Swiss modernism. Built for intellectual rigor, research, and uninterrupted deep work, the aesthetic treats digital workspace as an archival reading room or a gallery catalog: quiet, deliberate, and structurally uncompromising.

The visual style synthesizes minimalist restraint and editorial prestige:
- **Atmospheric Quietude:** Interfaces prioritize negative space, low visual noise, and razor-sharp typographic alignment over decoration.
- **Structural Legibility:** Forms and containers draw inspiration from spatial blueprints, employing crisp structural boundaries and strict proportional divisions.
- **Intentional Contrast:** Interaction points and textual anchors command attention through pristine hierarchy, contrasting a warm, paper-inspired neutral field against dense obsidian ink and disciplined botanical accents.

## Colors

The palette is rooted in a disciplined monochrome spectrum, accentuated by a deep forest green seed that provides organic authority without decorative distraction.

### Foundation & Surfaces
- **Canvas Base:** `#FAFAFA` provides a warm, archival paper foundation that prevents the retinal fatigue of uncalibrated digital white.
- **Surface Pure:** `#FFFFFF` is used strictly for nested panels, cards, and reading layers requiring deliberate separation.
- **Surface Recessed:** `#F1F1F1` denotes subtle backdrops, interactive hovering states, and utility drawers.
- **Structural Outlines:** `#DCDCDC` defines hair-thin structural divisions, grid rulers, and cell bounds.

### Ink & Semantics
- **Text Primary (Obsidian):** `#111111` ensures authoritative, uncompromised contrast for display headlines and active body prose.
- **Text Muted (Granite):** `#555555` controls auxiliary metadata, references, captions, and secondary actions.
- **Primary Accent (Forest Green):** `#246B4A` signals completion, state continuity, success, and positive progression.
- **Intelligence Accent (Muted Royal):** `#6D4C8D` identifies synthetic generation, deep analysis, and automated workflows.
- **Alert Semantics:** Warm Amber (`#A85B18`) delivers cautionary notices; Deep Crimson (`#B42318`) reserves urgency for irreversible mutations and errors; Slate Blue (`#315F83`) serves contextual telemetry.

## Typography

The typographic hierarchy juxtaposes the cerebral, literary presence of `Newsreader` with the neutral, engineered utility of `Geist`.

- **Headlines & Editorial Statements:** Set in `Newsreader` with tightened letterforms (`-0.015em` to `-0.03em`). This establishes an intentional intellectual tempo, transforming workspace headers and section overviews into authoritative narrative milestones.
- **Work Surface & Data Streams:** Set in `Geist`. The geometry provides absolute vertical and tabular precision for reading, writing, telemetry, and input orchestration.
- **Labels & Micro-indicators:** `Geist` at 11–12px with extended tracking (`0.02em` to `0.04em`), rendered uppercase or medium weight, emulating the subtle registration marks found in architectural draughting and fine print editions.

## Layout & Spacing

The layout is built upon an architectural 12-column editorial grid characterized by asymmetry and structured margins.

- **Asymmetric Proportions:** Avoid symmetric 6/6 desktop splits. Favor intellectual cadence using 8/4 splits (primary workspace and contextual reference) or 7/5 splits (reading pane and synthesis index).
- **Hairline Axis Alignment:** Grid columns may be bounded by solid 1px `#DCDCDC` vertical and horizontal boundaries, producing an explicit framework that confines data density without heavy fills.
- **Responsive Adaptations:**
  - **Desktop (1280px+):** Full 12-column system, `margin-lg` (4rem) canvas padding, `gutter-lg` (2.5rem). Multi-column reading and action bands remain visible simultaneously.
  - **Tablet (768px – 1279px):** 8-column layout with `gutter` (1.5rem) and `margin` (2rem). Secondary columns tuck into collapsible drawers or stacked modular bands.
  - **Mobile (<768px):** 4-column flow with `margin-sm` (1rem) and `gutter-sm` (1rem). Workspaces flatten into linear vertical sequences, anchoring critical controls to bottom toolbars.

## Elevation & Depth

Visual hierarchy rejects blurry volumetric drop-shadows and frosted glass effects in favor of structural clarity, high-contrast separation, and planar layering.

- **Hairline Framing:** Depth is achieved primarily through crisp 1px borders (`#DCDCDC`) against `#FAFAFA` and `#FFFFFF`. This creates a tactile, sheet-like presentation without blurring spatial boundaries.
- **Planar Stacking:** Overlays, floating utility palettes, and modal panes use solid `#FFFFFF` backgrounds bound by a firm 1px `#111111` or `#DCDCDC` stroke.
- **Shadow Profiles:** When physical elevation is mandatory (e.g., floating command bars, drag-and-drop elements), use an ultra-crisp, short-radius shadow: `0 2px 4px rgba(17, 17, 17, 0.04), 0 8px 16px rgba(17, 17, 17, 0.06)`. Diffuse ambient blurs are prohibited.
- **Surface Stepping:** Contextual distinction follows three architectural elevations: Ground (`#FAFAFA`), Tier 1 Deck (`#FFFFFF` with `#DCDCDC` perimeter), and Tier 2 Active Slot (`#F1F1F1` recessed inlay).

## Shapes

The geometry follows a strict dual-geometry paradigm:

- **Structural Framing (0.25rem / 4px):** Panels, cards, input surfaces, dialogue modules, and segmented viewports adopt a minimal `0.25rem` radius (roundedness: 1). This softens corner stress while maintaining the severe rectilinear integrity of an architectural sheet.
- **Interactive Capsules (Pill / 9999px):** Fully rounded pill geometry is strictly reserved for primary operational triggers, contextual action badges, and dynamic status tags. It signals an interactive mechanism within the rigid rectilinear frame.

## Components

### Buttons
- **Primary Action:** Solid obsidian `#111111` capsule (`border-radius: 9999px`) with `#FFFFFF` text in `Geist` 14px medium. Hover transitions to `#246B4A` smoothly (150ms). Focus rings use a 2px offset hairline ring.
- **Secondary Action:** `#FFFFFF` capsule with a 1px `#DCDCDC` hairline border and `#111111` text. Hover shifts background to `#F1F1F1`.
- **Tertiary / Ghost:** Borderless, zero fill. Styled with `#555555` text, shifting to `#111111` with an underline on hover.

### Inputs & Text Areas
- Built with a `#FFFFFF` base, 1px `#DCDCDC` boundary, and standard `0.25rem` corners.
- Active states turn the border to solid `#111111`. Focus rings avoid heavy glowing auras, relying solely on crisp line weight shifts.
- Placeholder text is balanced in `#555555` with `Geist` 14px.

### Cards & Work Containers
- Formed with a `#FFFFFF` fill and perimeter 1px `#DCDCDC` border. Corner radius remains locked at `0.25rem`.
- Divided internally by 1px horizontal and vertical hairline dividers rather than floating margins or stacked shadows.
- Card titles utilize `Newsreader` 20px, anchored by micro metadata tags in uppercase `Geist` 11px.

### Badges & Chips
- Status indicators and metadata tokens adopt pill styling (`9999px`).
- Feature a `#FAFAFA` background with a subtle border and colored dot glyph (e.g., `#246B4A` for completed, `#6D4C8D` for AI synthesis).

### Checkboxes & Radio Controls
- Checkboxes are 16x16px squares with `0.125rem` (2px) corners and a 1px border. Selected states fill with `#111111` displaying a razor-thin white tick.
- Radio buttons maintain the standard concentric circular geometry with `#111111` inner dot selection.

### Focus Timers & Editorial Meters
- Linear timeline rulers and progress meters employ raw 1px to 2px tick-marks reminiscent of drafting tools, abandoning rounded fluid progress bars for precise mechanical ticks.