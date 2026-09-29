import httpx

LOKI_URL = "http://localhost:3100"


def query_loki(query: str, start: int | None = None, end: int | None = None):
    params = {
        "query": query,
        "limit": 100,
    }

    if start is not None:
        params["start"] = start

    if end is not None:
        params["end"] = end

    response = httpx.get(
        f"{LOKI_URL}/loki/api/v1/query_range",
        params=params,
        timeout=5.0,
    )

    response.raise_for_status()

    return response.json()
