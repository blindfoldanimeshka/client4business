from tests.conftest import ALL_ACTIONS, auth_headers

WORKSPACE = "ws_idem"


def _payload():
    return {
        "sourceType": "publication",
        "sourceId": "pub_1",
        "title": "Draft",
        "reviewerUserIds": ["usr_1"],
    }


def test_repeated_create_with_same_idempotency_key_does_not_duplicate(client):
    headers = auth_headers(WORKSPACE, "usr_owner", ALL_ACTIONS)
    headers["Idempotency-Key"] = "key-123"

    first = client.post(
        f"/api/v1/workspaces/{WORKSPACE}/approval-requests",
        json=_payload(),
        headers=headers,
    )
    second = client.post(
        f"/api/v1/workspaces/{WORKSPACE}/approval-requests",
        json=_payload(),
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    listing = client.get(
        f"/api/v1/workspaces/{WORKSPACE}/approval-requests",
        headers=auth_headers(WORKSPACE, "usr_owner", ALL_ACTIONS),
    )
    assert listing.json()["total"] == 1


def test_same_key_different_body_conflicts(client):
    headers = auth_headers(WORKSPACE, "usr_owner", ALL_ACTIONS)
    headers["Idempotency-Key"] = "key-456"

    client.post(
        f"/api/v1/workspaces/{WORKSPACE}/approval-requests",
        json=_payload(),
        headers=headers,
    )
    other_payload = _payload()
    other_payload["title"] = "Different title"
    resp = client.post(
        f"/api/v1/workspaces/{WORKSPACE}/approval-requests",
        json=other_payload,
        headers=headers,
    )
    assert resp.status_code == 409
