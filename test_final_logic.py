import requests
import json
import sys

def test_debug_endpoint():
    url = "http://localhost:8000/api/debug/analyze"
    payload = {
        "error": "TypeError: Cannot read property 'map' of undefined in UserDashboard.tsx",
        "repo_id": 1
    }
    
    print(f"Testing endpoint: {url}")
    try:
        response = requests.post(url, json=payload, timeout=20)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Backend and Ollama are working perfectly!")
            print(json.dumps(response.json(), indent=2))
        elif response.status_code == 503:
            print("❌ Backend is running, but Ollama is NOT reachable or model is not pulled.")
            print(f"Details: {response.json().get('detail')}")
        else:
            print(f"❌ Unexpected Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("Is the backend running on port 8000?")

if __name__ == "__main__":
    test_debug_endpoint()
