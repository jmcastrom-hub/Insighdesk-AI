from datetime import date
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


class VentaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(gt=0, strict=True)
    cantidad: int = Field(gt=0, le=1_000_000, strict=True)
    fecha: date


class VentaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    cantidad: int
    fecha: date
    total: Decimal


class VentasCategoriaRead(BaseModel):
    categoria: str
    ingresos: Decimal
    cantidad_vendida: int
    numero_ventas: int


class IndicadoresRead(BaseModel):
    ingresos_totales: Decimal
    cantidad_total_vendida: int
    ticket_promedio: Decimal
    ventas_por_categoria: list[VentasCategoriaRead]


class ProductoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    categoria: str | None = Field(default=None, min_length=1, max_length=80)
    precio: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)

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
