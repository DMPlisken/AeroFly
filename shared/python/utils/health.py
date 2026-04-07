"""Shared health check utility."""


def health_response(service_name: str) -> dict:
    return {"status": "ok", "service": service_name}
