import os, time, httpx, pytest
BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
def _try_health():
    try:
        r = httpx.get(f"{BASE}/health", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False
pytestmark = pytest.mark.skipif(not _try_health(), reason="API not running; skip integration")

def test_happy_path_flow():
    order_id = str(int(time.time()))
    r = httpx.post(f"{BASE}/orders/{order_id}/start",
                   json={"payment_id": f"pay-{order_id}", "address":{"city":"Amherst"}}, timeout=5.0)
    assert r.status_code == 200
    r = httpx.post(f"{BASE}/orders/{order_id}/signals/update_address",
                   json={"address":{"city":"Boston","street":"456 Elm Ave"}}, timeout=5.0)
    assert r.status_code == 200
    r = httpx.post(f"{BASE}/orders/{order_id}/signals/approve", timeout=5.0)
    assert r.status_code == 200
    for _ in range(24):
        s = httpx.get(f"{BASE}/orders/{order_id}/status", timeout=5.0)
        if s.status_code == 200 and '"step":"done"' in s.text:
            body = s.json()
            assert body["address"]["city"] == "Boston"
            return
        time.sleep(0.5)
    pytest.fail("workflow did not reach done")
