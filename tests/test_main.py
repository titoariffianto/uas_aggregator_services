import pytest
import requests
import uuid
import time
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:8080"

def get_random_event_id():
    return str(uuid.uuid4())

def get_timestamp():
    return "2025-12-12T10:00:00Z"

def test_01_root_health_check():
    try:
        r = requests.get(f"{BASE_URL}/")
        assert r.status_code == 200
        assert r.json() == {"status": "Aggregator is running"}
    except requests.exceptions.ConnectionError:
        pytest.fail("Aggregator tidak bisa dihubungi. Pastikan Docker jalan!")

def test_02_method_not_allowed():
    r = requests.get(f"{BASE_URL}/publish")
    assert r.status_code == 405

def test_03_endpoint_not_found():
    r = requests.get(f"{BASE_URL}/ngawur")
    assert r.status_code == 404

def test_04_publish_valid_payload():
    payload = {
        "topic": "test-valid",
        "event_id": get_random_event_id(),
        "timestamp": get_timestamp(),
        "source": "pytest",
        "payload": {"status": "ok"}
    }
    r = requests.post(f"{BASE_URL}/publish", json=payload)
    assert r.status_code == 200
    assert r.json()['status'] == "processed"

def test_05_publish_missing_field():
    payload = {
        "topic": "test-invalid",
        "timestamp": get_timestamp(),
        "source": "pytest",
        "payload": {}
    }
    r = requests.post(f"{BASE_URL}/publish", json=payload)
    assert r.status_code == 422

def test_06_publish_empty_body():
    r = requests.post(f"{BASE_URL}/publish", json={})
    assert r.status_code == 422

def test_07_publish_wrong_data_type():
    payload = {
        "topic": "test-type",
        "event_id": get_random_event_id(),
        "timestamp": get_timestamp(),
        "source": "pytest",
        "payload": "ini string bukan dict"
    }
    r = requests.post(f"{BASE_URL}/publish", json=payload)
    assert r.status_code == 422

def test_08_idempotency_first_send():
    global shared_event_id 
    shared_event_id = get_random_event_id()
    
    payload = {
        "topic": "test-dedup",
        "event_id": shared_event_id,
        "timestamp": get_timestamp(),
        "source": "pytest",
        "payload": {"try": 1}
    }
    r = requests.post(f"{BASE_URL}/publish", json=payload)
    assert r.status_code == 200
    assert r.json()['status'] == "processed"

def test_09_idempotency_duplicate_send():
    payload = {
        "topic": "test-dedup",
        "event_id": shared_event_id,
        "timestamp": get_timestamp(),
        "source": "pytest",
        "payload": {"try": 2}
    }
    r = requests.post(f"{BASE_URL}/publish", json=payload)
    assert r.status_code == 200
    assert r.json()['status'] == "ignored_duplicate"

def test_10_deduplication_db_integrity():
    initial = requests.get(f"{BASE_URL}/stats").json()['unique_events_stored']
    
    evt_id = get_random_event_id()
    payload = {
        "topic": "test-spam",
        "event_id": evt_id,
        "timestamp": get_timestamp(),
        "source": "pytest",
        "payload": {}
    }
    for _ in range(5):
        requests.post(f"{BASE_URL}/publish", json=payload)
    
    final = requests.get(f"{BASE_URL}/stats").json()['unique_events_stored']
    
    assert final == initial + 1

def test_11_get_events_list():
    r = requests.get(f"{BASE_URL}/events")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "event_id" in data[0]

def test_12_stats_vs_events_consistency():
    stats = requests.get(f"{BASE_URL}/stats").json()
    events = requests.get(f"{BASE_URL}/events?limit=10").json()
    
    total_stored = stats['unique_events_stored']
    list_shown = len(events)
    
    assert total_stored >= list_shown

def test_13_topic_consistency_check():
    unique_topic = f"topic-{uuid.uuid4()}"
    payload = {
        "topic": unique_topic,
        "event_id": get_random_event_id(),
        "timestamp": get_timestamp(),
        "source": "pytest",
        "payload": {}
    }
    requests.post(f"{BASE_URL}/publish", json=payload)
    
    events = requests.get(f"{BASE_URL}/events?limit=5").json()
    topics_in_db = [e['topic'] for e in events]
    assert unique_topic in topics_in_db

def send_request_helper(payload):
    return requests.post(f"{BASE_URL}/publish", json=payload).json()

def test_14_concurrency_race_condition():
    evt_id = get_random_event_id()
    payload = {
        "topic": "race-test",
        "event_id": evt_id,
        "timestamp": get_timestamp(),
        "source": "thread-pool",
        "payload": {}
    }
    
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_request_helper, payload) for _ in range(10)]
        for f in futures:
            results.append(f.result())
            
    processed = sum(1 for r in results if r['status'] == 'processed')
    ignored = sum(1 for r in results if r['status'] == 'ignored_duplicate')
    
    assert processed == 1
    assert ignored == 9

def test_15_stress_test_latency():
    count = 50
    start_time = time.time()
    
    for _ in range(count):
        payload = {
            "topic": "stress-test",
            "event_id": get_random_event_id(),
            "timestamp": get_timestamp(),
            "source": "pytest-stress",
            "payload": {"val": _}
        }
        r = requests.post(f"{BASE_URL}/publish", json=payload)
        assert r.status_code == 200
        
    duration = time.time() - start_time
    print(f"\nStress Test: {count} events in {duration:.4f}s")
    
    assert duration < 5.0 

def test_16_persistence_check_simulation():
    stats = requests.get(f"{BASE_URL}/stats").json()
    count = stats['unique_events_stored']
    assert count > 50
    print(f"\nPersistence Check: Found {count} events stored.")
