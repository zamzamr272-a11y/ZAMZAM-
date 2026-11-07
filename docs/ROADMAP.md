# Roadmap dan status implementasi

Status ini mengikuti source repository saat paket dibuat. `Selesai` berarti jalur dasar tersedia dalam kode dan dites pada lingkup yang ditulis; bukan berarti sistem telah lolos audit produksi.

## Fondasi dan akun

- [x] FastAPI modular monolith, SQLAlchemy, Alembic dan PostgreSQL Compose.
- [x] Username/password dengan Argon2id, recovery code sekali pakai, access/refresh session.
- [x] Logout/logout-all, daftar sesi dan profile code lookup.
- [x] Export JSON data dan penghapusan akun dengan password + phrase confirmation.
- [ ] Admin platform terpisah, audit log menyeluruh dan consent center lengkap.

## Keuangan

- [x] Akun/dompet, kategori, transaksi income/expense/transfer, edit dan void.
- [x] Transfer internal tidak masuk income/expense.
- [x] Dashboard, summary, kategori, cashflow, filter tanggal lokal, ekspor CSV.
- [x] Edit/archive akun, CRUD kategori/anggaran, savings goals.
- [x] Recurring rules + worker dengan idempotency/dedupe.
- [ ] Budget alert push notification dan scheduler pengingat yang dapat dikonfigurasi penuh.
- [ ] Multi-currency conversion/rate source dan refund workflow terperinci.

## OCR dan suara

- [x] Upload foto/PDF privat dengan validasi file, hash duplicate hint dan delete.
- [x] Tesseract OCR `ind+eng` untuk foto dan dua halaman PDF awal; draft field suggestions dan confidence umum.
- [x] Konfirmasi transaksi manual setelah draft diperiksa; tidak ada auto-save hasil OCR.
- [x] Android SpeechRecognizer `id-ID` dan web SpeechRecognition fallback; hasil dibuat menjadi draft.
- [ ] OCR async queue, retry/backoff, parser rekening spesifik dan confidence per-field.
- [ ] Audio streaming cloud/AI assistant. Input suara saat ini bergantung pada recognizer perangkat/browser.
- [ ] Malware scan, S3 private object storage, short-lived signed download URLs dan file encryption.

## Komunitas/chat

- [x] Create/list group, preview invite, join request, owner/admin approval.
- [x] Group settings, invite rotation, role management dasar, remove members.
- [x] Chat text, WebSocket one-time ticket, edit/delete, reaction, report, moderation status, block/unblock.
- [ ] Invite expiration, usage quotas, configurable auto-accept, private/public discovery.
- [ ] Reply, pin, full-text search, image/file/sticker uploads, push notifications, mute preferences.
- [ ] Redis pub/sub / shared presence untuk lebih dari satu API instance.
- [ ] Voice room dan video call via managed SFU/WebRTC.

## Investasi

- [x] Watchlist and investment thesis notes with scenario/risk journaling.
- [x] Tidak membuat quote pasar palsu; status data provider unavailable jika belum dikonfigurasi.
- [ ] Provider market/news berlisensi, timestamp/currency/freshness metadata dan kalender event.
- [ ] AI decision-support yang memisahkan fakta bersumber, asumsi dan interpretasi; human review.
- [ ] Legal review Indonesia sebelum rekomendasi personal berbayar atau fitur teregulasi.

## Release/operasi

- [x] Responsive PWA, dark/light design tokens, Android WebView APK source.
- [x] GitHub Actions quality tests, debug APK artifact, optional signed release workflow, GHCR image publish.
- [x] Docker Compose Postgres + API + recurring worker; API health gate.
- [ ] Android Gradle build + install verification on physical device.
- [ ] Hosting production, HTTPS domain, monitoring/alerts, encrypted DB/file backups and restore drill.
- [ ] Penetration test, OWASP ASVS/MASVS review, accessibility and load tests.
- [ ] UU PDP/PSE and investment regulatory review before public release.

## Release gate

Tidak boleh menandai production-ready sampai test di CI dan perangkat nyata lolos, migrasi PostgreSQL dan backup/restore teruji, storage aman, rate limits/distributed WebSocket direncanakan, domain/TLS/monitoring aktif, security assessment diselesaikan, dan legal/privacy review Indonesia tercatat.
