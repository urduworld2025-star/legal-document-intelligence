import httpx
import pytest

from legalintel.docket.courtlistener_client import (
    CourtListenerAPIError,
    CourtListenerClient,
    CourtListenerConfigError,
    CourtListenerNotFoundError,
)

BASE_URL = "https://www.courtlistener.com/api/rest/v4/"


def test_missing_token_raises_config_error() -> None:
    with pytest.raises(CourtListenerConfigError):
        CourtListenerClient(api_token=None, base_url=BASE_URL)


def test_blank_token_raises_config_error() -> None:
    with pytest.raises(CourtListenerConfigError):
        CourtListenerClient(api_token="", base_url=BASE_URL)


def test_404_response_raises_not_found_error() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(404, json={"detail": "not found"}))
    client = CourtListenerClient(api_token="fake-token", base_url=BASE_URL, transport=transport)

    with pytest.raises(CourtListenerNotFoundError):
        client.get_docket(1)


def test_server_error_raises_api_error() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(500, text="internal error"))
    client = CourtListenerClient(api_token="fake-token", base_url=BASE_URL, transport=transport)

    with pytest.raises(CourtListenerAPIError):
        client.get_docket(1)


def test_get_docket_returns_json_payload() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"id": 1, "case_name": "Example"}))
    client = CourtListenerClient(api_token="fake-token", base_url=BASE_URL, transport=transport)

    assert client.get_docket(1) == {"id": 1, "case_name": "Example"}


def test_429_response_is_retried_and_eventually_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep_calls: list[float] = []
    monkeypatch.setattr("legalintel.docket.courtlistener_client.time.sleep", sleep_calls.append)

    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(429, json={"detail": "Request was throttled. Expected available in 3 seconds."})
        return httpx.Response(200, json={"id": 1, "case_name": "Example"})

    transport = httpx.MockTransport(handler)
    client = CourtListenerClient(api_token="fake-token", base_url=BASE_URL, transport=transport)

    result = client.get_docket(1)

    assert result == {"id": 1, "case_name": "Example"}
    assert attempts["count"] == 2
    assert sleep_calls == [4.0]  # parsed "3 seconds" + 1s buffer


def test_429_response_eventually_raises_after_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("legalintel.docket.courtlistener_client.time.sleep", lambda _seconds: None)
    transport = httpx.MockTransport(lambda request: httpx.Response(429, json={"detail": "throttled"}))
    client = CourtListenerClient(api_token="fake-token", base_url=BASE_URL, transport=transport)

    with pytest.raises(CourtListenerAPIError):
        client.get_docket(1)


def test_429_with_very_long_suggested_wait_fails_fast_instead_of_blocking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleep_calls: list[float] = []
    monkeypatch.setattr("legalintel.docket.courtlistener_client.time.sleep", sleep_calls.append)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            429, json={"detail": "Request was throttled. Expected available in 900 seconds."}
        )
    )
    client = CourtListenerClient(api_token="fake-token", base_url=BASE_URL, transport=transport)

    with pytest.raises(CourtListenerAPIError):
        client.get_docket(1)

    assert sleep_calls == []  # never slept - failed fast instead of blocking for 900s


def test_get_all_docket_entries_falls_back_to_recap_document_description() -> None:
    # Real CourtListener behavior: the entry's own `description` is often blank; the
    # actual filing text lives on the attached recap_documents instead.
    payload = {
        "results": [
            {
                "id": 1,
                "entry_number": 1,
                "description": "",
                "date_filed": "2026-08-21",
                "recap_documents": [{"description": "Petition for Writ of Habeas Corpus"}],
            }
        ],
        "next": None,
        "previous": None,
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    client = CourtListenerClient(api_token="fake-token", base_url=BASE_URL, transport=transport)

    entries = client.get_all_docket_entries(69510553)

    assert entries[0].description == "Petition for Writ of Habeas Corpus"


def test_get_all_docket_entries_prefers_entry_description_when_present() -> None:
    payload = {
        "results": [
            {
                "id": 1,
                "entry_number": 1,
                "description": "Order granting motion",
                "date_filed": "2026-08-21",
                "recap_documents": [{"description": "Should not be used"}],
            }
        ],
        "next": None,
        "previous": None,
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    client = CourtListenerClient(api_token="fake-token", base_url=BASE_URL, transport=transport)

    entries = client.get_all_docket_entries(69510553)

    assert entries[0].description == "Order granting motion"


def test_get_all_docket_entries_follows_pagination() -> None:
    page_1 = {
        "results": [{"id": 1, "entry_number": 1, "description": "First entry", "date_filed": "2026-01-01"}],
        "next": "https://www.courtlistener.com/api/rest/v4/docket-entries/?cursor=abc",
        "previous": None,
    }
    page_2 = {
        "results": [{"id": 2, "entry_number": 2, "description": "Second entry", "date_filed": "2026-01-02"}],
        "next": None,
        "previous": None,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if "cursor=abc" in str(request.url):
            return httpx.Response(200, json=page_2)
        return httpx.Response(200, json=page_1)

    transport = httpx.MockTransport(handler)
    client = CourtListenerClient(api_token="fake-token", base_url=BASE_URL, transport=transport)

    entries = client.get_all_docket_entries(69510553)

    assert [e.courtlistener_entry_id for e in entries] == [1, 2]
