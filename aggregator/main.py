import os
import time
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer, DateTime, UniqueConstraint, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

# --- 1. KONFIGURASI DATABASE ---
# Mengambil URL dari Environment Variable (diset di docker-compose)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/db")

# Setup SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 2. MODEL DATABASE (Tabel) ---
class EventModel(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True)
    event_id = Column(String, index=True) # ID unik dari event
    timestamp = Column(DateTime)
    source = Column(String)
    payload = Column(String) # Simpan JSON payload sebagai string sederhana
    created_at = Column(DateTime, default=datetime.utcnow)

    # CONSTRAINT UNIK: Kombinasi topic dan event_id tidak boleh kembar!
    # Ini adalah kunci DEDUPLIKASI di level Database.
    __table_args__ = (
        UniqueConstraint('topic', 'event_id', name='uq_topic_event_id'),
    )

# Buat tabel jika belum ada (Retrying connection logic sederhana)
def init_db():
    retries = 5
    while retries > 0:
        try:
            Base.metadata.create_all(bind=engine)
            print("Database connected and tables created.")
            break
        except Exception as e:
            print(f"Database connection failed, retrying... ({e})")
            time.sleep(5)
            retries -= 1

init_db()

# --- 3. SKEMA DATA (Pydantic) ---
class EventSchema(BaseModel):
    topic: str
    event_id: str
    timestamp: str
    source: str
    payload: dict

# --- 4. APLIKASI FASTAPI ---
app = FastAPI()

# Dependency untuk mengambil koneksi DB per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"status": "Aggregator is running"}

@app.post("/publish")
def publish_event(event: EventSchema, db: Session = Depends(get_db)):
    """
    Menerima event. Menerapkan IDEMPOTENCY.
    Jika event duplikat, DB akan menolak (IntegrityError),
    tapi API tetap return 200 OK (seolah sukses).
    """
    try:
        # Konversi payload dict ke string untuk disimpan
        new_event = EventModel(
            topic=event.topic,
            event_id=event.event_id,
            timestamp=datetime.fromisoformat(event.timestamp.replace("Z", "")),
            source=event.source,
            payload=str(event.payload)
        )
        
        # Mulai Transaksi
        db.add(new_event)
        db.commit() # Commit transaksi (Simpan permanen)
        db.refresh(new_event)
        
        print(f"[SUCCESS] Event processed: {event.event_id}")
        return {"status": "processed", "event_id": event.event_id}

    except IntegrityError:
        # INI ADALAH LOGIKA IDEMPOTENCY
        # Jika DB error karena constraint unik dilanggar (data duplikat)
        db.rollback() # Batalkan transaksi
        print(f"[IGNORED] Duplicate event detected: {event.event_id}")
        # Return 200 agar publisher mengira sukses (Idempotent behavior)
        return {"status": "ignored_duplicate", "event_id": event.event_id}
    
    except Exception as e:
        db.rollback()
        print(f"[ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    # Hitung total data unik yang tersimpan
    count = db.query(EventModel).count()
    return {
        "unique_events_stored": count,
        "note": "Duplicate events are dropped by Database Constraints"
    }

@app.get("/events")
def get_events(topic: Optional[str] = None, limit: int = 10, db: Session = Depends(get_db)):
    query = db.query(EventModel)
    
    # Tambahkan filter jika parameter topic ada
    if topic:
        query = query.filter(EventModel.topic == topic)
    
    events = query.order_by(EventModel.created_at.desc()).limit(limit).all()
    return events