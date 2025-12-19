import time
import uuid
import random
import requests
# PERBAIKAN: Import timezone secara eksplisit
from datetime import datetime, timezone

TARGET_URL = "http://aggregator:8080/publish"

topics = [
    "payment-processed",   
    "order-created",       
    "inventory-update",    
    "user-signup",         
    "shipping-status",     
    "system-alert"         
]

sources = [
    "payment-service-01",
    "order-service-west",
    "inventory-worker-03",
    "auth-service-prod",
    "logistics-gateway",
    "backend-api-node-05"
]

sent_event_ids = []

def generate_event():
    topic = random.choice(topics)
    
    if topic == "payment-processed":
        payload_data = {"amount": random.randint(10000, 500000), "currency": "IDR", "status": "SUCCESS"}
    elif topic == "inventory-update":
        payload_data = {"sku": f"ITEM-{random.randint(100, 999)}", "qty": random.randint(-5, 10)}
    else:
        payload_data = {"info": "generic log", "code": random.randint(100, 200)}

    return {
        "topic": topic,
        "event_id": str(uuid.uuid4()),
        # PERBAIKAN: Gunakan timezone.utc langsung (bukan datetime.timezone.utc)
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": random.choice(sources),
        "payload": payload_data
    }

def run_publisher():
    print("Publisher started. Waiting for aggregator...")
    time.sleep(10) 
    
    while True:
        try:
            if sent_event_ids and random.random() < 0.3:
                event_id = random.choice(sent_event_ids)
                payload = {
                    "topic": "payment-processed",
                    "event_id": event_id,
                    # PERBAIKAN: Gunakan timezone.utc langsung
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "REPLAY-ATTACK-SIMULATOR",
                    "payload": {"retry_count": 1, "warning": "duplicate_attempt"}
                }
                print(f"Sending DUPLICATE: {event_id}")
            else:
                payload = generate_event()
                sent_event_ids.append(payload['event_id'])
                if len(sent_event_ids) > 1000:
                    sent_event_ids.pop(0)
                print(f"Sending NEW: {payload['event_id']} [{payload['topic']}]")

            response = requests.post(TARGET_URL, json=payload, timeout=5)
            print(f"Status: {response.status_code} | Response: {response.text}")
            
        except Exception as e:
            # Print error lebih detail jika ada masalah lain
            print(f"Connection/Code Error: {e}")
        
        time.sleep(random.uniform(0.01, 0.1))

if __name__ == "__main__":
    run_publisher()