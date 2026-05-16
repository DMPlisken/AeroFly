"""Integration tests for /api/favorites — anonymous device-id based bookmarks."""

from __future__ import annotations

from fastapi.testclient import TestClient


DEVICE_A = "11111111-1111-4111-8111-111111111111"
DEVICE_B = "22222222-2222-4222-8222-222222222222"


def _h(device_id: str) -> dict[str, str]:
    return {"X-Device-Id": device_id}


class TestDeviceIdHeader:
    def test_missing_header_returns_400(self, client: TestClient):
        response = client.get("/api/favorites")
        assert response.status_code == 400
        assert "X-Device-Id" in response.json()["detail"]

    def test_too_short_header_returns_400(self, client: TestClient):
        response = client.get("/api/favorites", headers={"X-Device-Id": "abc"})
        assert response.status_code == 400

    def test_post_missing_header_returns_400(self, client: TestClient):
        response = client.post("/api/favorites", json={"icao": "EDDF"})
        assert response.status_code == 400

    def test_delete_missing_header_returns_400(self, client: TestClient):
        response = client.delete("/api/favorites/EDDF")
        assert response.status_code == 400


class TestList:
    def test_empty_list_when_no_favorites(self, client: TestClient):
        response = client.get("/api/favorites", headers=_h(DEVICE_A))
        assert response.status_code == 200
        assert response.json() == []

    def test_list_returns_favorites_sorted_by_icao(self, client: TestClient):
        for icao in ("EDDM", "EDDF", "EDDH"):
            client.post("/api/favorites", json={"icao": icao}, headers=_h(DEVICE_A))

        response = client.get("/api/favorites", headers=_h(DEVICE_A))
        assert response.status_code == 200
        assert [f["icao"] for f in response.json()] == ["EDDF", "EDDH", "EDDM"]

    def test_devices_are_isolated(self, client: TestClient):
        client.post("/api/favorites", json={"icao": "EDDF"}, headers=_h(DEVICE_A))
        client.post("/api/favorites", json={"icao": "EDDM"}, headers=_h(DEVICE_B))

        a_list = client.get("/api/favorites", headers=_h(DEVICE_A)).json()
        b_list = client.get("/api/favorites", headers=_h(DEVICE_B)).json()
        assert [f["icao"] for f in a_list] == ["EDDF"]
        assert [f["icao"] for f in b_list] == ["EDDM"]


class TestAdd:
    def test_add_returns_201_with_payload(self, client: TestClient):
        response = client.post("/api/favorites", json={"icao": "EDDF"}, headers=_h(DEVICE_A))
        assert response.status_code == 201
        body = response.json()
        assert body["icao"] == "EDDF"
        assert "created_at" in body

    def test_icao_is_normalized_to_uppercase(self, client: TestClient):
        response = client.post("/api/favorites", json={"icao": "eddf"}, headers=_h(DEVICE_A))
        assert response.status_code == 201
        assert response.json()["icao"] == "EDDF"

        listed = client.get("/api/favorites", headers=_h(DEVICE_A)).json()
        assert [f["icao"] for f in listed] == ["EDDF"]

    def test_add_is_idempotent(self, client: TestClient):
        first = client.post("/api/favorites", json={"icao": "EDDF"}, headers=_h(DEVICE_A))
        second = client.post("/api/favorites", json={"icao": "EDDF"}, headers=_h(DEVICE_A))
        assert first.status_code == 201
        assert second.status_code == 201
        # created_at must not advance on re-add (preserves original timestamp).
        assert first.json()["created_at"] == second.json()["created_at"]

        listed = client.get("/api/favorites", headers=_h(DEVICE_A)).json()
        assert len(listed) == 1

    def test_rejects_empty_icao(self, client: TestClient):
        response = client.post("/api/favorites", json={"icao": ""}, headers=_h(DEVICE_A))
        assert response.status_code == 422

    def test_rejects_overlong_icao(self, client: TestClient):
        response = client.post(
            "/api/favorites",
            json={"icao": "TOOLONGICAOCODE"},
            headers=_h(DEVICE_A),
        )
        assert response.status_code == 422


class TestDelete:
    def test_delete_existing_returns_204(self, client: TestClient):
        client.post("/api/favorites", json={"icao": "EDDF"}, headers=_h(DEVICE_A))
        response = client.delete("/api/favorites/EDDF", headers=_h(DEVICE_A))
        assert response.status_code == 204

        listed = client.get("/api/favorites", headers=_h(DEVICE_A)).json()
        assert listed == []

    def test_delete_missing_returns_204_idempotent(self, client: TestClient):
        response = client.delete("/api/favorites/EDDF", headers=_h(DEVICE_A))
        assert response.status_code == 204

    def test_delete_normalizes_icao_case(self, client: TestClient):
        client.post("/api/favorites", json={"icao": "EDDF"}, headers=_h(DEVICE_A))
        response = client.delete("/api/favorites/eddf", headers=_h(DEVICE_A))
        assert response.status_code == 204

        listed = client.get("/api/favorites", headers=_h(DEVICE_A)).json()
        assert listed == []

    def test_delete_does_not_affect_other_devices(self, client: TestClient):
        client.post("/api/favorites", json={"icao": "EDDF"}, headers=_h(DEVICE_A))
        client.post("/api/favorites", json={"icao": "EDDF"}, headers=_h(DEVICE_B))

        response = client.delete("/api/favorites/EDDF", headers=_h(DEVICE_A))
        assert response.status_code == 204

        assert client.get("/api/favorites", headers=_h(DEVICE_A)).json() == []
        assert [f["icao"] for f in client.get("/api/favorites", headers=_h(DEVICE_B)).json()] == ["EDDF"]
