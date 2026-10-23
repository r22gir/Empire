"""GET /jobs/{id}/related — mock SQLite only. No live data."""
import importlib
import json
import sqlite3


def _schema(conn: sqlite3.Connection):
    conn.executescript(
        """
        CREATE TABLE customers (
            id TEXT PRIMARY KEY, name TEXT, email TEXT, phone TEXT, address TEXT, business TEXT
        );
        CREATE TABLE jobs (
            id TEXT PRIMARY KEY, title TEXT, customer_id TEXT, quote_id TEXT, job_number TEXT,
            client_name TEXT, status TEXT, pipeline_stage TEXT, metadata TEXT,
            photos TEXT, drawings TEXT, mockups TEXT, quoted_amount REAL, created_at TEXT
        );
        CREATE TABLE quotes_v2 (
            id TEXT PRIMARY KEY, quote_number TEXT, job_id TEXT, customer_id TEXT,
            customer_name TEXT, project_name TEXT, status TEXT, total REAL, created_at TEXT, is_test INTEGER
        );
        CREATE TABLE invoices (
            id TEXT PRIMARY KEY, invoice_number TEXT, job_id TEXT, quote_id TEXT, customer_id TEXT,
            client_name TEXT, status TEXT, total REAL, balance_due REAL, amount_paid REAL, created_at TEXT
        );
        CREATE TABLE job_documents (
            id TEXT PRIMARY KEY, job_id TEXT, quote_id TEXT, document_type TEXT,
            url TEXT, filename TEXT, revision INTEGER, source_channel TEXT, created_at TEXT
        );
        CREATE TABLE job_clients (
            job_id TEXT NOT NULL, customer_id TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'primary',
            created_at TEXT DEFAULT (datetime('now')), PRIMARY KEY (job_id, customer_id)
        );
        """
    )


def _load(monkeypatch, tmp_path):
    db = tmp_path / "empire.db"
    monkeypatch.setenv("EMPIRE_TASK_DB", str(db))
    from app.db import database
    importlib.reload(database)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    _schema(conn)
    conn.commit()
    return database, conn


def test_related_gathers_quote_invoice_docs_and_job_json(monkeypatch, tmp_path):
    database, conn = _load(monkeypatch, tmp_path)
    conn.execute("INSERT INTO customers VALUES ('c1','Mock Client','m@example.com','555-0100','1 Mock','workroom')")
    conn.execute(
        """INSERT INTO jobs VALUES (
            'job-midi','Le Midi banquettes','c1','q-orphan','JOB-MOCK-1','Mock Client','in_progress','in_production',
            ?,?,?,?, 2400, '2026-03-01')""",
        (
            json.dumps({"job_folder_slug": "le-midi"}),
            json.dumps([{"url": "/api/v1/photos/job/job-midi/room.jpg", "filename": "room.jpg"}]),
            json.dumps([{"url": "/api/v1/drawings/files/le-midi.pdf", "filename": "le-midi.pdf", "title": "Le Midi plan"}]),
            json.dumps(["/api/v1/drawings/files/mockup.pdf"]),
        ),
    )
    # quote is NOT linked via job_id — only via job.quote_id
    conn.execute(
        "INSERT INTO quotes_v2 VALUES ('q-orphan','EST-2026-0888',NULL,NULL,'Mock Client','Le Midi','sent',2400,'2026-03-02',0)"
    )
    conn.execute(
        "INSERT INTO invoices VALUES ('inv-1','INV-2026-0888',NULL,'q-orphan',NULL,'Mock Client','sent',2400,2400,0,'2026-03-10')"
    )
    # job_documents with job_id but no quote_id (the Le Midi bug)
    conn.execute(
        "INSERT INTO job_documents VALUES ('jd-1','job-midi',NULL,'drawing','/api/v1/drawings/files/le-midi.pdf','le-midi.pdf',1,'upload','2026-03-03')"
    )
    conn.execute(
        "INSERT INTO job_documents VALUES ('jd-2','job-midi',NULL,'photo','/api/v1/photos/job/job-midi/room.jpg','room.jpg',1,'upload','2026-03-03')"
    )
    conn.commit()

    from app.services.job_related import gather_related

    payload = gather_related(conn, "job-midi", jobs_dir=tmp_path / "jobs", data_dir=tmp_path / "empire-data")
    conn.close()
    assert payload is not None
    assert payload["job_id"] == "job-midi"
    assert payload["job_folder_slug"] == "le-midi"
    assert "q-orphan" in payload["quote_ids"]
    assert any(q["id"] == "q-orphan" for q in payload["quotes"])
    assert payload["quotes"][0]["viewer"]["src"] == "/api/v1/quotes-v2/q-orphan/pdf"
    assert any(i["id"] == "inv-1" for i in payload["invoices"])
    assert any(d["id"] == "jd-1" for d in payload["documents"])
    assert any(p["filename"] == "room.jpg" for p in payload["photos"])
    assert any(d["filename"] == "le-midi.pdf" for d in payload["drawings"])
    assert any(m["filename"] == "mockup.pdf" for m in payload["mockups"])
    types = {g["type"] for g in payload["groups"]}
    assert {"estimate", "invoice", "drawing", "photo"} <= types


def test_related_404_for_unknown_job(monkeypatch, tmp_path):
    database, conn = _load(monkeypatch, tmp_path)
    from app.services.job_related import gather_related
    assert gather_related(conn, "missing") is None
    conn.close()


def test_shared_client_quotes_are_review_not_auto(monkeypatch, tmp_path):
    """EST-2026-292/293 (Willard Est 838 addendums) must not auto-link to Le Midi."""
    database, conn = _load(monkeypatch, tmp_path)
    shared = "f230cd42ff61aea9"
    conn.execute("INSERT INTO customers VALUES (?,\"Maggie O'Neill\",'m@example.test',NULL,NULL,'workroom')", (shared,))
    conn.execute("INSERT INTO customers VALUES ('cust-lauren','Lauren Bassett',NULL,NULL,NULL,'workroom')")
    conn.execute(
        """INSERT INTO jobs VALUES (
            'job-willard','Willard Est 838','{cid}','q-willard','JOB-W',\"Maggie O'Neill\",'in_progress','in_production',
            '{{}}', '[]', '[]', '[]', 1000, '2026-01-10')""".format(cid=shared)
    )
    conn.execute(
        """INSERT INTO jobs VALUES (
            'job-midi','Le Midi banquettes','{cid}',NULL,'JOB-M',\"Maggie O'Neill\",'in_progress','in_production',
            '{{}}', '[]', '[]', '[]', 2400, '2026-03-01')""".format(cid=shared)
    )
    conn.execute("INSERT INTO job_clients VALUES ('job-willard', ?, 'primary', '2026-01-10')", (shared,))
    conn.execute("INSERT INTO job_clients VALUES ('job-midi', ?, 'primary', '2026-03-01')", (shared,))
    conn.execute("INSERT INTO job_clients VALUES ('job-midi', 'cust-lauren', 'designer', '2026-03-02')")
    conn.execute(
        "INSERT INTO quotes_v2 VALUES ('q-willard','EST-2026-0100',NULL,?,'Maggie','Willard','sent',1000,'2026-01-11',0)",
        (shared,),
    )
    conn.execute(
        "INSERT INTO quotes_v2 VALUES ('q-292','EST-2026-292',NULL,?,'Maggie','Willard Est 838 addendum','sent',200,'2026-01-20',0)",
        (shared,),
    )
    conn.execute(
        "INSERT INTO quotes_v2 VALUES ('q-293','EST-2026-293',NULL,?,'Maggie','Willard Est 838 addendum 2','sent',150,'2026-01-21',0)",
        (shared,),
    )
    conn.commit()

    from app.services.job_related import gather_related

    payload = gather_related(conn, "job-midi")
    conn.close()
    assert payload is not None
    assert {c["customer_id"] for c in payload["clients"]} == {shared, "cust-lauren"}
    auto_nums = {q["quote_number"] for q in payload["quotes"]}
    review_nums = {q["quote_number"] for q in payload["possibly_related"]["quotes"]}
    assert "EST-2026-292" not in auto_nums
    assert "EST-2026-293" not in auto_nums
    assert {"EST-2026-292", "EST-2026-293"} <= review_nums
    assert any(g.get("review") for g in payload["groups"])
    assert any("Possibly related" in str(g.get("title")) for g in payload["groups"])
