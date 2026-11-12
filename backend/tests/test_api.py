import asyncio
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db, make_engine, migrate_sqlite_schema
from app.main import health
from app.models import AjusteVenta, EventoAuditoria, MovimientoInventario, Producto, SeedState, SolicitudAprobacion, Vendedor, Venta
from app.routers import (
    actualizar_producto, actualizar_venta, crear_producto, crear_solicitud, crear_venta,
    eliminar_producto, eliminar_venta, listar_auditoria, listar_productos, listar_solicitudes,
    listar_ventas, login, obtener_indicadores, resolver_solicitud, router, crear_vendedor,
)
from app.schemas import (
    DecisionSolicitud, LoginRequest, ProductoCreate, ProductoUpdate, SolicitudCreate,
    VentaCreate, VentaUpdate, VendedorCreate,
)
from app.security import CurrentUser, get_current_user, hash_password, require_manager
from app.seed import VENDEDORES_DEMO, seed_database, seed_demo_approvals, seed_demo_operations


def make_client(tmp_path):
    engine = make_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    migrate_sqlite_schema(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with TestingSession() as db:
        seed_database(db)

    def override_db():
        with TestingSession() as db:
            yield db

    return None, TestingSession


def add_seller(db, name="Vendedora Prueba", password="password-123"):
    salt, hashed = hash_password(password)
    seller = Vendedor(nombre=name, password_salt=salt, password_hash=hashed)
    db.add(seller); db.commit(); db.refresh(seller)
    return seller


def test_seed_endpoints_and_inventory_schema_are_reproducible(tmp_path):
    client, session = make_client(tmp_path)
    assert health() == {"status": "ok"}
    with session() as db:
        assert len(listar_productos(db)) == 8
        assert len(listar_ventas(db)) == 50
        assert all(product.existencias == 0 for product in db.scalars(select(Producto)).all())
        assert all(sale.vendedor_id is None for sale in db.scalars(select(Venta)).all())
        assert seed_database(db) is False
        assert db.scalar(select(func.count()).select_from(Venta)) == 50


def test_demo_operations_seed_creates_six_sellers_sales_and_is_idempotent(tmp_path, monkeypatch):
    _client, session = make_client(tmp_path)
    monkeypatch.setenv("DEMO_SELLER_PASSWORD", "demo-password-123")
    with session() as db:
        assert seed_demo_operations(db) is True
        assert seed_demo_operations(db) is False
        sellers = db.scalars(select(Vendedor).where(Vendedor.nombre.in_(VENDEDORES_DEMO))).all()
        sample_sales = db.scalars(select(Venta).where(Venta.vendedor_id.in_([seller.id for seller in sellers]))).all()
        sample_movements = db.scalars(select(MovimientoInventario).where(MovimientoInventario.tipo.in_(("entrada_demo", "venta_demo")))).all()
        assert len(sellers) == 6
        assert {seller.nombre for seller in sellers} == set(VENDEDORES_DEMO)
        assert len(sample_sales) == 6
        assert {sale.vendedor_id for sale in sample_sales} == {seller.id for seller in sellers}
        assert db.scalar(select(func.count()).select_from(Venta)) == 56
        assert len(sample_movements) == 12
        assert all(product.existencias >= 0 for product in db.scalars(select(Producto)).all())


def test_demo_approval_history_is_resolved_audited_and_idempotent(tmp_path, monkeypatch):
    _client, session = make_client(tmp_path)
    monkeypatch.setenv("DEMO_SELLER_PASSWORD", "demo-password-123")
    with session() as db:
        assert seed_demo_operations(db) is True
        assert seed_demo_approvals(db) is True
        assert seed_demo_approvals(db) is False
        history = db.scalars(select(SolicitudAprobacion).where(SolicitudAprobacion.motivo.like("DEMO-HISTORY-v1-%"))).all()
        states = {state: sum(request.estado == state for request in history) for state in ("aprobada", "denegada", "pendiente")}
        assert len(history) == 8
        assert states == {"aprobada": 4, "denegada": 4, "pendiente": 0}
        assert all(request.revisor_nombre == "DEMO | Jose Castro" for request in history)
        assert all(request.resuelta_en and request.respuesta.startswith("DEMO | ") for request in history)
        assert db.scalar(select(func.count()).select_from(AjusteVenta)) == 2
        assert db.scalar(select(func.count()).select_from(EventoAuditoria).where(EventoAuditoria.accion.in_(("solicitud_aprobada", "solicitud_denegada")))) == 8


def test_migration_adds_operational_columns_to_existing_sqlite(tmp_path):
    engine = make_engine(f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE productos (id INTEGER PRIMARY KEY, nombre VARCHAR(120) NOT NULL UNIQUE, categoria VARCHAR(80) NOT NULL, precio NUMERIC(12,2) NOT NULL)"))
        connection.execute(text("CREATE TABLE ventas (id INTEGER PRIMARY KEY, producto_id INTEGER NOT NULL, cantidad INTEGER NOT NULL, fecha DATE NOT NULL, total NUMERIC(14,2) NOT NULL)"))
        connection.execute(text("INSERT INTO productos (id,nombre,categoria,precio) VALUES (1,'Legacy','Prueba',10)"))
    Base.metadata.create_all(bind=engine)
    migrate_sqlite_schema(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT existencias FROM productos WHERE id=1")).scalar_one() == 0
        columns = {column["name"] for column in inspect(engine).get_columns("ventas")}
        assert {"vendedor_id", "moneda_pago", "tipo_cambio", "fecha_tipo_cambio", "estado_pago"}.issubset(columns)


def test_product_validation_and_sale_stock_rules(tmp_path):
    _client, session = make_client(tmp_path)
    manager = CurrentUser("Jose Castro", "gerente")
    with session() as db:
        seller = add_seller(db)
        product = crear_producto(ProductoCreate(nombre="Producto prueba", categoria="Prueba", precio="125.50"), db, manager)
        with pytest.raises(Exception):
            crear_producto(ProductoCreate(nombre="Producto prueba", categoria="Prueba", precio="2"), db, manager)
        lower_case = crear_producto(ProductoCreate(nombre="producto prueba", categoria="Prueba", precio="2"), db, manager)
        assert lower_case.nombre == "producto prueba"
        with pytest.raises(Exception):
            crear_venta(VentaCreate(producto_id=product.id, cantidad=1, fecha=date(2026, 11, 11)), db, CurrentUser(seller.nombre, "vendedor", seller.id))
        product.existencias = 5; db.commit()
        sale = crear_venta(VentaCreate(producto_id=product.id, cantidad=3, fecha=date(2026, 11, 11)), db, CurrentUser(seller.nombre, "vendedor", seller.id))
        assert sale.total == Decimal("376.50") and sale.vendedor_id == seller.id
        assert db.get(Producto, product.id).existencias == 2
        for bad_quantity in (0, -1, 1.5, True):
            with pytest.raises(ValidationError):
                VentaCreate(producto_id=product.id, cantidad=bad_quantity, fecha=date(2026, 11, 11))


def test_indicators_count_persisted_sales_and_approved_adjustments(tmp_path):
    _client, session = make_client(tmp_path)
    with session() as db:
        body = obtener_indicadores(db).model_dump()
        gross = db.scalar(select(func.sum(Venta.total)))
        quantity = db.scalar(select(func.sum(Venta.cantidad)))
        count = db.scalar(select(func.count(Venta.id)))
        assert Decimal(body["ingresos_brutos"]) == Decimal(str(gross))
        assert Decimal(body["ingresos_totales"]) == Decimal(str(gross))
        assert body["cantidad_total_vendida"] == quantity
        assert Decimal(body["ticket_promedio"]) == Decimal(str(gross)) / count


def test_price_inventory_return_credit_and_audit_require_approval(tmp_path):
    _client, session = make_client(tmp_path)
    manager = CurrentUser("Jose Castro", "gerente")
    with session() as db:
        seller = add_seller(db)
        employee = CurrentUser(seller.nombre, "vendedor", seller.id)
        starting_income = obtener_indicadores(db).ingresos_totales
        starting_units = obtener_indicadores(db).cantidad_total_vendida
        product = crear_producto(ProductoCreate(nombre="Café", categoria="Alimentos", precio="100"), db, manager)
        stock_request = crear_solicitud(SolicitudCreate(tipo="entrada_inventario", producto_id=product.id, cantidad=5, motivo="Compra de apertura"), db, employee)
        resolver_solicitud(stock_request.id, DecisionSolicitud(decision="aprobada"), db, manager)
        price_request = crear_solicitud(SolicitudCreate(tipo="cambio_precio", producto_id=product.id, nuevo_precio="120", motivo="Lista actualizada"), db, employee)
        with pytest.raises(Exception):
            actualizar_producto(product.id, ProductoUpdate(precio="110"), db, employee)
        resolver_solicitud(price_request.id, DecisionSolicitud(decision="aprobada"), db, manager)
        sale = crear_venta(VentaCreate(producto_id=product.id, cantidad=2, fecha=date(2026, 11, 11)), db, employee)
        return_request = crear_solicitud(SolicitudCreate(tipo="devolucion", venta_id=sale.id, cantidad=1, revendible=True, motivo="Producto devuelto"), db, employee)
        resolver_solicitud(return_request.id, DecisionSolicitud(decision="aprobada"), db, manager)
        credit_request = crear_solicitud(SolicitudCreate(tipo="nota_credito", venta_id=sale.id, monto_crc="20", motivo="Ajuste autorizado"), db, employee)
        resolver_solicitud(credit_request.id, DecisionSolicitud(decision="aprobada"), db, manager)
        indicators = obtener_indicadores(db)
        assert indicators.ingresos_brutos == starting_income + Decimal("240")
        assert indicators.ajustes_aprobados == Decimal("140")
        assert indicators.ingresos_totales == starting_income + Decimal("100")
        assert indicators.cantidad_total_vendida == starting_units + 1
        assert db.get(Producto, product.id).existencias == 4
        actions = db.scalars(select(EventoAuditoria)).all()
        assert any(row.actor == seller.nombre and row.accion == "solicitud_creada" for row in actions)
        assert any(row.actor == manager.name and row.accion == "devolucion_aprobada" for row in actions)


def test_denied_request_does_not_change_product_price(tmp_path):
    _client, session = make_client(tmp_path)
    manager = CurrentUser("Jose Castro", "gerente")
    with session() as db:
        seller = add_seller(db)
        product = crear_producto(ProductoCreate(nombre="Cuaderno nuevo", categoria="Papelería", precio="150"), db, manager)
        req = crear_solicitud(SolicitudCreate(tipo="cambio_precio", producto_id=product.id, nuevo_precio="200", motivo="Propuesta"), db, CurrentUser(seller.nombre, "vendedor", seller.id))
        resolver_solicitud(req.id, DecisionSolicitud(decision="denegada", respuesta="No autorizado"), db, manager)
        assert db.get(Producto, product.id).precio == Decimal("150")
        assert listar_solicitudes(db)[0]["estado"] == "denegada"


def test_currency_change_uses_stored_bccr_rate_and_rounds_to_crc_cent(tmp_path, monkeypatch):
    from app import routers
    monkeypatch.setattr(routers, "exchange_rate_details", lambda _currency, _date: {
        "crc_por_unidad": Decimal("450.123456"), "fecha": date(2026, 11, 11),
        "usd_crc_compra": Decimal("450.123456"), "fecha_usd": date(2026, 11, 11),
    })
    _client, session = make_client(tmp_path)
    manager = CurrentUser("Jose Castro", "gerente")
    with session() as db:
        seller = add_seller(db)
        product = crear_producto(ProductoCreate(nombre="Lámpara", categoria="Hogar", precio="250"), db, manager)
        product.existencias = 2; db.commit()
        sale = crear_venta(VentaCreate(producto_id=product.id, cantidad=2, fecha=date(2026, 11, 11)), db, CurrentUser(seller.nombre, "vendedor", seller.id))
        req = crear_solicitud(SolicitudCreate(tipo="cambio_moneda", venta_id=sale.id, moneda="USD", monto_moneda="2", motivo="Pago en dólares"), db, CurrentUser(seller.nombre, "vendedor", seller.id))
        assert req.datos["tipo_cambio"] == "450.123456"
        assert req.datos["detalle_tasas_bccr"]["usd_crc_compra"] == "450.123456"
        resolver_solicitud(req.id, DecisionSolicitud(decision="aprobada"), db, manager)
        db.refresh(sale)
        assert sale.moneda_pago == "USD" and sale.monto_moneda == Decimal("2")
        assert sale.total == Decimal("900.25")
        assert sale.fecha_tipo_cambio == date(2026, 11, 11)


def test_denied_currency_change_preserves_original_crc_sale(tmp_path, monkeypatch):
    from app import routers
    monkeypatch.setattr(routers, "exchange_rate_details", lambda _currency, _date: {
        "crc_por_unidad": Decimal("450"), "fecha": date(2026, 11, 11),
        "usd_crc_compra": Decimal("450"), "fecha_usd": date(2026, 11, 11),
    })
    _client, session = make_client(tmp_path)
    manager = CurrentUser("Jose Castro", "gerente")
    with session() as db:
        seller = add_seller(db)
        product = crear_producto(ProductoCreate(nombre="Taza distinta", categoria="Hogar", precio="100"), db, manager)
        product.existencias = 2; db.commit()
        sale = crear_venta(VentaCreate(producto_id=product.id, cantidad=2, fecha=date(2026, 11, 11)), db, CurrentUser(seller.nombre, "vendedor", seller.id))
        before = obtener_indicadores(db).ingresos_totales
        req = crear_solicitud(SolicitudCreate(tipo="cambio_moneda", venta_id=sale.id, moneda="USD", monto_moneda="1", motivo="Cambio solicitado"), db, CurrentUser(seller.nombre, "vendedor", seller.id))
        assert obtener_indicadores(db).ingresos_totales == before - sale.total
        resolver_solicitud(req.id, DecisionSolicitud(decision="denegada", respuesta="No aprobado"), db, manager)
        db.refresh(sale)
        assert sale.estado_pago == "denegada" and sale.moneda_pago == "CRC"
        assert obtener_indicadores(db).ingresos_totales == before


def test_euro_rate_uses_bccr_usd_purchase_and_eur_usd_series(tmp_path, monkeypatch):
    from app import exchange_rates
    monkeypatch.setenv("BCCR_API_TOKEN", "test-bccr-token")
    def fake_series(indicator, _start, _end, _token):
        if indicator == exchange_rates.USD_BUY_INDICATOR:
            return [{"fecha": "2026-11-10", "valorDatoPorPeriodo": 450.0}]
        return [{"fecha": "2026-11-09", "valorDatoPorPeriodo": 1.10}]
    monkeypatch.setattr(exchange_rates, "_series", fake_series)
    rate, rate_date = exchange_rates.exchange_rate("EUR", date(2026, 11, 11))
    assert rate == Decimal("495.000")
    assert rate_date == date(2026, 11, 9)


def test_bccr_sdde_response_parser_reads_official_nested_series(monkeypatch):
    import json
    from app import exchange_rates
    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *_args): return None
        def read(self):
            return json.dumps({"estado": True, "datos": [{"indicadores": [{"series": [
                {"fecha": "2026-11-10", "valorDatoPorPeriodo": 450.0},
                {"fecha": "2026-11-11", "valorDatoPorPeriodo": 451.0},
            ]}]}]}).encode()
    monkeypatch.setattr(exchange_rates, "urlopen", lambda _request, timeout: FakeResponse())
    rows = exchange_rates._series("317", date(2026, 11, 10), date(2026, 11, 11), "fake-token")
    assert exchange_rates._value_for_date(rows, date(2026, 11, 11)) == (Decimal("451.0"), date(2026, 11, 11))


def test_login_manager_and_employee_tokens(tmp_path, monkeypatch):
    monkeypatch.setenv("MANAGER_PASSWORD", "test-manager-password")
    monkeypatch.setenv("APP_AUTH_SECRET", "test-signing-secret-which-is-long-enough")
    _client, session = make_client(tmp_path)
    with session() as db:
        manager_login = login(LoginRequest(username="Jose Castro", password="test-manager-password"), db)
        manager = get_current_user(f"Bearer {manager_login.access_token}", db)
        assert manager.role == "gerente" and manager.name == "Jose Castro"
        created = crear_vendedor(VendedorCreate(nombre="Ana Ejemplo", password="password-123"), db, manager)
        assert created["nombre"] == "Ana Ejemplo"
        employee_login = login(LoginRequest(username="Ana Ejemplo", password="password-123"), db)
        employee = get_current_user(f"Bearer {employee_login.access_token}", db)
        assert employee.role == "vendedor" and employee.name == "Ana Ejemplo"


def test_manager_approval_rejects_non_local_connection():
    from starlette.requests import Request
    remote_request = Request({
        "type": "http", "http_version": "1.1", "method": "POST", "scheme": "http",
        "path": "/solicitudes/1/resolver", "raw_path": b"/solicitudes/1/resolver",
        "query_string": b"", "headers": [], "client": ("192.0.2.20", 54321),
        "server": ("127.0.0.1", 8000),
    })
    with pytest.raises(Exception) as error:
        require_manager(remote_request, CurrentUser("Jose Castro", "gerente"))
    assert getattr(error.value, "status_code", None) == 403
