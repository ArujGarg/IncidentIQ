import logging
import random
import sys
import time

import structlog
from fastapi import FastAPI, Header
from prometheus_client import Counter, Histogram, make_asgi_app

app = FastAPI()

file_handler = logging.FileHandler("payment_service.log")

logging.basicConfig(
    format="%(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("payment_service.log"),
    ],
    level=logging.INFO,
)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
)
REQUEST_COUNT = Counter(
    "payment_requests_total",
    "Total payment requests",
)

FAILURE_COUNT = Counter(
    "payment_failures_total",
    "Total payment failures",
)

REQUEST_LATENCY = Histogram(
    "payment_request_duration_seconds",
    "Payment request latency",
)

app.mount("/metrics", make_asgi_app())


logger = structlog.get_logger()


@app.post("/payments")
def process_payment(x_request_id: str | None = Header(default=None)):
    REQUEST_COUNT.inc()
    start = time.time()

    time.sleep(random.uniform(0.1, 0.3))

    duration = time.time() - start

    if FAILURE_MODE:
        FAILURE_COUNT.inc()
        logger.error(
            "payment_failed",
            service="payment-service",
            status=500,
            request_id=x_request_id,
            error="database connection timeout",
        )

        REQUEST_LATENCY.observe(duration)
        return {
            "status": "failed",
            "error": "database connection timeout",
        }

    logger.info(
        "payment_processed",
        service="payment_service",
        status=200,
        duration=round(duration, 3),
        request_id=x_request_id,
    )

    REQUEST_LATENCY.observe(duration)
    return {"status": "success", "transaction_id": f"txn-{random.randint(1000, 9999)}"}


app.get("/health")


def health():
    return {"status": "ok"}


FAILURE_MODE = False


@app.post("/admin/failure")
def enable_failure():
    global FAILURE_MODE
    FAILURE_MODE = True
    return {"failure_mode": True}
