from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, func, text
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
    existencias: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))

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
    vendedor_id: Mapped[int | None] = mapped_column(ForeignKey("vendedores.id"), nullable=True, index=True)
    moneda_pago: Mapped[str] = mapped_column(String(3), nullable=False, default="CRC", server_default=text("'CRC'"))
    monto_moneda: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    tipo_cambio: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False, default=Decimal("1"), server_default=text("1"))
    fecha_tipo_cambio: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado_pago: Mapped[str] = mapped_column(String(20), nullable=False, default="confirmada", server_default=text("'confirmada'"))

    producto: Mapped[Producto] = relationship(back_populates="ventas")
    vendedor: Mapped["Vendedor | None"] = relationship(back_populates="ventas")


class Vendedor(Base):
    __tablename__ = "vendedores"
    __table_args__ = (CheckConstraint("length(trim(nombre)) > 0", name="ck_vendedores_nombre_no_vacio"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_salt: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    activo: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=text("1"))
    ventas: Mapped[list[Venta]] = relationship(back_populates="vendedor")


class SolicitudAprobacion(Base):
    __tablename__ = "solicitudes_aprobacion"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente", index=True)
    datos: Mapped[dict] = mapped_column(JSON, nullable=False)
    motivo: Mapped[str] = mapped_column(String(500), nullable=False)
    solicitante_id: Mapped[int | None] = mapped_column(ForeignKey("vendedores.id"), nullable=True)
    solicitante_nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    revisor_nombre: Mapped[str | None] = mapped_column(String(120), nullable=True)
    respuesta: Mapped[str | None] = mapped_column(String(500), nullable=True)
    creada_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    resuelta_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class EventoAuditoria(Base):
    __tablename__ = "eventos_auditoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    accion: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entidad: Mapped[str] = mapped_column(String(80), nullable=False)
    entidad_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detalles: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), index=True)


class AjusteVenta(Base):
    __tablename__ = "ajustes_venta"

    id: Mapped[int] = mapped_column(primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id"), nullable=False, index=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes_aprobacion.id"), nullable=False, unique=True)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    monto_crc: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    cantidad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revendible: Mapped[bool | None] = mapped_column(nullable=True)
    motivo: Mapped[str] = mapped_column(String(500), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"

    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), nullable=False, index=True)
    solicitud_id: Mapped[int | None] = mapped_column(ForeignKey("solicitudes_aprobacion.id"), nullable=True)
    venta_id: Mapped[int | None] = mapped_column(ForeignKey("ventas.id"), nullable=True)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    motivo: Mapped[str] = mapped_column(String(500), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class SeedState(Base):
    """Marca interna para que un seed eliminado por el usuario no reaparezca al reiniciar."""

    __tablename__ = "seed_state"

    nombre: Mapped[str] = mapped_column(String(80), primary_key=True)
