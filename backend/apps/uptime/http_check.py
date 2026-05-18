import time
from dataclasses import dataclass
from typing import Optional
import requests


@dataclass
class CheckResult:
    is_up: bool
    status_code: Optional[int]
    response_ms: Optional[int]
    error: str


def _parse_expected_status(expected: str) -> list[int]:
    return [int(s.strip()) for s in expected.split(",") if s.strip()]


def perform_check(monitor) -> CheckResult:
    expected_codes = _parse_expected_status(monitor.expected_status)
    start = time.monotonic()
    try:
        resp = requests.get(monitor.url, timeout=monitor.timeout_secs)
    except requests.exceptions.Timeout:
        return CheckResult(is_up=False, status_code=None, response_ms=None, error="timeout")
    except requests.exceptions.ConnectionError:
        return CheckResult(is_up=False, status_code=None, response_ms=None, error="connection error")
    except requests.exceptions.RequestException as exc:
        return CheckResult(is_up=False, status_code=None, response_ms=None, error=str(exc)[:200])

    elapsed_ms = int((time.monotonic() - start) * 1000)

    if resp.status_code not in expected_codes:
        return CheckResult(
            is_up=False, status_code=resp.status_code,
            response_ms=elapsed_ms, error=f"status {resp.status_code}",
        )

    if monitor.expected_body and monitor.expected_body not in (resp.text or ""):
        return CheckResult(
            is_up=False, status_code=resp.status_code,
            response_ms=elapsed_ms, error="body mismatch",
        )

    return CheckResult(
        is_up=True, status_code=resp.status_code,
        response_ms=elapsed_ms, error="",
    )
