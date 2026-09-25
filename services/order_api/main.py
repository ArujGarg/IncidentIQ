import random
import time
import uuid

import httpx
import structlog
from fastapi import FastAPI

app = FastAPI()

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()


@app.get("/orders")
def get_orders():
    start = time.time()

    time.sleep(random.uniform(0.05, 0.2))

    request_id = str(uuid.uuid4())
    payment_response = httpx.post(
        "http://localhost:8001/payments", headers={"X-Request-ID": request_id}
    )

    duration = time.time() - start

    logger.info(
        "request_completed",
        service="order-api",
        endpoint="/orders",
        status=200,
        duration=round(duration, 3),
        payment_status=payment_response.status_code,
        request_id=request_id,
    )

    return {
        "orders": [
            {"id": 1, "item": "Laptop"},
            {"id": 2, "item": "Keyboard"},
        ],
        "payment": payment_response.json(),
    }


@app.get("/health")
def health():
    return {"status": "ok"}
