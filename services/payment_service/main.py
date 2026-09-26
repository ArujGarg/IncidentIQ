import logging
import random
import sys
import time

import structlog
from fastapi import FastAPI, Header
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


class OTelLogFilter(logging.Filter):
    def filter(self, record):
        record.__dict__.pop("_logger", None)
        record.__dict__.pop("_name", None)
        return True


logging.basicConfig(
    format="%(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
    level=logging.INFO,
)

resource = Resource.create({"service.name": "payment_service"})

logger_provider = LoggerProvider(resource=resource)

log_exporter = OTLPLogExporter(
    endpoint="http://localhost:14317",
    insecure=True,
)

logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

set_logger_provider(logger_provider)

otel_logging_handler = LoggingHandler(
    level=logging.INFO,
    logger_provider=logger_provider,
)

otel_logging_handler.addFilter(OTelLogFilter())

logging.getLogger().addHandler(otel_logging_handler)

provider = TracerProvider(resource=resource)

exporter = OTLPSpanExporter(
    endpoint="http://localhost:14317",
    insecure=True,
)

provider.add_span_processor(BatchSpanProcessor(exporter))

trace.set_tracer_provider(provider)

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

meter = metrics.get_meter("payment_service")

payment_requests = meter.create_counter(
    "payment_requests_total",
    description="Total number of payment requests",
)

payment_failures = meter.create_counter(
    "payment_failures_total",
    description="Total number of payment failures",
)

payment_latency = meter.create_histogram(
    "payment_request_duration_seconds",
    unit="s",
    description="Payment request duration in seconds",
)

app = FastAPI()

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
)

logger = structlog.get_logger()


@app.post("/payments")
def process_payment(x_request_id: str | None = Header(default=None)):
    payment_requests.add(1)

    start = time.perf_counter()

    time.sleep(random.uniform(0.1, 0.3))

    duration = time.perf_counter() - start

    if FAILURE_MODE:
        payment_failures.add(1)

        logger.error(
            "payment_failed",
            service="payment-service",
            status=500,
            request_id=x_request_id,
            error="database connection timeout",
        )

        payment_latency.record(duration)

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

    payment_latency.record(duration)

    return {
        "status": "success",
        "transaction_id": f"txn-{random.randint(1000, 9999)}",
    }


app.get("/health")


def health():
    return {"status": "ok"}


FAILURE_MODE = False


@app.post("/admin/failure")
def enable_failure():
    global FAILURE_MODE
    FAILURE_MODE = True
    return {"failure_mode": True}
