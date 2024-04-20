"""End-to-end coverage of the HTTP surface."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

PLAN = {
    "mappings": [
        {
            "target_column": "PolicyNumber",
            "source_column": "Policy_No",
            "transform": "strip_separators",
        },
        {
            "target_column": "Premium",
            "source_column": "Monthly_Premium",
            "transform": "to_integer",
        },
    ]
}


def files(sample_files: tuple[bytes, bytes]) -> dict:
    source, target = sample_files
    return {
        "input_table": ("employee_policies.csv", source, "text/csv"),
        "target_table": ("target_schema.csv", target, "text/csv"),
    }


def test_health(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["suggester"] == "local"
    assert body["llm_configured"] is False


def test_index_points_at_the_docs(client: TestClient) -> None:
    assert client.get("/").json()["docs"] == "/docs"


def test_transform_catalogue(client: TestClient) -> None:
    names = {item["name"] for item in client.get("/api/transforms").json()}
    assert {"identity", "to_date", "strip_separators"} <= names


def test_suggest_maps_the_sample_files(
    client: TestClient, sample_files: tuple[bytes, bytes]
) -> None:
    response = client.post("/api/mappings/suggest", files=files(sample_files))
    assert response.status_code == 200
    body = response.json()

    assert body["suggester"] == "local"
    assert body["source"]["row_count"] == 12
    assert [column["name"] for column in body["target"]["columns"]] == [
        "Date",
        "EmployeeName",
        "Plan",
        "PolicyNumber",
        "Premium",
    ]
    chosen = {
        item["target_column"]: item["best"]["source_column"]
        for item in body["suggestions"]
    }
    assert chosen == {
        "Date": "Date_of_Policy",
        "EmployeeName": "FullName",
        "Plan": "Insurance_Plan",
        "PolicyNumber": "Policy_No",
        "Premium": "Monthly_Premium",
    }
    assert body["run_id"] >= 1


def test_suggest_rejects_a_non_csv(
    client: TestClient, sample_files: tuple[bytes, bytes]
) -> None:
    payload = files(sample_files)
    payload["input_table"] = ("payload.exe", b"nope", "application/octet-stream")
    response = client.post("/api/mappings/suggest", files=payload)
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_file"


def test_suggest_rejects_a_header_only_file(
    client: TestClient, sample_files: tuple[bytes, bytes]
) -> None:
    payload = files(sample_files)
    payload["input_table"] = ("empty.csv", b"a,b,c\n", "text/csv")
    response = client.post("/api/mappings/suggest", files=payload)
    assert response.status_code == 422
    assert response.json()["error"] == "empty_file"


def test_traversal_filename_is_reduced_to_a_bare_name(
    client: TestClient, sample_files: tuple[bytes, bytes]
) -> None:
    source, target = sample_files
    response = client.post(
        "/api/mappings/suggest",
        files={
            "input_table": ("../../etc/passwd.csv", source, "text/csv"),
            "target_table": ("target_schema.csv", target, "text/csv"),
        },
    )
    assert response.status_code == 200
    assert response.json()["source"]["filename"] == "passwd.csv"


def test_apply_returns_a_preview_page(
    client: TestClient, sample_files: tuple[bytes, bytes]
) -> None:
    source, _ = sample_files
    response = client.post(
        "/api/mappings/apply",
        params={"limit": 2, "offset": 1},
        data={"plan": json.dumps(PLAN)},
        files={"input_table": ("employee_policies.csv", source, "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["columns"] == ["PolicyNumber", "Premium"]
    assert body["total_rows"] == 12
    assert body["rows"] == [
        {"PolicyNumber": "CD67890", "Premium": "50"},
        {"PolicyNumber": "EF10111", "Premium": "150"},
    ]


def test_apply_can_stream_the_whole_csv(
    client: TestClient, sample_files: tuple[bytes, bytes]
) -> None:
    source, _ = sample_files
    response = client.post(
        "/api/mappings/apply",
        params={"download": True},
        data={"plan": json.dumps(PLAN)},
        files={"input_table": ("employee_policies.csv", source, "text/csv")},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    lines = response.text.strip().splitlines()
    assert lines[0] == "PolicyNumber,Premium"
    assert len(lines) == 13


def test_apply_rejects_an_unknown_transform(
    client: TestClient, sample_files: tuple[bytes, bytes]
) -> None:
    source, _ = sample_files
    bad = {
        "mappings": [
            {
                "target_column": "X",
                "source_column": "Policy_No",
                "transform": "eval",
            }
        ]
    }
    response = client.post(
        "/api/mappings/apply",
        data={"plan": json.dumps(bad)},
        files={"input_table": ("employee_policies.csv", source, "text/csv")},
    )
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_plan"


def test_apply_rejects_malformed_plan_json(
    client: TestClient, sample_files: tuple[bytes, bytes]
) -> None:
    source, _ = sample_files
    response = client.post(
        "/api/mappings/apply",
        data={"plan": "{not json"},
        files={"input_table": ("employee_policies.csv", source, "text/csv")},
    )
    assert response.status_code == 422


def test_upload_over_the_size_cap_is_refused(
    client: TestClient, settings, sample_files: tuple[bytes, bytes]
) -> None:
    settings.max_upload_bytes = 64
    source, target = sample_files
    response = client.post(
        "/api/mappings/suggest",
        files={
            "input_table": ("big.csv", source, "text/csv"),
            "target_table": ("target_schema.csv", target, "text/csv"),
        },
    )
    assert response.status_code == 413
    assert response.json()["error"] == "file_too_large"
