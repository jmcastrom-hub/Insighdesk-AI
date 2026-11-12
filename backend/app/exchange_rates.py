"""Rates from the BCCR SDDE API; never falls back to a manually entered rate."""

import json
import os
from datetime import date, timedelta
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import HTTPException

API_BASE = "https://apim.bccr.fi.cr/SDDE/api/Bccr.GE.SDDE.Publico.Indicadores.API"
USD_BUY_INDICATOR = os.getenv("BCCR_USD_BUY_INDICATOR", "317")
EUR_USD_INDICATOR = os.getenv("BCCR_EUR_USD_INDICATOR", "333")


def _series(indicator: str, start: date, end: date, token: str) -> list[dict]:
    query = urlencode({"fechaInicio": start.strftime("%Y/%m/%d"), "fechaFin": end.strftime("%Y/%m/%d"), "idioma": "ES"})
    url = f"{API_BASE}/indicadoresEconomicos/{indicator}/series?{query}"
    request = Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise HTTPException(status_code=503, detail="El BCCR rechazó BCCR_API_TOKEN; revisa el token oficial en el .env.") from exc
        raise HTTPException(status_code=502, detail=f"El servicio del BCCR respondió HTTP {exc.code}.") from exc
    except (TimeoutError, URLError) as exc:
        raise HTTPException(status_code=504, detail="No se pudo consultar el tipo de cambio del BCCR.") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=502, detail="El BCCR devolvió una respuesta que no se pudo interpretar.") from exc

    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "series", "resultado", "result"):
            if isinstance(payload.get(key), list):
                return payload[key]
        data = payload.get("datos")
        if isinstance(data, list):
            rows = []
            for block in data:
                if not isinstance(block, dict):
                    continue
                indicators = block.get("indicadores")
                if isinstance(indicators, list):
                    for indicator_data in indicators:
                        if isinstance(indicator_data, dict) and isinstance(indicator_data.get("series"), list):
                            rows.extend(indicator_data["series"])
                if isinstance(block.get("series"), list):
                    rows.extend(block["series"])
            if rows:
                return rows
    raise HTTPException(status_code=502, detail="El formato de series del BCCR no es el esperado.")


def _value_for_date(rows: list[dict], target: date) -> tuple[Decimal, date] | None:
    candidates = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw_date = next((row[key] for key in ("fecha", "Fecha", "date", "Date") if row.get(key)), None)
        raw_value = next((row[key] for key in ("valor", "Valor", "value", "Value", "valorDatoPorPeriodo") if row.get(key) is not None), None)
        if raw_date is None or raw_value is None:
            continue
        try:
            if isinstance(raw_date, str):
                row_date = date.fromisoformat(raw_date[:10].replace("/", "-"))
            else:
                continue
            value = Decimal(str(raw_value).replace(",", "."))
        except (ValueError, ArithmeticError):
            continue
        if row_date <= target and value > 0:
            candidates.append((row_date, value))
    if not candidates:
        return None
    row_date, value = max(candidates, key=lambda item: item[0])
    return value, row_date


def exchange_rate_details(currency: str, on_date: date) -> dict:
    token = os.getenv("BCCR_API_TOKEN")
    if not token:
        raise HTTPException(status_code=503, detail="Configura BCCR_API_TOKEN en el .env del backend para usar tasas oficiales.")
    currency = currency.upper()
    start = on_date - timedelta(days=10)
    usd_data = _value_for_date(_series(USD_BUY_INDICATOR, start, on_date, token), on_date)
    if usd_data is None:
        raise HTTPException(status_code=503, detail="El BCCR no publicó una tasa de compra USD para esa fecha.")
    usd_crc, usd_date = usd_data
    if currency == "USD":
        return {"crc_por_unidad": usd_crc, "fecha": usd_date, "usd_crc_compra": usd_crc, "fecha_usd": usd_date}
    if currency != "EUR":
        raise HTTPException(status_code=422, detail="Solo se admiten pagos en CRC, USD o EUR.")
    eur_data = _value_for_date(_series(EUR_USD_INDICATOR, start, on_date, token), on_date)
    if eur_data is None:
        raise HTTPException(status_code=503, detail="El BCCR no publicó una tasa EUR/USD para esa fecha.")
    eur_usd, eur_date = eur_data
    return {
        "crc_por_unidad": usd_crc * eur_usd,
        "fecha": min(usd_date, eur_date),
        "usd_crc_compra": usd_crc,
        "fecha_usd": usd_date,
        "eur_usd": eur_usd,
        "fecha_eur_usd": eur_date,
    }


def exchange_rate(currency: str, on_date: date) -> tuple[Decimal, date]:
    details = exchange_rate_details(currency, on_date)
    return details["crc_por_unidad"], details["fecha"]
