"""Catálogo y 50 ventas ficticias deterministas para la base de demostración."""

import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import Producto, SeedState, Venta

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


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)


if __name__ == "__main__":
    initialize_database()
    print("Base inicializada con catálogo y 50 ventas deterministas.")
