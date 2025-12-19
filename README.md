# UAS Sistem Terdistribusi: Pub-Sub Log Aggregator

Nama: Syifa Maulida
NIM: 11221007

Project ini adalah implementasi sistem **Distributed Log Aggregator** yang memenuhi kriterPubia:
- **Idempotency & Strong Deduplication** (Database-level constraints).
- **Concurrency Control** (Atomic transactions).
- **Fault Tolerance & Persistence** (Docker volumes & Client retry simulation).

## Arsitektur
Sistem terdiri dari 3 layanan dalam Docker Compose:
1. **Publisher**: Mengirim event JSON (termasuk simulasi duplikasi 30%).
2. **Aggregator**: REST API (FastAPI) untuk menerima dan memproses event.
3. **Storage**: PostgreSQL 16 untuk penyimpanan data persisten dengan jaminan ACID.

## Cara Menjalankan (Run)

Prasyarat: Docker & Docker Compose sudah terinstall.

1. **Clone & Masuk ke Folder:**
   ```bash
   git clone https://github.com/syifamaulidaa/SISTER_Pub-Sub-Log-Aggregator-Terdistribusi
   cd SISTER_Pub-Sub Log Aggregator Terdistribusi
