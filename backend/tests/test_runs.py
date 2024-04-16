"""The suggestion-run log and its pagination."""

from __future__ import annotations

from fastapi.testclient import TestClient


def suggest(client: TestClient, sample_files: tuple[bytes, bytes]) -> dict:
    source, target = sample_files
    return client.post(
        "/api/mappings/suggest",
        files={
            "input_table": ("employee_policies.csv", source, "text/csv"),
            "target_table": ("target_schema.csv", target, "text/csv"),
        },
    ).json()


def test_runs_are_empty_before_any_suggestion(client: TestClient) -> None:
    body = client.get("/api/runs").json()
    assert body == {"total": 0, "limit": 20, "offset": 0, "items": []}


def test_a_run_is_recorded_per_suggestion(
    client: TestClient, sample_files: tuple[bytes, bytes]
) -> None:
    suggest(client, sample_files)
    body = client.get("/api/runs").json()

    assert body["total"] == 1
    [item] = body["items"]
    assert item["source_filename"] == "employee_policies.csv"
    assert item["target_columns"] == 5
    assert item["matched_columns"] == 5
    assert item["suggester"] == "local"


def test_run_detail_carries_the_stored_suggestions(
    client: TestClient, sample_files: tuple[bytes, bytes]
) -> None:
    run_id = suggest(client, sample_files)["run_id"]
    body = client.get(f"/api/runs/{run_id}").json()
    targets = [item["target_column"] for item in body["payload"]["suggestions"]]
    assert targets[0] == "Date"


def test_missing_run_is_a_404(client: TestClient) -> None:
    response = client.get("/api/runs/999")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_pagination_walks_the_log(
    client: TestClient, sample_files: tuple[bytes, bytes]
) -> None:
    for _ in range(3):
        suggest(client, sample_files)

    first = client.get("/api/runs", params={"limit": 2}).json()
    second = client.get("/api/runs", params={"limit": 2, "offset": 2}).json()

    assert first["total"] == 3
    assert len(first["items"]) == 2
    assert len(second["items"]) == 1
    ids = [item["id"] for item in first["items"] + second["items"]]
    assert ids == sorted(ids, reverse=True)


def test_page_size_is_capped(client: TestClient) -> None:
    body = client.get("/api/runs", params={"limit": 10_000}).json()
    assert body["limit"] == 100
