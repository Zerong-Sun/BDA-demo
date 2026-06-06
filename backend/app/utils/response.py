from uuid import uuid4


def envelope(data, trace_id: str | None = None) -> dict:
    return {"data": data, "trace_id": trace_id or str(uuid4())}
