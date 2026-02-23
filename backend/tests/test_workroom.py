"""
Unit tests for Workroom Forge CRUD operations and stats endpoint.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.models.workroom import WorkroomOrder, WorkroomClient
from app.schemas.workroom import (
    OrderCreate, OrderUpdate,
    ClientCreate, ClientUpdate,
    WorkroomStats,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db():
    """Return a MagicMock that mimics a SQLAlchemy Session."""
    db = MagicMock()
    return db


def _make_order(**kwargs) -> WorkroomOrder:
    defaults = dict(
        id=1,
        product="Custom curtains",
        status="pending",
        due_date="2026-03-01",
        total=250.0,
        notes="Blue fabric",
        images=None,
        client_id=1,
        created_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    order = WorkroomOrder()
    for k, v in defaults.items():
        setattr(order, k, v)
    return order


def _make_client(**kwargs) -> WorkroomClient:
    defaults = dict(
        id=1,
        name="Jane Doe",
        email="jane@example.com",
        phone="555-1234",
        address="123 Main St",
        total_orders=0,
        total_spent=0.0,
        created_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    client = WorkroomClient()
    for k, v in defaults.items():
        setattr(client, k, v)
    return client


# ---------------------------------------------------------------------------
# Order schema validation
# ---------------------------------------------------------------------------

class TestOrderSchemas:
    def test_order_create_valid(self):
        order = OrderCreate(product="Curtains", total=100.0)
        assert order.product == "Curtains"
        assert order.total == 100.0
        assert order.status == "pending"

    def test_order_create_requires_product(self):
        with pytest.raises(Exception):
            OrderCreate(product="", total=50.0)

    def test_order_create_total_non_negative(self):
        with pytest.raises(Exception):
            OrderCreate(product="Item", total=-5.0)

    def test_order_update_partial(self):
        update = OrderUpdate(status="completed")
        data = update.model_dump(exclude_unset=True)
        assert data == {"status": "completed"}


# ---------------------------------------------------------------------------
# Client schema validation
# ---------------------------------------------------------------------------

class TestClientSchemas:
    def test_client_create_valid(self):
        client = ClientCreate(name="Alice", email="alice@example.com")
        assert client.name == "Alice"
        assert client.email == "alice@example.com"

    def test_client_create_requires_name(self):
        with pytest.raises(Exception):
            ClientCreate(name="")

    def test_client_update_partial(self):
        update = ClientUpdate(phone="555-9999")
        data = update.model_dump(exclude_unset=True)
        assert data == {"phone": "555-9999"}


# ---------------------------------------------------------------------------
# Router – Orders CRUD (via FastAPI TestClient)
# ---------------------------------------------------------------------------

class TestOrdersRouter:
    @pytest.fixture
    def client(self):
        """Create a FastAPI test client with the workroom router."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.routers.workroom import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.fixture
    def mock_db(self):
        return _make_db()

    def test_list_orders_empty(self, client, mock_db):
        """GET /api/workroom/orders returns empty list when no orders exist."""
        mock_db.query.return_value.order_by.return_value.all.return_value = []
        from app.database import get_db
        from app.routers.workroom import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_db

        tc = TestClient(app)
        response = tc.get("/api/workroom/orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_order(self, mock_db):
        """POST /api/workroom/orders creates an order and returns 201."""
        order = _make_order()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        def mock_refresh(obj):
            obj.id = 1
            obj.created_at = datetime.utcnow()

        mock_db.refresh.side_effect = mock_refresh

        from app.database import get_db
        from app.routers.workroom import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_db

        tc = TestClient(app)
        payload = {"product": "Custom curtains", "total": 250.0, "status": "pending"}
        response = tc.post("/api/workroom/orders", json=payload)
        assert response.status_code == 201
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()

    def test_get_order_not_found(self, mock_db):
        """GET /api/workroom/orders/{id} returns 404 when not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from app.database import get_db
        from app.routers.workroom import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_db

        tc = TestClient(app)
        response = tc.get("/api/workroom/orders/999")
        assert response.status_code == 404

    def test_get_order_found(self, mock_db):
        """GET /api/workroom/orders/{id} returns order when found."""
        order = _make_order()
        mock_db.query.return_value.filter.return_value.first.return_value = order

        from app.database import get_db
        from app.routers.workroom import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_db

        tc = TestClient(app)
        response = tc.get("/api/workroom/orders/1")
        assert response.status_code == 200
        assert response.json()["product"] == "Custom curtains"

    def test_update_order_not_found(self, mock_db):
        """PUT /api/workroom/orders/{id} returns 404 when not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from app.database import get_db
        from app.routers.workroom import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_db

        tc = TestClient(app)
        response = tc.put("/api/workroom/orders/999", json={"status": "completed"})
        assert response.status_code == 404

    def test_update_order_status(self, mock_db):
        """PUT /api/workroom/orders/{id} updates the status field."""
        order = _make_order()
        mock_db.query.return_value.filter.return_value.first.return_value = order
        mock_db.refresh.side_effect = lambda obj: None

        from app.database import get_db
        from app.routers.workroom import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_db

        tc = TestClient(app)
        response = tc.put("/api/workroom/orders/1", json={"status": "completed"})
        assert response.status_code == 200
        assert order.status == "completed"

    def test_delete_order_not_found(self, mock_db):
        """DELETE /api/workroom/orders/{id} returns 404 when not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from app.database import get_db
        from app.routers.workroom import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_db

        tc = TestClient(app)
        response = tc.delete("/api/workroom/orders/999")
        assert response.status_code == 404

    def test_delete_order(self, mock_db):
        """DELETE /api/workroom/orders/{id} deletes the order and returns 204."""
        order = _make_order(client_id=None)  # No client_id to skip client lookup
        mock_db.query.return_value.filter.return_value.first.return_value = order

        from app.database import get_db
        from app.routers.workroom import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_db

        tc = TestClient(app)
        response = tc.delete("/api/workroom/orders/1")
        assert response.status_code == 204
        mock_db.delete.assert_called_once_with(order)


# ---------------------------------------------------------------------------
# Router – Clients CRUD
# ---------------------------------------------------------------------------

class TestClientsRouter:
    def _make_app_with_db(self, mock_db):
        from app.database import get_db
        from app.routers.workroom import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_db
        return TestClient(app)

    def test_list_clients_empty(self):
        mock_db = _make_db()
        mock_db.query.return_value.order_by.return_value.all.return_value = []
        tc = self._make_app_with_db(mock_db)
        response = tc.get("/api/workroom/clients")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_client(self):
        mock_db = _make_db()

        def mock_refresh(obj):
            obj.id = 1
            obj.total_orders = 0
            obj.total_spent = 0.0
            obj.created_at = datetime.utcnow()

        mock_db.refresh.side_effect = mock_refresh
        tc = self._make_app_with_db(mock_db)
        payload = {"name": "Jane Doe", "email": "jane@example.com"}
        response = tc.post("/api/workroom/clients", json=payload)
        assert response.status_code == 201
        mock_db.add.assert_called_once()

    def test_get_client_not_found(self):
        mock_db = _make_db()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        tc = self._make_app_with_db(mock_db)
        response = tc.get("/api/workroom/clients/999")
        assert response.status_code == 404

    def test_get_client_found(self):
        mock_db = _make_db()
        client = _make_client()
        mock_db.query.return_value.filter.return_value.first.return_value = client
        tc = self._make_app_with_db(mock_db)
        response = tc.get("/api/workroom/clients/1")
        assert response.status_code == 200
        assert response.json()["name"] == "Jane Doe"

    def test_update_client_not_found(self):
        mock_db = _make_db()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        tc = self._make_app_with_db(mock_db)
        response = tc.put("/api/workroom/clients/999", json={"phone": "555-0000"})
        assert response.status_code == 404

    def test_update_client(self):
        mock_db = _make_db()
        client = _make_client()
        mock_db.query.return_value.filter.return_value.first.return_value = client
        mock_db.refresh.side_effect = lambda obj: None
        tc = self._make_app_with_db(mock_db)
        response = tc.put("/api/workroom/clients/1", json={"phone": "555-9999"})
        assert response.status_code == 200
        assert client.phone == "555-9999"

    def test_delete_client_not_found(self):
        mock_db = _make_db()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        tc = self._make_app_with_db(mock_db)
        response = tc.delete("/api/workroom/clients/999")
        assert response.status_code == 404

    def test_delete_client(self):
        mock_db = _make_db()
        client = _make_client()
        mock_db.query.return_value.filter.return_value.first.return_value = client
        tc = self._make_app_with_db(mock_db)
        response = tc.delete("/api/workroom/clients/1")
        assert response.status_code == 204
        mock_db.delete.assert_called_once_with(client)


# ---------------------------------------------------------------------------
# Router – Stats
# ---------------------------------------------------------------------------

class TestStatsRouter:
    def _make_app_with_db(self, mock_db):
        from app.database import get_db
        from app.routers.workroom import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_db
        return TestClient(app)

    def test_stats_empty(self):
        mock_db = _make_db()
        mock_db.query.return_value.all.return_value = []
        mock_db.query.return_value.count.return_value = 0
        tc = self._make_app_with_db(mock_db)
        response = tc.get("/api/workroom/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_orders"] == 0
        assert data["total_revenue"] == 0.0
        assert data["total_clients"] == 0

    def test_stats_with_orders(self):
        mock_db = _make_db()
        orders = [
            _make_order(status="pending", total=100.0),
            _make_order(id=2, status="completed", total=200.0),
            _make_order(id=3, status="in_progress", total=150.0),
        ]
        mock_db.query.return_value.all.return_value = orders
        mock_db.query.return_value.count.return_value = 2
        tc = self._make_app_with_db(mock_db)
        response = tc.get("/api/workroom/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_orders"] == 3
        assert data["pending_orders"] == 1
        assert data["completed_orders"] == 1
        assert data["in_progress_orders"] == 1
        assert data["total_revenue"] == 200.0  # only completed orders
        assert data["total_clients"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
