# QA report — NEXORA engineering package

**Verification snapshot:** 7 November 2026 (Asia/Makassar)  
**Project:** NEXORA source package  
**Scope:** automated backend tests, Python syntax compilation, frontend JavaScript parse, empty-database migrations, workflow/configuration static checks.

## Automated checks executed in this packaging environment

| Check | Result | Notes |
|---|---|---|
| Backend pytest | PASS — 14 tests | SQLite isolated test database |
| Python compile | PASS | `main.py`, recurring worker, Alembic env |
| Frontend JS syntax | PASS | `node --check frontend/assets/app.js` |
| Alembic migration chain | PASS | Applied to an empty SQLite test database |
| JavaScript / Python basic static parse | PASS | Does not replace browser or Android runtime tests |
| YAML parse (Compose + 4 workflows) | PASS | PyYAML parse; Docker Compose engine validation remains pending |
| Docker Compose runtime | Not run | Docker engine/Compose unavailable in this environment |
| Android Gradle build | Not run | Android SDK/Gradle are not installed in packaging environment; GitHub Actions workflow performs build |
| Chrome user session | Not run | Connected browser extension did not provide originating browser context |

## Tested API behaviors

1. Registration, login and one-time recovery code redemption.
2. Transaction CRUD and internal transfer exclusion from income/expense totals.
3. Finance data ownership isolation across users.
4. WITA date filtering for daily reports and transaction listing.
5. Group invitation preview/request/approval and membership restrictions.
6. One-use 60-second WebSocket tickets; bearer token is not sent in query URL.
7. Message edit/delete, emoji reaction, report, moderation state, block/unblock visibility.
8. Recurring transaction idempotency and automatic pause when linked account is archived.
9. OCR synthetic PNG end-to-end: upload validation, duplicate detection, Tesseract `ind+eng` field suggestions and confidence, no transaction before explicit confirmation, transaction created only after confirm.
10. Category and budget create/edit/delete rules, including preventing semantic kind changes after references exist.
11. JSON data export and account deletion invalidating prior access token.

The synthetic OCR integration test verifies the technical pipeline on controlled text; it does not guarantee reading quality across real bank statement photos/layouts. The test suite does not emulate a live Android SpeechRecognizer, WebRTC, market-data providers, browser interactions, or physical devices.

## Configuration checks performed

- Android app uses an HTTPS-like local asset origin through AndroidX `WebViewAssetLoader`; no universal `file://` access is enabled.
- Backend production configuration rejects wildcard CORS and weak/default JWT secret.
- `.env.example` includes Android asset origin and placeholder for the exact web/PWA origin.
- Android workflow produces a debug APK artifact and optionally a signed release APK if the owner supplies keystore secrets.
- Quality workflow runs pytest, Python compile, JavaScript parse and migration check.
- Container publish workflow pushes tagged backend image to GHCR.

## Not verified / blockers before public production

- GitHub account connection returned no visible repositories at packaging time; no workflow run or artifact is verified from the user's GitHub account.
- Android SDK/Gradle/device unavailable here; no real APK has been compiled or installed in this environment.
- Chrome extension could not read a browser tab from this conversation context; no actual user-browser visual QA was performed.
- Docker Engine not available; PostgreSQL Compose, Docker image, recurring worker concurrency and health check need CI/staging validation.
- OCR requires Tesseract Indonesian/English models and Poppler, supplied in Dockerfile; representative bank documents need manual accuracy review and privacy/retention test.
- Android microphone recognition depends on device speech service and user permission; device testing remains required.
- No external market data licensing/provider, SFU for voice/video, object storage, malware scan, Redis/pub-sub or admin notification service configured.
- No full ASVS/MASVS penetration test, accessibility test, load test, backup/restore drill, legal/privacy review or PSE/PDP assessment has been completed.

## QA conclusion

The repository is suitable as an **engineering preview / test deployment source**, with automated CI and APK packaging definitions. It must not be described as production-ready or as a fully completed implementation of every PRD acceptance criterion until the outstanding integrations, infrastructure tests, Android device test, security assessment and legal review are completed.
