"""Local seller and manager authentication using only the Python standard library."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Vendedor

MANAGER_NAME = "Jose Castro"
TOKEN_TTL_SECONDS = 8 * 60 * 60


@dataclass(frozen=True)
class CurrentUser:
    name: str
    role: str
    seller_id: int | None = None


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _signing_key() -> bytes:
    secret = os.getenv("APP_AUTH_SECRET") or os.getenv("MANAGER_PASSWORD")
    if not secret:
        raise HTTPException(status_code=503, detail="Configura MANAGER_PASSWORD en el .env del backend.")
    return hashlib.sha256(secret.encode("utf-8")).digest()


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
    return salt, _b64(digest)


def verify_password(password: str, salt: str, expected: str) -> bool:
    _salt, digest = hash_password(password, salt)
    return hmac.compare_digest(digest, expected)


def issue_token(user: CurrentUser) -> str:
    payload = {"name": user.name, "role": user.role, "seller_id": user.seller_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    encoded = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(_signing_key(), encoded.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded}.{_b64(signature)}"


def _decode_token(token: str) -> CurrentUser:
    try:
        encoded, supplied_signature = token.split(".", 1)
        expected_signature = _b64(hmac.new(_signing_key(), encoded.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise ValueError("firma inválida")
        payload = json.loads(_unb64(encoded))
        if int(payload["exp"]) < int(time.time()):
            raise ValueError("sesión vencida")
        return CurrentUser(str(payload["name"]), str(payload["role"]), payload.get("seller_id"))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="La sesión no es válida o ya venció.") from exc


def authenticate(username: str, password: str, db: Session) -> CurrentUser:
    if username.strip().casefold() == MANAGER_NAME.casefold():
        configured = os.getenv("MANAGER_PASSWORD")
        if not configured:
            raise HTTPException(status_code=503, detail="Configura MANAGER_PASSWORD en el .env del backend.")
        if not hmac.compare_digest(password, configured):
            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
        return CurrentUser(MANAGER_NAME, "gerente")

    seller = db.query(Vendedor).filter(Vendedor.nombre == username.strip(), Vendedor.activo.is_(True)).first()
    if seller is None or not verify_password(password, seller.password_salt, seller.password_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
    return CurrentUser(seller.nombre, "vendedor", seller.id)


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Inicia sesión para continuar.")
    user = _decode_token(authorization[7:].strip())
    if user.role == "vendedor":
        seller = db.get(Vendedor, user.seller_id) if user.seller_id else None
        if seller is None or not seller.activo or seller.nombre != user.name:
            raise HTTPException(status_code=401, detail="La cuenta de vendedor está inactiva.")
    elif user.role != "gerente":
        raise HTTPException(status_code=401, detail="El rol de la sesión no es válido.")
    return user


def require_manager(request: Request, user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != "gerente":
        raise HTTPException(status_code=403, detail="Esta acción requiere aprobación de la gerencia.")
    client_host = request.client.host if request and request.client else ""
    if client_host not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(status_code=403, detail="Las aprobaciones solo se permiten desde la computadora local del gerente.")
    return user
