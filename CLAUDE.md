# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Required Reading Before Any Work

Before starting any development task, **always read these files first**:

1. **`docs/ROADMAP_PROGRESS.md`** — What has been completed and what remains. Check this to avoid redoing work or missing context.
2. **`docs/BUG_REGISTRY.md`** — Known bug patterns and fixes. Check this when debugging to see if the issue matches a known pattern.
3. **`docs/architecture/OVERVIEW.md`** — System architecture and module boundaries. Understand where your change fits.
4. **`docs/Design-Kits/aerofly-design-kit.html`** — The design kit. Before any frontend work, check this file for existing component patterns. If a component is missing, add it here first before implementing.

## Required Updates After Any Work

After completing any development task:

1. **Update `docs/ROADMAP_PROGRESS.md`** — Mark completed items as DONE with commit hash/PR number. Add new items if scope was discovered during work.
2. **Update `docs/BUG_REGISTRY.md`** — If you found and fixed a bug, document the root cause pattern, symptom, fix, and affected files. Future agents depend on this.

## Prompt Log (MANDATORY — Every Prompt)

**After every user prompt**, append a new entry to **`docs/PROMPT_LOG.md`**. This is a persistent audit trail of all user requests.

**Format** — each entry is a section with metadata line + full prompt text:

```markdown
### YYYY-MM-DD HH:MM — <very short task description> (`<branch-name>`)

> <exact original prompt text, verbatim>
```

- **Date/time**: Use the current date and time (24h format).
- **Description**: Maximum ~10 words — just enough to identify the request at a glance.
- **Branch**: The current git branch at the time of the prompt.
- **Prompt body**: The user's exact wording in a blockquote. Copy verbatim — do not paraphrase, shorten, or translate.
- Log **every** user prompt, including follow-ups, clarifications, and "do housekeeping".
- Do NOT skip this step. Do NOT batch entries. Log immediately after receiving each prompt.

## Bug/Feature Intake — Prefilled Form + Questions (Mandatory)

Whenever the user mentions a **problem/bug** or proposes a **new feature/change request** (even informally), you MUST do the following **before** implementation:

1) Create a **prefilled intake form** (Bug Report or Feature Request) using all information already provided.
2) Identify missing fields and ask **targeted questions** to fill the gaps.
3) Only after the user answered (or explicitly skipped), create the **GitHub Issue** with the finalized content.

### Step 1 — Output a Prefilled Intake Form

You MUST output the form in markdown under the heading:

- `### Draft: Bug Report` OR `### Draft: Feature Request`

Use this exact structure:

#### Bug Report Form
- **Title:** {prefilled or placeholder}
- **Context:** {what the user was trying to do}
- **Current behavior:** {what happens}
- **Expected behavior:** {what should happen}
- **Steps to reproduce:** {list or "Unknown yet"}
- **Frequency / impact:** {e.g. always / sometimes; severity guess}
- **Logs / screenshots:** {links/snippets or "Not provided"}
- **Environment:** {branch/commit, OS, docker stack, service, module if relevant}
- **Acceptance criteria:**
  - {bullet list; prefilled if possible}

#### Feature Request Form
- **Title:** {prefilled or placeholder}
- **Problem / motivation:** {why needed}
- **Proposed solution:** {what to build/change}
- **Scope (in/out):**
  - In: {...}
  - Out: {...}
- **User stories / use cases:** {bullets or "Not provided"}
- **UX / UI notes (if relevant):** {...}
- **Technical notes (if relevant):** {...}
- **Acceptance criteria:**
  - {bullet list; prefilled if possible}

### Step 2 — Ask Questions to Fill the Gaps

After showing the draft form, you MUST ask questions to fill missing info.

Rules for questions:
- Ask only what is necessary; keep it short and structured.
- Ask **at most 7 questions per turn**.
- Prefer **multiple choice** when possible.
- If a field is unknown, explicitly ask for it OR ask whether to proceed with "Not provided/Unknown".

Use the heading:
- `### Questions to finalize the issue`

Question strategy:
- **Bug**: prioritize reproduction steps, expected behavior, impact/severity, environment, logs.
- **Feature**: prioritize motivation, scope boundaries, acceptance criteria, UX expectations, constraints.

### Step 3 — Create the GitHub Issue (After Clarification)

Once enough info is available (or user says "create it anyway"), you MUST create the GitHub issue.

**Classification**
- **Bug report** -> label `bug`
- **Feature request** -> label `enhancement`

**Preferred method: GitHub CLI**
- Bug:
  `gh issue create --repo DMPlisken/AeroFly --title "{TITLE}" --body "{BODY}" --label "bug"`
- Feature:
  `gh issue create --repo DMPlisken/AeroFly --title "{TITLE}" --body "{BODY}" --label "enhancement"`

**After creating the issue**
- Paste the created Issue URL/number into the chat output for traceability.
- Reference the issue number in:
  - branch name (e.g., `fix/123-dfs-parser-error`)
  - PR title (e.g., `[#123] Fix DFS parser error`)
- Only then proceed with implementation work.

### Exception

Only skip this flow if the user explicitly says:
- "Do not create an issue for this." OR "No questions, just implement."

In that case: create the issue with best-effort assumptions and mark unknown fields as "Not provided".

## Project Context

- **Architecture**: Microservices — each functional module runs in its own Docker container
- **Backend stack**: Python 3.12+, FastAPI, per-service Dockerfiles
- **Frontend**: React/TypeScript with Vite
- **Database**: PostgreSQL 16 (primary data store, one schema per service)
- **Search engine**: Meilisearch (full-text search for aerodrome data, bilingual DE/EN)
- **Cache / messaging**: Redis 7 (caching + pub/sub for inter-service communication)
- **Orchestration**: Docker Compose (dev), production deployment TBD
- **Key libraries**: httpx (HTTP client), beautifulsoup4/lxml (HTML parsing), PyPDF2 (PDF parsing), SQLAlchemy 2.0 (ORM), Alembic (migrations), Pydantic v2 (validation), meilisearch-python (search client)
- **Primary data source**: DFS (Deutsche Flugsicherung) — AIP (Aeronautical Information Publication)
- **Languages**: German (DE) and English (EN) — bilingual throughout

### Service Modules

| Module | Directory | Port | Purpose |
|--------|-----------|------|---------|
| Gateway | `services/gateway/` | 8000 | API gateway, auth, routing, Swagger/OpenAPI |
| Data Ingestion | `services/data-ingestion/` | 8001 | DFS data scraping, PDF parsing, import |
| Search | `services/search/` | 8002 | Meilisearch indexing & full-text search |
| Frontend | `services/frontend/` | 3000 | Web UI (React/TypeScript) |

### Shared Code

- `shared/python/` — Shared models, schemas, and utilities used across Python services
- Each service imports shared code as a mounted volume in Docker

## Build & Run Commands

```bash
# Start full stack
docker compose up --build

# Start specific service
docker compose up --build gateway

# Run tests (Python service)
cd services/gateway && pytest tests/ -v

# Run tests (Frontend)
cd services/frontend && npm test

# Type check frontend
cd services/frontend && npx tsc --noEmit

# Database migration (per service)
cd services/gateway && alembic upgrade head

# Create new migration
cd services/gateway && alembic revision --autogenerate -m "description"

# Run test infrastructure only
docker compose -f docker-compose.test.yml up -d
```

## Git Branching Policy

- **`develop`** is the integration branch. All feature/fix work targets `develop`.
- **`main`** is the release branch. Only stable releases from `develop` are merged into `main`. NEVER commit directly to `main`.
- **NEVER commit directly to `develop`** either. Always create a feature/topic branch first.
- Branch naming convention: `<type>/<issue-number>-<short-description>` where type is `feat`, `fix`, `refactor`, `test`, `docs`, or `chore`.
- Create the branch from `develop`: `git checkout develop && git checkout -b <branch-name>`.
- After work is complete and verified, create a PR to merge into `develop`.
- **Hotfixes for `main`**: Only allowed with label `main-fix` or title prefix `[main-fix]`. Branch from `main`, PR back to `main`, then cherry-pick into `develop`.
- **Release flow**: When `develop` is stable -> merge into `main` -> tag with version (e.g., `git tag -a v1.0.0 -m "Release v1.0.0"`).

## Commit Message Convention

- Present tense ("Add feature" not "Added feature")
- First line max 50 characters
- Reference issue numbers: `[#123] Add runway data parser`
- AI-assisted commits: `Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>`

## Critical Rules

- **Design Kit rule (MANDATORY — NO EXCEPTIONS)**: Every frontend UI implementation MUST be based on the AeroFly Design Kit at `docs/Design-Kits/aerofly-design-kit.html`. This is the single source of truth for all visual components, colors, typography, spacing, and patterns. The workflow is:
  1. Before implementing any UI component, check if it exists in the design kit.
  2. If the component exists, implement it exactly as specified in the design kit (colors, spacing, fonts, variants).
  3. If the component does NOT exist in the design kit, you MUST **first add it to the design kit HTML file**, then implement it in the frontend based on the newly added design kit component.
  4. Never skip this process. Never invent ad-hoc styles, colors, or component patterns outside the design kit.
  5. The design kit defines: color tokens (light + dark mode), typography scale, button variants, badge/status styles (frequency types, NOTAM states), card layouts, table formats, search input, and all aviation-specific components (aerodrome cards, frequency badges, runway diagrams).
  6. When updating the design kit, follow the existing section numbering and naming conventions. Add new components as new numbered sections.
- **One service per container**: Each module has its own Dockerfile, dependencies, and lifecycle. Never merge services.
- **Inter-service communication**: Use Redis pub/sub or HTTP REST between services. Never import code directly across service boundaries — use `shared/python/` for shared types.
- **Database per module**: Each service that needs persistence gets its own PostgreSQL schema. Never share tables across services.
- **Environment variables**: All secrets and config via `.env` files. Never hardcode credentials.
- **DFS data flow rule (MANDATORY)**: All aerodrome data (charts, frequencies, runways, NOTAMs) MUST flow through the **Data Ingestion** service. Data Ingestion is the single source of truth for DFS data and decides what data to collect, at what frequency, and how to parse it. Other services NEVER scrape DFS directly. When adding any new data type:
  1. Check if Data Ingestion already provides it.
  2. If not, add the scraper/parser to Data Ingestion first.
  3. Data Ingestion writes to PostgreSQL and publishes update events via Redis pub/sub.
  4. Search service subscribes and syncs to Meilisearch.
  5. Gateway exposes the data via REST API.
  6. If this flow cannot be followed for technical reasons, **STOP and inform the user** with: (a) why it's not possible, (b) the proposed alternative, (c) ask for explicit permission before proceeding.
- **Bilingual rule**: All user-facing text and API fields must support both German (DE) and English (EN). Database columns use `name` (EN) and `name_de` (DE) pattern. Frontend uses i18n. Search indexes are configured for both languages.
- **API documentation rule**: Every new API endpoint MUST have proper OpenAPI/Swagger documentation via FastAPI's built-in support (type hints, docstrings, response models). The Swagger UI at `/api/docs` is the primary API reference for external consumers.

## Model Usage Strategy

### Default Model
Use **Opus 4.6** (`opus`) as the default model for the lead agent and for complex reasoning, architecture decisions, debugging, and agentic workflows.

### Hybrid Model Strategy (`opusplan`)
Use the `opusplan` alias for cost-efficient sessions:
- **Plan mode** -> Opus for complex reasoning and architecture decisions
- **Execution mode** -> Automatically switches to Sonnet 4.6 for code generation and implementation

This is the recommended default for long feature-build sessions.

### Context Management
- Monitor context usage with `/context` — when approaching **~70%**, either compact or generate a continuation prompt before resetting.
- For multi-hour sessions: prefer `opusplan` or start fresh with a structured handoff prompt rather than pushing context limits.

### Quick Reference
| Scenario | Model | Command |
|---|---|---|
| Default lead agent work | Opus 4.6 (200K) | `/model opus` |
| Cost-efficient feature builds | Opus plan + Sonnet exec | `/model opusplan` |
| Large codebase analysis | Sonnet 4.6 1M | `/model sonnet[1m]` |
| Full power + full context (API key) | Opus 1M | `/model opus[1m]` |
| Fast interactive debugging | Opus 4.6 fast mode | `/fast` |

## Housekeeping Workflow — "do housekeeping"

When the user says **"do housekeeping"** (or any variation like "housekeeping", "run housekeeping"), execute ALL of the following steps in order. Do NOT ask questions — just run through the full checklist. Report a summary at the end.

### Prerequisites (auto-detect)

Before starting, determine these values from context:
- **Branch name**: current git branch (must NOT be `develop` or `main`)
- **Issue number**: extract from branch name (e.g., `feat/14-search-page` -> `#14`)
- **Task type**: extract from branch prefix (`feat` -> feature, `fix` -> bug fix, `refactor`, `docs`, etc.)
- **Changed services**: which `services/*/` directories were modified (for targeted Docker rebuild)

If currently on `develop` or `main`, STOP and tell the user: "Housekeeping must be run from a feature/fix branch, not from develop/main."

### Step 1 — Commit

- Stage all changes: `git add -A`
- Create a commit message following the convention: `[#<issue>] <type>: <description>`
- Include `Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>`

### Step 2 — Push to origin

- `git push -u origin <branch-name>`
- If the branch does not exist on the remote yet, this creates it.

### Step 3 — Create PR (if none exists)

- Check: `gh pr list --head <branch-name>`
- If no PR exists, create one:
  ```
  gh pr create --repo DMPlisken/AeroFly --base develop --title "[#<issue>] <descriptive title>" --body "<body>"
  ```
- Body must include: Summary, Services affected, Test plan.

### Step 4 — Health check

- Run `docker compose up --build -d` and check all services start.
- Run tests for affected services.
- If any service fails to start or tests fail, report the error but continue.

### Step 5 — Merge the PR

- `gh pr merge <pr-number> --squash --delete-branch`
- If merge fails (e.g., conflicts), stop at this step, report the conflict, and ask the user how to proceed.

### Step 6 — Close the GitHub issue

- `gh issue close <issue-number> --repo DMPlisken/AeroFly`

### Step 7 — Update documentation

- Update `docs/ROADMAP_PROGRESS.md` — mark completed items.
- Update `docs/BUG_REGISTRY.md` — if a bug was fixed.
- Any other relevant docs.

### Step 8 — Switch to develop and pull

- `git checkout develop && git pull origin develop`

### Step 9 — Rebuild Docker and run migrations

- `docker compose up --build -d`
- Run any pending Alembic migrations for affected services.

### Step 10 — Final summary

Output a summary:
```
### Housekeeping Summary
- **Branch**: <branch-name>
- **Issue**: #<issue-number>
- **PR**: #<pr-number> (merged/failed)
- **Services rebuilt**: <list>
- **Tests**: passed/failed
- **Docs updated**: yes/no
```

### Error handling
- If any step fails, log the error and continue to the next step. Do NOT stop the entire workflow.
- At the end, report all failures in the summary under `### Issues encountered`.
- If the merge fails (e.g., conflicts), stop at that step, report the conflict, and ask the user how to proceed.

## Agent Team Guidelines

When a task involves 3+ independent services/modules, use agent teams for parallel execution.

### When to Use Teams
- Multi-service feature builds, test generation across modules, parallel refactoring
- Tasks with clear independent workstreams (e.g., gateway + data-ingestion + search)
- NOT for sequential work, single-file edits, or tasks where teammates would edit the same file

### Task Design
- **Each teammate owns distinct files/services** — never assign two teammates to the same file
- Create ALL tasks upfront with `TaskCreate` before spawning teammates
- Include full context in task descriptions: file paths, type definitions, conventions, acceptance criteria
- Final integration task should be blocked by all feature tasks and handled by the lead

### Team Size
- **2-4 teammates**: Efficient for most tasks
- **5-6 teammates**: Appropriate for multi-service builds
- **7+ teammates**: Rarely justified
