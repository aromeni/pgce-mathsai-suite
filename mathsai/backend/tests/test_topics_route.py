"""Phase 1/3 — Topics router (/api/topics)."""


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


def test_get_ks3_topics_returns_only_ks3(client):
    response = client.get("/api/topics/ks3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 34
    assert all(t["key_stage"] == "KS3" for t in data)


def test_get_ks4_topics_returns_only_ks4(client):
    response = client.get("/api/topics/ks4")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 40
    assert all(t["key_stage"] == "KS4" for t in data)


def test_search_topics_matches_substring_case_insensitively(client):
    response = client.get("/api/topics/search", params={"q": "quadratic"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert all("quadratic" in t["topic_name"].lower() for t in data)


def test_search_topics_no_match_returns_empty_list(client):
    response = client.get("/api/topics/search", params={"q": "nonexistent-topic-xyz"})
    assert response.status_code == 200
    assert response.json() == []


def test_get_single_topic_by_id(client):
    all_topics = client.get("/api/topics").json()
    first_id = all_topics[0]["id"]

    response = client.get(f"/api/topics/{first_id}")
    assert response.status_code == 200
    assert response.json()["id"] == first_id


def test_get_single_topic_not_found_returns_404(client):
    response = client.get("/api/topics/999999")
    assert response.status_code == 404
