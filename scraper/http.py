"""Polite HTTP for the adapters.

15-second timeout, descriptive User-Agent, 2 retries with exponential backoff
on 5xx / connection errors only. A 4xx is a configuration problem, never
retried.
"""

from __future__ import annotations

import time

import requests

USER_AGENT = (
    "offshore-bench/1.0 (personal internship job board; "
    "contact via the repository's issue tracker)"
)
TIMEOUT = 15
RETRIES = 2  # retries after the first attempt


class FetchError(RuntimeError):
    pass


def _request(method: str, url: str, json_body=None):
    last_error: Exception | None = None
    for attempt in range(RETRIES + 1):
        if attempt:
            time.sleep(2**attempt)
        try:
            resp = requests.request(
                method,
                url,
                json=json_body,
                timeout=TIMEOUT,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
        except requests.RequestException as exc:
            last_error = exc
            continue
        if resp.status_code >= 500:
            last_error = FetchError(f"{resp.status_code} from {url}")
            continue
        if resp.status_code >= 400:
            raise FetchError(f"{resp.status_code} from {url}")
        try:
            return resp.json()
        except ValueError as exc:
            raise FetchError(f"non-JSON response from {url}") from exc
    raise FetchError(f"giving up on {url}: {last_error}")


def get_json(url: str):
    return _request("GET", url)


def post_json(url: str, body: dict):
    return _request("POST", url, json_body=body)
