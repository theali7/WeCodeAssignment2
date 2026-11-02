# Playwright E2E inventory

The core suite drives real Chromium against the application Docker image and PostgreSQL. Authentication, profile writes and progress are not mocked. Each test has an isolated browser context and unique synthetic account. Cross-origin browser requests are blocked and fail the test. Tests retain screenshots, visible page text, traces and Compose logs as `playwright-evidence-0/1/2` Actions artifacts for seven days.

## Run safely

Use a separate disposable checkout/Compose project, not your everyday account database. The CI workflow creates its own runner, database, fixture lessons and random secrets, and removes that runner's database volume afterwards. Tests create synthetic accounts which remain until the disposable volume is removed. `seed.py` requires explicit opt-in and is not copied into the application image.

```sh
python3 -m pip install -r e2e/requirements.txt
python3 -m playwright install chromium
# Start and seed a disposable stack as in .github/workflows/e2e.yml.
WECODE_DISPOSABLE_E2E=yes python3 -m unittest discover -s e2e -p 'test_*.py' -v
```

The default URL is http://localhost:8080. Only localhost, 127.0.0.1 or the Compose hostname `web` is accepted. A fresh browser login is used for database-persistence checks, rather than trusting localStorage after refresh.

## Feature mapping

| Issue | Feature | Automated scenario / remaining work |
| --- | --- | --- |
| #11 | Landing / responsive menu | test_01; desktop anchors and mobile menu. Dialog Escape/close and focus return. |
| #12 | Signup | test_02; required fields, malformed email, short password, real signup, duplicate account. |
| #13 | Sessions | test_03; incorrect password, login, refresh, logout, fresh context. |
| #14 | Preferences | test_04; Java/Python/SQL, experience and display name persist in a fresh context. |
| #15 | Problem catalogue | test_05; 108 rows, search/empty/reset, three languages, difficulty/topic/title sorting. |
| #16 | Problem detail | test_06; next/previous/list and keyboard splitter. Examples, hint and both splitters. |
| #17 | Editor drafts | test_07; Python edit/reopen/reload; Java/SQL edit/reopen. |
| #18 | Real execution / reports | runtime_acceptance.py: all three engines, Run/Submit, accepted/wrong/error results, metrics and Python stop/restart. |
| #19 | Learn Languages | test_08; all three language cards, code examples, reference URLs and Learning Way navigation. |
| #20 | Learning Way notes | test_09; all three paths, notes, practice gating/five exercises, SQL notes persist in a new context. |
| #21 | Completed Learning Way topic | runtime_acceptance.py: first topic in each language, five real accepted exercises, next topic and completed status after a fresh login. |
| #22 | Library | test_10; search, empty result, language/status filters. Lesson/practice tabs. |
| #23 | Lesson progress | test_11; reader, complete, 25% of four fixture lessons, fresh login and another account's zero progress. |
| #24 | Bookmarks | test_12; library save, saved list, reload, unsave. Reader save/remove and same-browser other-account isolation. |
| #25 | Workspace | test_13; sidebar, project inspiration and progress. Announcements and Leaderboards are static labels; not functional destinations. |
| #26 | Unavailable integrations | test_14; disabled Google/GitHub, recovery reports unsupported rather than false success. This does not test working OAuth/email. |

Feature issues close only after passing Actions evidence. A passing core suite alone is not proof of real execution/topic completion; the separate six-scenario suite must also pass.

## Runtime and topic acceptance

```sh
WECODE_DISPOSABLE_E2E=yes python3 -m unittest e2e.runtime_acceptance -v
```

The six additional scenarios run in CI group 0: real Python/Java/SQL Run/Submit, accepted/wrong/error outcomes, reports/metrics and Python cancellation/restart; then five actual accepted exercises for the first topic in each language and completed-topic persistence in a new browser context. No worker results or progress responses are mocked. The 14 core scenarios still run separately. Acceptance is based on the actual Actions result, not merely the presence of test code.

CI runs three independent groups on separate ephemeral stacks, keeping normal authentication limits. Local serial runs may encounter normal rate limits if repeated quickly. Runtime provenance and reproducible download checksums are recorded in scripts/runtime-manifest.json and DOCKER_SETUP.md.
