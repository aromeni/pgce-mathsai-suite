"""Phase 1 — GET /api/topics."""


def test_get_topics_returns_full_curriculum(client):
    response = client.get("/api/topics")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 74
    expected_keys = {
        "id",
        "key_stage",
        "strand",
        "topic_name",
        "edexcel_ref",
        "difficulty_band",
        "created_at",
    }
    assert expected_keys <= set(data[0].keys())


def test_get_topics_split_by_key_stage(client):
    response = client.get("/api/topics")
    data = response.json()

    ks3 = [t for t in data if t["key_stage"] == "KS3"]
    ks4 = [t for t in data if t["key_stage"] == "KS4"]

    assert len(ks3) == 34
    assert len(ks4) == 40


def test_get_topics_is_stable_across_repeated_calls(client):
    """The startup seed is idempotent, so repeated requests return the
    same count rather than growing."""
    first = client.get("/api/topics").json()
    second = client.get("/api/topics").json()
    assert len(first) == len(second) == 74
