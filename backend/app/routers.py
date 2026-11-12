from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.agent import answer_business_chat
from app.models import (
    AjusteVenta, EventoAuditoria, MovimientoInventario, Producto,
    SolicitudAprobacion, Vendedor, Venta,
)
from app.exchange_rates import exchange_rate, exchange_rate_details
from app.security import (
    MANAGER_NAME, TOKEN_TTL_SECONDS, CurrentUser, authenticate, get_current_user,
    hash_password, issue_token, require_manager,
)
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
    DecisionSolicitud, EventoAuditoriaRead, IndicadorVendedorRead, LoginRequest,
    LoginResponse, SolicitudCreate, SolicitudRead, VendedorCreate, VendedorRead,
)

router = APIRouter()


def _audit(db: Session, user, action: str, entity: str, entity_id: int | None, details: dict):
    actor = user.name if isinstance(user, CurrentUser) else "Sistema"
    db.add(EventoAuditoria(actor=actor, accion=action, entidad=entity, entidad_id=entity_id, detalles=jsonable_encoder(details)))


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate(payload.username, payload.password, db)
    token = issue_token(user)
    _audit(db, user, "inicio_sesion", "sesion", None, {"rol": user.role})
    db.commit()
    return LoginResponse(access_token=token, nombre=user.name, rol=user.role, expires_in=TOKEN_TTL_SECONDS)


@router.get("/auth/me")
def who_am_i(user: CurrentUser = Depends(get_current_user)):
    return {"nombre": user.name, "rol": user.role, "vendedor_id": user.seller_id}


@router.post("/vendedores", status_code=status.HTTP_201_CREATED)
def crear_vendedor(
    payload: VendedorCreate, db: Session = Depends(get_db), manager: CurrentUser = Depends(require_manager)
):
    salt, hashed = hash_password(payload.password)
    seller = Vendedor(nombre=payload.nombre, password_salt=salt, password_hash=hashed)
    db.add(seller)
    try:
        db.flush()
        _audit(db, manager, "vendedor_creado", "vendedor", seller.id, {"nombre": seller.nombre})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un vendedor con ese nombre") from exc
    return {"id": seller.id, "nombre": seller.nombre, "activo": seller.activo}


@router.get("/vendedores", response_model=list[VendedorRead])
def listar_vendedores(db: Session = Depends(get_db)):
    sellers = db.scalars(select(Vendedor).where(Vendedor.activo.is_(True)).order_by(Vendedor.nombre)).all()
    rows = []
    for seller in sellers:
        sales = db.scalars(select(Venta).where(Venta.vendedor_id == seller.id, Venta.estado_pago != "pendiente")).all()
        gross = sum((Decimal(sale.total) for sale in sales), Decimal("0"))
        adjustments = db.scalar(select(func.coalesce(func.sum(AjusteVenta.monto_crc), 0)).where(AjusteVenta.venta_id.in_([sale.id for sale in sales]))) if sales else 0
        returned = db.scalar(select(func.coalesce(func.sum(AjusteVenta.cantidad), 0)).where(AjusteVenta.venta_id.in_([sale.id for sale in sales]), AjusteVenta.tipo == "devolucion")) if sales else 0
        rows.append(VendedorRead(
            id=seller.id, nombre=seller.nombre, activo=seller.activo, ventas=len(sales),
            unidades=sum(sale.cantidad for sale in sales) - int(returned or 0), ingresos=gross - Decimal(str(adjustments)),
        ))
    return rows


@router.get("/vendedores/indicadores", response_model=list[IndicadorVendedorRead])
def indicadores_vendedores(db: Session = Depends(get_db)):
    sellers = listar_vendedores(db)
    result = [IndicadorVendedorRead(vendedor_id=seller.id, vendedor=seller.nombre, ventas=seller.ventas, unidades=seller.unidades, ingresos=seller.ingresos) for seller in sellers]
    unassigned = db.scalars(select(Venta).where(Venta.vendedor_id.is_(None), Venta.estado_pago != "pendiente")).all()
    if unassigned:
        sale_ids = [sale.id for sale in unassigned]
        adjustments = db.scalar(select(func.coalesce(func.sum(AjusteVenta.monto_crc), 0)).where(AjusteVenta.venta_id.in_(sale_ids)))
        returned = db.scalar(select(func.coalesce(func.sum(AjusteVenta.cantidad), 0)).where(AjusteVenta.venta_id.in_(sale_ids), AjusteVenta.tipo == "devolucion"))
        result.append(IndicadorVendedorRead(
            vendedor_id=None, vendedor="Sin asignar", ventas=len(unassigned),
            unidades=sum(sale.cantidad for sale in unassigned) - int(returned or 0),
            ingresos=sum((Decimal(sale.total) for sale in unassigned), Decimal("0")) - Decimal(str(adjustments)),
        ))
    return result


@router.get("/productos", response_model=list[ProductoRead])
def listar_productos(db: Session = Depends(get_db)):
    return db.scalars(select(Producto).order_by(Producto.id)).all()


@router.get("/inventario/movimientos")
def listar_movimientos_inventario(db: Session = Depends(get_db)):
    movements = db.scalars(select(MovimientoInventario).order_by(MovimientoInventario.creado_en.desc(), MovimientoInventario.id.desc()).limit(500)).all()
    products = {product.id: product.nombre for product in db.scalars(select(Producto)).all()}
    return [{
        "id": movement.id, "producto_id": movement.producto_id,
        "producto": products.get(movement.producto_id, f"Producto {movement.producto_id}"),
        "cantidad": movement.cantidad, "tipo": movement.tipo, "actor": movement.actor,
        "motivo": movement.motivo, "creado_en": movement.creado_en.isoformat(),
    } for movement in movements]


@router.post("/productos", response_model=ProductoRead, status_code=status.HTTP_201_CREATED)
def crear_producto(payload: ProductoCreate, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    producto = Producto(**payload.model_dump())
    db.add(producto)
    try:
        db.flush()
        _audit(db, user, "producto_creado", "producto", producto.id, {"nombre": producto.nombre, "precio": str(producto.precio)})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El nombre del producto ya existe") from exc
    db.refresh(producto)
    return producto


@router.patch("/productos/{producto_id}", response_model=ProductoRead)
def actualizar_producto(producto_id: int, payload: ProductoUpdate, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "precio" and value != producto.precio:
            raise HTTPException(status_code=409, detail="Los cambios de precio deben enviarse como solicitud para aprobación.")
        if field == "existencias" and value != producto.existencias:
            raise HTTPException(status_code=409, detail="Los cambios de inventario deben enviarse como solicitud para aprobación.")
        setattr(producto, field, value)
    _audit(db, user, "producto_actualizado", "producto", producto.id, payload.model_dump(exclude_unset=True))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El nombre del producto ya existe") from exc
    db.refresh(producto)
    return producto


@router.delete("/productos/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_producto(producto_id: int, db: Session = Depends(get_db), manager: CurrentUser = Depends(require_manager)):
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if db.scalar(select(func.count(Venta.id)).where(Venta.producto_id == producto_id)):
        raise HTTPException(status_code=409, detail="No se puede eliminar un producto con ventas registradas")
    db.delete(producto)
    _audit(db, manager, "producto_eliminado", "producto", producto_id, {"nombre": producto.nombre})
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


@router.get("/tipos-cambio/{moneda}")
def consultar_tipo_cambio(moneda: str, fecha: str | None = None):
    try:
        target = datetime.strptime(fecha, "%Y-%m-%d").date() if fecha else datetime.now().date()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="La fecha debe tener formato AAAA-MM-DD.") from exc
    rate, rate_date = exchange_rate(moneda, target)
    return {"moneda": moneda.upper(), "crc_por_unidad": str(rate), "fecha_bccr": rate_date.isoformat(), "fuente": "Banco Central de Costa Rica"}


@router.post("/solicitudes", response_model=SolicitudRead, status_code=status.HTTP_201_CREATED)
def crear_solicitud(
    payload: SolicitudCreate, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)
):
    data = payload.model_dump(mode="json", exclude_none=True, exclude={"motivo", "tipo"})
    if payload.producto_id is not None and db.get(Producto, payload.producto_id) is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    sale = db.get(Venta, payload.venta_id) if payload.venta_id else None
    if payload.venta_id and sale is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if payload.tipo in {"devolucion", "nota_credito"} and sale.estado_pago == "pendiente":
        raise HTTPException(status_code=409, detail="No se puede ajustar una venta mientras su pago esté pendiente de aprobación.")
    if payload.tipo == "devolucion" and payload.cantidad and payload.cantidad > sale.cantidad:
        raise HTTPException(status_code=422, detail="La devolución supera las unidades de esa venta.")
    if payload.tipo == "nota_credito" and payload.monto_crc and payload.monto_crc > sale.total:
        raise HTTPException(status_code=422, detail="La nota de crédito supera el total de la venta.")
    if payload.tipo == "cambio_moneda":
        if sale.estado_pago == "pendiente":
            raise HTTPException(status_code=409, detail="La venta ya tiene un cambio de moneda pendiente.")
        if db.scalar(select(func.count(AjusteVenta.id)).where(AjusteVenta.venta_id == sale.id)):
            raise HTTPException(status_code=409, detail="No puede cambiarse la moneda después de aplicar devoluciones o notas de crédito.")
        rate_details = exchange_rate_details(payload.moneda, sale.fecha)
        rate = rate_details["crc_por_unidad"]
        rate_date = rate_details["fecha"]
        foreign_amount = Decimal(payload.monto_moneda)
        equivalent = (foreign_amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        data.update({
            "tipo_cambio": str(rate), "fecha_tipo_cambio": rate_date.isoformat(),
            "equivalente_crc": str(equivalent),
            "detalle_tasas_bccr": {key: str(value) if isinstance(value, Decimal) else value.isoformat() if isinstance(value, date) else value for key, value in rate_details.items()},
        })
        sale.estado_pago = "pendiente"
        _audit(db, user, "pago_puesto_en_revision", "venta", sale.id, {"solicitud_tipo": payload.tipo, "moneda_solicitada": payload.moneda})
    request_record = SolicitudAprobacion(
        tipo=payload.tipo, datos=data, motivo=payload.motivo, solicitante_id=user.seller_id,
        solicitante_nombre=user.name,
    )
    db.add(request_record)
    db.flush()
    _audit(db, user, "solicitud_creada", "solicitud", request_record.id, {"tipo": payload.tipo, "motivo": payload.motivo})
    db.commit()
    db.refresh(request_record)
    return request_record


def _serialize_request(item: SolicitudAprobacion) -> dict:
    return {
        "id": item.id, "tipo": item.tipo, "estado": item.estado, "datos": item.datos,
        "motivo": item.motivo, "solicitante_nombre": item.solicitante_nombre,
        "revisor_nombre": item.revisor_nombre, "respuesta": item.respuesta,
        "creada_en": item.creada_en, "resuelta_en": item.resuelta_en,
    }


@router.get("/solicitudes", response_model=list[SolicitudRead])
def listar_solicitudes(db: Session = Depends(get_db)):
    items = db.scalars(select(SolicitudAprobacion).order_by(SolicitudAprobacion.creada_en.desc(), SolicitudAprobacion.id.desc())).all()
    return [_serialize_request(item) for item in items]


def _apply_request(item: SolicitudAprobacion, db: Session, manager: CurrentUser) -> None:
    data = item.datos
    if item.tipo == "cambio_precio":
        product = db.get(Producto, int(data["producto_id"]))
        if product is None:
            raise HTTPException(status_code=404, detail="El producto de la solicitud ya no existe.")
        old = str(product.precio)
        product.precio = Decimal(data["nuevo_precio"])
        _audit(db, manager, "precio_cambiado", "producto", product.id, {"precio_anterior": old, "precio_nuevo": str(product.precio), "solicitud_id": item.id})
    elif item.tipo == "entrada_inventario":
        product = db.get(Producto, int(data["producto_id"]))
        if product is None:
            raise HTTPException(status_code=404, detail="El producto de la solicitud ya no existe.")
        quantity = int(data["cantidad"])
        product.existencias += quantity
        db.add(MovimientoInventario(producto_id=product.id, solicitud_id=item.id, cantidad=quantity, tipo="entrada", actor=manager.name, motivo=item.motivo))
        _audit(db, manager, "inventario_recibido", "producto", product.id, {"cantidad": quantity, "existencias": product.existencias, "solicitud_id": item.id})
    elif item.tipo in {"devolucion", "nota_credito"}:
        sale = db.get(Venta, int(data["venta_id"]))
        if sale is None:
            raise HTTPException(status_code=404, detail="La venta de la solicitud ya no existe.")
        if item.tipo == "devolucion":
            quantity = int(data["cantidad"])
            already_returned = db.scalar(select(func.coalesce(func.sum(AjusteVenta.cantidad), 0)).where(AjusteVenta.venta_id == sale.id, AjusteVenta.tipo == "devolucion"))
            if quantity + int(already_returned) > sale.cantidad:
                raise HTTPException(status_code=409, detail="Las devoluciones aprobadas ya cubren esa cantidad.")
            already_adjusted = Decimal(str(db.scalar(select(func.coalesce(func.sum(AjusteVenta.monto_crc), 0)).where(AjusteVenta.venta_id == sale.id))))
            if quantity + int(already_returned) == sale.cantidad:
                amount = Decimal(sale.total) - already_adjusted
            else:
                amount = (Decimal(sale.total) * quantity / sale.cantidad).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if amount <= 0 or already_adjusted + amount > Decimal(sale.total):
                raise HTTPException(status_code=409, detail="Los ajustes aprobados ya cubren el valor de la venta.")
            resellable = bool(data.get("revendible", False))
            db.add(AjusteVenta(venta_id=sale.id, solicitud_id=item.id, tipo="devolucion", monto_crc=amount, cantidad=quantity, revendible=resellable, motivo=item.motivo))
            if resellable:
                product = db.get(Producto, sale.producto_id)
                product.existencias += quantity
                db.add(MovimientoInventario(producto_id=product.id, venta_id=sale.id, solicitud_id=item.id, cantidad=quantity, tipo="devolucion", actor=manager.name, motivo=item.motivo))
        else:
            amount = Decimal(data["monto_crc"])
            already_credited = db.scalar(select(func.coalesce(func.sum(AjusteVenta.monto_crc), 0)).where(AjusteVenta.venta_id == sale.id))
            if amount + Decimal(str(already_credited)) > Decimal(sale.total):
                raise HTTPException(status_code=409, detail="Los ajustes aprobados superarían el total de la venta.")
            db.add(AjusteVenta(venta_id=sale.id, solicitud_id=item.id, tipo="nota_credito", monto_crc=amount, motivo=item.motivo))
        _audit(db, manager, f"{item.tipo}_aprobada", "venta", sale.id, {"monto_crc": str(amount), "solicitud_id": item.id})
    elif item.tipo == "cambio_moneda":
        sale = db.get(Venta, int(data["venta_id"]))
        if sale is None:
            raise HTTPException(status_code=404, detail="La venta de la solicitud ya no existe.")
        if sale.estado_pago != "pendiente":
            raise HTTPException(status_code=409, detail="La venta ya no está pendiente de revisión de pago.")
        old = {"total_crc": str(sale.total), "moneda": sale.moneda_pago, "monto_moneda": str(sale.monto_moneda) if sale.monto_moneda else None}
        sale.moneda_pago = str(data["moneda"])
        sale.monto_moneda = Decimal(data["monto_moneda"])
        sale.tipo_cambio = Decimal(data["tipo_cambio"])
        sale.fecha_tipo_cambio = datetime.strptime(data["fecha_tipo_cambio"], "%Y-%m-%d").date()
        sale.total = Decimal(data["equivalente_crc"])
        sale.estado_pago = "confirmada"
        _audit(db, manager, "moneda_venta_cambiada", "venta", sale.id, {"anterior": old, "nueva": {"total_crc": str(sale.total), "moneda": sale.moneda_pago, "monto_moneda": str(sale.monto_moneda), "tipo_cambio": str(sale.tipo_cambio), "fecha_tipo_cambio": sale.fecha_tipo_cambio.isoformat(), "detalle_tasas_bccr": data.get("detalle_tasas_bccr")}, "solicitud_id": item.id})


@router.post("/solicitudes/{solicitud_id}/resolver", response_model=SolicitudRead)
def resolver_solicitud(
    solicitud_id: int, payload: DecisionSolicitud, db: Session = Depends(get_db),
    manager: CurrentUser = Depends(require_manager),
):
    item = db.get(SolicitudAprobacion, solicitud_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if item.estado != "pendiente":
        raise HTTPException(status_code=409, detail="La solicitud ya fue resuelta.")
    if payload.decision == "aprobada":
        _apply_request(item, db, manager)
    elif item.tipo == "cambio_moneda":
        sale = db.get(Venta, int(item.datos["venta_id"]))
        if sale is not None and sale.estado_pago == "pendiente":
            sale.estado_pago = "denegada"
            _audit(db, manager, "pago_cambio_denegado", "venta", sale.id, {"solicitud_id": item.id})
    item.estado = payload.decision
    item.revisor_nombre = manager.name
    item.respuesta = payload.respuesta.strip() or None
    item.resuelta_en = datetime.now(timezone.utc).replace(tzinfo=None)
    _audit(db, manager, f"solicitud_{payload.decision}", "solicitud", item.id, {"tipo": item.tipo, "solicitante": item.solicitante_nombre, "respuesta": item.respuesta})
    db.commit()
    db.refresh(item)
    return _serialize_request(item)


@router.get("/auditoria", response_model=list[EventoAuditoriaRead])
def listar_auditoria(db: Session = Depends(get_db)):
    events = db.scalars(select(EventoAuditoria).order_by(EventoAuditoria.creado_en.desc(), EventoAuditoria.id.desc()).limit(500)).all()
    return [EventoAuditoriaRead(
        id=event.id, actor=event.actor, accion=event.accion, entidad=event.entidad,
        entidad_id=event.entidad_id, detalles=event.detalles, creado_en=event.creado_en.isoformat(),
    ) for event in events]


@router.post("/ventas", response_model=VentaRead, status_code=status.HTTP_201_CREATED)
def crear_venta(payload: VentaCreate, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    producto = db.get(Producto, payload.producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if producto.existencias < payload.cantidad:
        raise HTTPException(status_code=409, detail=f"Inventario insuficiente. Existencias disponibles: {producto.existencias}.")
    seller_id = user.seller_id if user.role == "vendedor" else payload.vendedor_id
    if user.role == "gerente" and seller_id is not None:
        seller = db.get(Vendedor, seller_id)
        if seller is None or not seller.activo:
            raise HTTPException(status_code=404, detail="Vendedor no encontrado")
    producto.existencias -= payload.cantidad
    venta = Venta(
        producto_id=producto.id,
        cantidad=payload.cantidad,
        fecha=payload.fecha,
        total=producto.precio * payload.cantidad,
        vendedor_id=seller_id,
        moneda_pago="CRC",
        monto_moneda=producto.precio * payload.cantidad,
    )
    db.add(venta)
    db.flush()
    db.add(MovimientoInventario(producto_id=producto.id, venta_id=venta.id, cantidad=-payload.cantidad, tipo="venta", actor=user.name, motivo=f"Venta #{venta.id}"))
    _audit(db, user, "venta_creada", "venta", venta.id, {"producto_id": producto.id, "cantidad": payload.cantidad, "total_crc": str(venta.total), "vendedor_id": seller_id})
    db.commit()
    db.refresh(venta)
    return venta


@router.patch("/ventas/{venta_id}", response_model=VentaRead)
def actualizar_venta(venta_id: int, payload: VentaUpdate, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    venta = db.get(Venta, venta_id)
    if venta is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    updates = payload.model_dump(exclude_unset=True)
    if set(updates) != {"vendedor_id"}:
        raise HTTPException(status_code=409, detail="Los cambios financieros deben solicitarse para aprobación; solo la gerencia puede reasignar vendedor.")
    if user.role != "gerente":
        raise HTTPException(status_code=403, detail="Solo la gerencia puede reasignar un vendedor.")
    previous = venta.vendedor_id
    seller = db.get(Vendedor, updates["vendedor_id"])
    if seller is None or not seller.activo:
        raise HTTPException(status_code=404, detail="Vendedor no encontrado")
    venta.vendedor_id = seller.id
    _audit(db, user, "venta_reasignada", "venta", venta.id, {"vendedor_anterior_id": previous, "vendedor_nuevo_id": seller.id})
    db.commit()
    db.refresh(venta)
    return venta


@router.delete("/ventas/{venta_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_venta(venta_id: int, db: Session = Depends(get_db), manager: CurrentUser = Depends(require_manager)):
    venta = db.get(Venta, venta_id)
    if venta is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    raise HTTPException(status_code=409, detail="Las ventas son historial contable; registra una devolución o nota de crédito aprobada.")


@router.get("/indicadores", response_model=IndicadoresRead)
def obtener_indicadores(db: Session = Depends(get_db)):
    suma = db.scalar(select(func.coalesce(func.sum(Venta.total), 0)).where(Venta.estado_pago != "pendiente"))
    sale_ids = select(Venta.id).where(Venta.estado_pago != "pendiente")
    ajustes = db.scalar(select(func.coalesce(func.sum(AjusteVenta.monto_crc), 0)).where(AjusteVenta.venta_id.in_(sale_ids)))
    cantidad_bruta = db.scalar(select(func.coalesce(func.sum(Venta.cantidad), 0)).where(Venta.estado_pago != "pendiente"))
    cantidad_devuelta = db.scalar(select(func.coalesce(func.sum(AjusteVenta.cantidad), 0)).where(AjusteVenta.tipo == "devolucion", AjusteVenta.venta_id.in_(sale_ids)))
    numero = db.scalar(select(func.count(Venta.id)).where(Venta.estado_pago != "pendiente"))
    agrupado_ajustes = (
        select(AjusteVenta.venta_id.label("venta_id"), func.sum(AjusteVenta.monto_crc).label("monto"), func.sum(AjusteVenta.cantidad).label("unidades"))
        .group_by(AjusteVenta.venta_id)
        .subquery()
    )
    agrupado = db.execute(
        select(
            Producto.categoria,
            func.sum(Venta.total - func.coalesce(agrupado_ajustes.c.monto, 0)),
            func.sum(Venta.cantidad - func.coalesce(agrupado_ajustes.c.unidades, 0)),
            func.count(Venta.id),
        )
        .join(Venta, Venta.producto_id == Producto.id)
        .outerjoin(agrupado_ajustes, agrupado_ajustes.c.venta_id == Venta.id)
        .where(Venta.estado_pago != "pendiente")
        .group_by(Producto.categoria)
        .order_by(Producto.categoria)
    ).all()
    total_bruto = Decimal(str(suma))
    total_ajustes = Decimal(str(ajustes))
    total = total_bruto - total_ajustes
    count_value = int(numero)
    return IndicadoresRead(
        ingresos_totales=total,
        ingresos_brutos=total_bruto,
        ajustes_aprobados=total_ajustes,
        cantidad_total_vendida=int(cantidad_bruta) - int(cantidad_devuelta),
        ticket_promedio=(total / count_value if count_value else Decimal("0")),
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
