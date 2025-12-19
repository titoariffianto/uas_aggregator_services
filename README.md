# Pub-Sub Log Aggregator Terdistribusi (UAS Sistem Terdistribusi)

Sistem Log Aggregator berbasis **Microservices** yang dibangun menggunakan **Python (FastAPI)** dan **PostgreSQL**, diorkestrasi dengan **Docker Compose**. Sistem ini dirancang untuk menangani ribuan event dengan jaminan **Idempotency**, **Deduplication**, dan **Data Consistency** yang kuat menggunakan transaksi ACID database.

## 📋 Daftar Isi
- [Arsitektur & Desain](#-arsitektur--desain)
- [Teknologi yang Digunakan](#-teknologi-yang-digunakan)
- [Persiapan & Cara Menjalankan](#-persiapan--cara-menjalankan)
- [API Endpoints](#-api-endpoints)
- [Mekanisme Idempotency & Konkurensi](#-mekanisme-idempotency--konkurensi-penting)
- [Pengujian (Testing)](#-pengujian-testing)
- [Asumsi & Batasan](#-asumsi--batasan)

---

## 🏗 Arsitektur & Desain

Sistem berjalan dalam jaringan internal Docker yang terisolasi tanpa akses publik ke Database.

**Komponen:**
1.  **Publisher (Python Script):**
    - Mensimulasikan layanan mikro (e.g., Payment Service, Order Service).
    - Mengirim event JSON ke Aggregator via HTTP POST.
    - Secara acak mengirimkan **duplikat event** (30% chance) untuk menguji ketahanan sistem.
    
2.  **Aggregator (FastAPI Service):**
    - Entry point (REST API) untuk menerima log.
    - Bertindak sebagai *Gatekeeper* untuk validasi data dan deduplikasi.
    - Mengelola koneksi ke database menggunakan SQLAlchemy Session.

3.  **Storage (PostgreSQL 16):**
    - Database relasional untuk menyimpan event secara persisten.
    - Menangani *Constraint Checking* untuk deduplikasi atomik.
    - Data disimpan dalam **Docker Volume** (`pg_data`) agar aman dari crash/restart.

**Alur Data:**
`Publisher` -> `HTTP POST` -> `Aggregator` -> `DB Transaction (Insert)` -> `PostgreSQL`

---

## 🛠 Teknologi yang Digunakan
- **Language:** Python 3.11 (Slim Image)
- **Framework:** FastAPI + Uvicorn
- **ORM:** SQLAlchemy
- **Database:** PostgreSQL 16 Alpine
- **Containerization:** Docker & Docker Compose
- **Testing:** Pytest & Requests

---

## 🚀 Persiapan & Cara Menjalankan

### Prasyarat
- Docker Engine & Docker Compose terinstal di komputer.

### Langkah-langkah
1.  **Clone / Buka Folder Project**
2.  **Build & Run Container**
    Jalankan perintah berikut di terminal:
    ```bash
    docker compose up --build
    ```
    *Tunggu hingga log menampilkan "Database connected and tables created".*

3.  **Akses Layanan**
    - **API Docs (Swagger UI):** [http://localhost:8080/docs](http://localhost:8080/docs)
    - **Cek Statistik:** [http://localhost:8080/stats](http://localhost:8080/stats)
    - **Lihat Event:** [http://localhost:8080/events](http://localhost:8080/events)

4.  **Menghentikan Layanan**
    ```bash
    docker compose down
    ```
    *Gunakan `docker compose down -v` jika ingin menghapus volume data (reset database).*

---

## 📡 API Endpoints

### 1. Publish Event
`POST /publish`
Menerima event baru. Jika event ID duplikat, sistem akan mengabaikannya tetapi tetap mengembalikan status sukses (Idempotent).

**Contoh Body:**
```json
{
  "topic": "payment-processed",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-19T10:00:00Z",
  "source": "payment-service",
  "payload": {
    "amount": 50000,
    "status": "SUCCESS"
  }
}
