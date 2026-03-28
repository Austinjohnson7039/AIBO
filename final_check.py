import requests
import json

def test():
    print("Testing Llama 4 Scout on Port 8001...")
    try:
        res = requests.post(
            "http://localhost:8001/query/",
            json={"query": "What are your opening hours?"},
            timeout=30
        )
        print(f"Status: {res.status_code}")
        print(f"Answer: {res.json()['answer']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
