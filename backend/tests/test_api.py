import asyncio
from datetime import date
from decimal import Decimal

from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db, make_engine
from app.main import health
from app.models import Producto, SeedState, Venta
from app.routers import (
    actualizar_producto,
    actualizar_venta,
    crear_producto,
    crear_venta,
    eliminar_producto,
    eliminar_venta,
    listar_productos,
    listar_ventas,
    obtener_indicadores,
    router,
)
from app.seed import seed_database
from app.schemas import ChatMessage, ProductoCreate, ProductoUpdate, VentaCreate, VentaUpdate


def make_client(tmp_path):
    engine = make_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with TestingSession() as db:
        seed_database(db)

    def override_db():
        with TestingSession() as db:
            yield db

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = override_db
    app.get("/health")(health)
    return app, TestingSession


def test_health_product_sales_endpoints_and_seed(tmp_path):
    _app, session = make_client(tmp_path)
    assert health() == {"status": "ok"}
    with session() as db:
        products = listar_productos(db)
        sales = listar_ventas(db)
        assert len(products) == 8
        assert len(sales) == 50
        assert seed_database(db) is False
        assert db.scalar(select(func.count()).select_from(Venta)) == 50


def test_create_product_and_sale_validates_business_rules(tmp_path):
    _app, session = make_client(tmp_path)
    with session() as db:
        product = crear_producto(
            ProductoCreate(nombre="Producto prueba", categoria="Prueba", precio="125.50"), db
        )
        product_id = product.id
        try:
            crear_producto(ProductoCreate(nombre="Producto prueba", categoria="Prueba", precio="2"), db)
            assert False, "Debe rechazar nombre duplicado"
        except Exception as exc:
            from fastapi import HTTPException
            assert isinstance(exc, HTTPException) and exc.status_code == 409
        lower_case = crear_producto(
            ProductoCreate(nombre="producto prueba", categoria="Prueba", precio="2"), db
        )
        assert lower_case.nombre == "producto prueba"

        sale = crear_venta(
            VentaCreate(producto_id=product_id, cantidad=3, fecha=date(2026, 11, 11)), db
        )
        assert sale.total == Decimal("376.50")
    for bad_quantity in (0, -1, 1.5, True):
        from pydantic import ValidationError
        try:
            VentaCreate(producto_id=product_id, cantidad=bad_quantity, fecha=date(2026, 11, 11))
            assert False, f"Cantidad inválida aceptada: {bad_quantity}"
        except ValidationError:
            pass
    with session() as db:
        try:
            crear_venta(VentaCreate(producto_id=99999, cantidad=1, fecha=date(2026, 11, 11)), db)
            assert False, "Debe rechazar producto no registrado"
        except Exception as exc:
            from fastapi import HTTPException
            assert isinstance(exc, HTTPException) and exc.status_code == 404


def test_indicators_cover_all_persisted_sales(tmp_path):
    _app, session = make_client(tmp_path)
    with session() as db:
        total = db.scalar(select(func.sum(Venta.total)))
        units = db.scalar(select(func.sum(Venta.cantidad)))
        count = db.scalar(select(func.count(Venta.id)))
        body = obtener_indicadores(db).model_dump()
    assert Decimal(body["ingresos_totales"]) == Decimal(str(total))
    assert body["cantidad_total_vendida"] == units
    assert Decimal(body["ticket_promedio"]) == Decimal(str(total)) / count
    assert sum(row["numero_ventas"] for row in body["ventas_por_categoria"]) == count
    assert sum(Decimal(row["ingresos"]) for row in body["ventas_por_categoria"]) == Decimal(str(total))


def test_product_and_sale_updates_and_deletes(tmp_path):
    _app, session = make_client(tmp_path)
    with session() as db:
        product = crear_producto(ProductoCreate(nombre="CRUD", categoria="Prueba", precio="100"), db)
        updated_product = actualizar_producto(product.id, ProductoUpdate(precio="125.50"), db)
        assert updated_product.precio == Decimal("125.50")
        sale = crear_venta(VentaCreate(producto_id=product.id, cantidad=2, fecha=date(2026, 11, 11)), db)
        changed_sale = actualizar_venta(sale.id, VentaUpdate(cantidad=4), db)
        assert changed_sale.cantidad == 4
        assert changed_sale.total == Decimal("502.00")
        try:
            eliminar_producto(product.id, db)
            assert False, "No debe permitir eliminar productos con ventas"
        except Exception as exc:
            from fastapi import HTTPException
            assert isinstance(exc, HTTPException) and exc.status_code == 409
        eliminar_venta(sale.id, db)
        eliminar_producto(product.id, db)
        assert db.get(Venta, sale.id) is None
        assert db.get(Producto, product.id) is None


def test_chat_uses_current_business_data_without_exposing_api_key(tmp_path, monkeypatch):
    from app import agent
    from app.routers import chatear
    from app.schemas import ChatRequest

    _app, session = make_client(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    captured = {}

    def fake_gemini(key, messages, context):
        captured["key"] = key
        captured["messages"] = messages
        captured["context"] = context
        return "Alimentos es la categoría con más ingresos."

    monkeypatch.setattr(agent, "_request_gemini", fake_gemini)
    with session() as db:
        response = asyncio.run(chatear(ChatRequest(messages=[ChatMessage(role="user", content="¿Qué categoría vende más?")]), db))
    assert response.reply.startswith("Alimentos")
    assert captured["key"] == "test-key"
    assert captured["context"]["indicadores"]["cantidad_total_vendida"] == 210
    assert len(captured["context"]["ventas_recientes"]) == 50

    monkeypatch.delenv("GEMINI_API_KEY")
    with session() as db:
        try:
            asyncio.run(chatear(ChatRequest(messages=[ChatMessage(role="user", content="Hola")]), db))
            assert False, "Debe pedir configuración de la clave"
        except Exception as exc:
            from fastapi import HTTPException
            assert isinstance(exc, HTTPException) and exc.status_code == 503


def test_seed_does_not_restore_sales_deleted_by_user(tmp_path):
    _app, session = make_client(tmp_path)
    with session() as db:
        db.query(Venta).delete()
        db.commit()
        assert seed_database(db) is False
        assert db.scalar(select(func.count()).select_from(Venta)) == 0
        assert db.get(SeedState, "sales-demo-v1") is not None
