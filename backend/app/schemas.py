from datetime import date, datetime
from decimal import Decimal

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProductoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=120)
    categoria: str = Field(min_length=1, max_length=80)
    precio: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

    @field_validator("nombre", "categoria")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El campo no puede estar vacío")
        return value


class ProductoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    categoria: str
    precio: Decimal
    existencias: int = 0


class VentaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(gt=0, strict=True)
    cantidad: int = Field(gt=0, le=1_000_000, strict=True)
    fecha: date
    vendedor_id: int | None = Field(default=None, gt=0, strict=True)


class VentaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    cantidad: int
    fecha: date
    total: Decimal
    vendedor_id: int | None = None
    moneda_pago: str = "CRC"
    monto_moneda: Decimal | None = None
    tipo_cambio: Decimal = Decimal("1")
    fecha_tipo_cambio: date | None = None
    estado_pago: Literal["confirmada", "pendiente", "denegada"] = "confirmada"


class VentasCategoriaRead(BaseModel):
    categoria: str
    ingresos: Decimal
    cantidad_vendida: int
    numero_ventas: int


class IndicadoresRead(BaseModel):
    ingresos_totales: Decimal
    ingresos_brutos: Decimal = Decimal("0")
    ajustes_aprobados: Decimal = Decimal("0")
    cantidad_total_vendida: int
    ticket_promedio: Decimal
    ventas_por_categoria: list[VentasCategoriaRead]


class ProductoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    categoria: str | None = Field(default=None, min_length=1, max_length=80)
    precio: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    existencias: int | None = Field(default=None, ge=0, strict=True)

    @field_validator("nombre", "categoria")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("El campo no puede estar vacío")
        return value

    @model_validator(mode="after")
    def require_update(self):
        if not self.model_fields_set:
            raise ValueError("Debe enviar al menos un campo para actualizar")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Los campos enviados no pueden ser nulos")
        return self


class VentaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    producto_id: int | None = Field(default=None, gt=0, strict=True)
    cantidad: int | None = Field(default=None, gt=0, le=1_000_000, strict=True)
    fecha: date | None = None
    vendedor_id: int | None = Field(default=None, gt=0, strict=True)

    @model_validator(mode="after")
    def require_update(self):
        if not self.model_fields_set:
            raise ValueError("Debe enviar al menos un campo para actualizar")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Los campos enviados no pueden ser nulos")
        return self


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=3000)

    @field_validator("content")
    @classmethod
    def trim_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El mensaje no puede estar vacío")
        return value


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def require_user_message_last(self):
        if self.messages[-1].role != "user":
            raise ValueError("El último mensaje debe ser del usuario")
        return self


class ChatResponse(BaseModel):
    reply: str


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    nombre: str
    rol: Literal["gerente", "vendedor"]


class VendedorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=256)

    @field_validator("nombre")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre no puede estar vacío")
        return value


class VendedorRead(BaseModel):
    id: int
    nombre: str
    activo: bool
    ventas: int
    unidades: int
    ingresos: Decimal


class SolicitudCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tipo: Literal["cambio_precio", "devolucion", "nota_credito", "cambio_moneda", "entrada_inventario"]
    motivo: str = Field(min_length=3, max_length=500)
    producto_id: int | None = Field(default=None, gt=0, strict=True)
    venta_id: int | None = Field(default=None, gt=0, strict=True)
    nuevo_precio: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    cantidad: int | None = Field(default=None, gt=0, le=1_000_000, strict=True)
    revendible: bool = False
    monto_crc: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    moneda: Literal["USD", "EUR"] | None = None
    monto_moneda: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=4)

    @field_validator("motivo")
    @classmethod
    def clean_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Explique el motivo de la solicitud")
        return value

    @model_validator(mode="after")
    def validate_action_fields(self):
        required = {
            "cambio_precio": ("producto_id", "nuevo_precio"),
            "devolucion": ("venta_id", "cantidad"),
            "nota_credito": ("venta_id", "monto_crc"),
            "cambio_moneda": ("venta_id", "moneda", "monto_moneda"),
            "entrada_inventario": ("producto_id", "cantidad"),
        }[self.tipo]
        if any(getattr(self, field) is None for field in required):
            raise ValueError("Faltan datos requeridos para este tipo de solicitud")
        return self


class SolicitudRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tipo: str
    estado: str
    datos: dict
    motivo: str
    solicitante_nombre: str
    revisor_nombre: str | None
    respuesta: str | None
    creada_en: datetime | None = None
    resuelta_en: datetime | None = None


class DecisionSolicitud(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["aprobada", "denegada"]
    respuesta: str = Field(default="", max_length=500)


class EventoAuditoriaRead(BaseModel):
    id: int
    actor: str
    accion: str
    entidad: str
    entidad_id: int | None
    detalles: dict
    creado_en: str


class IndicadorVendedorRead(BaseModel):
    vendedor_id: int | None
    vendedor: str
    ventas: int
    unidades: int
    ingresos: Decimal
