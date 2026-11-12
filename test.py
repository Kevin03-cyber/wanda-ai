import requests

BASE = "http://localhost:5004/api"

chat_id = requests.post(f"{BASE}/chats").json()["id"]
print("chat id:", chat_id)

def ask(q):
    r = requests.post(f"{BASE}/chats/{chat_id}/message", json={"message": q}, timeout=300)
    print("Q:", q)
    print("A:", r.json().get("answer") or r.json())
    print("-" * 40)

ask("My name is Kevin. Remember it.")
ask("What is my name?")

print("Chats:", requests.get(f"{BASE}/chats").json())
print("Saved messages:", len(requests.get(f"{BASE}/chats/{chat_id}").json()))