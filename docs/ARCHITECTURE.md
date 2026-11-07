# Architecture

## High level

```text
Android WebView + packaged PWA ───┐
                                  ├── HTTPS REST ── FastAPI modular monolith ── PostgreSQL
Browser / installable PWA ────────┘                         │
                                                           ├── private persistent document volume
                                                           ├── local Tesseract OCR execution
                                                           ├── recurring transaction worker
                                                           └── group WebSocket (single API instance)
```

The first release uses a modular monolith to keep deployment and operations tractable. Domain boundaries are auth/profile, finance/reports, receipts/OCR, groups/chat, investment journal and support. Frontend is a responsive PWA using HTML/CSS/JavaScript. Android hosts a packaged copy of the same frontend in WebView.

## Android local asset origin

Android loads assets through AndroidX `WebViewAssetLoader` using `https://appassets.androidplatform.net/assets/...`, not `file://`. This uses a normal web-like origin compatible with the same-origin policy. `allowFileAccess` stays disabled; content URI access is enabled only for the system document picker so a user-selected upload can be read. Android origin must be explicitly listed in backend `CORS_ORIGINS` as `https://appassets.androidplatform.net`. External HTTPS links are handed to the system browser. Debug cleartext is opt-in; production mixed content is rejected.

AndroidX WebKit 1.17.1 is pinned from the stable release catalog (October 2026). Reference: [AndroidX WebKit release notes](https://developer.android.com/jetpack/androidx/releases/webkit) and [WebViewAssetLoader API](https://developer.android.com/reference/androidx/webkit/WebViewAssetLoader).

## Data integrity and ownership

- Finance records include `user_id`; endpoint reads and writes verify ownership.
- Transaction kind is `income`, `expense`, or `transfer`. Transfer uses two distinct accounts owned by one user and no income/expense category.
- Reports include only confirmed transactions; transaction delete is a soft void.
- Amounts use SQL `NUMERIC(18,2)` and JSON serialization uses decimal strings.
- Timestamps persist in UTC; reports filter/bucket in `APP_TIMEZONE` (default `Asia/Makassar`).
- Category semantic kind is protected from change after transactions, budgets, or recurring rules refer to it.
- Archived accounts are excluded from new transaction/recurrence creation; active recurrence rules using an archived account are paused.
- Receipt file bytes are private and not mounted as public frontend assets; owner checks gate read/download/delete.
- Group history and WebSocket ticket minting require current membership. Join requests require owner/admin approval.

## Authentication/session

- Password hashing with Argon2id.
- Recovery code SHA-256 hash stored server-side; raw value shown once.
- Short-lived HMAC-SHA256 access JWT and opaque refresh token hash with rotation.
- Current-session logout and logout-all revoke sessions; account deletion verifies password and explicit phrase.
- WebSocket tickets are random, group-scoped, hashed at rest, single-use, and expire after 60 seconds. The primary bearer token is never placed in a WebSocket URL.

## OCR and recurring jobs

- File upload validates extension, MIME, signature and size; SHA-256 fingerprint is used for duplicate hints.
- OCR uses Tesseract `ind+eng`; PDFs use Poppler for a maximum of two first pages. The parser emits candidate date, amount, type and description. User review is mandatory; no transaction is persisted before confirmation.
- OCR currently executes synchronously in API request and has no external queue/retry scheduler. For large scale, move to worker queue.
- A separate recurring worker polls due rules; the unique rule/date execution row protects idempotency. Docker Compose starts it only after API health passes so DB migrations are applied.

## Current deployment constraints

- WebSocket broadcast hub is process-local; run a single API instance until shared pub/sub is added.
- Authentication throttling is process-local; multi-instance deployment requires Redis or gateway rate limit.
- Uploaded files use a private persistent filesystem. Before public production, add encrypted object storage, short-lived signed downloads, file scanning, retention lifecycle and an incident process.
- Frontend bearer/refresh tokens currently use `sessionStorage`; XSS assessment is required and HTTP-only same-site cookie architecture should be evaluated.
- Database backups do not include document volume; back up both together and test restoration.
- Market-data provider and WebRTC SFU are not configured. The app must report these unavailable rather than showing fabricated data.
