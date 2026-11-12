from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.agent import answer_business_chat
from app.models import Producto, Venta
from app.schemas import (
    IndicadoresRead,
    ChatRequest,
    ChatResponse,
    ProductoUpdate,
    ProductoCreate,
    ProductoRead,
    VentaCreate,
    VentaRead,
    VentaUpdate,
    VentasCategoriaRead,
)

router = APIRouter()


@router.get("/productos", response_model=list[ProductoRead])
def listar_productos(db: Session = Depends(get_db)):
    return db.scalars(select(Producto).order_by(Producto.id)).all()


@router.post("/productos", response_model=ProductoRead, status_code=status.HTTP_201_CREATED)
def crear_producto(payload: ProductoCreate, db: Session = Depends(get_db)):
    producto = Producto(**payload.model_dump())
    db.add(producto)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El nombre del producto ya existe") from exc
    db.refresh(producto)
    return producto


@router.patch("/productos/{producto_id}", response_model=ProductoRead)
def actualizar_producto(producto_id: int, payload: ProductoUpdate, db: Session = Depends(get_db)):
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(producto, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El nombre del producto ya existe") from exc
    db.refresh(producto)
    return producto


@router.delete("/productos/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_producto(producto_id: int, db: Session = Depends(get_db)):
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if db.scalar(select(func.count(Venta.id)).where(Venta.producto_id == producto_id)):
        raise HTTPException(status_code=409, detail="No se puede eliminar un producto con ventas registradas")
    db.delete(producto)
    db.commit()


@router.get("/productos/{producto_id}", response_model=ProductoRead)
def obtener_producto(producto_id: int, db: Session = Depends(get_db)):
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.get("/ventas", response_model=list[VentaRead])
def listar_ventas(db: Session = Depends(get_db)):
    return db.scalars(select(Venta).order_by(Venta.id)).all()


@router.post("/ventas", response_model=VentaRead, status_code=status.HTTP_201_CREATED)
def crear_venta(payload: VentaCreate, db: Session = Depends(get_db)):
    producto = db.get(Producto, payload.producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    venta = Venta(
        producto_id=producto.id,
        cantidad=payload.cantidad,
        fecha=payload.fecha,
        total=producto.precio * payload.cantidad,
    )
    db.add(venta)
    db.commit()
    db.refresh(venta)
    return venta


@router.patch("/ventas/{venta_id}", response_model=VentaRead)
def actualizar_venta(venta_id: int, payload: VentaUpdate, db: Session = Depends(get_db)):
    venta = db.get(Venta, venta_id)
    if venta is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    updates = payload.model_dump(exclude_unset=True)
    producto_id = updates.get("producto_id", venta.producto_id)
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    venta.producto_id = producto.id
    venta.cantidad = updates.get("cantidad", venta.cantidad)
    venta.fecha = updates.get("fecha", venta.fecha)
    venta.total = producto.precio * venta.cantidad
    db.commit()
    db.refresh(venta)
    return venta


@router.delete("/ventas/{venta_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_venta(venta_id: int, db: Session = Depends(get_db)):
    venta = db.get(Venta, venta_id)
    if venta is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    db.delete(venta)
    db.commit()


@router.get("/indicadores", response_model=IndicadoresRead)
def obtener_indicadores(db: Session = Depends(get_db)):
    suma = db.scalar(select(func.coalesce(func.sum(Venta.total), 0)))
    cantidad = db.scalar(select(func.coalesce(func.sum(Venta.cantidad), 0)))
    numero = db.scalar(select(func.count(Venta.id)))
    agrupado = db.execute(
        select(
            Producto.categoria,
            func.sum(Venta.total),
            func.sum(Venta.cantidad),
            func.count(Venta.id),
        )
        .join(Venta, Venta.producto_id == Producto.id)
        .group_by(Producto.categoria)
        .order_by(Producto.categoria)
    ).all()
    total = Decimal(str(suma))
    return IndicadoresRead(
        ingresos_totales=total,
        cantidad_total_vendida=int(cantidad),
        ticket_promedio=(total / numero if numero else Decimal("0")),
        ventas_por_categoria=[
            VentasCategoriaRead(
                categoria=row[0], ingresos=Decimal(str(row[1])),
                cantidad_vendida=int(row[2]), numero_ventas=int(row[3])
            )
            for row in agrupado
        ],
    )


@router.post("/chat", response_model=ChatResponse)
async def chatear(payload: ChatRequest, db: Session = Depends(get_db)):
    return ChatResponse(reply=await answer_business_chat(payload.messages, db))
