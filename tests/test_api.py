"""
CRM API Tests
Run: python -m pytest tests/test_api.py -v
"""

import json
import os
import sys
import tempfile

import pytest

# Add crm directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "crm"))

from app import app
from models import init_db, DB_PATH
import models


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    """Use a temp database for each test."""
    db_path = str(tmp_path / "test.db")
    models.DB_PATH = db_path
    init_db()
    yield
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# --- Contact Tests ---

def test_create_contact(client):
    res = client.post("/api/contacts", json={
        "first_name": "John", "last_name": "Doe",
        "email": "john@example.com", "company": "ACME Electric"
    })
    assert res.status_code == 201
    data = json.loads(res.data)
    assert data["id"] == 1


def test_create_contact_missing_fields(client):
    res = client.post("/api/contacts", json={"first_name": "John"})
    assert res.status_code == 400


def test_list_contacts(client):
    client.post("/api/contacts", json={"first_name": "John", "last_name": "Doe"})
    client.post("/api/contacts", json={"first_name": "Jane", "last_name": "Smith"})
    res = client.get("/api/contacts")
    data = json.loads(res.data)
    assert len(data) == 2


def test_search_contacts(client):
    client.post("/api/contacts", json={
        "first_name": "John", "last_name": "Doe", "company": "PowerTech"
    })
    client.post("/api/contacts", json={
        "first_name": "Jane", "last_name": "Smith", "company": "SolarCo"
    })
    res = client.get("/api/contacts?search=PowerTech")
    data = json.loads(res.data)
    assert len(data) == 1
    assert data[0]["company"] == "PowerTech"


def test_get_contact(client):
    client.post("/api/contacts", json={
        "first_name": "John", "last_name": "Doe"
    })
    res = client.get("/api/contacts/1")
    data = json.loads(res.data)
    assert data["contact"]["first_name"] == "John"


def test_update_contact(client):
    client.post("/api/contacts", json={
        "first_name": "John", "last_name": "Doe"
    })
    res = client.put("/api/contacts/1", json={"status": "customer"})
    assert res.status_code == 200
    res = client.get("/api/contacts/1")
    assert json.loads(res.data)["contact"]["status"] == "customer"


def test_delete_contact(client):
    client.post("/api/contacts", json={
        "first_name": "John", "last_name": "Doe"
    })
    res = client.delete("/api/contacts/1")
    assert res.status_code == 200
    res = client.get("/api/contacts/1")
    assert res.status_code == 404


# --- Deal Tests ---

def test_create_deal(client):
    client.post("/api/contacts", json={
        "first_name": "John", "last_name": "Doe"
    })
    res = client.post("/api/deals", json={
        "contact_id": 1, "title": "Transformer Order", "value": 50000
    })
    assert res.status_code == 201


def test_list_deals(client):
    client.post("/api/contacts", json={"first_name": "John", "last_name": "Doe"})
    client.post("/api/deals", json={"contact_id": 1, "title": "Deal A", "value": 10000})
    client.post("/api/deals", json={"contact_id": 1, "title": "Deal B", "value": 20000})
    res = client.get("/api/deals")
    assert len(json.loads(res.data)) == 2


def test_update_deal_stage(client):
    client.post("/api/contacts", json={"first_name": "John", "last_name": "Doe"})
    client.post("/api/deals", json={"contact_id": 1, "title": "Deal", "value": 10000})
    res = client.put("/api/deals/1", json={"stage": "closed_won"})
    assert res.status_code == 200


def test_delete_deal(client):
    client.post("/api/contacts", json={"first_name": "John", "last_name": "Doe"})
    client.post("/api/deals", json={"contact_id": 1, "title": "Deal"})
    res = client.delete("/api/deals/1")
    assert res.status_code == 200


# --- Activity Tests ---

def test_create_activity(client):
    client.post("/api/contacts", json={"first_name": "John", "last_name": "Doe"})
    res = client.post("/api/activities", json={
        "contact_id": 1, "type": "call", "subject": "Follow-up call"
    })
    assert res.status_code == 201


def test_complete_activity(client):
    client.post("/api/contacts", json={"first_name": "John", "last_name": "Doe"})
    client.post("/api/activities", json={
        "contact_id": 1, "type": "task", "subject": "Send quote"
    })
    res = client.post("/api/activities/1/complete")
    assert res.status_code == 200


# --- Dashboard Tests ---

def test_dashboard(client):
    client.post("/api/contacts", json={"first_name": "John", "last_name": "Doe"})
    client.post("/api/deals", json={
        "contact_id": 1, "title": "Won Deal", "value": 50000, "stage": "closed_won"
    })
    res = client.get("/api/dashboard")
    data = json.loads(res.data)
    assert data["total_contacts"] == 1
    assert data["total_revenue"] == 50000


# --- Export Tests ---

def test_export_contacts(client):
    client.post("/api/contacts", json={
        "first_name": "John", "last_name": "Doe", "email": "john@test.com"
    })
    res = client.get("/api/contacts/export")
    assert res.status_code == 200
    assert b"John" in res.data
