# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

```xml
<project>
 <name>AgentForge-OpenEMR</name>
 <description>Production-ready healthcare AI agent built on OpenEMR — domain-specific tools, eval framework, observability, and verification layer</description>
 <purpose>
  Gauntlet AI, G4 — Week 2 Assignment (AgentForge)
 </purpose>
 <docs>
  <readonly>
   @docs/assignment.md
   @docs/pre-search.md
  </readonly>
  <readwrite>
   <devlog>
    <file>docs/ai-dev-log.md</file>
    <purpose>Track MCP tools used</purpose>
   </devlog>
   <costanalysis>
    <file>docs/costs.md</file>
    <purpose>Track development and projected production costs</purpose>
   </costanalysis>
  </readwrite>
 </docs>
 <urls>
  <repo>https://github.com/menasheh/openemr</repo>
  <dev>http://localhost:8300</dev>
  <dev-ssl>https://localhost:9300</dev-ssl>
  <phpmyadmin>http://localhost:8310</phpmyadmin>
  <mysql-port>8320</mysql-port>
 </urls>
 <stack>
  <frontend>jQuery, Bootstrap 4, Gulp, SCSS (legacy — OpenEMR's existing UI)</frontend>
  <backend>PHP 8.2+, Laminas MVC, Symfony components, REST API, FHIR R4, OAuth2</backend>
  <database>MySQL/MariaDB 11.8 (via Docker), phpMyAdmin at :8310</database>
  <hosting>Docker (dev), TBD for production deploy</hosting>
  <dev-tools>Claude Code, Cursor, Docker Compose, Composer, npm/gulp</dev-tools>
  <note>OpenEMR is a massive existing codebase. Our agent work lives alongside it — new modules, not rewrites. Read @composer.json and @package.json for dependency details.</note>
 </stack>
</project>

<workflow>
 <understand>
  Charlie is always neurodivergent and sometimes quite ethereal. You need to respect his boundaries and be patient with him. Reflect the parts of his speech which make sense, and wait until he communicates clearly. You may nudge him for clarity before proceeding. Don't assume anything about his intention.
 </understand>
 <plan/>
 <test>
  Use E2E tests for features. Keep code coverage 100% for feature code.
  OpenEMR has existing test infrastructure: PHPUnit (phpunit.xml), Jest (jest.config.js), Playwright.
  Run isolated tests with: composer phpunit-isolated
 </test>
 <implement/>
</workflow>

<culture>
 We do our best.
 We do not assume.
 We honor our spoken word.
 We take nothing personally.

 We deeply honor the user's actual intention.
 When we don't understand it, we hold space for the idea that it exists and is valid.
 Then, we ask.
</culture>
```

## Build & Development Commands

```bash
# Development environment (from repo root)
cd docker/development-easy && docker compose up    # Start dev environment
cd docker/development-easy && docker compose down   # Stop (keep volumes)
cd docker/development-easy && docker compose down -v # Stop and wipe volumes

# Build frontend assets (requires Node.js 22+)
npm install
npm run build          # Production build (gulp)
npm run dev            # Dev build + watch

# PHP dependencies
composer install --no-dev
composer dump-autoload -o

# Code quality (host — higher memory limits than Docker devtools)
composer phpstan       # Static analysis (level 10, strictest)
composer phpcs         # Code style check (PSR-12)
composer phpcbf        # Code style auto-fix
composer rector-check  # Code modernization dry-run
composer rector-fix    # Apply rector changes
npm run lint:js        # ESLint
npm run stylelint      # CSS/SCSS linting

# Tests
composer phpunit-isolated                    # Isolated tests (no DB/Docker needed)
composer update-twig-fixtures                # Regenerate Twig test fixtures after template changes
npm run test:js                              # Jest JS unit tests
npm run test:js-coverage                     # Jest with coverage

# Docker devtools (inside container, requires running Docker environment)
docker compose exec openemr /root/devtools unit-test          # PHPUnit with DB
docker compose exec openemr /root/devtools api-test           # API tests
docker compose exec openemr /root/devtools e2e-test           # E2E (view at localhost:7900, pw: openemr123)
docker compose exec openemr /root/devtools services-test      # Services tests
docker compose exec openemr /root/devtools clean-sweep-tests  # All tests in one command
docker compose exec openemr /root/devtools clean-sweep        # All checks + all tests
docker compose exec openemr /root/devtools dev-reset-install-demodata  # Reset with demo data

# Run a single PHPUnit test file
./vendor/bin/phpunit -c phpunit-isolated.xml --filter TestClassName
./vendor/bin/phpunit -c phpunit-isolated.xml tests/Tests/Isolated/path/to/TestFile.php

# Login credentials
# OpenEMR: http://localhost:8300 — admin / pass
# phpMyAdmin: http://localhost:8310 — openemr / openemr
# MySQL direct: port 8320 — openemr / openemr
# Swagger API docs: https://localhost:9300/swagger
```

## Testing

Two PHPUnit configurations:
- `phpunit-isolated.xml` — Tests in `tests/Tests/Isolated/` and select `tests/Tests/Unit/` dirs. No DB needed, runs on host.
- `phpunit.xml` — Full suite (unit, e2e, api, services, fixtures, validators, controllers, common). Requires Docker DB.

Test suites in `phpunit.xml`: `unit`, `e2e`, `api`, `services`, `fixtures`, `validators`, `controllers`, `common`, `ECQM`, `certification`, `email`.

PHPStan runs at **level 10** (strictest). Uses per-identifier baselines in `.phpstan/baseline/`. Config: `phpstan.neon.dist`.

## Commits

Conventional Commits required (enforced by `ramsey/conventional-commits`). Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. Scopes are optional, kebab-case.

CI skip trick for WIP: `git commit --trailer "Skip-Slow-Tests: true" -m "fix: work in progress"` — must remove before merge.

## Architecture

OpenEMR is a monolithic PHP application. PSR-4 autoload: `OpenEMR\` → `src/`.

### REST API Dispatch Flow

1. **Entry**: `apis/dispatch.php` → creates `HttpRestRequest` → `ApiApplication::run()`
2. **Listener Pipeline** (Symfony EventDispatcher, in order): ExceptionHandler → Telemetry → ApiResponseLogger → SessionCleanup → SiteSetup (DB/globals init) → CORS → OAuth2Authorization → Authorization → RoutesExtension (route matching + controller invocation) → ViewRenderer
3. **Route files**: `apis/routes/_rest_routes_standard.inc.php` (core REST), `_rest_routes_fhir_r4_us_core_3_1_0.inc.php` (FHIR R4), `_rest_routes_portal.inc.php` (patient portal)
4. **Controllers**: `src/RestControllers/*RestController` — methods like `post()`, `put()`, `getOne()`, `getAll()` with OpenAPI annotations

### Services Layer

- **Base class**: `BaseService` (constructor takes table name, auto-introspects fields via `QueryUtils::listTableFields()`)
- Built-in: event dispatcher access, session, search via `FhirSearchWhereClauseBuilder`, CRUD helpers
- Services emit domain events (e.g., `PatientCreatedEvent`, `BeforePatientUpdatedEvent`)
- Key services: `PatientService`, `AppointmentService`, `EncounterService`, `DrugService`, etc.

### Events System

Symfony `EventDispatcher` — accessed via `$service->getEventDispatcher()` or `OEGlobalsBag::getInstance()->getKernel()->getEventDispatcher()`. 80+ event classes in `src/Events/` covering: domain CRUD (Patient, Appointment, Encounter, User), API extension (`RestApiResourceServiceEvent`), lifecycle (`GlobalsInitializedEvent`, `ModuleLoadEvents`), UI (`Card`, `StyleFilterEvent`).

### Module System

- **Custom modules** (modern): `interface/modules/custom_modules/` — bootstrap file `openemr.bootstrap.php` receives EventDispatcher for hooking into the system
- **Laminas modules** (legacy): `interface/modules/zend_modules/` — full MVC
- Loaded by `ModulesApplication` — emits `MODULES_LOADED` event after all modules bootstrap

### FHIR

- Auto-generated PHP objects in `src/FHIR/R4/` (via PHPFHIRAutoloader)
- FHIR service classes: `src/Services/FHIR/Fhir{Resource}Service`
- Metadata endpoint: `/fhir/metadata` (CapabilityStatement)

### Globals

`library/globals.inc.php` — sets language, currency, global constants. Emits `GlobalsInitializedEvent`. Global state via `OEGlobalsBag::getInstance()`.

### Key Directories

- `src/Services/` — Business logic, primary integration point for agent tools
- `src/RestControllers/` — REST API controllers
- `src/FHIR/` — FHIR R4 resource definitions
- `src/Validators/` — Input validation
- `src/Events/` — Event classes
- `interface/` — Frontend views (PHP templates, JS, CSS)
- `library/` — Legacy shared PHP functions (globals, sanitization, formatting)
- `apis/` — API routing and dispatch
- `docker/development-easy/` — Dev Docker (MariaDB, OpenEMR, Selenium, phpMyAdmin, CouchDB, OpenLDAP, Mailpit)

## AI-Generated Code Policy

Per `.github/copilot-instructions.md`: clearly mark AI-generated code with comments at the beginning and end of code blocks, and at end-of-line for single lines.

## AgentForge Project Context

This fork adds a healthcare AI agent to OpenEMR. Our work lives alongside the existing codebase as new modules, not rewrites. Key integration points:
- New service classes extending `BaseService` in `src/Services/`
- New REST endpoints via route files in `apis/routes/`
- Custom modules in `interface/modules/custom_modules/` for complex agent logic
- Event dispatcher hooks for extending existing workflows
- See `docs/assignment.md` for full requirements and `docs/pre-search.md` for architecture decisions
