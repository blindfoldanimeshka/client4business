from tests.conftest import ALL_ACTIONS, auth_headers

WS_A = "ws_a"
WS_B = "ws_b"


def _payload():
    return {
        "sourceType": "publication",
        "sourceId": "pub_1",
        "title": "Draft",
        "reviewerUserIds": ["usr_1"],
    }


def test_workspace_cannot_read_other_workspace_request(client):
    headers_a = auth_headers(WS_A, "usr_a", ALL_ACTIONS)
    create_resp = client.post(
        f"/api/v1/workspaces/{WS_A}/approval-requests", json=_payload(), headers=headers_a
    )
    request_id = create_resp.json()["id"]

    # Тот же пользователь пытается прочитать заявку через чужой workspace в URL,
    # но заголовок X-Workspace-Id у него - ws_b -> должно быть 404, а не утечка.
    headers_b = auth_headers(WS_B, "usr_a", ALL_ACTIONS)
    resp = client.get(
        f"/api/v1/workspaces/{WS_A}/approval-requests/{request_id}", headers=headers_b
    )
    assert resp.status_code == 404


def test_list_is_scoped_to_workspace(client):
    headers_a = auth_headers(WS_A, "usr_a", ALL_ACTIONS)
    headers_b = auth_headers(WS_B, "usr_b", ALL_ACTIONS)

    client.post(f"/api/v1/workspaces/{WS_A}/approval-requests", json=_payload(), headers=headers_a)
    client.post(f"/api/v1/workspaces/{WS_B}/approval-requests", json=_payload(), headers=headers_b)

    list_a = client.get(f"/api/v1/workspaces/{WS_A}/approval-requests", headers=headers_a).json()
    list_b = client.get(f"/api/v1/workspaces/{WS_B}/approval-requests", headers=headers_b).json()

    assert list_a["total"] == 1
    assert list_b["total"] == 1
    assert list_a["items"][0]["id"] != list_b["items"][0]["id"]
