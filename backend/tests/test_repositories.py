import pytest

from backend.app.db import connect, release_connection
from backend.app.repositories import catalog
from backend.app.repositories.base import (
    RepositoryError,
    _validate_order_by,
    _validate_table,
    decode_row,
    get_by_id,
    list_table,
)


@pytest.fixture
def db():
    connection = connect()
    try:
        yield connection
    finally:
        release_connection(connection)


def test_validate_table_rejects_unknown():
    with pytest.raises(RepositoryError, match="invalid_table"):
        _validate_table("users; DROP TABLE projects")


def test_validate_order_by_accepts_desc():
    assert _validate_order_by("created_at DESC") == "created_at DESC"


def test_validate_order_by_rejects_bad_column():
    with pytest.raises(RepositoryError, match="invalid_order_by"):
        _validate_order_by("password_hash DESC")


def test_list_table_projects(db):
    projects = list_table(db, "projects", "created_at DESC")
    assert len(projects) >= 1
    assert "project_id" in projects[0]


def test_list_projects_paginated(db):
    items, total = catalog.list_projects_paginated(db, limit=1, offset=0)
    assert total >= 1
    assert len(items) == 1


def test_list_project_candidates_filtered_sort(db):
    items, total = catalog.list_project_candidates_filtered(
        db,
        "proj_pd1_0423",
        sort="plddt",
        order="desc",
        limit=3,
    )
    assert total >= 1
    assert len(items) <= 3
    scores = [item["plddt"] for item in items]
    assert scores == sorted(scores, reverse=True)


def test_list_project_candidates_invalid_sort(db):
    with pytest.raises(ValueError, match="invalid_sort"):
        catalog.list_project_candidates_filtered(db, "proj_pd1_0423", sort="password")


def test_get_workflow_run_project_id(db):
    project_id = catalog.get_workflow_run_project_id(db, "run_pd1_round1")
    assert project_id == "proj_pd1_0423"


def test_get_by_id_missing_candidate(db):
    assert get_by_id(db, "candidates", "candidate_id", "missing_candidate") is None


def test_decode_row_parses_json_column():
    class FakeRow:
        def __init__(self):
            self._data = {"metadata_json": '{"chains": ["A"]}', "enabled": 1}

        def keys(self):
            return self._data.keys()

        def __iter__(self):
            return iter(self._data.items())

        def __getitem__(self, key):
            return self._data[key]

    row = decode_row(FakeRow())
    assert row is not None
    assert row["metadata_json"] == {"chains": ["A"]}
    assert row["enabled"] is True
