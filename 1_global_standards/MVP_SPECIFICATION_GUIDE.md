Perfect — this is an essential piece of your meta-framework’s developer onboarding.
Below is a **complete documentation file** that you can drop into your repo at:

```
/1_global_standards/MVP_SPECIFICATION_GUIDE.md
```

It explains *why* the file exists, *how* it’s structured, *validation rules*, and *common pitfalls* when authoring a new `MVP_SPECIFICATION.yaml`.
The format is consistent with your L2.5 meta-framework conventions and readable by both humans and AI (Cursor agent).

---

# 🧭 MVP_SPECIFICATION_GUIDE.md

**Title:** Authoring and Maintaining `MVP_SPECIFICATION.yaml`
**Version:** 1.0
**Audience:** Developers, Architects, AI Agents (Cursor)
**Purpose:** Define and standardize how new projects describe themselves for initialization under the L2.5 meta-framework.

---

## 🧠 What is `MVP_SPECIFICATION.yaml`?

The `MVP_SPECIFICATION.yaml` file is the **single source of truth** for describing how an MVP (Minimum Viable Product) should be initialized, scaffolded, and executed by the meta-framework.
It is a declarative blueprint that the **initializer (human or AI)** reads to generate:

* The project folder structure
* Tech stack and dependencies
* Environment configuration
* Active build plan (`ACTIVE_PLAN.yaml`)
* Sandbox permissions and validation checks

Think of it as the “genetic code” of the project — everything else (CI, folders, tasks, code scaffolds) is *derived from it*.

---

## 📦 File Location

Always place the file in:

```
/0_phase0_bootstrap/MVP_SPECIFICATION.yaml
```

This ensures that:

* The `project_initializer` can auto-detect it during `ai-dev init`.
* Schema validation (`/7_schemas/mvp_spec.schema.json`) runs automatically.
* AI sandbox rules treat it as **read-only**.

---

## ⚙️ Validation and Enforcement

* The spec is validated against `/7_schemas/mvp_spec.schema.json` on every initialization.
* The pre-commit hook and `schema_enforcement.py` block commits if invalid.
* It must include all **core sections** and follow the correct key hierarchy.

---

## 🧩 Core Structure Overview

```yaml
Project: string
Maturity: string (e.g., "L2.5")
Architecture: string
Repo_Type: string
Execution_Mode: string
GOALS_AND_PRINCIPLES: {}
TECH_STACK: {}
MONOREPO_LAYOUT: {}
ENVIRONMENT_AND_CONFIG: {}
ROUTING_MODEL: {}
SCHEMA_DEFINITION: {}
BRAND_MODULE: {}
ANALYTICS_AND_EVENTS: {}
INTEGRATIONS: {}
SEO_AND_JSONLD: {}
AI_UI_GENERATION: {}
AUTOMATION_SCRIPTS: {}
INTERACTIVE_PATTERNS: {}
QA_CHECKLIST: {}
DEPLOYMENT: {}
MIGRATION_PATH: {}
FIRST_RUN_PLAYBOOK: {}
POST_MVP_FEATURES: {}
DELIVERABLES_DAY1: {}
ACTIVE_PLAN_TEMPLATE: {}
FEATURE_FLAGS_REFERENCE: {}
SUMMARY_FOR_INITIALIZER: {}
```

Each section must exist, even if empty or minimal.

---

## 🧱 1. Header Fields (Required)

```yaml
Project: My Awesome MVP
Maturity: L2.5
Architecture: Single Vercel App with App Router
Repo_Type: frontend
Execution_Mode: Controlled Agentic Execution
```

**Rules**

* `Maturity` must match meta-framework levels (`L2`, `L2.5`, or `L3`).
* `Execution_Mode` must correspond to sandbox type in `feature_flags.yml`.

---

## 🚀 2. Goals and Principles

Defines *why the project exists* and the *guiding rules*.

```yaml
GOALS_AND_PRINCIPLES:
  goals:
    - Deliver a working MVP with minimal manual setup.
    - Maintain brand consistency and analytics accuracy.
  principles:
    - DRY, typed, modular code.
    - TDD, SOLID, and explicit documentation.
```

---

## 🧰 3. Tech Stack

Describes frameworks, languages, and dependencies.

```yaml
TECH_STACK:
  frontend:
    framework: Next.js
    version: 14
    language: TypeScript
    styling: [TailwindCSS, shadcn/ui]
  backend:
    framework: FastAPI
    language: Python
  validation: Zod
  integrations:
    - OpenAI
    - Google Tag Manager
```

**Tip:** The stack must align with `feature_flags.components` to avoid conflicts.

---

## 🗂️ 4. Monorepo Layout

This tells the initializer **exactly** what to create.

```yaml
MONOREPO_LAYOUT:
  root:
    files: [.env, package.json, README.md]
    apps:
      web:
        next.config.mjs
        app/
        components/
        content/
        lib/
        public/
  scripts:
    - new-funnel.ts
```

**Rules**

* Must reflect the canonical folder pattern (frontend/backend/shared).
* `apps/` and `scripts/` are recognized keywords by the scaffolder.

---

## 🔑 5. Environment and Config

```yaml
ENVIRONMENT_AND_CONFIG:
  vercel_env:
    NEXT_PUBLIC_GTM_ID: GTM-XXXXXXX
    OPENAI_API_KEY: ...
  notes:
    - All secrets are stored in Vercel envs.
```

---

## 🌐 6. Routing Model

Defines the app’s entry and routing structure.

```yaml
ROUTING_MODEL:
  type: path-based
  base_path: /funnel/[slug]
  data_source: /content/funnels/[slug]/content.json
```

---

## 🧾 7. Schema Definition

Describes the core Zod (or JSON) schema for data validation.

```yaml
SCHEMA_DEFINITION:
  validation_lib: Zod
  schema_files: [/lib/schema.ts]
  modules: [hero, scenario, cta, quiz, faq]
```

---

## 🎨 8. Brand Module

```yaml
BRAND_MODULE:
  colors: { primary: "#0C4A6E", accent: "#EAB308" }
  font: { heading: Inter, body: Inter }
  disclaimers:
    - "Educational only. Not financial advice."
```

---

## 📊 9. Analytics and Events

```yaml
ANALYTICS_AND_EVENTS:
  provider: GTM
  events:
    - VIEW
    - CTA_CLICK
    - FORM_SUBMIT
  pixels:
    - LinkedIn
    - TikTok
```

---

## 🔗 10. Integrations

```yaml
INTEGRATIONS:
  oncehub: iframe
  activecampaign: script_embed
```

---

## 🔍 11. SEO and JSON-LD

```yaml
SEO_AND_JSONLD:
  meta_fields: [title, description, noindex]
  jsonld: [faq, howto]
```

---

## 🧠 12. AI UI Generation

```yaml
AI_UI_GENERATION:
  tool: v0.dev
  prompt_library: /prompts/ui/
  pattern: |
    Create a responsive section using Tailwind + shadcn.
```

---

## 🧩 13. Automation Scripts

```yaml
AUTOMATION_SCRIPTS:
  new-funnel.ts: scaffold content.json from PDF
  pdf-to-json.ts: transform source to JSON
```

---

## 💬 14. Interactive Patterns

```yaml
INTERACTIVE_PATTERNS:
  quiz:
    questions: 3
  sticky_cta:
    trigger_scroll_pct: 30
```

---

## 🧪 15. QA Checklist

```yaml
QA_CHECKLIST:
  - links_working
  - pixels_triggered
  - mobile_responsive
  - accessibility_passed
  - seo_flags_valid
```

---

## ☁️ 16. Deployment

```yaml
DEPLOYMENT:
  provider: Vercel
  domain: funnels.example.com
  dns: Cloudflare
```

---

## 🔄 17. Migration Path

```yaml
MIGRATION_PATH:
  future_subdomains: supported
  automation: Cloudflare API via CI
```

---

## 🧾 18. First-Run Playbook

```yaml
FIRST_RUN_PLAYBOOK:
  steps:
    - init_repo
    - set_env_vars
    - run_script: pnpm new:funnel
    - review_content_json
    - deploy_to_vercel
```

---

## 🚀 19. Post-MVP Features

```yaml
POST_MVP_FEATURES:
  - server_actions
  - ab_testing
  - ai_feedback_loop
```

---

## 🎯 20. Deliverables (Day 1)

```yaml
DELIVERABLES_DAY1:
  outputs:
    - Functional MVP deployment
    - Automated PDF → funnel converter
  success_metric: "Two funnels live within 3 days."
```

---

## 🗺️ 21. Active Plan Template

Describes the plan to generate `/6_ai_runtime_context/ACTIVE_PLAN.yaml`.

```yaml
ACTIVE_PLAN_TEMPLATE:
  plan_id: MVP-Project-Init
  component: frontend
  goal: Initialize and deploy MVP
  tasks:
    - id: 1
      name: Setup framework & dependencies
    - id: 2
      name: Implement core modules
    - id: 3
      name: QA & deploy
  status: active
  auto_commit: true
```

---

## 🔐 22. Feature Flags Reference

```yaml
FEATURE_FLAGS_REFERENCE:
  cursor_agent_mode: sandboxed
  agentic_write_ops: true
  modify_meta_framework: false
  components:
    frontend:
      coverage_threshold: 95
  gates:
    block_on_schema_violation: true
```

---

## 🧩 23. Summary for Initializer

This section tells the AI **exactly what to do**.

```yaml
SUMMARY_FOR_INITIALIZER:
  intent:
    - Initialize project per MONOREPO_LAYOUT
    - Validate schemas
    - Generate Active Plan
    - Install dependencies
    - Run pre-commit hooks
    - Report success in ai_reports/init_report.json
```

---

## 🧠 Best Practices

| Principle               | Description                                                          |
| ----------------------- | -------------------------------------------------------------------- |
| **Declarative only**    | No imperative instructions or shell commands in YAML.                |
| **Portable**            | Avoid absolute paths. Use relative repo paths only.                  |
| **Readable**            | Keep key names lowercase or snake_case.                              |
| **Schema-aligned**      | Validate against `/7_schemas/mvp_spec.schema.json` before commit.    |
| **Immutable post-init** | Do not modify after `ai-dev init`. Changes require new spec version. |

---

## 🧱 Common Mistakes

| Mistake                               | Result                                       |
| ------------------------------------- | -------------------------------------------- |
| Missing `ACTIVE_PLAN_TEMPLATE`        | Initializer can’t create `ACTIVE_PLAN.yaml`. |
| Invalid YAML indentation              | Parsing errors during initialization.        |
| Missing keys under `TECH_STACK`       | Dependency installer fails.                  |
| Changing meta-framework paths         | AI sandbox rejects plan.                     |
| Setting `modify_meta_framework: true` | Disables safety in L2.5.                     |

---

## ✅ Validation Command

Once written, run:

```bash
python3 3_bootstrap_scripts/schema_enforcement.py --file 0_phase0_bootstrap/MVP_SPECIFICATION.yaml
```

---

## 📜 Versioning

* Each major update to the MVP spec should increment a version comment at the top.
* Keep previous versions archived under `/docs/archive/mvp_specs/`.

---

## 🧩 Example Minimal Template (Valid)

```yaml
Project: Example MVP
Maturity: L2.5
Architecture: Single Next.js App
Execution_Mode: Controlled Agentic Execution
GOALS_AND_PRINCIPLES:
  goals: [Build quickly, stay maintainable]
TECH_STACK:
  frontend:
    framework: Next.js
    language: TypeScript
MONOREPO_LAYOUT:
  apps:
    web:
      app/
      components/
ACTIVE_PLAN_TEMPLATE:
  plan_id: MVP-Init
  component: frontend
  tasks:
    - { id: 1, name: "Scaffold Next.js project" }
SUMMARY_FOR_INITIALIZER:
  intent:
    - "Generate folder structure"
    - "Install dependencies"
```

---

**✅ End of Guide**

> This guide defines how to author, validate, and maintain a well-formed `MVP_SPECIFICATION.yaml`.
> Following it ensures every project in the L2.5 ecosystem initializes predictably, reproducibly, and safely.
