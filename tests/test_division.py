import pytest

from .test_regulation import test_create_regulation
from .test_department import test_create_department


@pytest.fixture
def test_create_division(authorized_client, test_create_regulation, test_create_department):
    regulation = test_create_regulation
    department_1 = test_create_department
    department_2 = test_create_department
    res = authorized_client.post(
        '/divisions',
        json={
            "name": "test division",
            "hours": 142,
            "private": False,
            "group": False,
            "regulation_id": regulation["id"],
            "department_1_id": department_1["id"],
            "department_2_id": department_2["id"]
        }
    )
    assert res.status_code == 201
    assert res.json()["name"] == "test division"
    assert res.json()["hours"] == 142
    assert res.json()["private"] == False
    assert res.json()["group"] == False
    assert res.json()["regulation"]["id"] == regulation["id"]
    assert res.json()["department_1"]["id"] == department_1["id"]
    assert res.json()["department_2"]["id"] == department_2["id"]
    return res.json()


def test_get_all_divisions(authorized_client):
    res = authorized_client.get(
        '/divisions',
    )
    assert res.status_code == 200


def test_get_division(authorized_client, test_create_division):
    division = test_create_division
    res = authorized_client.get(
        f'/divisions/{division["id"]}',
    )
    assert res.status_code == 200


def test_get_non_existing_division(authorized_client):
    res = authorized_client.get(
        '/divisions/-1',
    )
    assert res.status_code == 404


def test_update_division(authorized_client, test_create_division, test_create_regulation, test_create_department):
    regulation = test_create_regulation
    department_1 = test_create_department
    department_2 = test_create_department
    division = {
        **test_create_division,
        'name': "updated division",
        "hours": 142,
        "private": False,
        "group": False,
        "regulation_id": regulation["id"],
        "department_1_id": department_1["id"],
        "department_2_id": department_2["id"]
    }
    res = authorized_client.put(
        f'/divisions/{division["id"]}',
        json=division
    )
    assert res.status_code == 200
    assert res.json()['name'] == "updated division"
    assert res.json()["hours"] == 142
    assert res.json()["private"] == False
    assert res.json()["group"] == False
    assert res.json()["regulation"]["id"] == regulation["id"]
    assert res.json()["department_1"]["id"] == department_1["id"]
    assert res.json()["department_2"]["id"] == department_2["id"]


def test_update_non_exisitng_division(authorized_client, test_create_regulation, test_create_department):
    regulation = test_create_regulation
    department_1 = test_create_department
    department_2 = test_create_department
    division = {
        'name': "updated division",
        "hours": 142,
        "private": False,
        "group": False,
        "regulation_id": regulation["id"],
        "department_1_id": department_1["id"],
        "department_2_id": department_2["id"]
    }
    res = authorized_client.put(
        '/divisions/-1',
        json=division
    )
    assert res.status_code == 404


def test_delete_division(authorized_client, test_create_division):
    division = test_create_division
    res = authorized_client.delete(
        f'/divisions/{division["id"]}',
    )
    assert res.status_code == 204


def test_delete_non_exisitng_division(authorized_client):
    res = authorized_client.delete(
        '/divisions/-1',
    )
    assert res.status_code == 404