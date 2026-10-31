# Initial audit — 1 November 2026

Source obtained through authorized Drive connector; 165 ZIP entries; integrity test successful. Original archive and extracted tree preserved outside working source. Baseline: 209 tests passed; TypeScript/Vite build passed. See captured logs.

## Architecture and scope
React 18.3.1, TypeScript 5.6, Vite 5.4, FastAPI 0.115, SQLAlchemy 2, Pydantic 2; PostgreSQL driver psycopg2, SQLite local option. JWT/bcrypt accounts; scoped ORM repositories. Curated skills/roles, assessment, resume parsing, dependency graph, gap/readiness scoring, progress, learning, jobs, projects, interviews, calibration and recall. Main analysis is deterministic; optional semantic helpers and separate training experiments are not evidence of a trained production recommender. Existing coherent visual identity should be retained.

## Prioritized findings
|Severity|File/module|Root cause and impact|Correction|Verification|
|---|---|---|---|---|
|High|frontend/src/services/api.ts|Bearer secret in localStorage increases persistence of XSS theft|HttpOnly cookie for web, preserve bearer API compatibility|Cookie, reload, logout tests|
|High|backend/app/utils/rate_limit.py|Arbitrary X-Forwarded-For accepted; spoofing bypass|Use trusted ASGI client address, normalize route aliases|Spoofed-header regression|
|High|backend/app/core/migrations.py|Duplicate migration DELETE removes original rows without approval|Stop with operator guidance instead of deduplication|Duplicate migration rollback test|
|High|Dependencies|Scanner-reported vulnerable packages; see JSON logs; applicability needs review|Compatible updates and repeat build/tests/audits|Scanner logs|
|High|Account lifecycle|No reset/verification service or server-side admin permissions|Hashed expiring one-use tokens, session epoch and protected admin API|Integration tests|
|Medium|schemas/auth.py|8-character composition policy, bcrypt 72-byte limit|Argon2id for new hashes, preserve bcrypt verification, passphrases|Password compatibility tests|
|Medium|main.py|Exception logging may print SQL parameters/PII|Log error type/path only|Code inspection|
|Medium|Operations|No configured Neon/email/live deployment|Prepare environment, connectivity check, controlled provisioning|External verification explicitly pending|
|Medium|Privacy|No age gate or published privacy/terms workflow|Adult-only eligibility and versioned consent; draft legal documents|Registration tests; legal review pending|
|Informational|Evaluation|Passing unit/API tests is not proof of efficacy or physical-device support|Reproducible research and device plan, real browser evidence where possible|Documentation|

## Plan
1. Preserve and baseline (done).
2. Essential security/data-preservation changes; additive account tables and lifecycle service.
3. Frontend lifecycle controls, restrained responsive/accessibility refinements.
4. Retest existing and added tests, build, dependency scan, browser checks where available.
5. Document actual status, archive and compare inventory. No production database or third-party destructive testing.

Not a comprehensive vulnerability-free certification. Literature, legal applicability, live services and physical devices require separate evidence. Full requested scope is larger than baseline build verification; unresolved items must remain explicit.
