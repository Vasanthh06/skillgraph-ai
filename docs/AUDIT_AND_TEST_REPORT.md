# Audit, remediation and test report

## Delivery status
**Substantial working revision; requested full production scope is NOT complete.** No claim of deployment, live Neon verification, real email delivery, legal certification or complete vulnerability elimination. Read the release blockers below before using real student data.

## Acquisition and preservation
Authorized Google Drive retrieval of `Skillgraph-ai.zip` (1,370,070 bytes). ZIP integrity passed; 165 original file entries inventoried. Original archive and extracted source remain outside the application working directory, unchanged. `preservation/` in the delivery contains original versions of every modified original file; unchanged originals remain in their original relative paths. `CHANGELOG.json`, original inventory and integrity hashes are generated during packaging. No original file is deleted. Generated dependencies/caches and synthetic local database are excluded. Backups are outside backend/frontend import paths and are not a second application.

## Initial architecture
React 18/TypeScript/Vite/Tailwind/React Query frontend, FastAPI/SQLAlchemy/Pydantic backend, PostgreSQL production driver and SQLite development option. Existing JWT/bcrypt login, per-user scope repository, curated roles/skills/prerequisites, resume analysis, assessments, deterministic gap/roadmap/recommendations, projects, jobs, interviews, recall and calibration. Separate ML experiments preserved, not represented as validated deployed inference. Existing design and all pages retained. Baseline: 209 tests passed and build passed.

## Implemented remediation and verification
|Issue|Severity / reproduction|Change and retest|
|---|---|---|
|Persisted bearer secret|High: original browser `localStorage.sg_token` survives reload|Web login now opts into HttpOnly SameSite cookie; browser stores only a session sentinel in memory. Existing bearer API response remains compatible. Browser registration/login/reload/logout and cookie/CSRF tests executed|
|Forwarded-header spoofing|High: original limiter changes bucket with arbitrary X-Forwarded-For|Ignore raw forwarding headers; use ASGI client. `/api` alias shares bucket. Updated regression expects spoofed client still blocked. Production trusted-edge/shared limiting still needed|
|Destructive duplicate migration|High: duplicate assessments previously merged with DELETE|Stop with explicit operator instruction before merge; preservation test verifies both rows survive. Existing unique-index upgrade remains for clean data|
|Outdated dependencies|High initial scan findings|Updated detected vulnerable direct dependencies plus FastAPI's resolved dependencies. Python audit reports no findings for declared resolved requirement set. npm has two moderate React Router findings remaining; JSON evidence retained|
|Upload XML expansion|Medium: malicious DOCX XML entities / oversized document.xml|Use defusedxml; bound expanded document.xml to 2 MB; reject unsafe/invalid XML. Entity-injection regression executed. PDF parsing still needs resource isolation for high-risk deployment|
|Password limitations|Medium: short composition policy and bcrypt byte bound|New normal-mode passwords: 15–128 Unicode characters, spaces allowed, small common-password denylist; Argon2id hashes. Old bcrypt hashes remain verifiable. Full compromised-password corpus not integrated|
|Account lifecycle missing|High functional/security gap|Additive metadata/token/delivery tables. 20-minute random hashed token, conditional one-use consume, session cutoff on reset, verified-email gate for roadmap email. Replay, expired, malformed, invalid tokens and old-session rejection tests executed|
|Admin permissions absent|High feature gap|Explicit bootstrap command refuses existing email; protected read-only paginated users endpoint returns 403 for normal users; UI available at /admin. Not a complete audit/event management system|
|Potential sensitive exception logging|Medium|Log exception type and route rather than SQL exception traceback/parameters; no secret provider response bodies logged|
|Skill graph mobile overflow|Medium: browser measured page overflow at 320–768 px|Min-width-zero grid card fix confines wide graph to its internal scroll region. Rerun 48 route/viewport combinations: zero document overflow|
|Reduced motion / focus / small input UX|Low|Visible focus, reduced-motion fallback retained/enforced, mobile form font sizing; browser checks used reduced motion. No independent WCAG audit|

## Test evidence
|Category|Actual result|Evidence|
|---|---|---|
|Baseline automated suite|209 passed|baseline-tests.txt|
|Final automated suite|223 passed, 3 warnings|tests-final.txt|
|TypeScript typecheck|Pass|typecheck-final.txt|
|Production frontend build|Pass|build-final.txt|
|Python dependency audit|No reported findings in resolved requirements|python-audit-after.json|
|npm audit, including production-only|2 moderate findings remain|npm-audit-final.json, npm-production-audit.json|
|Bandit static scan|6 residual findings; not a clean scanner certification|bandit-final.json|
|Chromium smoke|3 journey checks completed|browser-results.json, browser-run-final.txt|
|Responsive|48 route/viewport measurements, zero horizontal document overflow|browser-results.json|
|Physical devices / Safari / Firefox|Not run|No claim|
|Live Neon/PostgreSQL|Not configured / not run|SQLite only|
|Email provider|Mocked tests; real delivery not configured|test_account_security.py|
|Public deployment / Docker image execution|Not run|Prepared config only|
|Formatting / dedicated frontend lint / accessibility scanner / load test|Not run|Not represented as passed|

Browser evidence: actual headless Chromium, Linux sandbox, widths 320, 375, 390, 430, 768, 1024, 1280, 1440; routes landing, login, register, dashboard, roadmap, skill graph. Because the session is signed in for part of the viewport loop, login/register routes can redirect to dashboard; screenshots of initial registration and signed-out recovery are separate. Viewport checks establish overflow only, not full keyboard/touch usability. Three journey checks: UI adult registration; authenticated API role/assessment/generation/progress with browser reload; UI sign-in and reload. Other screenshots show actual rendered pages, not full interaction coverage. `/admin` screenshot is the normal user's denial state, NOT a fabricated authorized dashboard.

Tests updated for intentional contracts, not to hide faults: bcrypt prefix -> Argon2id, arbitrary forwarded-client allowance -> spoof rejection, token-only Web Storage -> no Web Storage, multi-segment route parser and migration deletion -> explicit stop retaining records. Original tests are backed up. Initial failed iterations are retained as redacted development logs; only latest successful logs describe final status. Legacy DEMO_MODE fixtures preserve old password policy; a new normal-mode test exercises adult/consent policy and passphrases.

## Static scanner triage
Remaining Bandit findings: placeholder-secret constant (startup refuses it in normal mode); migration string-built SQL uses internal fixed table/column/index identifiers, never user identifiers; optional embedding fallback catches import/initialization errors; YouTube URL opens use fixed HTTPS googleapis URLs and encoded query parameters. These are reviewed findings, not proof of absence of injection/SSRF. Do not mark them suppressed without an independent review. DOCX XML findings were fixed rather than dismissed.

## Scope gaps / release blockers
1. Password-reset requests have generic text but synchronous known-account email dispatch can leak timing. Queue-based dispatch/uniform handling and distributed abuse control remain required. No confirmation email after reset.
2. Email outbox crash recovery, webhook/bounce validation and true delivery confirmation are absent. Successful retries with same ID are deduplicated; pending/ambiguous results need operator review. Frontend new page visits can generate a new request ID; deliberate repeated sends remain rate-limited, not globally forbidden.
3. Registration duplicate-email 409 remains an account-enumeration signal inherited from original API; do not claim full enumeration resistance. Concurrent registration can still return generic DB error on uniqueness race. Signup and consent metadata creation currently span commits, not one atomic service transaction.
4. Admin view is read-only account listing/search/verification/goal, not per-user progress/history/security-event exploration. No sensitive admin operations or audit event pipeline added. Account search currently uses per-user profile/security loads and needs bulk loading for scale.
5. No automated account/data deletion, completed retention schedule, operator/grievance contact, privacy preferences or independently approved legal text. Do not publicly launch draft legal pages.
6. No full literature/competitor systematic review, human usefulness evaluation, performance benchmark, formal graph-quality audit over all custom catalogs, trained ML validation or employment-effectiveness claim.
7. SQLite test transactions do not establish PostgreSQL correctness under races. Neon pooled TLS and production migrations must be tested against a separate branch.
8. Production Docker/nginx configuration is not executed here. Original development compose still has local-only sample DB credentials and Redis unused by auth limiter; do not deploy it as hardened production config.
9. CORS-cookie behavior assumes same-origin web deployment. Login API still returns bearer tokens for compatibility; API consumers must protect them. XSS can still act as a user even when HttpOnly prevents reading the cookie. Full CSP and separate bearer-token deprecation were not implemented.
10. Process-local limiter has no shared store or global key eviction; reverse proxy default shares bucket. Apply edge limits, worker budgets and trusted proxy design. Resume parsing remains in-process and should move to bounded workers for untrusted public workloads.
11. Draft age attestation prevents ineligible normal-mode signup, but does not retroactively validate existing users or establish verifiable age. Existing accounts remain preserved. Minors are unsupported.
12. No production secrets were supplied. Placeholder/default development values are not secrets suitable for deployment. Rotate any previously exposed credentials if the student discovers them in their own history; deleting the current source is insufficient.

## Completion matrix
Acquisition/preservation: complete with machine comparison. Baseline and prioritized remediation: executed. Existing features retained: regression suite passes. Neon: prepared, not live. Email: adapter and mocks, not live. Security: improved, residual issues above. UI: targeted improvement, not wholesale redesign. Responsive: Chromium overflow checked, other compatibility partial. Academic/legal: grounded draft and honest plan, not final legal opinion. Deployment: prepared, not deployed. Complete user-requested production lifecycle: not complete.
