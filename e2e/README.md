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
| #18 | Real execution / reports | Blocked: missing runtimes/ assets. runtime_acceptance.py deliberately fails on missing Python worker. Java/SQL, wrong answer/error/cancel/metrics remain. |
| #19 | Learn Languages | test_08; all three language cards, code examples, reference URLs and Learning Way navigation. |
| #20 | Learning Way notes | test_09; all three paths, notes, practice gating/five exercises, SQL notes persist in a new context. |
| #21 | Completed Learning Way topic | Blocked by #18. Notes read is not the same as passing all five exercises or a completed topic checkmark. |
| #22 | Library | test_10; search, empty result, language/status filters. Lesson/practice tabs. |
| #23 | Lesson progress | test_11; reader, complete, 25% of four fixture lessons, fresh login and another account's zero progress. |
| #24 | Bookmarks | test_12; library save, saved list, reload, unsave. Reader save/remove and same-browser other-account isolation. |
| #25 | Workspace | test_13; sidebar, project inspiration and progress. Announcements and Leaderboards are static labels; not functional destinations. |
| #26 | Unavailable integrations | test_14; disabled Google/GitHub, recovery reports unsupported rather than false success. This does not test working OAuth/email. |

All feature issues stay open until their complete criteria have passing evidence. A passing core suite is not a claim of all-feature coverage. First-run execution results are available in Actions; do not infer a pass from the presence of tests.

## Missing runtime acceptance

```sh
WECODE_DISPOSABLE_E2E=yes python3 -m unittest e2e.runtime_acceptance -v
```

This explicit gate must fail while the captured workers are missing. It is excluded from the core suite by its filename and is not counted as passing or skipped coverage. The default workflow covers the core scenarios; full assignment acceptance (#5) remains open until #18/#21 and the remaining scenarios above are implemented and pass. No fake worker or canned execution result is used.

References: [Playwright Python installation](https://playwright.dev/python/docs/intro), [CI setup](https://playwright.dev/python/docs/ci).

CI runs three independent groups on separate ephemeral stacks. This keeps each run below the normal authentication-attempt limit without weakening that limit. Local discovery runs all scenarios serially and may encounter the normal rate limit if executed rapidly.
