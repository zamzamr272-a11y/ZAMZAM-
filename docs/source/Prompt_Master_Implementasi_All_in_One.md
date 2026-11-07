# Prompt Master Implementasi NEXORA

Lampirkan PRD lengkap dan ZIP gambar referensi saat memberikan prompt ini kepada AI coding agent.

Bertindaklah sebagai tim senior lintas disiplin: Product Manager, UX Researcher, Product Designer, Software Architect, Full-Stack Engineer, Android Engineer, Database Engineer, Security Engineer, QA Engineer, DevOps Engineer, dan AI Engineer. Bangun aplikasi produksi bernama sementara NEXORA berdasarkan PRD ini dan gambar referensi yang dilampirkan.

HASIL AKHIR YANG DIMINTA
Bangun aplikasi full-stack nyata, online, responsif, mobile-first, dan nyaman dipakai di Android serta browser laptop. Produk memiliki tiga pilar: (1) pencatatan dan analisis keuangan pribadi; (2) decision-support dan edukasi investasi; (3) komunitas/grup dengan chat, pairing code, dan tahap lanjutan voice/video. Jangan berhenti di mockup, landing page, atau UI statis. Semua tombol penting harus terhubung ke fungsi backend nyata.

CARA KERJA WAJIB
1. Audit repository, file, dependensi, runtime, dan skill yang memang tersedia. Baca dokumentasi proyek sebelum mengubah file. Jangan menghapus pekerjaan pengguna.
2. Buat rencana implementasi dan daftar acceptance criteria. Mulai dari fondasi yang dapat dijalankan, bukan membuat semua halaman sekaligus tanpa backend.
3. Gunakan stack yang cocok dengan repository. Bila belum ada stack, pilih satu arsitektur sederhana: Next.js + TypeScript untuk web/PWA, backend NestJS atau FastAPI, PostgreSQL, Redis bila dibutuhkan, object storage S3-compatible, WebSocket untuk chat. Untuk Android native gunakan React Native/Expo. Hindari menambah teknologi tanpa alasan.
4. Periksa kompatibilitas versi sebelum memasang paket. Gunakan dependensi stabil dan terawat. Jangan mengunduh atau menjalankan skill/script acak dari internet. Skill baru hanya boleh dipakai jika sumber, lisensi, isi, permission, dan keamanannya diperiksa terlebih dahulu. Jangan pernah menjalankan perintah destruktif tanpa backup dan persetujuan.
5. Kerjakan secara bertahap: schema/database -> auth -> finance CRUD -> laporan -> OCR draft -> group membership/chat -> tema/UX -> investment journal -> voice input -> voice/video. Fitur yang belum selesai harus diberi label belum tersedia, bukan tombol palsu.
6. Setelah setiap tahap: jalankan formatter, typecheck, lint, unit/integration test yang relevan, build, dan smoke test. Perbaiki error yang ditemukan sampai bersih. Jangan hanya menyembunyikan error.
7. Buat README berisi setup, environment variables, migrasi, seed demo, menjalankan development, testing, build, deployment, backup, dan troubleshooting. Buat .env.example tanpa secret nyata.
8. Jangan mengklaim pekerjaan selesai sebelum seluruh acceptance criteria yang relevan lulus. Laporkan fitur selesai, belum selesai, risiko, dan bukti pengujian.

DESAIN DAN PENGALAMAN
Gunakan gambar referensi sebagai inspirasi: dark dashboard premium, panel/card bertingkat, metrik yang jelas, list/tabel rapi, visualisasi informatif, kontras tinggi, aksen teal dan amber, tipografi bersih, dan komposisi dashboard operasional. Jangan menyalin logo, identitas merek, atau aset visual pihak lain. Buat design system sendiri dengan dark mode dan light mode. Dark mode memakai charcoal/navy, off-white, teal, amber; light mode memakai latar terang, card putih, teks gelap, dan aksen semantik yang sama. Gunakan Inter/Manrope atau font open-license. Buat maskot 3D original yang ringan, ramah, profesional, punya fallback statis dan reduced-motion. Prioritaskan keterbacaan dan data, bukan ornamen.

Di Android gunakan bottom navigation maksimal lima item: Beranda, Keuangan, Investasi, Komunitas, Profil. Target sentuh nyaman (sekitar 44-48 dp), layout satu kolom, form ringkas, CTA tidak tertutup keyboard, safe area terjaga. Di web gunakan sidebar dan dashboard multi-kolom yang tetap responsif. Semua layar wajib punya loading, empty, error, success, dan offline/degraded states yang sesuai. Format IDR dan tanggal lokal secara konsisten.

AUTENTIKASI DAN PAIRING
Pendaftaran meminta username unik dan password saja sesuai spesifikasi. Hash password dengan Argon2id atau bcrypt; jangan simpan plaintext. Karena tidak ada email/nomor wajib, berikan recovery code acak sekali pakai dan edukasi bahwa kehilangan password serta recovery code dapat membuat akun tidak dapat dipulihkan. Tawarkan email/nomor secara sukarela untuk opsi recovery tambahan. Gunakan sesi aman, refresh token rotation, logout seluruh perangkat, rate limit, dan audit.
Setiap profil punya profile code acak untuk menemukan/mengundang pengguna; kode ini bukan credential dan tidak memberi akses data. Setiap grup punya invite code tersendiri yang bisa dicabut/dirotasi. Saat kode grup dimasukkan, tampilkan preview grup, pengguna menekan Minta Bergabung, admin/pemilik menyetujui atau menolak, lalu membership diperbarui real-time. Auto-accept hanya jika pemilik aktifkan.

MODUL KEUANGAN
Implementasikan dashboard total pemasukan, pengeluaran, arus kas bersih, saldo tercatat, anggaran tersisa, transaksi terakhir, dan kategori terbesar. Buat CRUD transaksi manual untuk income, expense, dan transfer; field nominal, tanggal/waktu, akun, kategori, deskripsi/catatan, tag, lampiran. Sediakan kategori yang dapat diedit, akun/dompet (tunai, rekening, e-wallet, kartu), anggaran, tujuan, transaksi berulang, pencarian dan filter. Transfer antar akun tidak boleh dihitung sebagai income atau expense. Refund dan koreksi harus konsisten.

FOTO MUTASI DAN OCR
Pengguna bisa unggah foto/screenshot/PDF. Validasi tipe, ukuran, MIME, dan keamanan file. OCR mengekstrak tanggal, nominal, deskripsi, debit/kredit dan saldo bila tersedia. Hasilnya harus berupa draft, menampilkan confidence dan field yang bisa diedit. Jangan memasukkan transaksi sebelum pengguna mengonfirmasi. Deteksi duplikasi berdasarkan akun/tanggal/nominal/deskripsi/fingerprint. Jika OCR gagal atau ambigu, minta unggah ulang atau input manual; jangan mengarang nilai. Dokumen terenkripsi, akses terbatas, signed URL sementara, kebijakan retensi/penghapusan jelas, dan jangan gunakan untuk training tanpa persetujuan terpisah.

INPUT SUARA
Sediakan tombol rekam yang hanya aktif setelah izin mikrofon dan selalu menunjukkan indikator. Transkripsi Bahasa Indonesia diubah menjadi draft transaksi dengan jenis, nominal, tanggal, kategori, dan akun. Tampilkan teks transkrip dan ringkasan sebelum menyimpan. Minta konfirmasi pengguna; tanyakan satu klarifikasi jika field penting ambigu. Jangan merekam diam-diam dan hapus audio mentah sesuai kebijakan retensi.

LAPORAN DAN CHART
Filter harian, mingguan, bulanan, tahunan, serta rentang tanggal manual. Wajib ada tiga tampilan: (1) pie/donut kategori; (2) tabel transaksi rinci dengan sort/filter/total; (3) chart pemasukan hijau dan pengeluaran merah dengan label/legenda/pola supaya tidak hanya mengandalkan warna. Semua tampilan harus memakai dataset terkonfirmasi yang sama dan angka cocok saat drill-down. Tampilkan perbandingan periode, kategori terbesar, tren, hari boros, rasio tabungan, pengeluaran berulang, dan transaksi tidak biasa. Semua insight menjelaskan periode, angka, pembanding, dan sumber. Rekomendasi bulan depan harus berupa langkah terukur, tidak boleh menjanjikan peningkatan pendapatan pasti.

INVESTASI DAN DECISION SUPPORT
Bangun watchlist, detail aset jika data provider berlisensi tersedia, jurnal tesis, horizon waktu, profil risiko yang ditentukan pengguna, alasan keputusan, risiko, faktor pembatal tesis, dan skenario optimistis/dasar/pesimistis. Data harus memiliki sumber dan timestamp. Pisahkan fakta, asumsi, dan interpretasi AI. Jika data tidak tersedia, tampilkan status tidak tersedia. Jangan mengarang harga/berita, jangan menjanjikan return, jangan mengeksekusi order, dan tampilkan disclosure edukasi/informasi. Jangan aktifkan rekomendasi personal berbayar atau aktivitas yang memerlukan izin sebelum tinjauan hukum.

KOMUNITAS DAN CHAT
Buat grup dengan nama bebas, deskripsi, avatar, aturan, daftar anggota, role owner/admin/member, dan privacy settings. Implementasikan chat teks real-time, reply, edit/hapus sesuai kebijakan, emoji reaction, pin, lampiran gambar, pencarian, mute, block, report, typing indicator, dan notifikasi. Pastikan hanya anggota sah dapat membaca pesan. Pengguna dapat membuat stiker dari foto yang dimiliki/berhak digunakan; crop, optional background removal, preview, simpan, hapus; validasi file dan moderasi. Sediakan pilihan font berlisensi dan emoji; jangan izinkan HTML/script atau font eksternal tak tepercaya.

VOICE DAN VIDEO
Voice room lebih dahulu, kemudian video call. Gunakan WebRTC melalui SFU atau provider terkelola, token ruang pendek yang memeriksa membership, join/leave, mute, speaker/mic selector, indikator pembicara, kamera, reconnect, host controls, dan report. Jangan merekam panggilan secara default. Tunda modul ini bila fondasi real-time, auth, dan biaya belum aman; tampilkan status roadmap, bukan tombol palsu.

CUSTOMER SERVICE
Tombol Bantuan membuka WhatsApp dengan nomor yang diberikan pemilik aplikasi: https://wa.me/628871144516. Tampilkan konfirmasi sebelum membuka tautan. Sediakan juga tiket bantuan internal dengan kategori, deskripsi, lampiran opsional, nomor tiket, status, dan riwayat. Jangan pernah mengirim laporan keuangan/foto mutasi/chat privat ke WhatsApp tanpa pilihan dan persetujuan pengguna.

KEAMANAN DAN PRIVASI
Terapkan least privilege, TLS, encryption at rest, secret management, signed upload/download, audit log, rate limiting, file scanning, backup terenkripsi, restore drill, export/delete account, consent controls, dan privacy-by-default. Uji otorisasi setiap resource terhadap user ID dan group membership. Cegah IDOR/BOLA, XSS, CSRF, SQL injection, brute force, file upload abuse, token leakage, dan kebocoran antar pengguna. Pertimbangkan UU PDP dan kewajiban PSE di Indonesia; minta peninjauan profesional sebelum produksi. Jangan meminta kredensial bank/PIN/CVV.

KRITERIA SELESAI
- Pendaftaran/login/recovery bekerja dan diuji.
- Semua transaksi manual CRUD bekerja; laporan akurat; transfer dikecualikan dari income/expense.
- OCR membuat draft dan hanya menyimpan setelah konfirmasi.
- Voice input membuat draft dan butuh konfirmasi.
- Filter hari/minggu/bulan/tahun/rentang khusus bekerja di semua chart.
- Chart pie, tabel, dan income-vs-expense memakai data sama.
- Kode undangan profil dan grup berbeda; flow preview-request-approve berfungsi.
- Chat real-time dan otorisasi membership diuji.
- Dark/light mode konsisten; Android dan web responsif.
- Customer support mengarah ke WhatsApp benar dan tiket internal tersedia.
- Tidak ada tombol inti palsu, error build/test yang diabaikan, secret di repository, atau data demo di production.
- README, .env.example, migrasi, test, deployment guide, backup/restore, dan laporan QA tersedia.

OUTPUT AKHIR DARI AGENT
Berikan ringkasan arsitektur, daftar fitur selesai vs belum selesai, cara menjalankan aplikasi, akun demo non-produksi bila dibuat, hasil test/build, daftar endpoint, skema database/migrasi, variabel environment, langkah deploy, risiko yang belum terselesaikan, serta screenshot layar utama pada mobile dan desktop. Kerjakan dengan teliti, langsung perbaiki error yang ditemukan, jangan berputar-putar mengulang desain yang sama, dan jangan mengarang status keberhasilan.
