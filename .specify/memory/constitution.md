# Project Constitution — WorkAgent Gateway

## Preamble
This gateway (nginx + One API + Pico Claw) runs on Render Free Tier.
It is a brownfield production system. Every deploy must be safe,
idempotent, and verifiable. These rules bind all spec, plan, and
implementation phases. No override without explicit constitution
amendment via /speckit.constitution.

---

## Rule 1: Idempotent Channel Creation
**Statement**: Groq channel MUST be REPLACED by ID, not CREATED new.
**Enforcement**: HARD — entrypoint.sh must resolve existing channels
  by name before POST or PUT; never POST without checking first.
**Bug Prevented**: 3× Groq channel duplication per deploy.
**Failure Mode**: One API returns status 200 but duplicates accumulate.
**Check**: `ls -d changes/archive/*Groq*` must show ≤1 entry.

## Rule 2: Config Purity Before Startup
**Statement**: `.security.yml` MUST be deleted before regeneration.
  Any existing file is stale and MUST NOT be reused.
**Enforcement**: HARD — `rm -f /data/.security.yml` in entrypoint.sh
  BEFORE the config generation loop.
**Bug Prevented**: modelperm- duplicate keys causing parse failure.
**Failure Mode**: Gateway fails to start; 502 on all routes.
**Check**: `grep modelperm- /data/.security.yml` MUST return 0 lines.

## Rule 3: Env Var Completeness
**Statement**: Every LLM provider referenced in entrypoint.sh MUST
  have its API key declared in render.yaml env vars with `sync: false`.
**Enforcement**: HARD — a CI gate (or pre-deploy checklist) MUST
  cross-reference entrypoint.sh for `$GROQ_API_KEY`-like vars and
  confirm they appear in render.yaml.
**Bug Prevented**: Deploy succeeds but gateway cannot reach LLM.
**Failure Mode**: All requests return 500; gateway logs show auth error.
**Check**: For each `$*_API_KEY` in entrypoint.sh, `grep "$var" render.yaml`.

## Rule 4: Gateway Model Reachability
**Statement**: Before gateway start, the configured `model_name`
  MUST be confirmed present in One API's `/v1/models` response.
**Enforcement**: HARD — entrypoint.sh must poll `/v1/models` and
  FAIL START if the model is absent. The launcher API's
  `/api/gateway/start` must NOT be called pre-verification.
**Bug Prevented**: Gateway starts with unreachable model, user gets
  silent failures on every message.
**Failure Mode**: WebSocket connects but all turns fail with "model
  not found" or 413.
**Check**: `gateway_start_allowed` status endpoint returns True.

## Rule 5: Token Quota Adequacy
**Statement**: Every API token used for `/v1/chat/completions` MUST
  have `unlimited_quota: true` in One API.
**Enforcement**: SOFT — documented requirement; verified by checklist.
**Bug Prevented**: Silent rate limiting after quota exhaustion.
**Failure Mode**: Users get "insufficient quota" mid-session.
**Check**: One API `/api/token/` shows `unlimited_quota: true` for
  token ID used in entrypoint.sh.

## Rule 6: One Model Mapping Per Direction
**Statement**: The `model_mapping` field in each One API channel
  MUST be a bijection — every incoming model name maps to exactly
  one outgoing model name. No wildcard `default` mapping without
  explicit enablement review.
**Enforcement**: HARD — verified by analyze gate. The mapping table
  must be reviewed as a section in every spec that touches channels.
**Bug Prevented**: Silent model fallback to wrong provider.
**Failure Mode**: Gateway sends `llama-3.3-70b-versatile` expecting
  Groq, gets routed to OpenRouter (zero credits).
**Check**: `model_mapping` JSON has no duplicate keys; values are in
  channel's `models` list.

## Rule 7: Proxy Route Completeness
**Statement**: Every internal service port (One API :3001, Launcher
  :18800, Gateway :18790) MUST have a corresponding nginx location
  block documented in the spec with its proxy_pass target, websocket
  support flag, and auth requirement.
**Enforcement**: HARD — spec completeness check. An undocumented route
  is an unrouteable service.
**Bug Prevented**: Adding a new service but forgetting the nginx
  route; WebSocket connection fails silently.
**Failure Mode**: Client connects to /pico/ws but gets 404.
**Check**: `grep -c proxy_pass nginx.conf` >= number of internal ports.

## Rule 8: Change Atomicity
**Statement**: Every `/speckit.implement` cycle MUST produce exactly
  one working state — code either passes all checklist items or is
  REVERTED. No partial deploys.
**Enforcement**: SOFT — enforced by PR review and checklist gate.
**Bug Prevented**: Half-baked deploy that disables the gateway.
**Failure Mode**: Deploy succeeds but gateway is STOPPED.
**Check**: After merge, `curl /api/gateway/status` returns `running`.

## Rule 9: Never Fabricate Experience
**Statement**: The CV adapter MUST NEVER add, modify, or extrapolate
  experience, dates, titles, companies, or certifications not present
  in the source CV (`cv/curriculum.md`). Only reordering and rewording
  of the summary are permitted.
**Enforcement**: HARD — spec-gates CI must verify that every spec
  referencing `cv_adapter` includes a "never fabricate" clause.
  Checklist item on every CV adapter PR.
**Bug Prevented**: LLM hallucinates experience in adapted CV →
  user submits fabricated CV → professional reputation damage.
**Failure Mode**: Adapted CV contains skills/dates the user never had.
**Check**: For each adapted CV file, `diff --ignore-all-space` against
  original shows only reorders and summary changes.

## Rule 10: CV is Source of Truth
**Statement**: The matcher MUST read experience solely from
  `cv/curriculum.md`. It MUST NOT infer, guess, or generate experience
  from LLM training data. Skills_matched MUST be traceable to explicit
  CV sections.
**Enforcement**: HARD — match output MUST include `skills_matched`
  labeled with the CV section they came from. Checklist item.
**Bug Prevented**: Matcher gives 90% score for a Rust job when CV has
  zero Rust experience, because LLM "assumes" transferable skills.
**Failure Mode**: User gets notified for offers they don't qualify for.
**Check**: Every `skills_matched` entry has a corresponding section in `cv/curriculum.md`.

## Rule 11: Skill Spec Completeness
**Statement**: Every Pico Claw skill or tool used in this project MUST
  have a corresponding spec file in `specs/skills/` before
  implementation begins. A skill is any capability the agent can invoke
  autonomously (scraper, matcher, adapter, channel).
**Enforcement**: HARD — CI gate checks that
  `specs/skills/*-<skill-name>.md` exists for every skill referenced in
  AGENTS.md, bootstrap files, or `config/`. Implementation PR without
  spec is auto-blocked.
**Bug Prevented**: Undocumented skills drift from intended behavior;
  new contributors (or future you) can't tell what a skill should do.
**Failure Mode**: Skill implemented but produces wrong output format;
  dependent skills break silently.
**Check**: `ls specs/skills/` matches all skill names in `ls skills/`.

## Rule 12: Pre-deploy Validation Gate
**Statement**: Before every push to main, the `devops_qa` preflight script
  MUST pass all checks. No commit that breaks Python syntax, YAML validity,
  spec coverage, constitution rules, or env var completeness may be pushed.
**Enforcement**: HARD — preflight runs locally before commit; CI gate checks
  spec coverage and constitution rules. If preflight fails, commit is blocked.
**Bug Prevented**: Deploying broken code that fails the Render build.
**Failure Mode**: Build fails on Render after 5+ minute wait; wasted
  time and quota.
**Check**: `python3 skills/devops_qa/scripts/preflight.py` exits with code 0.

---

## Appendix: Enforcement Levels
| Level | Meaning | Example |
|-------|---------|---------|
| HARD | Blocking — gate fails, deployment stops | modelperm- filter missing |
| SOFT | Warning — gate warns, CI passes | token quota not verified |

## Appendix: Scope
This constitution covers:

### Infrastructure Layer (`/`)
`entrypoint.sh`, `nginx.conf`, `render.yaml`, `supervisord.conf`,
`Dockerfile`, `.dockerignore`, `docker-compose.yml`, `README.md`,
`POST_DEPLOYMENT.md`

### Agent Layer (`specs/`)
- `specs/09-agent-overview.md` — Agent architecture + skill inventory
- `specs/10-skill-scrapers.md` — Portal scraping standards
- `specs/11-skill-matcher.md` — CV vs offer comparison
- `specs/12-skill-cv-adapter.md` — Tailored CV generation
- `specs/13-channel-telegram.md` — Bot notifications + commands
- `specs/14-provider-failover.md` — Multi-provider failover logic
- `specs/15-scheduler-database.md` — APScheduler + SQLite schema

### Agent Directories (future)
- `skills/` — Pico Claw skill implementations (one subdir per skill)
- `cv/` — `curriculum.md` (source of truth) + `adapted/` (generated CVs)
- `config/` — `search_params.yaml`, `schedule.yaml`
- `data/` — SQLite databases
