import httpx

PROMETHEUS_URL = "http://localhost:9090"


def query_prometheus(query: str):
    response = httpx.get(
        f"{PROMETHEUS_URL}/api/v1/query",
        params={"query": query},
        timeout=5.0,
    )

    response.raise_for_status()

    return response.json()
