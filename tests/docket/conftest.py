import httpx
import pytest

DOCKET_ID = 69510553
DOCKET_DETAIL = {"id": DOCKET_ID, "court": "scotus", "docket_number": "23-1234", "case_name": "Example v. Example"}


def make_entries_transport(entries: list[dict], *, docket_detail: dict | None = None) -> httpx.MockTransport:
    """Serves `docket_detail` for GET /dockets/{id}/ and one unpaginated page of `entries`
    for GET /docket-entries/. Lets a test control exactly what CourtListener 'currently has'."""
    detail = docket_detail if docket_detail is not None else DOCKET_DETAIL

    def handler(request: httpx.Request) -> httpx.Response:
        if "/docket-entries/" in request.url.path:
            return httpx.Response(200, json={"results": entries, "next": None, "previous": None})
        if "/dockets/" in request.url.path:
            return httpx.Response(200, json=detail)
        return httpx.Response(404, json={"detail": "not found"})

    return httpx.MockTransport(handler)


@pytest.fixture
def entries_transport_factory():
    return make_entries_transport


@pytest.fixture
def patch_courtlistener_client(monkeypatch: pytest.MonkeyPatch):
    """Forces both call sites that construct CourtListenerClient (the /track route and
    monitor.check_docket_for_updates) to use a test transport, while still exercising the
    real token-validation logic in CourtListenerClient.__init__."""

    def _patch(transport: httpx.MockTransport) -> None:
        from legalintel.docket.courtlistener_client import CourtListenerClient

        def _factory(*, api_token, base_url, **kwargs):
            return CourtListenerClient(api_token=api_token, base_url=base_url, transport=transport)

        monkeypatch.setattr("app.api.routes.dockets.CourtListenerClient", _factory)
        monkeypatch.setattr("legalintel.docket.monitor.CourtListenerClient", _factory)

    return _patch
