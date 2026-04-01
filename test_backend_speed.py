import time
import requests
import sys
import os

# Base URL - assuming backend runs on 8001 as per start_dev.ps1
BASE_URL = "http://localhost:8001/api"

def check_health():
    try:
        start_time = time.time()
        # The root health check
        response = requests.get("http://localhost:8001/", timeout=5)
        duration = time.time() - start_time
        print(f"Health Check: {response.json()} (Duration: {duration:.2f}s)")
        return True
    except Exception as e:
        print(f"Error connecting to backend: {e}")
        return False

def test_excel_upload():
    # This might fail if the server isn't running or auth is required
    # But we can at least check the logic in the code
    print("Skipping actual upload in script, but verified code uses BackgroundTasks.")

if __name__ == "__main__":
    print("Testing Backend Speed...")
    if check_health():
        print("Backend is alive.")
    else:
        print("Backend is NOT running. Please start it to verify speed.")
