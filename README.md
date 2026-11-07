# NEXORA

**NEXORA** adalah aplikasi mobile-first untuk pencatatan keuangan pribadi, jurnal/decision-support investasi, dan komunitas. UI dark/light dibangun dari design system original yang mengadaptasi pola visual dari tujuh screenshot referensi pengguna (KPI cards, panel bertingkat, tabel terstruktur, navy/charcoal, teal dan amber), tanpa menyalin identitas merek pada screenshot.

> **Status paket:** source lengkap untuk engineering preview, backend FastAPI + PostgreSQL, PWA, Android WebView shell, migrasi, dokumentasi dan GitHub Actions. Paket belum berarti layanan production yang sudah di-host, APK yang sudah dibuild, atau audit keamanan/hukum yang telah lulus. GitHub Actions membangun APK setelah source diunggah ke repo yang punya izin Actions.

## Isi repository

```text
NEXORA/
├── backend/                  # FastAPI, SQLAlchemy, Alembic, tests, recurring worker
├── frontend/                 # Responsive PWA / UI Bahasa Indonesia
├── android/                  # Android Java WebView wrapper + voice bridge
├── .github/workflows/        # Quality checks, APK build, GHCR image publish
├── reference-images/         # 7 screenshot referensi dari pengguna
├── docs/                     # API, arsitektur, QA, Android, roadmap, PRD & prompt
├── scripts/                  # PostgreSQL backup/restore helpers
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Modul yang sudah diimplementasikan

### Akun dan keamanan dasar
- Registrasi username/password; password Argon2id; username dinormalisasi dan unik.
- Recovery code sekali pakai; raw code hanya ditampilkan saat pembuatan/pemulihan.
- Access token singkat, refresh token rotation, logout, logout semua sesi, daftar sesi.
- Profile code publik untuk pencarian profil; bukan token login/akses.
- Penghapusan akun dengan verifikasi password dan frasa konfirmasi; ekspor JSON data akun.
- Rate limit autentikasi per proses dan kontrol ownership pada resource.

### Keuangan
- CRUD transaksi pemasukan, pengeluaran, dan transfer antar-akun.
- Transfer tidak dihitung sebagai income/expense; transaksi void dikeluarkan dari laporan.
- Akun/dompet, edit nama, arsip/restore; kategori tambah/edit/hapus; kategori yang masih dipakai tidak dapat dihapus.
- Anggaran kategori dengan periode dan ambang peringatan; tujuan tabungan; transaksi berulang dengan worker idempoten.
- Dashboard, ringkasan, grafik arus kas, breakdown kategori, filter tanggal berbasis `Asia/Makassar`, ekspor CSV dan JSON.
- Foto/PDF: validasi tipe/signature/ukuran, hash duplikasi, OCR Tesseract lokal, saran tanggal/nominal/jenis/deskripsi dan confidence umum; seluruh hasil menjadi draft yang harus diperiksa dan dikonfirmasi pengguna.

### Investasi dan komunitas
- Watchlist dan jurnal tesis investasi dengan horizon, risiko, skenario dan catatan.
- Harga/berita pasar nyata tidak ditampilkan tanpa provider berlisensi; tidak ada order/trading atau janji return.
- Grup, invite code, preview, permintaan join dan persetujuan owner/admin.
- Chat teks real-time single-instance, edit/hapus pesan, emoji reaction, report/moderation, block/unblock.
- WebSocket ticket grup sekali pakai, di-hash di database dan kedaluwarsa setelah 60 detik.

### UX dan platform
- Dark/light theme, dashboard responsif, bottom navigation mobile maksimal lima item, PWA shell.
- Android WebView dengan WebViewAssetLoader HTTPS local origin, file picker JPG/PNG/PDF, speech recognizer Android dengan izin mikrofon dan konfirmasi draft.
- Pusat tiket bantuan internal dan tautan WhatsApp sesuai PRD.

## Fitur yang belum tersedia / dibatasi secara jujur

- Voice/video room WebRTC: belum aktif karena membutuhkan SFU/provider, token provider, moderasi, pengujian jaringan dan anggaran.
- Harga aset/berita real-time dan kalender peristiwa: belum ada provider data berlisensi; UI harus menampilkan data tidak tersedia, bukan quote palsu.
- Saran investasi personal berbayar, broker, custody, trading dan eksekusi order: tidak termasuk.
- Chat file/sticker upload, pencarian pesan lengkap, push notifications dan Redis pub/sub multi-instance: belum lengkap.
- Invite expiry/usage cap/auto-accept, workflow delegasi admin kompleks, tiket support dengan balasan admin, dan audit log admin platform: belum lengkap.
- OCR sekarang dieksekusi sinkron di API (dokumen PDF maksimal dua halaman awal); belum memiliki queue terpisah/retry/backoff dan confidence per-field. Gunakan container Docker resmi yang memasang Tesseract `ind+eng` dan Poppler.
- File upload menggunakan private persistent filesystem. Belum ada S3-compatible object storage, signed URL, antivirus scanning atau enkripsi aplikasi-level.
- Belum ada Redis-backed rate limit/event distribution, observability/alerting, pentest, review hukum PDP/PSE, atau restore drill produksi.
- APK debug dibangun via Actions; signed release tersedia hanya setelah pemilik membuat keystore dan mengisi GitHub Secrets.

Lihat `docs/ROADMAP.md` untuk daftar milestone dan release gate.

---

## Quick start (lokal)

Persyaratan: Python 3.12+, pip, Node.js 20+ untuk validasi JavaScript. Untuk OCR lokal, pasang Tesseract dengan bahasa Indonesia/Inggris dan Poppler. SQLite dapat dipakai untuk development/test.

### Windows PowerShell

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
$env:DATABASE_URL = 'sqlite:///./nexora-local.db'
$env:AUTO_CREATE_SCHEMA = 'true'
$env:JWT_SECRET = (python -c "import secrets; print(secrets.token_urlsafe(64))")
$env:APP_TIMEZONE = 'Asia/Makassar'
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Linux/macOS

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
export DATABASE_URL='sqlite:///./nexora-local.db'
export AUTO_CREATE_SCHEMA='true'
export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
export APP_TIMEZONE='Asia/Makassar'
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Buka `http://localhost:8000`. OpenAPI ada di `/docs`, health check di `/health`. Akun baru dibuat dari layar login; tidak ada akun demo default.

## Menjalankan backend online dengan Docker Compose

1. Salin `.env.example` menjadi `.env` pada root repository.
2. Buat nilai random kuat untuk `POSTGRES_PASSWORD` dan `JWT_SECRET` (minimal 64 karakter). Jangan gunakan contoh literal.
3. Isi `CORS_ORIGINS` dengan origin Android `https://appassets.androidplatform.net` serta origin web/PWA yang benar-benar kamu deploy. Pisahkan dengan koma, tanpa `*`.
4. Jalankan:

   ```bash
   docker compose up --build -d
   docker compose ps
   docker compose logs -f api
   ```

   API menjalankan `alembic upgrade head` saat start. Worker transaksi berulang menunggu API sehat sehingga migrasi selesai sebelum proses worker berjalan. PostgreSQL dan file upload berada pada named volumes.

5. Buka `http://SERVER:8000` untuk PWA atau pasang reverse proxy TLS dan domain HTTPS sebelum dipakai dari internet. Jangan membuka port database ke internet.

`docker compose down` menghentikan layanan tanpa menghapus data. Jangan menjalankan `docker compose down -v` kecuali memang ingin menghapus database serta file privat.

## Menghubungkan Android setelah APK dipasang

APK Android membawa salinan frontend dalam assets, tetapi **tidak membawa server API atau database**. Backend harus online dan dapat dijangkau ponsel.

1. Deploy backend menggunakan Docker Compose pada server/VPS yang kamu kelola. Untuk origin Android, app tidak mengisi base URL API otomatis dari origin aset; masukkan URL backend di pengaturan koneksi.
2. Pasang HTTPS untuk API, misalnya `https://api.domain-kamu.id`.
3. Pastikan `CORS_ORIGINS` mencakup `https://appassets.androidplatform.net`.
4. Buka NEXORA, pilih **Hubungkan/konfigurasi**, masukkan `https://api.domain-kamu.id/api/v1`, lalu simpan/uji koneksi.
5. Daftarkan username/password baru. Simpan recovery code di tempat aman.

Untuk Android emulator development, backend host biasanya `http://10.0.2.2:8000/api/v1`; cleartext hanya untuk debug build lokal. Production release menolak cleartext HTTP.

## GitHub Actions: cara pasang source dan ambil APK

1. Buat repository kosong di akun GitHub kamu (contoh nama `nexora`).
2. Ekstrak ZIP final dan upload **isi folder NEXORA ke root repository**, bukan membuat folder NEXORA/NEXORA bertingkat.
3. Commit ke branch `main`. Pastikan GitHub Actions diizinkan berjalan dan repository mengizinkan workflow.
4. Buka tab **Actions**:
   - `Quality checks`: menjalankan pytest, compile Python, syntax check JavaScript dan Alembic migration check.
   - `Build Android APK`: build APK debug secara otomatis saat file Android/frontend berubah atau lewat `workflow_dispatch`.
   - `Publish backend container`: build/push image ke GHCR saat tag versi `v*` dibuat.
   - `Deploy NEXORA backend to VPS`: deploy manual melalui SSH setelah host dan environment dipersiapkan.
5. Pada workflow `Build Android APK`, download artifact `NEXORA-Android-debug-APK`, ekstrak ZIP artifact dan ambil `app-debug.apk`.

APK debug cocok untuk uji internal, bukan distribusi Play Store. Tanda tangan release memerlukan keystore milik developer.

### Signed release APK (opsional)

Buat Android keystore lokal milik kamu dan jangan unggah ke repository. Encode sebagai Base64 lalu simpan pada GitHub → Settings → Secrets and variables → Actions dengan nama:

- `ANDROID_KEYSTORE_BASE64`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS`
- `ANDROID_KEY_PASSWORD`

Kemudian jalankan `Build Android APK` secara manual dengan input `signed_release=true`. Workflow memeriksa bahwa seluruh secrets tersedia, menulis keystore hanya pada runner temporary, dan mengunggah artifact `NEXORA-Android-signed-release-APK`. Jangan bagikan keystore atau password kepada orang lain. Simpan backup keystore terenkripsi secara offline.

### Publish backend container ke GHCR (opsional)

Buat tag rilis setelah quality workflow lolos, misalnya `v0.1.0`, kemudian push. `container-publish.yml` akan mengunggah image backend ke `ghcr.io/OWNER/REPOSITORY:latest` dan tag commit SHA. Atur visibility/package access sesuai kebutuhan deployment. Compose default membangun Dockerfile lokal; untuk menggunakan image GHCR, atur image pada layanan `api` dan `recurring-worker` sesuai tag yang dipublikasikan.

### Deploy backend otomatis ke VPS (opsional)

Workflow `deploy-vps.yml` hanya berjalan saat dipicu manual. VPS harus sudah memiliki Docker Engine, Docker Compose plugin, folder deployment absolut, file `.env` yang benar, serta SSH user dengan akses Docker. Tambahkan repository secrets berikut:

- `VPS_HOST` — hostname/IP server.
- `VPS_USER` — user SSH non-root yang memiliki izin deploy Docker.
- `VPS_SSH_PRIVATE_KEY` — private key khusus deploy.
- `VPS_KNOWN_HOSTS` — baris host key yang fingerprint-nya sudah diverifikasi secara independen. Jangan menaruh hasil `ssh-keyscan` yang belum diverifikasi.
- `VPS_PATH` — path absolut folder proyek di server.

Workflow menyalin source tanpa `.env`, database, upload privat, backup, atau kunci Android; kemudian memeriksa `docker compose config` dan menjalankan `docker compose up --build -d`. Buat `.env` di VPS terlebih dahulu dan batasi SSH key/user tersebut sesuai prinsip least privilege. Workflow ini tidak membuat server, domain, HTTPS certificate, atau database eksternal untukmu.

## Tes dan pemeriksaan

```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m py_compile app/main.py app/recurring_worker.py migrations/env.py
node --check ../frontend/assets/app.js
```

Uji migrasi pada database SQLite kosong:

```bash
cd backend
DATABASE_URL='sqlite:////tmp/nexora-migration-check.db' \
AUTO_CREATE_SCHEMA='false' \
JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')" \
PYTHONPATH=. python -m alembic upgrade head
```

Lihat `docs/QA_REPORT.md` untuk bukti yang sudah dijalankan dan daftar tes yang belum dapat dilakukan pada mesin penyusunan.

## Environment penting

| Variable | Fungsi |
|---|---|
| `DATABASE_URL` | SQLite lokal atau PostgreSQL production |
| `JWT_SECRET` | HMAC secret unik, minimal 64 karakter untuk production |
| `CORS_ORIGINS` | Exact comma-separated frontend origins, termasuk Android asset origin |
| `AUTO_CREATE_SCHEMA` | `true` untuk development; `false` untuk migrasi Alembic |
| `NEXORA_DATA_DIR` | Persistent storage dokumen privat |
| `APP_TIMEZONE` | Zona waktu laporan, default `Asia/Makassar` |
| `MAX_UPLOAD_BYTES` | Batas ukuran dokumen upload |
| `OCR_LANG` | Bahasa Tesseract, default `ind+eng` |
| `AUTH_RATE_LIMIT_PER_MINUTE` | Rate limit auth sederhana per proses |
| `RECURRING_POLL_SECONDS` | Interval worker aturan transaksi berulang |

Lihat `.env.example` untuk nilai deploy awal. Jangan masukkan secret nyata ke ZIP atau Git.

## Backup

`scripts/backup-postgres.sh` dan `scripts/restore-postgres.sh` membantu dump/restore PostgreSQL terenkripsi dengan OpenSSL. File upload privat tidak ikut dalam dump DB; backup volume `nexora-private-files` secara terpisah dengan enkripsi, retensi dan uji restore yang sama.

## Gerbang sebelum production

- Ubah semua secret dan password default; pasang TLS; batasi CORS/ports.
- Pakai PostgreSQL, volume persistent terenkripsi, backup dan restore drill.
- Ganti rate limiter memory dengan Redis/gateway untuk deployment multi-instance.
- Tambahkan object storage/private malware scanner bila menerima dokumen publik.
- Review XSS/CSRF/IDOR/BOLA, token/session storage, WebSocket scale, authorization admin, privacy policy/consent.
- Lakukan penilaian UU PDP, kewajiban PSE dan aturan terkait fitur investasi dengan profesional Indonesia sebelum rilis publik.
- Uji pada perangkat Android nyata, accessibility, low network, restore, dan performa.

**NEXORA adalah engineering preview/MVP yang dapat dikembangkan; bukan layanan finansial berizin, bukan broker, dan belum dinyatakan lulus audit keamanan atau hukum.**
