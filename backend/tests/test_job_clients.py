"""Multiple clients per job. Mock records only."""
import importlib
import sqlite3

from app.services.job_clients import (
    add_client,
    attach_clients,
    customer_ids_for_job,
    ensure_job_clients_schema,
    job_ids_for_customer,
    list_clients,
    migrate_primary_clients,
    remove_client,
    shared_customer_ids,
)


def _load(monkeypatch, tmp_path):
    db = tmp_path / "empire.db"
    monkeypatch.setenv("EMPIRE_TASK_DB", str(db))
    from app.db import database
    importlib.reload(database)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE customers (
            id TEXT PRIMARY KEY, name TEXT, email TEXT, phone TEXT, address TEXT, company TEXT, type TEXT
        );
        CREATE TABLE jobs (
            id TEXT PRIMARY KEY, title TEXT, customer_id TEXT, job_number TEXT,
            client_name TEXT, status TEXT, updated_at TEXT
        );
        """
    )
    ensure_job_clients_schema(conn)
    return conn


def test_migration_keeps_existing_customer_as_primary(monkeypatch, tmp_path):
    conn = _load(monkeypatch, tmp_path)
    conn.execute("INSERT INTO customers VALUES ('cust-maggie',\"Maggie O'Neill\",'m@example.test','555-0101','1 Mock',NULL,'residential')")
    conn.execute("INSERT INTO customers VALUES ('cust-lauren','Lauren Bassett','l@example.test','555-0102',NULL,NULL,'designer')")
    conn.execute("INSERT INTO jobs VALUES ('job-midi','Le Midi banquettes','cust-maggie','JOB-M',\"Maggie O'Neill\",'in_progress',NULL)")
    conn.execute("INSERT INTO jobs VALUES ('job-willard','Willard drapery','cust-maggie','JOB-W',\"Maggie O'Neill\",'in_progress',NULL)")
    conn.commit()
    added = migrate_primary_clients(conn)
    assert added >= 2
    midi = list_clients(conn, "job-midi")
    assert len(midi) == 1
    assert midi[0]["customer_id"] == "cust-maggie"
    assert midi[0]["role"] == "primary"
    assert midi[0]["name"] == "Maggie O'Neill"


def test_add_second_client_and_shared_membership(monkeypatch, tmp_path):
    conn = _load(monkeypatch, tmp_path)
    conn.execute("INSERT INTO customers VALUES ('cust-maggie',\"Maggie O'Neill\",NULL,NULL,NULL,NULL,'residential')")
    conn.execute("INSERT INTO customers VALUES ('cust-lauren','Lauren Bassett',NULL,NULL,NULL,NULL,'designer')")
    conn.execute("INSERT INTO jobs VALUES ('job-midi','Le Midi','cust-maggie','JOB-M',\"Maggie O'Neill\",'in_progress',NULL)")
    conn.execute("INSERT INTO jobs VALUES ('job-willard','Willard','cust-maggie','JOB-W',\"Maggie O'Neill\",'in_progress',NULL)")
    conn.commit()
    migrate_primary_clients(conn)
    add_client(conn, "job-midi", "cust-lauren", "designer")
    clients = list_clients(conn, "job-midi")
    assert [c["customer_id"] for c in clients] == ["cust-maggie", "cust-lauren"]
    assert clients[1]["role"] == "designer"
    assert customer_ids_for_job(conn, "job-midi") == ["cust-maggie", "cust-lauren"]
    # Maggie stays one record on both jobs
    assert set(job_ids_for_customer(conn, "cust-maggie")) == {"job-midi", "job-willard"}
    assert shared_customer_ids(conn, ["cust-maggie", "cust-lauren"]) == {"cust-maggie"}
    jobs = [{"id": "job-midi"}, {"id": "job-willard"}]
    attach_clients(conn, jobs)
    assert len(jobs[0]["clients"]) == 2
    assert len(jobs[1]["clients"]) == 1
    # cannot remove the last client on Willard
    try:
        remove_client(conn, "job-willard", "cust-maggie")
        assert False, "should refuse last-client remove"
    except ValueError:
        pass
    conn.close()


def test_job_clients_api_lists_and_adds(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from app.db.database import get_db
    from app.main import app

    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO customers (id, name) VALUES ('cust-maggie', \"Maggie O'Neill\")")
        conn.execute("INSERT OR IGNORE INTO customers (id, name) VALUES ('cust-lauren', 'Lauren Bassett')")
    client = TestClient(app)
    created = client.post("/api/v1/jobs", json={
        "title": "Le Midi banquettes",
        "customer_id": "cust-maggie",
        "client_name": "Maggie O'Neill",
        "pipeline_stage": "in_production",
    })
    assert created.status_code == 200, created.text
    job_id = created.json()["job"]["id"]
    listed = client.get(f"/api/v1/jobs/{job_id}/clients")
    assert listed.status_code == 200
    assert any(c["customer_id"] == "cust-maggie" for c in listed.json()["clients"])
    added = client.post(f"/api/v1/jobs/{job_id}/clients", json={"customer_id": "cust-lauren", "role": "designer"})
    assert added.status_code == 200, added.text
    names = [c["name"] for c in added.json()["clients"]]
    assert "Maggie O'Neill" in names
    assert "Lauren Bassett" in names
    detail = client.get(f"/api/v1/jobs/{job_id}")
    assert len(detail.json()["job"]["clients"]) == 2
    related = client.get(f"/api/v1/jobs/{job_id}/related")
    assert related.status_code == 200
    assert len(related.json()["clients"]) == 2
    # same customer can also sit on a second job
    other = client.post("/api/v1/jobs", json={
        "title": "Willard drapery",
        "customer_id": "cust-maggie",
        "client_name": "Maggie O'Neill",
    })
    assert other.status_code == 200
    by_cust = client.get("/api/v1/jobs?customer_id=cust-maggie")
    assert by_cust.status_code == 200
    assert by_cust.json()["total"] >= 2
