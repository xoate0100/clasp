---
description: SEO + AI-discoverability audit — schema.org, metadata, headings, llms.txt, internal linking
argument-hint: "[--scope <route>] [--fix]"
id: audit-seo
applies_to: [next, any]
modes: [discovery, fix]
output_dir: docs/audit/seo/
depends_on: []
related: [audit-conversion]
---

# /audit-seo — SEO + AI-discoverability audit

Follow the shared flow in `_skeleton.md`. Covers classic SEO and answer-engine /
LLM discoverability (the SureWealth AI-discoverability initiative). Ahrefs MCP is
available for backlink/keyword data when connected.

## Inventory
Route list with: title, meta description, canonical, OG/Twitter tags, structured
data present, heading outline, and indexability (robots/sitemap status).

## Checks
- **Metadata** — unique title + description per route; canonical correctness; no
  duplicate/missing tags; App Router `metadata`/`generateMetadata` coverage.
- **Structured data** — schema.org JSON-LD appropriate to page type
  (Organization, LocalBusiness for CutRates, Course/EducationalOccupationalProgram
  for SureWealth CE); validates without errors.
- **Headings** — single H1, logical hierarchy, descriptive.
- **Social cards** — OG/Twitter image, title, description render correctly.
- **AI-discoverability** — `llms.txt` present and accurate; content structured for
  answer-engine extraction (clear Q/A, entities, definitions); machine-readable
  key facts.
- **Crawlability** — `robots.txt`, `sitemap.xml` present, correct, and current; no
  accidental `noindex`; clean status codes.
- **Internal linking** — orphan pages, anchor-text quality, depth from home.
- **Performance signals** — Core Web Vitals affect ranking (defer to
  `/audit-optimization` for specifics).

## Evidence
Route + tag/markup snippet + validator result per finding.
