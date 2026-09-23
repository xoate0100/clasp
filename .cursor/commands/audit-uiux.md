---
description: Design-system conformance + UI/UX audit (shadcn/Tailwind tokens, atmosphere layer, a11y, Figma drift)
argument-hint: "[--fix] [--scope <route|component>]"
id: audit-uiux
applies_to: [next]
modes: [discovery, fix]
output_dir: docs/audit/uiux/
depends_on: []
related: [audit-media, audit-optimization]
---

# /audit-uiux — design-system conformance + UI/UX audit

Follow the shared flow in `_skeleton.md`. This is conformance-to-system, not taste:
does the UI use the design system correctly, render as intended, and stay usable?

## Inventory
Enumerate: shadcn/ui components in use, Tailwind theme tokens (colors, spacing,
radius, typography scale), the `.atm-*` atmosphere utilities and
`components/atmosphere/*`, breakpoints, and (SureWealth) the Figma design-system
tokens/components for comparison.

## Checks
- **Token conformance** — flag hardcoded hex/px and inline styles that bypass
  Tailwind theme tokens; off-scale spacing/typography; ad-hoc color values.
- **Atmosphere layer actually renders** — confirm `.atm-*` utilities and
  `components/atmosphere/*` are present in the DOM *and visibly affect* the page
  (the CutRates symptom: applied but not showing — check z-index, opacity,
  stacking context, overflow clip, and whether the layer is painted behind an
  opaque background).
- **Component consistency** — same intent uses the same component (buttons,
  inputs, cards); no divergent one-offs of a systematized component.
- **Responsive** — every breakpoint; no overflow, overlap, or unusable tap targets.
- **Dark mode / theming** — parity and contrast across themes.
- **Accessibility** — contrast ratios, visible focus rings, keyboard nav, ARIA
  roles/labels, alt text presence (hand image weight to `/audit-media`).
- **State coverage (visual)** — loading/empty/error/success states exist and look
  intentional.
- **Figma drift (SureWealth)** — implemented tokens/components vs the Figma design
  system; list divergences (CE components: Reporting Status Badge, Transcript Row,
  Certificate Card, Renewal Deadline Indicator).

## Evidence
Screenshot ref + component/file path per finding. Prefer live render inspection
over reading JSX alone — the CutRates atmosphere bug is invisible in source.
