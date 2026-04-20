import requests
import json

print("\n--- TESTING INGESTION ---")
res = requests.post("http://127.0.0.1:8000/api/process", json={"video_id": "Gfr50f6ZBvo"})
print(res.json())

print("\n--- TESTING CHAT ---")
res = requests.post("http://127.0.0.1:8000/api/chat", json={
    "video_id": "Gfr50f6ZBvo", 
    "question": "Who is Demis Hassabis and what does deepmind do?"
})
print(json.dumps(res.json(), indent=2))
