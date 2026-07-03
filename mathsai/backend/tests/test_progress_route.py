"""Phase 3 — Progress router (/api/progress). Real CRUD against the
teaching_log table — no AI dependency, no mocking needed."""

import pytest

from models import Topic


@pytest.fixture()
def topic(db_session) -> Topic:
    t = Topic(key_stage="KS4", strand="Algebra", topic_name="Quadratic Equations", edexcel_ref="A12")
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


def test_list_progress_empty_initially(client):
    response = client.get("/api/progress")
    assert response.status_code == 200
    assert response.json() == []


def test_log_taught_creates_entry(client, topic):
    response = client.post(
        "/api/progress",
        json={
            "topic_id": topic.id,
            "taught_date": "2026-03-05",
            "class_label": "Year 9 Set 2",
            "notes": "Went well, most got factorising",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["topic_id"] == topic.id
    assert data["class_label"] == "Year 9 Set 2"
    assert "id" in data


def test_log_taught_unknown_topic_returns_404(client):
    response = client.post(
        "/api/progress",
        json={"topic_id": 999999, "taught_date": "2026-03-05"},
    )
    assert response.status_code == 404


def test_log_taught_then_list_shows_entry(client, topic):
    client.post("/api/progress", json={"topic_id": topic.id, "taught_date": "2026-03-05"})
    response = client.get("/api/progress")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_topic_progress_empty_when_not_taught(client, topic):
    response = client.get(f"/api/progress/topic/{topic.id}")
    assert response.status_code == 200
    assert response.json() == []


def test_get_topic_progress_returns_entries_for_that_topic(client, topic):
    client.post("/api/progress", json={"topic_id": topic.id, "taught_date": "2026-03-05"})
    client.post("/api/progress", json={"topic_id": topic.id, "taught_date": "2026-03-12"})

    response = client.get(f"/api/progress/topic/{topic.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(entry["topic_id"] == topic.id for entry in data)


def test_get_topic_progress_unknown_topic_returns_404(client):
    response = client.get("/api/progress/topic/999999")
    assert response.status_code == 404


def test_delete_progress_removes_entry(client, topic):
    created = client.post(
        "/api/progress", json={"topic_id": topic.id, "taught_date": "2026-03-05"}
    ).json()

    response = client.delete(f"/api/progress/{created['id']}")
    assert response.status_code == 204

    remaining = client.get("/api/progress").json()
    assert remaining == []


def test_delete_progress_unknown_id_returns_404(client):
    response = client.delete("/api/progress/999999")
    assert response.status_code == 404
