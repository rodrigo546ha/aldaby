"""Imagen de un inmueble desde fuentes públicas (ADR-0054).

- **Foto de fachada del Catastro** (`OVCFotoFachada`, servicio libre de la Sede Electrónica del
  Catastro, el mismo host que ADR-0016): por los 14 caracteres de la parcela. Si la parcela no
  tiene foto, el servicio responde 200 sin cuerpo.
- **Ortofoto del PNOA** (WMS del IGN, CC BY 4.0 scne.es): un recorte de unos 250 × 160 m
  alrededor del punto del inmueble.

Solo descargan; el recorte, la marca del punto y la caché están en `offers/photos.py`.
"""

from __future__ import annotations

import math

import httpx

FACADE_URL = (
    "https://ovc.catastro.meh.es/OVCServWeb/OVCWcfLibres/OVCFotoFachada.svc/"
    "RecuperarFotoFachadaGet"
)
AERIAL_URL = "https://www.ign.es/wms-inspire/pnoa-ma"
FACADE_ATTRIBUTION = "Foto de fachada: Dirección General del Catastro"
AERIAL_ATTRIBUTION = "Ortofoto PNOA: CC BY 4.0 scne.es"
AERIAL_SIZE = (640, 400)  # píxeles
AERIAL_HEIGHT_M = 160  # metros que cubre la imagen de arriba abajo
METERS_PER_DEGREE = 111_320
TIMEOUT = 10.0


def facade(client: httpx.Client, parcel_ref: str) -> bytes | None:
    """La foto de fachada de la parcela, o None si el Catastro no tiene."""
    resp = client.get(FACADE_URL, params={"ReferenciaCatastral": parcel_ref[:14]},
                      timeout=TIMEOUT)
    resp.raise_for_status()
    if not resp.content or not resp.headers.get("content-type", "").startswith("image/"):
        return None
    return resp.content


def aerial_bbox(lon: float, lat: float) -> tuple[float, float, float, float]:
    """Caja (sur, oeste, norte, este) del recorte, con el punto en el centro.

    En WMS 1.3.0 con EPSG:4326 el orden de los ejes es latitud, longitud.
    """
    width, height = AERIAL_SIZE
    half_lat = AERIAL_HEIGHT_M / 2 / METERS_PER_DEGREE
    half_lon = half_lat * width / height / math.cos(math.radians(lat))
    return (lat - half_lat, lon - half_lon, lat + half_lat, lon + half_lon)


def aerial(client: httpx.Client, lon: float, lat: float) -> bytes | None:
    """El recorte de la ortofoto alrededor del punto, o None si el IGN no da imagen."""
    width, height = AERIAL_SIZE
    resp = client.get(AERIAL_URL, params={
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap",
        "LAYERS": "OI.OrthoimageCoverage", "STYLES": "", "CRS": "EPSG:4326",
        "BBOX": ",".join(f"{v:.6f}" for v in aerial_bbox(lon, lat)),
        "WIDTH": str(width), "HEIGHT": str(height), "FORMAT": "image/jpeg",
    }, timeout=TIMEOUT)
    resp.raise_for_status()
    if not resp.headers.get("content-type", "").startswith("image/"):
        return None  # un error del WMS llega como XML con 200
    return resp.content
