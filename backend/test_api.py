import urllib.request
import json

def test_api():
    base_url = "http://127.0.0.1:8000"
    print("🧪 Testing EcoPulse Backend Endpoints...")
    
    # 1. Latest Reading
    try:
        req = urllib.request.Request(f"{base_url}/api/reading/latest")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print(f"✅ /api/reading/latest -> Status: 200 OK")
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"❌ /api/reading/latest failed: {e}")

    # 2. History Readings
    try:
        req = urllib.request.Request(f"{base_url}/api/reading/history?limit=3")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print(f"✅ /api/reading/history -> Count: {len(data)} items")
    except Exception as e:
        print(f"❌ /api/reading/history failed: {e}")

if __name__ == "__main__":
    test_api()
