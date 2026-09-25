import random
import time

import httpx

while True:
    try:
        response = httpx.get("http://127.0.0.1:8000/orders")
        print(response.status_code)
    except Exception as e:
        print(f"Request failed: {e}")

    time.sleep(random.uniform(0.5, 2))
