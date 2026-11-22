"""Policy enforcement and lifecycle accounting tests for the dynamic API."""

from __future__ import annotations

import uuid

DEMO_USER = "demo@cryptavault.dev"
VIEWER_USER = "viewer@cryptavault.dev"
ADMIN_USER = "admin@cryptavault.dev"


def _upload(
    api_client,
    headers: dict[str, str],
    workspace_id: str,
    file_id: str,
    *,
    version: int = 1,
    payload: bytes = b"encrypted-payload",
) -> None:
    response = api_client.post(
        f"/api/workspaces/{workspace_id}/files/upload",
        headers=headers,
        data={
            "file_id": file_id,
            "version": str(version),
            "encrypted_meta": "ZW5jcnlwdGVkLW1ldGE=",
            "meta_iv": "MTIzNDU2Nzg5MDEy",
            "wrapped_key": "d3JhcHBlZC1rZXk=",
            "wrapped_iv": "MTIzNDU2Nzg5MDEy",
            "profile": "BALANCED",
            "storage_target": "local",
        },
        files={"ciphertext": ("payload.cv", payload, "application/octet-stream")},
    )
    assert response.status_code == 201, response.text


def _owned_workspace(api_client, headers: dict[str, str], name: str) -> str:
    response = api_client.post("/api/workspaces", headers=headers, json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _used_bytes(api_client, headers: dict[str, str]) -> int:
    response = api_client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["user"]["used_bytes"]


def _set_flag(api_client, admin_headers: dict[str, str], key: str, enabled: bool) -> None:
    response = api_client.put(
        f"/api/admin/flags/{key}", headers=admin_headers, json={"enabled": enabled}
    )
    assert response.status_code == 200, response.text


def test_share_creation_rejects_past_expiry_and_deletion_removes_shares(
    api_client, auth_headers
) -> None:
    """A share must expire in the future, and workspace deletion must purge shares."""
    headers = auth_headers(DEMO_USER)
    workspace_id = _owned_workspace(api_client, headers, "Share policy workspace")
    file_id = str(uuid.uuid4())
    before = _used_bytes(api_client, headers)
    try:
        _upload(api_client, headers, workspace_id, file_id, payload=b"share-policy-body")

        past = api_client.post(
            "/api/shares",
            headers=headers,
            json={"file_id": file_id, "expires_at": "2000-01-01T00:00:00Z"},
        )
        assert past.status_code == 422, past.text

        created = api_client.post(
            "/api/shares",
            headers=headers,
            json={"file_id": file_id, "expires_at": "2999-01-01T00:00:00Z", "max_uses": 5},
        )
        assert created.status_code == 201, created.text
        token = created.json()["token"]
        assert api_client.get(f"/api/shares/{token}").status_code == 200

        deleted = api_client.delete(f"/api/workspaces/{workspace_id}", headers=headers)
        assert deleted.status_code == 200, deleted.text
        assert api_client.get(f"/api/shares/{token}").status_code == 404
        assert _used_bytes(api_client, headers) == before
    finally:
        api_client.delete(f"/api/workspaces/{workspace_id}", headers=headers)


def test_permanent_delete_credits_each_version_creator(api_client, auth_headers) -> None:
    """Ciphertext quota is refunded to the uploader of each version, not the file owner."""
    demo_headers = auth_headers(DEMO_USER)
    viewer_headers = auth_headers(VIEWER_USER)
    workspace_id = _owned_workspace(api_client, demo_headers, "Quota attribution workspace")
    file_id = str(uuid.uuid4())
    add = api_client.post(
        f"/api/workspaces/{workspace_id}/members",
        headers=demo_headers,
        json={"email": VIEWER_USER, "role": "editor"},
    )
    assert add.status_code == 201, add.text
    demo_before = _used_bytes(api_client, demo_headers)
    viewer_before = _used_bytes(api_client, viewer_headers)
    try:
        _upload(api_client, demo_headers, workspace_id, file_id, payload=b"a" * 100)
        _upload(
            api_client,
            viewer_headers,
            workspace_id,
            file_id,
            version=2,
            payload=b"b" * 250,
        )
        assert _used_bytes(api_client, demo_headers) == demo_before + 100
        assert _used_bytes(api_client, viewer_headers) == viewer_before + 250

        deleted = api_client.delete(f"/api/files/{file_id}/permanent", headers=demo_headers)
        assert deleted.status_code == 200, deleted.text
        assert _used_bytes(api_client, demo_headers) == demo_before
        assert _used_bytes(api_client, viewer_headers) == viewer_before
    finally:
        api_client.delete(f"/api/workspaces/{workspace_id}", headers=demo_headers)


def test_feature_flags_disable_versions_connectors_and_writes(api_client, auth_headers) -> None:
    """Stored admin flags must change route behavior rather than being display-only."""
    admin_headers = auth_headers(ADMIN_USER)
    demo_headers = auth_headers(DEMO_USER)
    workspace_id = _owned_workspace(api_client, demo_headers, "Flag enforcement workspace")
    file_id = str(uuid.uuid4())
    try:
        # Version 1 is the initial upload and must stay available with versions disabled.
        _upload(api_client, demo_headers, workspace_id, file_id, payload=b"v1-body")

        _set_flag(api_client, admin_headers, "enable_versions", False)
        blocked = api_client.post(
            f"/api/workspaces/{workspace_id}/files/upload",
            headers=demo_headers,
            data={
                "file_id": file_id,
                "version": "2",
                "encrypted_meta": "ZW5jcnlwdGVkLW1ldGE=",
                "meta_iv": "MTIzNDU2Nzg5MDEy",
                "wrapped_key": "d3JhcHBlZC1rZXk=",
                "wrapped_iv": "MTIzNDU2Nzg5MDEy",
                "profile": "BALANCED",
                "storage_target": "local",
            },
            files={"ciphertext": ("v2.cv", b"v2-body", "application/octet-stream")},
        )
        assert blocked.status_code == 403, blocked.text
        restore = api_client.post(f"/api/files/{file_id}/restore/1", headers=demo_headers)
        assert restore.status_code == 403
        _set_flag(api_client, admin_headers, "enable_versions", True)

        _set_flag(api_client, admin_headers, "enable_cloud_connectors", False)
        cloud = api_client.post(
            "/api/storage/targets",
            headers=admin_headers,
            json={"name": "flag-gdrive", "kind": "gdrive", "config": {}},
        )
        assert cloud.status_code == 403, cloud.text
        _set_flag(api_client, admin_headers, "enable_cloud_connectors", True)

        _set_flag(api_client, admin_headers, "maintenance_mode", True)
        maintenance = api_client.post(
            f"/api/workspaces/{workspace_id}/files/upload",
            headers=demo_headers,
            data={
                "file_id": str(uuid.uuid4()),
                "version": "1",
                "encrypted_meta": "ZW5jcnlwdGVkLW1ldGE=",
                "meta_iv": "MTIzNDU2Nzg5MDEy",
                "wrapped_key": "d3JhcHBlZC1rZXk=",
                "wrapped_iv": "MTIzNDU2Nzg5MDEy",
                "profile": "BALANCED",
                "storage_target": "local",
            },
            files={"ciphertext": ("paused.cv", b"paused-body", "application/octet-stream")},
        )
        assert maintenance.status_code == 503, maintenance.text
        assert api_client.get("/api/workspaces", headers=demo_headers).status_code == 200
        _set_flag(api_client, admin_headers, "maintenance_mode", False)
    finally:
        for key, value in (
            ("enable_versions", True),
            ("enable_cloud_connectors", True),
            ("maintenance_mode", False),
        ):
            _set_flag(api_client, admin_headers, key, value)
        api_client.delete(f"/api/workspaces/{workspace_id}", headers=demo_headers)


def test_sharing_flag_blocks_new_shares_without_breaking_existing_links(
    api_client, auth_headers
) -> None:
    """Disabling sharing prevents new links but leaves existing policy in force."""
    admin_headers = auth_headers(ADMIN_USER)
    demo_headers = auth_headers(DEMO_USER)
    workspace_id = _owned_workspace(api_client, demo_headers, "Sharing flag workspace")
    file_id = str(uuid.uuid4())
    try:
        _upload(api_client, demo_headers, workspace_id, file_id, payload=b"sharing-flag-body")
        created = api_client.post(
            "/api/shares", headers=demo_headers, json={"file_id": file_id, "max_uses": 2}
        )
        assert created.status_code == 201, created.text
        token = created.json()["token"]

        _set_flag(api_client, admin_headers, "enable_sharing", False)
        blocked = api_client.post(
            "/api/shares", headers=demo_headers, json={"file_id": file_id, "max_uses": 2}
        )
        assert blocked.status_code == 403, blocked.text
        assert api_client.get(f"/api/shares/{token}").status_code == 200
        _set_flag(api_client, admin_headers, "enable_sharing", True)
    finally:
        _set_flag(api_client, admin_headers, "enable_sharing", True)
        api_client.delete(f"/api/workspaces/{workspace_id}", headers=demo_headers)
