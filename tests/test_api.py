"""End-to-end API tests covering core workflows."""
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Any]:
    engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()
    Path("test.db").unlink(missing_ok=True)


@pytest.fixture()
def client(test_engine: Any) -> Iterator[TestClient]:
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, class_=Session)

    def override_get_db() -> Iterator[Session]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_full_api_flow(client: TestClient) -> None:
    register_response = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "name": "Alice", "password": "secret123"},
    )
    assert register_response.status_code == 201
    body = register_response.json()
    token = body["token"]
    user = body["user"]
    assert user["email"] == "alice@example.com"

    # login for good measure
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "secret123"},
    )
    assert login_response.status_code == 200
    login_token = login_response.json()["token"]
    assert login_token

    headers = _auth_headers(token)

    workspace_resp = client.post("/workspaces", json={"name": "Acme"}, headers=headers)
    assert workspace_resp.status_code == 201
    workspace = workspace_resp.json()
    workspace_id = workspace["id"]
    assert workspace["owner"]["email"] == "alice@example.com"

    list_workspaces = client.get("/workspaces", headers=headers)
    assert list_workspaces.status_code == 200
    assert len(list_workspaces.json()) == 1

    project_resp = client.post(
        "/projects",
        json={"name": "Launch", "workspace_id": workspace_id, "description": "Site rebuild"},
        headers=headers,
    )
    assert project_resp.status_code == 201
    project = project_resp.json()
    project_id = project["id"]
    assert project["workspace"]["id"] == workspace_id

    section_resp = client.post(
        "/sections",
        json={"name": "To Do", "project_id": project_id, "position": 0},
        headers=headers,
    )
    assert section_resp.status_code == 201
    section_id = section_resp.json()["id"]

    task_resp = client.post(
        "/tasks",
        json={
            "name": "Design hero",
            "project_id": project_id,
            "section_id": section_id,
            "description": "Create first-pass mockups",
        },
        headers=headers,
    )
    assert task_resp.status_code == 201
    task = task_resp.json()
    task_id = task["id"]
    assert task["completed"] is False
    assert task["project"]["id"] == project_id

    get_task_resp = client.get(f"/tasks/{task_id}", headers=headers)
    assert get_task_resp.status_code == 200
    assert get_task_resp.json()["project"]["workspace"]["id"] == workspace_id

    list_tasks_resp = client.get(
        "/tasks",
        params={"workspace_id": workspace_id},
        headers=headers,
    )
    assert list_tasks_resp.status_code == 200
    payload = list_tasks_resp.json()
    assert payload["pagination"]["total"] == 1
    assert len(payload["data"]) == 1

    comment_resp = client.post(
        f"/tasks/{task_id}/comments",
        json={"text": "Remember mobile breakpoints"},
        headers=headers,
    )
    assert comment_resp.status_code == 201
    comment = comment_resp.json()
    comment_id = comment["id"]
    assert comment["text"] == "Remember mobile breakpoints"

    comments_list = client.get(f"/tasks/{task_id}/comments", headers=headers)
    assert comments_list.status_code == 200
    assert len(comments_list.json()) == 1

    updated_comment = client.patch(
        f"/comments/{comment_id}",
        json={"text": "Add tablet views"},
        headers=headers,
    )
    assert updated_comment.status_code == 200
    assert updated_comment.json()["text"] == "Add tablet views"

    attachment_resp = client.post(
        f"/tasks/{task_id}/attachments",
        json={"filename": "brief.pdf", "url": "http://example.com/brief.pdf"},
        headers=headers,
    )
    assert attachment_resp.status_code == 201
    attachment_id = attachment_resp.json()["id"]

    attachments_list = client.get(f"/tasks/{task_id}/attachments", headers=headers)
    assert attachments_list.status_code == 200
    assert len(attachments_list.json()) == 1

    tag_resp = client.post(
        "/tags",
        json={"name": "High Priority", "workspace_id": workspace_id, "color": "#ff0000"},
        headers=headers,
    )
    assert tag_resp.status_code == 201
    tag_id = tag_resp.json()["id"]

    assign_tag = client.post(f"/tags/tasks/{task_id}/tags/{tag_id}", headers=headers)
    assert assign_tag.status_code == 204

    unassign_tag = client.delete(f"/tags/tasks/{task_id}/tags/{tag_id}", headers=headers)
    assert unassign_tag.status_code == 204

    custom_field_resp = client.post(
        f"/projects/{project_id}/custom-fields",
        json={
            "name": "Priority",
            "type": "dropdown",
            "project_id": project_id,
            "options": [{"value": "High"}],
        },
        headers=headers,
    )
    assert custom_field_resp.status_code == 201
    custom_field_id = custom_field_resp.json()["id"]

    set_value_resp = client.post(
        f"/tasks/{task_id}/custom-fields/{custom_field_id}",
        json={"value_text": "High"},
        headers=headers,
    )
    assert set_value_resp.status_code == 200
    assert set_value_resp.json()["name"] == "Priority"

    clear_value_resp = client.delete(
        f"/tasks/{task_id}/custom-fields/{custom_field_id}",
        headers=headers,
    )
    assert clear_value_resp.status_code == 204

    team_resp = client.post(
        "/teams",
        json={"name": "Design", "workspace_id": workspace_id},
        headers=headers,
    )
    assert team_resp.status_code == 201
    assert len(team_resp.json()["members"]) == 1

    delete_comment = client.delete(f"/comments/{comment_id}", headers=headers)
    assert delete_comment.status_code == 204

    delete_attachment = client.delete(f"/attachments/{attachment_id}", headers=headers)
    assert delete_attachment.status_code == 204

    delete_task = client.delete(f"/tasks/{task_id}", headers=headers)
    assert delete_task.status_code == 204

    final_tasks = client.get(
        "/tasks",
        params={"workspace_id": workspace_id},
        headers=headers,
    )
    assert final_tasks.json()["pagination"]["total"] == 0
