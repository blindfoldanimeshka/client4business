from tests.conftest import ALL_ACTIONS, auth_headers

WORKSPACE = "ws_1"


def _create_payload():
    return {
        "sourceType": "publication",
        "sourceId": "pub_123",
        "title": "Instagram reel draft",
        "description": "Needs final approval",
        "reviewerUserIds": ["usr_1", "usr_2"],
    }


def test_create_and_get_approval_request(client):
    headers = auth_headers(WORKSPACE, "usr_owner", ALL_ACTIONS)

    create_resp = client.post(
        f"/api/v1/workspaces/{WORKSPACE}/approval-requests",
        json=_create_payload(),
        headers=headers,
    )
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["status"] == "pending"
    assert body["workspaceId"] == WORKSPACE
    assert body["reviewerUserIds"] == ["usr_1", "usr_2"]

    get_resp = client.get(
        f"/api/v1/workspaces/{WORKSPACE}/approval-requests/{body['id']}",
        headers=headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == body["id"]


def test_create_requires_action(client):
    headers = auth_headers(WORKSPACE, "usr_owner", ["approval:read"])  # нет approval:create
    resp = client.post(
        f"/api/v1/workspaces/{WORKSPACE}/approval-requests",
        json=_create_payload(),
        headers=headers,
    )
    assert resp.status_code == 403


def test_list_approval_requests(client):
    headers = auth_headers(WORKSPACE, "usr_owner", ALL_ACTIONS)
    client.post(
        f"/api/v1/workspaces/{WORKSPACE}/approval-requests",
        json=_create_payload(),
        headers=headers,
    )
    list_resp = client.get(
        f"/api/v1/workspaces/{WORKSPACE}/approval-requests", headers=headers
    )
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
