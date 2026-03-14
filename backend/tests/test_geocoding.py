from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from data_sources import geocoding


class _FakeResponse:
    def __init__(self, url: str, status_code: int, payload):
        self._url = url
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=httpx.Request("GET", self._url),
                response=httpx.Response(self.status_code, request=httpx.Request("GET", self._url)),
            )

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, params=None, headers=None):
        if "api.maptiler.com/geocoding" in url:
            return _FakeResponse(url, 403, {"message": "forbidden"})
        if "nominatim.openstreetmap.org/search" in url:
            payload = [
                {
                    "lat": "54.5743",
                    "lon": "-118.0871",
                    "address": {"county": "Municipal District of Greenview"},
                }
            ]
            return _FakeResponse(url, 200, payload)
        return _FakeResponse(url, 404, {})


@pytest.mark.asyncio
async def test_geocode_uses_nominatim_when_maptiler_forbidden(monkeypatch):
    monkeypatch.setattr(
        geocoding,
        "get_settings",
        lambda: SimpleNamespace(
            maptiler_api_key="dummy-maptiler-key",
            strict_data_mode=True,
            request_timeout_seconds=5.0,
            nominatim_user_agent="unit-test-agent",
        ),
    )
    monkeypatch.setattr(geocoding.httpx, "AsyncClient", _FakeAsyncClient)

    location, freshness = await geocoding.geocode_address("Grande Prairie, AB", "AB")

    assert location["municipality"] == "Municipal District of Greenview"
    assert location["census_subdivision_id"] == ""
    assert freshness["maptiler_geocoding"].startswith("live:nominatim:")


@pytest.mark.asyncio
async def test_geocode_simplifies_query_for_nominatim(monkeypatch):
    queried_addresses: list[str] = []

    class _RetryClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url: str, params=None, headers=None):
            if "api.maptiler.com/geocoding" in url:
                return _FakeResponse(url, 403, {"message": "forbidden"})
            if "nominatim.openstreetmap.org/search" in url:
                query = str((params or {}).get("q") or "")
                queried_addresses.append(query)
                if query == "Grande Prairie, Alberta, Canada":
                    payload = [
                        {
                            "lat": "55.17108",
                            "lon": "-118.7949873",
                            "address": {"city": "Grande Prairie"},
                        }
                    ]
                    return _FakeResponse(url, 200, payload)
                return _FakeResponse(url, 200, [])
            return _FakeResponse(url, 404, {})

    monkeypatch.setattr(
        geocoding,
        "get_settings",
        lambda: SimpleNamespace(
            maptiler_api_key="dummy-maptiler-key",
            strict_data_mode=True,
            request_timeout_seconds=5.0,
            nominatim_user_agent="unit-test-agent",
        ),
    )
    monkeypatch.setattr(geocoding.httpx, "AsyncClient", _RetryClient)

    location, freshness = await geocoding.geocode_address(
        "Municipal District of Greenview, Grande Prairie, Alberta, Canada",
        "AB",
    )

    assert "Municipal District of Greenview, Grande Prairie, Alberta, Canada" in queried_addresses
    assert "Grande Prairie, Alberta, Canada" in queried_addresses
    assert location["municipality"] == "Grande Prairie"
    assert freshness["maptiler_geocoding"].startswith("live:nominatim:")
