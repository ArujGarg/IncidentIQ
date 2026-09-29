import random
import time

from fastapi import FastAPI, Header, HTTPException
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

app = FastAPI(title="Inventory Service")

FAILURE_MODE = False

resource = Resource.create(
    {
        "service.name": "inventory_service",
    }
)

provider = TracerProvider(resource=resource)

exporter = OTLPSpanExporter(
    endpoint="http://localhost:14317",
    insecure=True,
)

provider.add_span_processor(BatchSpanProcessor(exporter))

trace.set_tracer_provider(provider)

FastAPIInstrumentor.instrument_app(
    app,
    exclude_spans=["receive", "send"],
)

tracer = trace.get_tracer("inventory_service")

metric_exporter = OTLPMetricExporter(
    endpoint="http://localhost:14317",
    insecure=True,
)

metric_reader = PeriodicExportingMetricReader(
    metric_exporter,
    export_interval_millis=5000,
)

meter_provider = MeterProvider(
    resource=resource,
    metric_readers=[metric_reader],
)

metrics.set_meter_provider(meter_provider)

meter = metrics.get_meter("inventory_service")

inventory_failures = meter.create_counter(
    "inventory_dependency_failures_total",
    description="Number of inventory dependency failures",
)


@app.get("/inventory/{item_id}")
def check_inventory(
    item_id: str,
    x_request_id: str | None = Header(default=None),
):
    with tracer.start_as_current_span("inventory.check") as span:
        time.sleep(random.uniform(0.05, 0.15))

        if FAILURE_MODE:
            error = Exception("inventory service unavailable")

            inventory_failures.add(1)

            span.record_exception(error)
            span.set_status(
                trace.Status(
                    trace.StatusCode.ERROR,
                    "inventory service unavailable",
                )
            )

            raise HTTPException(
                status_code=503,
                detail="inventory service unavailable",
            )

        return {
            "item_id": item_id,
            "available": True,
        }


@app.post("/admin/failure")
def enable_failure():
    global FAILURE_MODE
    FAILURE_MODE = True
    return {"failure_mode": True}


@app.post("/admin/recover")
def recover():
    global FAILURE_MODE
    FAILURE_MODE = False
    return {"failure_mode": False}


@app.get("/health")
def health():
    return {"status": "ok"}
