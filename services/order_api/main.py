import random
import time
import uuid

import httpx
import structlog
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

resource = Resource.create({"service.name": "order_api"})

provider = TracerProvider(resource=resource)

exporter = OTLPSpanExporter(
    endpoint="http://localhost:14317",
    insecure=True,
)

provider.add_span_processor(BatchSpanProcessor(exporter))

trace.set_tracer_provider(provider)

app = FastAPI()

FastAPIInstrumentor.instrument_app(
    app,
    exclude_spans=["receive", "send"],
)
HTTPXClientInstrumentor().instrument()

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

    inventory_response = httpx.get(
        "http://localhost:8003/inventory/item-123",
        headers={
            "X-Request-ID": request_id,
        },
        timeout=2.0,
    )

    inventory_response.raise_for_status()

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
