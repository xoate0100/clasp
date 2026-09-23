---
description: Envato media-slot pipeline audit (SLOT_MAP → media-map → mediaSrc, broken/orphaned assets, licensing)
argument-hint: "[--fix] [--scope <slot|route>]"
id: audit-media
applies_to: [next]
modes: [discovery, fix]
output_dir: docs/audit/media/
depends_on: []
related: [audit-uiux, audit-optimization]
---

# /audit-media — Envato media-slot pipeline audit

Follow the shared flow in `_skeleton.md`. Audits the media-slot pipeline that
CutRates and SureWealth use for Envato textures/photos/patterns/videos.

## Pipeline (inventory targets)
- `docs/media/SLOT_MAP.yaml` — declared slots.
- `lib/generated/media-map.json` — generated resolution.
- `lib/media.ts` `mediaSrc()` — the resolver every render should go through.
- Atmosphere layer: `app/globals.css` `.atm-*`, `components/atmosphere/*`.
- SureWealth course media contract: `narration_script` + `media[]` slots per
  `<package_id>.course.json`, and the render seam to `surewealth-course-factory`
  (assets served from Google Cloud Storage + secure CDN, not Supabase Storage).

Build the inventory: every declared slot, every rendered media reference, and the
mapping between them.

## Checks
- **Unresolved / broken slots** — slot in SLOT_MAP with no `media-map.json` entry;
  `mediaSrc()` returning missing/404 assets; broken `<img>`/`<video>`/`background`.
- **Orphaned declared slots** — in SLOT_MAP but never rendered.
- **Out-of-pipeline media** — assets rendered directly, bypassing `mediaSrc()`
  (these break the update pipeline and licensing tracking).
- **Alt text** — every image/informative media has meaningful `alt`; decorative
  marked appropriately.
- **Asset weight** — photos/videos against a perf budget (hand LCP specifics to
  `/audit-optimization`); flag unoptimized originals.
- **Format** — webp/avif for images; posters + lazy + `preload` discipline for
  video; no autoplay-with-sound.
- **Atmosphere visibility** — texture/pattern/overlay layers present but not
  visible (cross-check with `/audit-uiux`).
- **Licensing / attribution** — each Envato asset traceable to a license record;
  flag assets with no provenance.
- **Course media contract (SureWealth)** — every `media[]` slot in a course
  package resolves and the render seam to the course-factory is satisfiable.

## Evidence
Slot id + source path + resolved URL + render location per finding.
