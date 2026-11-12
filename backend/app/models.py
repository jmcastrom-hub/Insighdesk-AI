from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Producto(Base):
    __tablename__ = "productos"
    __table_args__ = (
        CheckConstraint("length(trim(nombre)) > 0", name="ck_productos_nombre_no_vacio"),
        CheckConstraint("precio > 0", name="ck_productos_precio_positivo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    categoria: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    precio: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    ventas: Mapped[list["Venta"]] = relationship(back_populates="producto")


class Venta(Base):
    __tablename__ = "ventas"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_ventas_cantidad_positiva"),
        CheckConstraint("total >= 0", name="ck_ventas_total_no_negativo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), nullable=False, index=True)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    producto: Mapped[Producto] = relationship(back_populates="ventas")


class SeedState(Base):
    """Marca interna para que un seed eliminado por el usuario no reaparezca al reiniciar."""

    __tablename__ = "seed_state"

    nombre: Mapped[str] = mapped_column(String(80), primary_key=True)
