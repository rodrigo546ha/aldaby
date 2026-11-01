"""Coordenadas de una parcela por su referencia catastral (ADR-0016) y referencia de una finca
rústica por su polígono y parcela (ADR-0020).

Servicio `Consulta_CPMRC` de la Sede Electrónica del Catastro, versión WCF con salida JSON:
información catastral no protegida, sin registro. Devuelve el centroide de la parcela y su
dirección catastral (`ldt`). Solo se envían los 14 primeros caracteres de la referencia, los de la
parcela. `Consulta_DNPPP`, del mismo servicio, da la referencia a partir de provincia, municipio,
polígono y parcela. Cita: «Fuente: Dirección General del Catastro».
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import httpx

from housefinder.geo.http import failure

CPMRC_URL = (
    "https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCoordenadas.svc/json/"
    "Consulta_CPMRC"
)
DNPPP_URL = (
    "https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCallejero.svc/json/Consulta_DNPPP"
)
SOURCE_ID = "catastro-coordenadas"
SOURCE_NAME = "Servicio de coordenadas de la Sede Electrónica del Catastro (Consulta_CPMRC)"
ATTRIBUTION = "Fuente: Dirección General del Catastro"
LICENSE_URL = "https://www.catastro.hacienda.gob.es/es-ES/avisolegal.html"
SRS = "EPSG:4326"
PARCEL = re.compile(r"^[0-9A-Z]{14}$")


class ParcelNotFound(LookupError):
    """El Catastro no tiene esa referencia o no devuelve coordenadas."""


class CatastroUnavailable(ParcelNotFound):
    """El Catastro no responde: otro intento, otro día, puede encontrarla."""


@dataclass(frozen=True)
class Parcel:
    lon: float
    lat: float
    parcel_ref: str  # 14 caracteres
    address: str  # dirección catastral: «CR CAMARMA 21 ALCALA DE HENARES (MADRID)»


def parcel_ref(cadastral_ref: str) -> str:
    """Los 14 caracteres de la parcela de una referencia de 14, 18 o 20."""
    ref = re.sub(r"\s", "", cadastral_ref).upper()[:14]
    if not PARCEL.match(ref):
        raise ParcelNotFound("La referencia catastral no está bien formada")
    return ref


def parse_cpmrc(payload: Any) -> Parcel:
    result = payload.get("Consulta_CPMRCResult") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        raise ParcelNotFound("Respuesta del Catastro sin resultado")
    errors = result.get("lerr") or []
    if errors:
        first = errors[0] if isinstance(errors, list) else errors
        raise ParcelNotFound(f"Catastro: {first.get('des', 'error')} ({first.get('cod', '?')})")
    coords = (result.get("coordenadas") or {}).get("coord") or []
    if isinstance(coords, dict):
        coords = [coords]
    if len(coords) != 1:
        raise ParcelNotFound(f"El Catastro devuelve {len(coords)} parcelas para la referencia")
    coord = coords[0]
    geo = coord.get("geo") or {}
    if geo.get("srs") != SRS:
        raise ParcelNotFound(f"Coordenadas en {geo.get('srs')}, no en {SRS}")
    pc = coord.get("pc") or {}
    return Parcel(
        lon=float(geo["xcen"]),
        lat=float(geo["ycen"]),
        parcel_ref=f"{pc.get('pc1', '')}{pc.get('pc2', '')}",
        address=" ".join(str(coord.get("ldt", "")).split()),
    )


def find_parcel(client: httpx.Client, cadastral_ref: str) -> Parcel:
    """Parcela de la referencia. Si el Catastro no responde, `CatastroUnavailable`: la oferta se
    ubica por otra vía o se queda sin ubicar, y la ingesta sigue."""
    ref = parcel_ref(cadastral_ref)
    return parse_cpmrc(_get(client, CPMRC_URL, {"SRS": SRS, "RefCat": ref}))


def parse_dnppp(payload: Any) -> str:
    """Referencia de la parcela (14 caracteres) de la respuesta de `Consulta_DNPPP`."""
    result = payload.get("consulta_dnpppResult") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        raise ParcelNotFound("Respuesta del Catastro sin resultado")
    errors = result.get("lerr") or []
    if errors:
        first = errors[0] if isinstance(errors, list) else errors
        raise ParcelNotFound(f"Catastro: {first.get('des', 'error')} ({first.get('cod', '?')})")
    if isinstance(result.get("bico"), dict):
        found = [(result["bico"].get("bi") or {}).get("idbi", {}).get("rc") or {}]
    else:
        listed = (result.get("lrcdnp") or {}).get("rcdnp") or []
        items = listed if isinstance(listed, list) else [listed]
        found = [item.get("rc") or {} for item in items]
    refs = {f"{rc.get('pc1', '')}{rc.get('pc2', '')}" for rc in found}
    if len(refs) != 1:
        raise ParcelNotFound(f"El Catastro devuelve {len(refs)} parcelas para ese polígono")
    return parcel_ref(refs.pop())


def find_rustic_parcel(client: httpx.Client, province: str, municipality: str, polygon: str,
                       parcel: str) -> str:
    """Referencia de la parcela rústica `parcel` del polígono `polygon`. Acepta los nombres con o
    sin tildes; la provincia es obligatoria."""
    return parse_dnppp(_get(client, DNPPP_URL, {
        "Provincia": province, "Municipio": municipality, "Poligono": polygon, "Parcela": parcel,
    }))


def _get(client: httpx.Client, url: str, params: dict[str, str]) -> Any:
    try:
        response = client.get(url, params=params, timeout=20)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise CatastroUnavailable(f"El Catastro no responde: {failure(exc)}") from exc
