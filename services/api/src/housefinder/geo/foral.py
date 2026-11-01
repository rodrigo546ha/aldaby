"""Parcelas de los catastros forales (ADR-0032): País Vasco y Navarra, que la Dirección General del
Catastro no cubre.

Las tres diputaciones vascas publican sus parcelas como WFS INSPIRE (`cp:CadastralParcel`, con su
`referencePoint`); el Gobierno de Navarra, en IDENA, por municipio, polígono y parcela, sin punto:
se calcula uno dentro del polígono. Solo se leen las referencias con formatos comprobados contra
cada servicio el 2026-11-01.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

import httpx

from housefinder.geo.catastro import CatastroUnavailable, Parcel, ParcelNotFound
from housefinder.geo.http import failure

FES = "http://www.opengis.net/fes/2.0"
SPAIN_LAT = (27.0, 44.5)  # para comprobar que las coordenadas no vienen al revés
SPAIN_LON = (-19.0, 5.0)


@dataclass(frozen=True)
class ForalService:
    province: str  # código INE de la provincia
    territory: str
    source_id: str
    name: str
    url: str
    attribution: str
    conditions: str


GIPUZKOA = ForalService(
    "20", "Gipuzkoa", "gipuzkoa-catastro-wfs",
    "Parcelas catastrales de Gipuzkoa (WFS INSPIRE, Diputación Foral de Gipuzkoa)",
    "https://b5m.gipuzkoa.eus/inspire/wfs/gipuzkoa_wfs_cp", "Fuente: Diputación Foral de Gipuzkoa",
    "Reutilización libre indicando la autoría (GetCapabilities, AccessConstraints)")
BIZKAIA = ForalService(
    "48", "Bizkaia", "bizkaia-catastro-wfs",
    "Parcelas catastrales de Bizkaia (WFS INSPIRE, Diputación Foral de Bizkaia)",
    "https://geo.bizkaia.eus/arcgisserverinspire/rest/services/Catastro/Annex1/MapServer/exts/"
    "InspireFeatureDownload/service", "Fuente: Diputación Foral de Bizkaia",
    "Sin condiciones declaradas en el servicio (por verificar)")
ARABA = ForalService(
    "01", "Araba/Álava", "araba-catastro-wfs",
    "Parcelas catastrales de Araba/Álava (WFS INSPIRE, Diputación Foral de Álava)",
    "https://geo.araba.eus/geoserver/INSPIRE_CP/wfs", "Fuente: Diputación Foral de Álava",
    "Sin condiciones declaradas en el servicio (por verificar)")
NAVARRA = ForalService(
    "31", "Navarra", "idena-catastro-navarra",
    "Parcelas catastrales de Navarra (IDENA, Gobierno de Navarra)",
    "https://idena.navarra.es/ogc/wfs", "Fuente: Gobierno de Navarra (IDENA)", "CC BY 4.0")
SERVICES = {s.province: s for s in (GIPUZKOA, BIZKAIA, ARABA, NAVARRA)}
FORAL = frozenset(SERVICES)
NAVARRA_LAYERS = ("CATAST_Pol_ParcelaRusti", "CATAST_Pol_ParcelaUrba", "CATAST_Pol_ParcelaMixta")

# Provincia (20), municipio (3), parcela (7) y la unidad: «2001860840226144403E».
GIPUZKOA_REF = re.compile(r"^20(\d{3})(\d{7})[0-9A-Z]{0,8}$")
BIZKAIA_REF = re.compile(r"^48\.?(\d{3})\.?(\d{4})\.?(\d{5})$")
ARABA_REF = re.compile(r"^\d{8}$")


def foral_key(province: str | None, cadastral_ref: str) -> tuple[str, str] | None:
    """(provincia, clave de la parcela) de una referencia foral; None si no tiene la forma de
    ninguna. Sin provincia, solo las formas que no se confunden con las de la Dirección General
    (que llevan letras en las posiciones 6 u 8)."""
    ref = re.sub(r"\s", "", cadastral_ref).upper()
    if province in (None, "20") and (found := GIPUZKOA_REF.match(ref)):
        return "20", f"{found[1]}-{found[2]}"
    if province in (None, "48") and (found := BIZKAIA_REF.match(ref)):
        return "48", f"48.{found[1]}.{found[2]}.{found[3]}"
    if province == "01" and ARABA_REF.match(ref):
        return "01", ref
    return None


def navarra_key(municipality: str, polygon: str, parcel: str) -> str:
    """Clave de una parcela de Navarra: código INE del municipio, polígono y parcela."""
    return f"{municipality}-{int(polygon)}-{int(parcel)}"


def find_foral_parcel(client: httpx.Client, province: str, key: str) -> Parcel:
    if province == "20":
        municipality, number = key.split("-")
        root = _get_xml(client, GIPUZKOA, "cp:CadastralParcel", _cp_filter(number), {})
        features = [f for f in _parcels(root) if f.local_id.startswith(f"{municipality}-{number}-")]
    elif province == "48":
        root = _get_xml(client, BIZKAIA, "cp:CadastralParcel", _cp_filter(key), {})
        features = _parcels(root)
    elif province == "01":
        root = _get_xml(client, ARABA, "INSPIRE_CP:CP.CadastralParcel", _araba_filter(key),
                        {"SRSNAME": "EPSG:4258"})
        features = _parcels(root)
    elif province == "31":
        return _navarra(client, key)
    else:
        raise ParcelNotFound(f"La provincia {province} no tiene catastro foral")
    return _current(features, SERVICES[province], key)


@dataclass(frozen=True)
class ForalParcel:
    local_id: str
    current: bool  # sin `endLifespanVersion`: la versión vigente
    lon: float | None
    lat: float | None


def parse_parcels(xml: bytes) -> list[ForalParcel]:
    try:
        return _parcels(ET.fromstring(xml))
    except ET.ParseError as exc:
        raise ParcelNotFound(f"Respuesta del catastro foral que no es XML: {exc}") from exc


def point_on_surface(geometry: dict[str, Any]) -> tuple[float, float]:
    """Un punto dentro del polígono más grande (lon, lat): el centro del tramo más ancho de la
    horizontal que pasa por su centroide. El centroide solo no basta: puede caer fuera."""
    if geometry.get("type") == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry.get("type") == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        raise ParcelNotFound(f"Geometría {geometry.get('type')!r} no esperada")
    ring = max((p[0] for p in polygons if p and len(p[0]) >= 4), key=lambda r: abs(_area(r)),
               default=None)
    if ring is None:
        raise ParcelNotFound("Parcela sin polígono")
    _, y = _centroid(ring)
    crossings = sorted(
        x1 + (y - y1) * (x2 - x1) / (y2 - y1)
        for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False)
        if (y1 <= y < y2) or (y2 <= y < y1)
    )
    spans = list(zip(crossings[::2], crossings[1::2], strict=False))
    if not spans:
        raise ParcelNotFound("No se encuentra un punto dentro de la parcela")
    left, right = max(spans, key=lambda s: s[1] - s[0])
    return (left + right) / 2, y


def _navarra(client: httpx.Client, key: str) -> Parcel:
    municipality, polygon, parcel = key.split("-")
    query = (f"CMUNICIPIO={int(municipality[2:])} AND POLIGONO={int(polygon)} "
             f"AND PARCELA={int(parcel)}")
    features: list[Any] = []
    for layer in NAVARRA_LAYERS:
        payload = _get(client, NAVARRA, {
            "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
            "TYPENAMES": f"IDENA:{layer}", "outputFormat": "application/json",
            "srsName": "EPSG:4326", "CQL_FILTER": query,
        }).json()
        features = (payload.get("features") or []) if isinstance(payload, dict) else []
        if features:
            break
    if len(features) != 1:
        raise ParcelNotFound(f"Navarra: {len(features)} parcelas para el polígono {polygon}, "
                             f"parcela {parcel}")
    lon, lat = point_on_surface(features[0].get("geometry") or {})
    _check_spain(lon, lat)
    name = (features[0].get("properties") or {}).get("MUNICIPIO") or ""
    return Parcel(lon, lat, key, f"Polígono {polygon} Parcela {parcel} {name} (NAVARRA)")


def _current(features: list[ForalParcel], service: ForalService, key: str) -> Parcel:
    current = [f for f in features if f.current and f.lon is not None and f.lat is not None]
    if len(current) != 1:
        raise ParcelNotFound(f"{service.territory}: {len(current)} parcelas vigentes con la "
                             f"referencia {key}")
    lon, lat = current[0].lon or 0.0, current[0].lat or 0.0
    _check_spain(lon, lat)
    return Parcel(lon, lat, key, f"Parcela {key} ({service.territory})")


def _parcels(root: ET.Element) -> list[ForalParcel]:
    parcels: list[ForalParcel] = []
    for element in root.iter():
        if _local(element.tag) not in ("CadastralParcel", "CP.CadastralParcel"):
            continue
        ids = [e.text or "" for e in element.iter() if _local(e.tag) in ("localId", "inspireId")
               and (e.text or "").strip()]
        end = next((e for e in element.iter() if _local(e.tag) == "endLifespanVersion"), None)
        current = end is None or not (end.text or "").strip()
        lon, lat = _reference_point(element)
        parcels.append(ForalParcel(ids[0].strip() if ids else "", current, lon, lat))
    return parcels


def _reference_point(element: ET.Element) -> tuple[float | None, float | None]:
    reference = next((e for e in element.iter() if _local(e.tag) == "referencePoint"), None)
    if reference is None:
        return None, None
    point = next((e for e in reference.iter() if _local(e.tag) == "Point"), None)
    pos = next((e for e in reference.iter() if _local(e.tag) == "pos"), None)
    if point is None or pos is None or not pos.text:
        return None, None
    first, second = (float(v) for v in pos.text.split()[:2])
    srs = point.get("srsName", "")
    # «…/def/crs/EPSG/0/4258» y «urn:ogc:def:crs:…» van en el orden del sistema (lat, lon);
    # «…epsg.xml#4258» y «EPSG:4258», en el de GML antiguo (lon, lat).
    if "4258" not in srs and "4326" not in srs:
        return None, None
    if "/def/crs/" in srs or srs.startswith("urn:ogc:def:crs"):
        return second, first
    return first, second


def _check_spain(lon: float, lat: float) -> None:
    if not (SPAIN_LAT[0] <= lat <= SPAIN_LAT[1] and SPAIN_LON[0] <= lon <= SPAIN_LON[1]):
        raise ParcelNotFound(f"Coordenadas fuera de España: {lon}, {lat}")


def _cp_filter(reference: str) -> str:
    return _equal_filter("http://inspire.ec.europa.eu/schemas/cp/4.0", "cp",
                         "cp:nationalCadastralReference", reference)


def _araba_filter(reference: str) -> str:
    return _equal_filter("http://geo.araba.eus/INSPIRE_CP", "INSPIRE_CP",
                         "INSPIRE_CP:nationalCadastralReference", reference)


def _equal_filter(namespace: str, prefix: str, field: str, value: str) -> str:
    return (f'<fes:Filter xmlns:fes="{FES}" xmlns:{prefix}="{namespace}"><fes:PropertyIsEqualTo>'
            f"<fes:ValueReference>{field}</fes:ValueReference><fes:Literal>{value}</fes:Literal>"
            "</fes:PropertyIsEqualTo></fes:Filter>")


def _get_xml(client: httpx.Client, service: ForalService, type_name: str, query: str,
             extra: dict[str, str]) -> ET.Element:
    response = _get(client, service, {"SERVICE": "WFS", "VERSION": "2.0.0",
                                      "REQUEST": "GetFeature", "TYPENAMES": type_name,
                                      "FILTER": query, **extra})
    try:
        return ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise CatastroUnavailable(f"{service.territory}: respuesta que no es XML") from exc


def _get(client: httpx.Client, service: ForalService, params: dict[str, str]) -> httpx.Response:
    try:
        response = client.get(service.url, params=params, timeout=30)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise CatastroUnavailable(
            f"El catastro de {service.territory} no responde: {failure(exc)}") from exc
    return response


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1]


def _area(ring: list[list[float]]) -> float:
    return sum(x1 * y2 - x2 * y1
               for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False)) / 2


def _centroid(ring: list[list[float]]) -> tuple[float, float]:
    area = _area(ring)
    if area == 0:
        return ring[0][0], ring[0][1]
    cx = sum((x1 + x2) * (x1 * y2 - x2 * y1)
             for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False)) / (6 * area)
    cy = sum((y1 + y2) * (x1 * y2 - x2 * y1)
             for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False)) / (6 * area)
    return cx, cy
