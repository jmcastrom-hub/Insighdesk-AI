"""Catálogo y 50 ventas ficticias deterministas para la base de demostración."""

import random
import os
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine, migrate_sqlite_schema
from app.models import EventoAuditoria, MovimientoInventario, Producto, SeedState, SolicitudAprobacion, Vendedor, Venta

SEED = 20261028
PRODUCTOS = (
    ("Café molido", "Alimentos", "3200.00"),
    ("Té verde", "Alimentos", "1850.00"),
    ("Botella térmica", "Hogar", "8900.00"),
    ("Cuaderno", "Papelería", "1250.00"),
    ("Bolígrafo", "Papelería", "450.00"),
    ("Lámpara LED", "Hogar", "7400.00"),
    ("Galletas de avena", "Alimentos", "975.00"),
    ("Organizador", "Hogar", "5250.00"),
)
NUMERO_VENTAS = 50
FECHA_INICIO = date(2026, 1, 1)
VENDEDORES_DEMO = (
    "Ana Rodríguez", "Luis Morales", "María Fernanda Soto",
    "Carlos Jiménez", "Sofía Vargas", "Diego Ramírez",
)
VENTAS_DEMO = (
    ("Café molido", 2), ("Botella térmica", 1), ("Cuaderno", 3),
    ("Té verde", 2), ("Lámpara LED", 1), ("Organizador", 2),
)


def seed_database(db: Session) -> bool:
    """Si no hay ventas, inserta un catálogo base y exactamente 50 ventas."""
    seed_name = "sales-demo-v1"
    if db.get(SeedState, seed_name):
        return False
    if db.scalar(select(func.count()).select_from(Venta)):
        db.add(SeedState(nombre=seed_name))
        db.commit()
        return False

    existing_products = {
        product.nombre: product
        for product in db.scalars(select(Producto)).all()
    }
    products: list[Producto] = []
    for nombre, categoria, precio in PRODUCTOS:
        product = existing_products.get(nombre)
        if product is None:
            product = Producto(nombre=nombre, categoria=categoria, precio=Decimal(precio))
            db.add(product)
            existing_products[nombre] = product
        products.append(product)

    db.flush()
    rng = random.Random(SEED)
    sales = []
    for _ in range(NUMERO_VENTAS):
        product = rng.choice(products)
        cantidad = rng.randint(1, 8)
        sales.append(
            Venta(
                producto=product,
                cantidad=cantidad,
                fecha=FECHA_INICIO + timedelta(days=rng.randrange(365)),
                total=product.precio * cantidad,
            )
        )
    db.add_all(sales)
    db.add(SeedState(nombre=seed_name))
    db.commit()
    return True


def seed_demo_operations(db: Session) -> bool:
    """Create six clearly labeled demo accounts, stock entries and linked sales once.

    Demo accounts use DEMO_SELLER_PASSWORD (or MANAGER_PASSWORD for local demos).
    Passwords are hashed with the same stdlib security helper used by login.
    """
    seed_name = "operations-demo-v1"
    if db.get(SeedState, seed_name):
        return False
    password = os.getenv("DEMO_SELLER_PASSWORD") or os.getenv("MANAGER_PASSWORD")
    if not password:
        return False

    from app.security import hash_password

    sellers_by_name = {
        seller.nombre: seller
        for seller in db.scalars(select(Vendedor).where(Vendedor.nombre.in_(VENDEDORES_DEMO))).all()
    }
    for name in VENDEDORES_DEMO:
        if name not in sellers_by_name:
            salt, password_hash = hash_password(password)
            seller = Vendedor(nombre=name, password_salt=salt, password_hash=password_hash)
            db.add(seller)
            sellers_by_name[name] = seller

    products_by_name = {
        product.nombre: product
        for product in db.scalars(select(Producto).where(Producto.nombre.in_([name for name, _ in VENTAS_DEMO]))).all()
    }
    if len(products_by_name) != len(VENTAS_DEMO):
        return False

    db.flush()
    for index, ((product_name, quantity), seller_name) in enumerate(zip(VENTAS_DEMO, VENDEDORES_DEMO)):
        product = products_by_name[product_name]
        # Labeled demo receipt makes inventory actions visible in the workspace.
        receipt = quantity + 4
        product.existencias += receipt
        db.add(MovimientoInventario(
            producto_id=product.id, cantidad=receipt, tipo="entrada_demo",
            actor="Seed de demostración", motivo="DEMO: existencias iniciales para probar el dashboard",
        ))
        sale = Venta(
            producto_id=product.id, cantidad=quantity, fecha=date(2026, 11, 12),
            total=product.precio * quantity, vendedor=sellers_by_name[seller_name],
        )
        db.add(sale)
        db.flush()
        product.existencias -= quantity
        db.add(MovimientoInventario(
            producto_id=product.id, venta_id=sale.id, cantidad=-quantity,
            tipo="venta_demo", actor=seller_name, motivo=f"DEMO: venta de muestra #{index + 1}",
        ))

    db.add(EventoAuditoria(
        actor="Seed de demostración", accion="datos_demo_creados", entidad="seed",
        detalles={"vendedores": len(VENDEDORES_DEMO), "ventas": len(VENTAS_DEMO), "marcador": seed_name},
    ))
    db.add(SeedState(nombre=seed_name))
    db.commit()
    return True


def seed_demo_approvals(db: Session) -> bool:
    """Add an idempotent, explicitly labeled approval history using real resolution rules."""
    marker = "approvals-demo-v1"
    if db.get(SeedState, marker):
        return False
    operations_marker = "operations-demo-v1"
    if not db.get(SeedState, operations_marker):
        return False

    from app.routers import _audit, resolver_solicitud
    from app.schemas import DecisionSolicitud, SolicitudCreate
    from app.security import CurrentUser

    sellers = {
        seller.nombre: seller
        for seller in db.scalars(select(Vendedor).where(Vendedor.nombre.in_(VENDEDORES_DEMO))).all()
    }
    products = {
        product.nombre: product
        for product in db.scalars(select(Producto).where(Producto.nombre.in_([row[0] for row in PRODUCTOS]))).all()
    }
    if len(sellers) != len(VENDEDORES_DEMO) or len(products) != len(PRODUCTOS):
        return False
    sales_by_seller = {}
    for sale in db.scalars(select(Venta).where(Venta.vendedor_id.in_([seller.id for seller in sellers.values()])).order_by(Venta.id)).all():
        sales_by_seller.setdefault(sale.vendedor_id, []).append(sale)
    if any(not sales_by_seller.get(seller.id) for seller in sellers.values()):
        return False

    ana, luis, maria, carlos, sofia, diego = (sellers[name] for name in VENDEDORES_DEMO)
    history = (
        ("cambio_precio", "Ana Rodríguez", {"producto_id": products["Té verde"].id, "nuevo_precio": "1950.00"}, True, "Actualización demo aceptada tras revisión.", "Se acepta el ajuste de precio de muestra."),
        ("cambio_precio", "Luis Morales", {"producto_id": products["Bolígrafo"].id, "nuevo_precio": "550.00"}, False, "Cambio de precio de muestra no aprobado.", "Se conserva el precio vigente."),
        ("entrada_inventario", "María Fernanda Soto", {"producto_id": products["Café molido"].id, "cantidad": 10}, True, "Recepción demo verificada.", "Entrada de muestra aprobada."),
        ("entrada_inventario", "Carlos Jiménez", {"producto_id": products["Lámpara LED"].id, "cantidad": 8}, False, "Cantidad de muestra pendiente de verificación.", "No se aplica la entrada."),
        ("devolucion", "Ana Rodríguez", {"venta_id": sales_by_seller[ana.id][0].id, "cantidad": 1, "revendible": True}, True, "Devolución demo aceptada; producto revendible.", "Se ajusta ingreso e inventario conforme a la regla aprobada."),
        ("devolucion", "Luis Morales", {"venta_id": sales_by_seller[luis.id][0].id, "cantidad": 1, "revendible": False}, False, "Solicitud demo denegada en revisión.", "No se modifica el ingreso ni el inventario."),
        ("nota_credito", "María Fernanda Soto", {"venta_id": sales_by_seller[maria.id][0].id, "monto_crc": "250.00"}, True, "Nota demo aceptada.", "Se descuenta del ingreso neto conforme a la regla vigente."),
        ("nota_credito", "Diego Ramírez", {"venta_id": sales_by_seller[diego.id][0].id, "monto_crc": "200.00"}, False, "Solicitud demo denegada en revisión.", "No se aplica ajuste financiero."),
    )
    demo_manager = CurrentUser("DEMO | Jose Castro", "gerente")
    for index, (kind, seller_name, fields, approved, reason, answer) in enumerate(history, start=1):
        reference = f"DEMO-HISTORY-v1-{index:02d}: {reason}"
        existing = db.scalar(select(SolicitudAprobacion).where(SolicitudAprobacion.motivo == reference))
        if existing is not None and existing.estado != "pendiente":
            continue
        seller = sellers[seller_name]
        request_data = SolicitudCreate(tipo=kind, motivo=reference, **fields)
        if existing is None:
            request = SolicitudAprobacion(
                tipo=kind,
                datos=request_data.model_dump(mode="json", exclude_none=True, exclude={"motivo", "tipo"}),
                motivo=reference,
                solicitante_id=seller.id,
                solicitante_nombre=f"DEMO | {seller_name}",
                creada_en=datetime(2026, 11, 3, 9, 0) + timedelta(days=index - 1),
            )
            db.add(request)
            db.flush()
            _audit(db, demo_manager, "solicitud_creada", "solicitud", request.id, {"demo": True, "tipo": kind, "motivo": reason})
        else:
            request = existing
        decision = DecisionSolicitud(
            decision="aprobada" if approved else "denegada",
            respuesta=f"DEMO | {answer}",
        )
        resolver_solicitud(request.id, decision, db, demo_manager)

    db.add(SeedState(nombre=marker))
    db.commit()
    return True


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    migrate_sqlite_schema(engine)
    with SessionLocal() as db:
        seed_database(db)
        seed_demo_operations(db)
        seed_demo_approvals(db)


if __name__ == "__main__":
    initialize_database()
    print("Base inicializada con catálogo y 50 ventas deterministas.")
