from tests.conftest import ALL_ACTIONS, auth_headers

WORKSPACE = "ws_decisions"


def _payload():
    return {
        "sourceType": "scenario",
        "sourceId": "scn_1",
        "title": "Scenario draft",
        "reviewerUserIds": ["usr_1"],
    }


def _create(client):
    headers = auth_headers(WORKSPACE, "usr_owner", ALL_ACTIONS)
    resp = client.post(
        f"/api/v1/workspaces/{WORKSPACE}/approval-requests", json=_payload(), headers=headers
    )
    return resp.json()["id"], headers


def test_approve_transitions_to_final_state(client):
    request_id, headers = _create(client)
    resp = client.post(
        f"/api/v1/workspaces/{WORKSPACE}/approval-requests/{request_id}/approve",
        json={"comment": "Looks good"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_cannot_reject_after_approve(client):
    request_id, headers = _create(client)
    client.post(
        f"/api/v1/workspaces/{WORKSPACE}/approval-requests/{request_id}/approve",
        json={"comment": "ok"},
        headers=headers,
    )
    resp = client.post(
        f"/api/v1/workspaces/{WORKSPACE}/approval-requests/{request_id}/reject",
        json={"reason": "changed my mind"},
        headers=headers,
    )
    assert resp.status_code == 409


def test_reject_requires_reason(client):
    request_id, headers = _create(client)
    resp = client.post(
        f"/api/v1/workspaces/{WORKSPACE}/approval-requests/{request_id}/reject",
        json={},
        headers=headers,
    )
    assert resp.status_code == 422


def test_cancel_pending_request(client):
    request_id, headers = _create(client)
    resp = client.post(
        f"/api/v1/workspaces/{WORKSPACE}/approval-requests/{request_id}/cancel",
        json={"reason": "Draft was removed"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
