import re
import time

import httpx

from legalintel.models.docket import DocketEntry

# CourtListener's free tier is 5 req/min. A docket with enough entries to span
# several pages can exhaust that budget mid-pagination on its own, so `_get`
# retries on 429 rather than failing the whole operation - without this, any
# sufficiently large docket could never successfully complete a check.
_MAX_RATE_LIMIT_RETRIES = 5
_DEFAULT_RETRY_WAIT_SECONDS = 15.0
# CourtListener also enforces hourly/daily caps (50/hr, 125/day) whose 429s report a
# much longer wait than the per-minute one. Blocking a request thread for that long
# would make the app look hung, so if the suggested wait exceeds this, fail fast with
# a clear message instead of sleeping through it.
_MAX_RETRY_WAIT_SECONDS = 30.0


class CourtListenerConfigError(RuntimeError):
    pass


class CourtListenerNotFoundError(RuntimeError):
    pass


class CourtListenerAPIError(RuntimeError):
    pass


def _retry_wait_seconds(response: httpx.Response) -> float:
    """Prefer the standard Retry-After header; fall back to parsing CourtListener's
    "Expected available in N seconds" message from the response body; otherwise use a
    conservative default. Adds a 1s buffer either way to avoid retrying a hair too early."""
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return float(retry_after) + 1
        except ValueError:
            pass

    try:
        detail = response.json().get("detail", "")
    except ValueError:
        detail = response.text
    match = re.search(r"available in (\d+(?:\.\d+)?) seconds", detail)
    if match:
        return float(match.group(1)) + 1

    return _DEFAULT_RETRY_WAIT_SECONDS


def _entry_description(item: dict) -> str:
    """CourtListener's `description` field on the docket-entry itself is often blank -
    the actual filing description usually lives on the attached document(s) instead
    (`recap_documents[*].description`), same as what courtlistener.com's own docket
    view displays. Fall back to those, joining if there's more than one document on
    this entry."""
    description = item.get("description") or ""
    if description:
        return description

    recap_documents = item.get("recap_documents") or []
    doc_descriptions = [doc.get("description") for doc in recap_documents if doc.get("description")]
    return "; ".join(doc_descriptions)


class CourtListenerClient:
    def __init__(
        self,
        *,
        api_token: str | None,
        base_url: str,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not api_token:
            raise CourtListenerConfigError(
                "No CourtListener API token configured. Sign up for a free account and "
                "generate one at https://www.courtlistener.com/profile/api-token/, then "
                "set COURTLISTENER_API_TOKEN in .env."
            )
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Token {api_token}"},
            timeout=timeout,
            transport=transport,
        )

    def __enter__(self) -> "CourtListenerClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._client.close()

    def _get(self, url: str, params: dict | None = None) -> dict:
        for attempt in range(_MAX_RATE_LIMIT_RETRIES + 1):
            try:
                response = self._client.get(url, params=params)
            except httpx.RequestError as exc:
                raise CourtListenerAPIError(f"Network error contacting CourtListener: {exc}") from exc

            if response.status_code == 429:
                wait_seconds = _retry_wait_seconds(response)
                if wait_seconds > _MAX_RETRY_WAIT_SECONDS:
                    raise CourtListenerAPIError(
                        f"CourtListener rate limit exceeded for {url}, and it's asking us to "
                        f"wait {wait_seconds:.0f}s - too long to block on. This usually means "
                        "the hourly/daily quota (50/hr, 125/day) is exhausted, not just the "
                        "5/min one. Try again later."
                    )
                if attempt == _MAX_RATE_LIMIT_RETRIES:
                    raise CourtListenerAPIError(
                        f"CourtListener rate limit still exceeded after {_MAX_RATE_LIMIT_RETRIES} "
                        f"retries for {url}"
                    )
                time.sleep(wait_seconds)
                continue

            if response.status_code == 404:
                raise CourtListenerNotFoundError(f"CourtListener returned 404 for {url}")
            if response.status_code // 100 != 2:
                raise CourtListenerAPIError(
                    f"CourtListener returned {response.status_code} for {url}: {response.text[:300]}"
                )
            return response.json()

        raise AssertionError("unreachable")  # loop always returns or raises

    def get_docket(self, courtlistener_docket_id: int) -> dict:
        return self._get(f"/dockets/{courtlistener_docket_id}/")

    def get_all_docket_entries(self, courtlistener_docket_id: int) -> list[DocketEntry]:
        entries: list[DocketEntry] = []
        url: str | None = "/docket-entries/"
        params: dict | None = {"docket": courtlistener_docket_id}

        while url is not None:
            payload = self._get(url, params=params)
            for item in payload.get("results", []):
                entries.append(
                    DocketEntry(
                        courtlistener_entry_id=item["id"],
                        entry_number=item.get("entry_number"),
                        description=_entry_description(item),
                        date_filed=item.get("date_filed"),
                    )
                )
            # `next` is already a full absolute URL (includes its own cursor query
            # params), so it's passed straight through with no further params.
            url = payload.get("next")
            params = None

        return entries
