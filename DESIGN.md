---
name: Neo Dining Intelligence
colors:
  surface: '#121317'
  surface-dim: '#121317'
  surface-bright: '#38393d'
  surface-container-lowest: '#0d0e12'
  surface-container-low: '#1a1b20'
  surface-container: '#1f1f24'
  surface-container-high: '#292a2e'
  surface-container-highest: '#343439'
  on-surface: '#e3e2e7'
  on-surface-variant: '#e0bfbd'
  inverse-surface: '#e3e2e7'
  inverse-on-surface: '#2f3035'
  outline: '#a78a88'
  outline-variant: '#584140'
  surface-tint: '#ffb3b0'
  primary: '#ffb3b0'
  on-primary: '#68000f'
  primary-container: '#ff6b6b'
  on-primary-container: '#6d0010'
  inverse-primary: '#ae2f34'
  secondary: '#c4c6d0'
  on-secondary: '#2d3038'
  secondary-container: '#464952'
  on-secondary-container: '#b6b8c2'
  tertiary: '#52dea2'
  on-tertiary: '#003824'
  tertiary-container: '#00b179'
  on-tertiary-container: '#003b26'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdad8'
  primary-fixed-dim: '#ffb3b0'
  on-primary-fixed: '#410006'
  on-primary-fixed-variant: '#8c1520'
  secondary-fixed: '#e0e2ed'
  secondary-fixed-dim: '#c4c6d0'
  on-secondary-fixed: '#181b23'
  on-secondary-fixed-variant: '#44474f'
  tertiary-fixed: '#72fbbc'
  tertiary-fixed-dim: '#52dea2'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#121317'
  on-background: '#e3e2e7'
  surface-variant: '#343439'
typography:
  display-lg:
    fontFamily: Space Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.03em
  display-lg-mobile:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 38px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Space Grotesk
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 30px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Space Grotesk
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.03em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-tablet: 2rem
  margin-desktop: 3rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
  space-2xl: 2rem
---

## Brand & Style

The design system embodies a youthful, culture-forward culinary AI companion built for a digitally native, Gen-Z audience. The personality balances razor-sharp utility with effortless street-smart polish: punchy, curated, direct, and unpretentious. It strips away cluttered traditional restaurant portals in favor of a sleek, dark-canvas dining feed driven by algorithmic recommendations, conversational discovery, and group curation.

Visually, the style pairs **Modern Gen-Z Minimalism** with **Structured Spatial Clarity**. It intentionally rejects gimmicks like heavy glassmorphism, muddy neon blurs, skeuomorphic gradients, and excessive drop shadows. Instead, depth and visual pacing rely on deliberate charcoal tonal stacking, crisp geometric framing, high-contrast expressive headline cuts, and punchy coral action moments. The UI feels fast, hyper-legible, tactile, and restrained.

## Colors

The palette is engineered exclusively for an immersive, reduced-strain dark environment with tactile tonal separation.

### Core Color Roles
- **Canvas / Root Background (`#111216`)**: Soft midnight charcoal creating deep, grounding negative space without the harshness of pure `#000000`.
- **Card / Surface Container (`#1C1E24`)**: Moderately elevated charcoal for panels, modular containers, recommendation decks, and modal sheets.
- **Input & Control Surface (`#282B33`)**: Recessed charcoal layer for text inputs, search fields, unselected segment switches, and chip foundations.
- **Main Accent / Coral (`#FF6B6B`)**: Punchy, youthful coral reserved strictly for high-priority interactive touchpoints, primary buttons, dynamic tags, active highlights, and conversion triggers.
- **Border / Structural Divider (`#343640`)**: Low-contrast boundary tone delivering crisp containment and division without visual weight.

### Typography & Content Color Roles
- **Primary Content / Headings (`#F5F3F0`)**: Warm off-white providing ultra-sharp typographic contrast against midnight grounds while feeling softer and more refined than stark paper white.
- **Secondary Content / Body (`#B3B5BD`)**: Balanced, neutral slate-gray optimized for sustained readability across long restaurant reviews, menus, and conversational chat outputs.
- **Muted / Subtext (`#6C707E`)**: Quiet slate tone for metadata, timestamps, input placeholders, and inactive indicator states.

## Typography

The type system blends the energetic, tech-forward geometric quirks of **Space Grotesk** with the neutral, hyper-legible ergonomics of **Inter**.

- **Display & Headlines (`Space Grotesk`)**: Employed across screen hero tags, restaurant names, AI prompt triggers, and modal titles. Always configured with tight tracking (`-0.01em` to `-0.03em`) to deliver confident, high-density editorial impact.
- **Body, Controls & Labels (`Inter`)**: Delivers maximum utility across dynamic feed updates, AI explanations, menus, ingredient listings, button text, and timestamps. Renders cleanly even on low-end screens with micro line lengths.
- **Hierarchy Rules**: Never combine italic weights with Space Grotesk. Maintain strict tracking rules: headings tighten as font size increases; functional labels and badges open up tracking (`0.01em` to `0.03em`) for immediate recognition at reduced scales.

## Layout & Spacing

The layout is constructed on an adaptable fluid grid built for fast, scroll-driven interactions, scannable food discovery carousels, and persistent AI inputs.

### Grid & Breakpoints
- **Mobile (< 768px)**: 4-column fluid layout with `1rem` (16px) margins and `1rem` gutters. Content stacks vertically with full-width action decks and bottom-pinned AI conversational dock bars.
- **Tablet (768px – 1024px)**: 8-column layout with `2rem` (32px) margins and `1.25rem` gutters. Splits feeds into two-column recommendation modules.
- **Desktop (> 1024px)**: 12-column layout capped at `1280px` max content width, centered with `3rem` (48px) margins and `1.5rem` (24px) gutters. Uses persistent vertical left navigation, primary feed columns, and contextual side-drawers for map inspection and cart curation.

### Spacing Philosophy
Consistent visual rhythm follows a strict 4px/8px modular scale. Dense functional groupings (e.g., tags, calorie badges, dietary flags) lock to `space-xs` and `space-sm`. Internal card padding uses `space-lg` (16px), while modular sections and list separations pull from `space-xl` (24px) and `space-2xl` (32px).

## Elevation & Depth

This design system rejects fuzzy drop shadows, glowing outer glows, and glassmorphic blurs. Depth is conveyed strictly via **Surface Tonal Stacking** reinforced by **Crisp Low-Contrast Outlines**.

### Elevation Hierarchy
1. **Level 0 (Canvas Base)**: `#111216`. Pure flat ground where root page flows and background layers live.
2. **Level 1 (Card & Module Surface)**: `#1C1E24` outlined by a `1px` continuous border in `#343640`. Used for food cards, recommendation chips, chat message modules, and profile pods.
3. **Level 2 (Active Overlays & Dropdowns)**: `#22252C` with a `1px` border in `#3D404C`. Used for filter dropdowns, search result trays, and contextual menus.
4. **Level 3 (Modal Sheets & Floating Docks)**: `#1C1E24` bordered by `#3D404C`, elevated over a 60% opacity `#0A0B0E` dimming scrim.

### State Transitions
Elevations do not animate along the Z-axis using blooming shadows. Instead, interactive hover and active states shift borders from muted slate (`#343640`) to active border contrast (`#525563`), or directly into the accent coral (`#FF6B6B`) for focused selection states.

## Shapes

The visual geometry adheres strictly to a cohesive **10px – 12px corner radius standard** (`roundedness: 2`), projecting an approachable, modern digital feel that avoids feeling cartoonish or sharp.

- **Primary Components (Cards, Containers, Input Fields, Modals)**: Standardized at `12px` (`0.75rem`) border radius. This creates a uniform outer silhouette across every major UI container.
- **Secondary Nested Controls (Buttons, Form Elements, Inner Badges)**: Scaled to `10px` (`0.625rem`) or matches the container's inner contour so borders maintain visual concentricity.
- **Filter Chips & Interactive Pills**: Allowed a full pill silhouette (`9999px`) only when representing micro status filters, dietary icons (e.g., "Vegan", "Halal"), or inline dismissible tags.

## Components

### Buttons
- **Primary Action**: Solid `#FF6B6B` fill, `#111216` bold text (Inter 14px, Semi-Bold), `10px` corner radius. Hover state transitions to `#FA5252` with zero glow. Active state scales subtly (`scale(0.98)`).
- **Secondary / Surface**: `#282B33` fill, `1px solid #343640`, `#F5F3F0` text. Hover shifts background to `#32353F` and border to `#525563`.
- **Ghost / Tertiary**: Transparent fill, `#B3B5BD` text. Hover yields `#1C1E24` background with `#F5F3F0` text.

### Input Fields & Search Bars
- **Container**: Fill `#282B33`, `1px solid #343640`, `12px` radius. Height fixed at `44px` (touch-optimized).
- **Text & Placeholder**: Input text in `#F5F3F0` (Inter 14px); placeholder in `#6C707E`.
- **Focus State**: `1px solid #FF6B6B` border. No outer glow or halo rings.

### Cards & Feed Tiles
- **Structure**: Surface fill `#1C1E24`, `1px solid #343640`, `12px` corner radius, `space-lg` (16px) internal padding.
- **Imagery**: Restaurant food media clipped at `10px` inner radius with zero inset shadows.
- **Card Interactive State**: On desktop hover, border transitions smoothly from `#343640` to `#525563` with a clean `transform: translateY(-2px)` translation.

### Chips & Tags
- **Selection Chips**: Fill `#282B33`, border `1px solid #343640`, text `#B3B5BD`. In active selected state, background switches to `#FF6B6B` with `#111216` text and no border.
- **Dietary & Meta Badges**: Pill-shaped (`9999px`), background `#1C1E24`, border `1px solid #343640`, subtext `#B3B5BD` (Inter 11px Medium).

### Checkboxes & Radio Controls
- **Checkboxes**: `18px x 18px` square with `4px` radius, background `#282B33`, border `1px solid #343640`. Checked state fills `#FF6B6B` with a sharp `#111216` check icon.
- **Radio Buttons**: `18px` circular control, `#282B33` background, `#343640` border. Active state features a solid `#FF6B6B` inner circle (`8px` diameter).

### Conversational AI Chat Dock (Specialized Component)
- **Dock Bar**: Pinned bottom navigation wrapper built with `#1C1E24` and a top boundary of `1px solid #343640`. Houses an integrated `#282B33` conversational command prompt accompanied by a distinct `#FF6B6B` circular prompt execution trigger.