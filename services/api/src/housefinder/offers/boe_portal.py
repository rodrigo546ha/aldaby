"""Scraper del Portal de Subastas del BOE (subastas.boe.es).

Extrae las condiciones generales y particulares de la subasta a través de todas sus pestañas
(ver=1 a ver=5), los bienes/lotes con sus datos catastrales y registrales, la autoridad gestora,
los acreedores/ejecutantes y los documentos oficiales adjuntos (edictos, certificaciones registrales
de dominio y cargas, informes ocupacionales, pliegos).
"""

from __future__ import annotations

import html
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse

import httpx

from housefinder.ingestion.public_pdf import UnreadablePdf, pdf_pages
from housefinder.offers.model import NormalizedOffer

BASE_URL = "https://subastas.boe.es"
DETAIL_URL = f"{BASE_URL}/detalleSubasta.php"
DOC_URL = f"{BASE_URL}/verDocumento.php"
SEARCH_URL = f"{BASE_URL}/subastas_ava.php"

PORTAL_ID_RE = re.compile(r"SUB-[A-Z]{2}-\d{4}-\w+", re.IGNORECASE)
MAX_DOCUMENT_BYTES = 15 * 1024 * 1024
DEFAULT_TIMEOUT_S = 30.0
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
)


@dataclass(frozen=True)
class DocumentRef:
    """Enlace a un documento oficial adjunto en el portal."""

    id_doc: str
    title: str
    url: str


@dataclass(frozen=True)
class ManagingAuthority:
    """Autoridad gestora / juzgado o administración que tramita la subasta (ver=2)."""

    codigo: str | None
    descripcion: str | None
    direccion: str | None
    telefono: str | None
    fax: str | None
    email: str | None


@dataclass(frozen=True)
class ScrapedPropertyItem:
    """Bien inmueble individual subastado dentro de un lote (ver=3)."""

    bien_num: int
    tipo_bien: str
    descripcion: str
    idufir: str | None
    referencia_catastral: str | None
    direccion: str | None
    codigo_postal: str | None
    localidad: str | None
    provincia: str | None
    vivienda_habitual: str | None
    situacion_posesoria: str | None
    visitable: str | None
    cargas: str | None
    inscripcion_registral: str | None


@dataclass(frozen=True)
class ScrapedLot:
    """Lote de la subasta con sus condiciones económicas y bienes (ver=3)."""

    lote_num: int
    titulo: str | None
    valor_subasta: Decimal | None
    tasacion: Decimal | None
    deposito: Decimal | None
    puja_minima: Decimal | None
    tramos: Decimal | None
    cantidad_reclamada: Decimal | None
    bienes: list[ScrapedPropertyItem] = field(default_factory=list)


@dataclass(frozen=True)
class CreditorParty:
    """Acreedor o ejecutante de la subasta (ver=4)."""

    nombre: str | None
    nif: str | None
    direccion: str | None
    localidad: str | None
    provincia: str | None
    pais: str | None


@dataclass(frozen=True)
class ScrapedAuctionNotice:
    """Datos generales de la subasta y documentos (ver=1)."""

    portal_id: str
    portal_url: str
    tipo_subasta: str | None
    cuenta_expediente: str | None
    fecha_inicio: str | None
    fecha_conclusion: str | None
    cantidad_reclamada: Decimal | None
    lotes_label: str | None
    anuncio_boe: str | None
    valor_subasta: Decimal | None
    tasacion: Decimal | None
    puja_minima: Decimal | None
    tramos_entre_pujas: Decimal | None
    importe_deposito: Decimal | None
    documents: list[DocumentRef] = field(default_factory=list)


BiddingState = Literal[
    "sin_pujas",
    "con_pujas_requiere_login",
    "puja_secreta",
    "puja_publica",
    "desconocido",
]


@dataclass(frozen=True)
class ScrapedAuction:
    """Subasta completa recopilada de todas las pestañas del Portal de Subastas."""

    portal_id: str
    portal_url: str
    notice: ScrapedAuctionNotice
    authority: ManagingAuthority | None
    lots: list[ScrapedLot]
    creditors: list[CreditorParty]
    highest_bid: Decimal | None
    bid_status: str | None
    bidding_state: str = "sin_pujas"
    lot_bids: dict[int, dict[str, Any]] = field(default_factory=dict)
    raw_html: dict[str, str] = field(default_factory=dict)

    def summary_text(self) -> str:
        """Texto consolidado de todas las pestañas para el análisis del LLM."""
        lines = [
            f"SUBASTA: {self.portal_id}",
            f"Tipo: {self.notice.tipo_subasta or 'Desconocido'}",
            f"Expediente: {self.notice.cuenta_expediente or 'No consta'}",
            f"Anuncio BOE: {self.notice.anuncio_boe or 'No consta'}",
            f"Fecha inicio: {self.notice.fecha_inicio or 'No consta'}",
            f"Fecha conclusión: {self.notice.fecha_conclusion or 'No consta'}",
            f"Cantidad reclamada: {self.notice.cantidad_reclamada} €"
            if self.notice.cantidad_reclamada is not None
            else "Cantidad reclamada: No consta",
            f"Valor subasta: {self.notice.valor_subasta} €"
            if self.notice.valor_subasta is not None
            else "Valor subasta: No consta",
            f"Tasación: {self.notice.tasacion} €"
            if self.notice.tasacion is not None
            else "Tasación: No consta",
            f"Depósito: {self.notice.importe_deposito} €"
            if self.notice.importe_deposito is not None
            else "Depósito: No consta",
            f"Puja mínima: {self.notice.puja_minima} €"
            if self.notice.puja_minima is not None
            else "Puja mínima: Sin puja mínima",
            f"Tramos: {self.notice.tramos_entre_pujas} €"
            if self.notice.tramos_entre_pujas is not None
            else "Tramos: Sin tramos",
        ]
        if self.authority and self.authority.descripcion:
            auth_desc = self.authority.descripcion
            auth_dir = f" ({self.authority.direccion})" if self.authority.direccion else ""
            lines.append(f"Autoridad gestora: {auth_desc}{auth_dir}")
        if self.creditors:
            lines.append(
                "Acreedores: " + "; ".join(c.nombre or "" for c in self.creditors if c.nombre)
            )

        lines.append(f"\nEstado de las pujas: {self.bidding_state}")
        if self.highest_bid is not None:
            lines.append(f"Puja máxima actual: {self.highest_bid} €")
        elif self.bidding_state == "con_pujas_requiere_login":
            lines.append(
                "Pujas: La subasta ha recibido pujas "
                "(el importe exacto requiere usuario registrado en el portal)."
            )
        elif self.bidding_state == "puja_secreta":
            lines.append("Pujas: La puja máxima de la subasta es secreta (sobre cerrado).")
        elif self.bidding_state == "sin_pujas":
            lines.append("Pujas: La subasta no ha recibido pujas hasta el momento.")
        elif self.bid_status:
            lines.append(f"Detalle pujas: {self.bid_status}")

        for lot in self.lots:
            lines.append(f"\n--- LOTE {lot.lote_num}: {lot.titulo or ''} ---")
            if lot.valor_subasta is not None:
                lines.append(f"Valor subasta lote: {lot.valor_subasta} €")
            if lot.deposito is not None:
                lines.append(f"Depósito lote: {lot.deposito} €")
            for bien in lot.bienes:
                lines.append(f"Bien {bien.bien_num} ({bien.tipo_bien}):")
                lines.append(f"  Descripción: {bien.descripcion}")
                if bien.direccion:
                    cp = bien.codigo_postal or ""
                    loc_name = bien.localidad or ""
                    prov = f" ({bien.provincia})" if bien.provincia else ""
                    lines.append(f"  Dirección: {bien.direccion}, {cp} {loc_name}{prov}")
                if bien.referencia_catastral:
                    lines.append(f"  Referencia catastral: {bien.referencia_catastral}")
                if bien.idufir:
                    lines.append(f"  IDUFIR/CRU: {bien.idufir}")
                if bien.vivienda_habitual:
                    lines.append(f"  Vivienda habitual: {bien.vivienda_habitual}")
                if bien.situacion_posesoria:
                    lines.append(f"  Situación posesoria: {bien.situacion_posesoria}")
                if bien.visitable:
                    lines.append(f"  Visitable: {bien.visitable}")
                if bien.inscripcion_registral:
                    lines.append(f"  Inscripción registral: {bien.inscripcion_registral}")
                if bien.cargas:
                    lines.append(f"  Cargas indicadas: {bien.cargas}")

        if self.notice.documents:
            lines.append("\nDocumentos adjuntos disponibles en el portal:")
            for doc in self.notice.documents:
                lines.append(f"- {doc.title} (idDoc={doc.id_doc})")

        return "\n".join(lines)


@dataclass(frozen=True)
class DownloadedDocument:
    """Documento oficial (PDF) descargado y convertido a texto."""

    id_doc: str
    title: str
    content_bytes: bytes
    text: str
    pages: int
    method: str


@dataclass(frozen=True)
class AuctionSearchResult:
    """Resultado individual de una búsqueda de subastas en subastas_ava.php."""

    portal_id: str
    court: str | None
    procedure: str | None
    status: str | None
    conclusion_date: str | None
    summary: str | None
    url: str


def clean_html_text(raw: str) -> str:
    """Normaliza entidades HTML, elimina etiquetas y colapsa espacios."""
    unescaped = html.unescape(raw)
    without_tags = re.sub(r"<[^>]+>", " ", unescaped)
    return " ".join(without_tags.split())


def parse_money(raw_text: str | None) -> Decimal | None:
    """Parsea importes monetarios (e.g. '130.560,00 €' o '130560.00' -> Decimal)."""
    if not raw_text:
        return None
    cleaned = raw_text.replace("€", "").strip()
    if "." in cleaned and "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    try:
        return Decimal(match.group(0))
    except Exception:
        return None


def extract_portal_id(url_or_id: str) -> str:
    """Extrae el identificador SUB-... de una URL o de una cadena suelta."""
    clean = url_or_id.strip()
    match = PORTAL_ID_RE.search(clean)
    if match:
        return match.group(0).upper()
    raise ValueError(f"No se encontró un identificador de subasta válido en: {url_or_id}")


def build_auction_url(portal_id: str, ver: int = 1, id_lote: int | None = None) -> str:
    """Genera la URL del detalle de la subasta con la pestaña y lote indicados."""
    url = f"{DETAIL_URL}?idSub={portal_id}&ver={ver}"
    if id_lote is not None:
        url += f"&idLote={id_lote}"
    return url


def parse_table_rows(html_block: str) -> dict[str, str]:
    """Parsea filas <tr><th>Clave</th><td>Valor</td></tr> en un diccionario limpio."""
    rows = re.findall(r"<tr>\s*<th>(.*?)</th>\s*<td>(.*?)</td>\s*</tr>", html_block, re.DOTALL)
    return {clean_html_text(k): clean_html_text(v) for k, v in rows}


def parse_auction_tab1(html_content: str, portal_id: str) -> ScrapedAuctionNotice:
    """Parsea la pestaña 1 (Información general) y los enlaces a documentos."""
    block = re.search(
        r"<div id=\"idBloqueDatos1\">(.*?)</div>\s*<div class=\"bloqueBotones\">",
        html_content,
        re.DOTALL,
    )
    table_dict: dict[str, str] = {}
    if block:
        table_dict = parse_table_rows(block.group(1))
    else:
        # Fallback a buscar cualquier tabla
        table_dict = parse_table_rows(html_content)

    doc_links: list[DocumentRef] = []
    # Documentos en <a href="verDocumento.php?idSub=...&idDoc=...">TITULO</a>
    for href, title in re.findall(
        r"<a\s+[^>]*href=\"([^\"]*verDocumento\.php\?[^\"]*)\"[^>]*>(.*?)</a>",
        html_content,
        re.IGNORECASE | re.DOTALL,
    ):
        clean_title = clean_html_text(title)
        id_doc_match = re.search(r"idDoc=([^&\"\s]+)", href)
        if id_doc_match:
            doc_id = id_doc_match.group(1)
            full_url = f"{DOC_URL}?idSub={portal_id}&idDoc={doc_id}"
            doc_links.append(DocumentRef(id_doc=doc_id, title=clean_title, url=full_url))

    return ScrapedAuctionNotice(
        portal_id=portal_id,
        portal_url=build_auction_url(portal_id, 1),
        tipo_subasta=table_dict.get("Tipo de subasta"),
        cuenta_expediente=table_dict.get("Cuenta expediente"),
        fecha_inicio=table_dict.get("Fecha de inicio"),
        fecha_conclusion=table_dict.get("Fecha de conclusión"),
        cantidad_reclamada=parse_money(table_dict.get("Cantidad reclamada")),
        lotes_label=table_dict.get("Lotes"),
        anuncio_boe=table_dict.get("Anuncio BOE"),
        valor_subasta=parse_money(table_dict.get("Valor subasta")),
        tasacion=parse_money(table_dict.get("Tasación")),
        puja_minima=parse_money(table_dict.get("Puja mínima")),
        tramos_entre_pujas=parse_money(table_dict.get("Tramos entre pujas")),
        importe_deposito=parse_money(table_dict.get("Importe del depósito")),
        documents=doc_links,
    )


def parse_auction_tab2(html_content: str) -> ManagingAuthority:
    """Parsea la pestaña 2 (Autoridad gestora)."""
    table_dict = parse_table_rows(html_content)
    return ManagingAuthority(
        codigo=table_dict.get("Código"),
        descripcion=table_dict.get("Descripción"),
        direccion=table_dict.get("Dirección"),
        telefono=table_dict.get("Teléfono"),
        fax=table_dict.get("Fax"),
        email=table_dict.get("Correo electrónico") or table_dict.get("Email"),
    )


def _parse_bienes_from_html(html_block: str) -> list[ScrapedPropertyItem]:
    """Extrae todos los bloques '<h4>Bien X - Inmueble (...)</h4><table>...</table>'."""
    bienes: list[ScrapedPropertyItem] = []
    matches = re.findall(
        r"<h4>Bien (\d+)\s*-\s*([^<]+)</h4>\s*<table>(.*?)</table>",
        html_block,
        re.DOTALL | re.IGNORECASE,
    )
    for b_num_str, b_type_raw, b_table_html in matches:
        b_num = int(b_num_str)
        b_type = clean_html_text(b_type_raw)
        rows = parse_table_rows(b_table_html)
        bienes.append(
            ScrapedPropertyItem(
                bien_num=b_num,
                tipo_bien=b_type,
                descripcion=rows.get("Descripción") or "",
                idufir=rows.get("IDUFIR") or rows.get("CRU"),
                referencia_catastral=rows.get("Referencia catastral"),
                direccion=rows.get("Dirección"),
                codigo_postal=rows.get("Código Postal"),
                localidad=rows.get("Localidad"),
                provincia=rows.get("Provincia"),
                vivienda_habitual=rows.get("Vivienda habitual"),
                situacion_posesoria=rows.get("Situación posesoria"),
                visitable=rows.get("Visitable"),
                cargas=rows.get("Cargas"),
                inscripcion_registral=rows.get("Inscripción registral"),
            )
        )
    return bienes


def parse_auction_tab3(
    html_content: str,
    lot_subpages: Mapping[int, str] | None = None,
) -> list[ScrapedLot]:
    """Parsea la pestaña 3 (Bienes o Lotes).

    Soporta tanto subastas de lote único como subastas con múltiples lotes (navlistver).
    Si se suministra `lot_subpages`, se incorporan las páginas de los lotes ya descargadas.
    """
    lots: list[ScrapedLot] = []

    # Detectar si hay navegación por lotes en pestaña vertical: idTabLote1, idTabLote2...
    lot_nav_matches = re.findall(
        r"<a[^>]+idTabLote(\d+)[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>",
        html_content,
        re.IGNORECASE | re.DOTALL,
    )

    if lot_nav_matches:
        # Subasta multi-lote
        for lot_str, _, lot_anchor_text in lot_nav_matches:
            lot_num = int(lot_str)
            lot_html = (lot_subpages or {}).get(lot_num) or html_content

            # Buscar bloque de este lote si está en el mismo HTML
            pattern = (
                rf"<div class=\"bloque\" id=\"idBloqueLote{lot_num}\">(.*?)</div>\s*"
                r"(?=<div class=\"bloque\"|<div class=\"bloqueBotones\">|$)"
            )
            lote_block_match = re.search(pattern, lot_html, re.DOTALL | re.IGNORECASE)
            target_html = lote_block_match.group(1) if lote_block_match else lot_html

            # Título o descripción del lote
            title_match = re.search(r"<div class=\"caja\">(.*?)</div>", target_html, re.DOTALL)
            lot_title = (
                clean_html_text(title_match.group(1))
                if title_match
                else clean_html_text(lot_anchor_text)
            )

            # Datos económicos del lote (Datos relacionados con la subasta del lote X)
            lot_data_match = re.search(
                r"<h3>Datos relacionados con la subasta del lote \d+</h3>\s*<table>(.*?)</table>",
                target_html,
                re.DOTALL | re.IGNORECASE,
            )
            lot_econ = parse_table_rows(lot_data_match.group(1)) if lot_data_match else {}

            bienes = _parse_bienes_from_html(target_html)
            lots.append(
                ScrapedLot(
                    lote_num=lot_num,
                    titulo=lot_title,
                    valor_subasta=parse_money(
                        lot_econ.get("Valor Subasta") or lot_econ.get("Valor subasta")
                    ),
                    tasacion=parse_money(
                        lot_econ.get("Valor de tasación") or lot_econ.get("Tasación")
                    ),
                    deposito=parse_money(
                        lot_econ.get("Importe del depósito") or lot_econ.get("Depósito")
                    ),
                    puja_minima=parse_money(lot_econ.get("Puja mínima")),
                    tramos=parse_money(lot_econ.get("Tramos entre pujas")),
                    cantidad_reclamada=parse_money(lot_econ.get("Cantidad reclamada")),
                    bienes=bienes,
                )
            )
    else:
        # Subasta de lote único (idBloqueLote1 o bienes directos)
        title_match = re.search(r"<div class=\"caja\">(.*?)</div>", html_content, re.DOTALL)
        single_title = clean_html_text(title_match.group(1)) if title_match else None
        bienes = _parse_bienes_from_html(html_content)
        lots.append(
            ScrapedLot(
                lote_num=1,
                titulo=single_title,
                valor_subasta=None,  # se toma del general de la subasta (tab 1)
                tasacion=None,
                deposito=None,
                puja_minima=None,
                tramos=None,
                cantidad_reclamada=None,
                bienes=bienes,
            )
        )

    return lots


def parse_auction_tab4(html_content: str) -> list[CreditorParty]:
    """Parsea la pestaña 4 (Relacionados / Acreedores / Ejecutante)."""
    table_dict = parse_table_rows(html_content)
    if not table_dict:
        return []
    return [
        CreditorParty(
            nombre=table_dict.get("Nombre"),
            nif=table_dict.get("NIF"),
            direccion=table_dict.get("Dirección"),
            localidad=table_dict.get("Localidad"),
            provincia=table_dict.get("Provincia"),
            pais=table_dict.get("País"),
        )
    ]


def parse_auction_tab5(
    html_content: str,
) -> tuple[Decimal | None, str | None, str, dict[int, dict[str, Any]]]:
    """Parsea la pestaña 5 (Pujas) y categoriza el estado de licitación.

    Devuelve:
      (highest_bid, bid_status, bidding_state, lot_bids)
    donde bidding_state es:
      - 'sin_pujas': 0 pujas recibidas
      - 'con_pujas_requiere_login': hay pujas activas pero el BOE exige usuario registrado
        para ver el importe exacto
      - 'puja_secreta': subasta con plica / sobre cerrado
      - 'puja_publica': importe de puja visible públicamente
      - 'desconocido': no se pudo determinar
    """
    block = re.search(
        r"<div id=\"idBloqueDatos\d+\">(.*?)</div>\s*<div class=\"bloqueBotones\">",
        html_content,
        re.DOTALL,
    )
    if not block:
        return None, None, "desconocido", {}

    raw_block = block.group(1)
    text = clean_html_text(raw_block)

    # Multi-lote: detectar tabla de lotes
    lot_bids: dict[int, dict[str, Any]] = {}
    rows = re.findall(
        r"<tr>\s*<td headers=\"lote\">(\d+)</td>\s*<td headers=\"cantidad\">(.*?)</td>\s*</tr>",
        raw_block,
        re.DOTALL | re.IGNORECASE,
    )
    for lote_str, cant_html in rows:
        lote_num = int(lote_str)
        cant_clean = clean_html_text(cant_html)
        cant_lower = cant_clean.lower()
        if "no ha recibido pujas" in cant_lower or "sin puja" in cant_lower:
            lote_state = "sin_pujas"
            lote_money = None
        elif "secreta" in cant_lower:
            lote_state = "puja_secreta"
            lote_money = None
        elif (
            "inicie sesión" in cant_lower
            or "usuario registrado" in cant_lower
            or "con puja" in cant_lower
            or "alguna puja" in cant_lower
        ):
            lote_state = "con_pujas_requiere_login"
            lote_money = None
        else:
            lote_money = parse_money(cant_clean)
            lote_state = "puja_publica" if lote_money is not None else "desconocido"

        lot_bids[lote_num] = {
            "highest_bid": lote_money,
            "raw_status": cant_clean,
            "state": lote_state,
        }

    lower = text.lower()
    highest_bid = None

    if lot_bids:
        valid_bids = [b["highest_bid"] for b in lot_bids.values() if b["highest_bid"] is not None]
        if valid_bids:
            highest_bid = max(valid_bids)
            state = "puja_publica"
        elif any(b["state"] == "con_pujas_requiere_login" for b in lot_bids.values()):
            state = "con_pujas_requiere_login"
        elif any(b["state"] == "puja_secreta" for b in lot_bids.values()):
            state = "puja_secreta"
        elif all(b["state"] == "sin_pujas" for b in lot_bids.values()):
            state = "sin_pujas"
        else:
            state = "desconocido"
    else:
        if "no ha recibido pujas" in lower or "sin puja" in lower:
            state = "sin_pujas"
        elif "secreta" in lower:
            state = "puja_secreta"
        elif (
            "inicie sesión" in lower
            or "usuario registrado" in lower
            or "ha recibido alguna puja" in lower
            or "con puja" in lower
        ):
            state = "con_pujas_requiere_login"
        else:
            amount_m = re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€", text)
            if amount_m:
                highest_bid = parse_money(amount_m.group(0))
                state = "puja_publica" if highest_bid is not None else "desconocido"
            else:
                highest_bid = parse_money(text)
                state = "puja_publica" if highest_bid is not None else "desconocido"

    return highest_bid, text, state, lot_bids


def parse_search_results(html_content: str) -> list[AuctionSearchResult]:
    """Parsea el HTML resultante de subastas_ava.php."""
    results: list[AuctionSearchResult] = []
    # Cada subasta está en un <li class="resultado-busqueda">
    items = re.findall(
        r"<li class=\"resultado-busqueda\">(.*?)</li>\s*(?=<li class=\"resultado-busqueda\"|</ul>)",
        html_content,
        re.DOTALL | re.IGNORECASE,
    )
    for item in items:
        link_match = re.search(r"href=\"([^\"]*idSub=([^\"]+?)(?:&[^\"]*)?)\"", item)
        if not link_match:
            continue
        sub_id = link_match.group(2).upper()
        full_url = f"{DETAIL_URL}?idSub={sub_id}"

        h4_match = re.search(r"<h4>(.*?)</h4>", item, re.DOTALL)
        court = clean_html_text(h4_match.group(1)) if h4_match else None

        paragraphs = re.findall(r"<p>(.*?)</p>", item, re.DOTALL)
        clean_ps = [clean_html_text(p) for p in paragraphs]

        procedure = None
        status = None
        conclusion = None
        summary_parts = []

        for p in clean_ps:
            if p.startswith("Expediente:"):
                procedure = p.removeprefix("Expediente:").strip()
            elif p.startswith("Estado:"):
                status_part = p.removeprefix("Estado:").strip()
                status = status_part
                end_match = re.search(r"Conclusión prevista:\s*([\d/]+ a las [\d:]+)", status_part)
                if end_match:
                    conclusion = end_match.group(1)
            else:
                summary_parts.append(p)

        results.append(
            AuctionSearchResult(
                portal_id=sub_id,
                court=court,
                procedure=procedure,
                status=status,
                conclusion_date=conclusion,
                summary=" · ".join(summary_parts) if summary_parts else None,
                url=full_url,
            )
        )
    return results


def make_client() -> httpx.Client:
    """Cliente HTTP optimizado para el portal del BOE."""
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept-Language": "es-ES,es;q=0.9"},
        timeout=DEFAULT_TIMEOUT_S,
        follow_redirects=True,
    )


def scrape_auction(
    client: httpx.Client,
    url_or_id: str,
    fetch_all_tabs: bool = True,
) -> ScrapedAuction:
    """Descarga y extrae los datos de una subasta a través de sus pestañas."""
    portal_id = extract_portal_id(url_or_id)
    raw_html: dict[str, str] = {}

    # Pestaña 1: Información general
    url_ver1 = build_auction_url(portal_id, 1)
    resp1 = client.get(url_ver1)
    resp1.raise_for_status()
    raw_html["ver1"] = resp1.text
    notice = parse_auction_tab1(resp1.text, portal_id)

    authority: ManagingAuthority | None = None
    lots: list[ScrapedLot] = []
    creditors: list[CreditorParty] = []
    highest_bid: Decimal | None = None
    bid_status: str | None = None
    bidding_state: str = "sin_pujas"
    lot_bids: dict[int, dict[str, Any]] = {}

    if fetch_all_tabs:
        # Pestaña 2: Autoridad gestora
        url_ver2 = build_auction_url(portal_id, 2)
        resp2 = client.get(url_ver2)
        if resp2.status_code == 200:
            raw_html["ver2"] = resp2.text
            authority = parse_auction_tab2(resp2.text)

        # Pestaña 3: Bienes / Lotes
        url_ver3 = build_auction_url(portal_id, 3)
        resp3 = client.get(url_ver3)
        lot_subpages: dict[int, str] = {}
        if resp3.status_code == 200:
            raw_html["ver3"] = resp3.text
            # Verificar si hay múltiples lotes y descargarlos si tienen página propia
            lot_navs = re.findall(
                r"<a[^>]+idTabLote(\d+)[^>]+href=\"([^\"]+)\"[^>]*>",
                resp3.text,
                re.IGNORECASE,
            )
            for lot_str, href in lot_navs:
                lot_num = int(lot_str)
                # Si la navegación pide idLote
                parsed_qs = parse_qs(urlparse(href).query)
                if "idLote" in parsed_qs:
                    lote_val = parsed_qs["idLote"][0]
                    lot_url = build_auction_url(portal_id, 3, id_lote=int(lote_val))
                    lot_resp = client.get(lot_url)
                    if lot_resp.status_code == 200:
                        lot_subpages[lot_num] = lot_resp.text
                        raw_html[f"ver3_lote{lot_num}"] = lot_resp.text

            lots = parse_auction_tab3(resp3.text, lot_subpages=lot_subpages)

        # Pestaña 4: Relacionados / Acreedores
        url_ver4 = build_auction_url(portal_id, 4)
        resp4 = client.get(url_ver4)
        if resp4.status_code == 200:
            raw_html["ver4"] = resp4.text
            creditors = parse_auction_tab4(resp4.text)

        # Pestaña 5: Pujas
        url_ver5 = build_auction_url(portal_id, 5)
        resp5 = client.get(url_ver5)
        if resp5.status_code == 200:
            raw_html["ver5"] = resp5.text
            highest_bid, bid_status, bidding_state, lot_bids = parse_auction_tab5(resp5.text)
    else:
        # Solo pestaña 1
        bidding_state = "desconocido"
        lots = [
            ScrapedLot(
                lote_num=1,
                titulo=notice.lotes_label or "Lote único",
                valor_subasta=notice.valor_subasta,
                tasacion=notice.tasacion,
                deposito=notice.importe_deposito,
                puja_minima=notice.puja_minima,
                tramos=notice.tramos_entre_pujas,
                cantidad_reclamada=notice.cantidad_reclamada,
            )
        ]

    return ScrapedAuction(
        portal_id=portal_id,
        portal_url=build_auction_url(portal_id, 1),
        notice=notice,
        authority=authority,
        lots=lots,
        creditors=creditors,
        highest_bid=highest_bid,
        bid_status=bid_status,
        bidding_state=bidding_state,
        lot_bids=lot_bids,
        raw_html=raw_html,
    )


def download_documents(
    client: httpx.Client,
    auction: ScrapedAuction,
    max_docs: int = 5,
    max_pages: int = 40,
) -> list[DownloadedDocument]:
    """Descarga los documentos PDF de la subasta y extrae su texto (con pypdf)."""
    downloaded: list[DownloadedDocument] = []
    for doc_ref in auction.notice.documents[:max_docs]:
        try:
            resp = client.get(doc_ref.url)
            if resp.status_code != 200 or not resp.content.startswith(b"%PDF"):
                continue
            pages = pdf_pages(resp.content, max_pages=max_pages)
            full_text = "\n\n".join(p for p in pages if p.strip())
            downloaded.append(
                DownloadedDocument(
                    id_doc=doc_ref.id_doc,
                    title=doc_ref.title,
                    content_bytes=resp.content,
                    text=full_text,
                    pages=len(pages),
                    method="pypdf",
                )
            )
        except (UnreadablePdf, Exception):
            # Si un documento concreto falla o no es accesible, se continúa con los demás
            continue
    return downloaded


def search_boe_auctions(
    client: httpx.Client,
    province: str = "28",  # 28 = Madrid
    status: str = "EJ",  # EJ = Celebrándose, PU = Próxima apertura
    goods_type: str = "I",  # I = Inmuebles
    page: int = 1,
    page_hits: int = 50,
) -> list[AuctionSearchResult]:
    """Realiza una búsqueda avanzada en el Portal de Subastas (subastas_ava.php)."""
    form_data = {
        "campo[0]": "SUBASTA.ORIGEN",
        "dato[0]": "",
        "campo[2]": "SUBASTA.ESTADO.CODIGO",
        "dato[2]": status,
        "campo[3]": "BIEN.TIPO",
        "dato[3]": goods_type,
        "campo[8]": "BIEN.COD_PROVINCIA",
        "dato[8]": province,
        "page_hits": str(page_hits),
        "accion": "Buscar",
    }
    resp = client.post(SEARCH_URL, data=form_data)
    resp.raise_for_status()
    return parse_search_results(resp.text)


# Tipo de bien del Portal → tipo de inmueble de la extracción (agent/extraction.PropertyType)
PROPERTY_TYPES = (("vivienda", "vivienda"), ("garaje", "garaje"), ("trastero", "trastero"),
                  ("local", "local"), ("oficina", "oficina"), ("nave", "otro"),
                  ("solar", "suelo"), ("suelo", "suelo"), ("rústic", "rustica"),
                  ("rustic", "rustica"), ("edificio", "edificio"))
ORIGIN = {"J": "judicial", "A": "administrativa", "N": "notarial"}


def property_type(tipo_bien: str | None) -> str | None:
    """«Inmueble (Vivienda)» → «vivienda». Sin tipo conocido, «otro»; sin tipo, None."""
    if not tipo_bien:
        return None
    lowered = tipo_bien.lower()
    return next((kind for word, kind in PROPERTY_TYPES if word in lowered), "otro")


def lot_records(auction: ScrapedAuction, search: AuctionSearchResult | None = None
                ) -> list[dict[str, Any]]:
    """Cada lote como registro plano y serializable (ADR-0053): lo que se guarda con lo recibido
    y de lo que sale la oferta. Los importes, como texto exacto."""
    notice = auction.notice
    multi = len(auction.lots) > 1
    records = []
    for lot in auction.lots:
        bien = lot.bienes[0] if lot.bienes else None
        value = lot.valor_subasta or notice.valor_subasta
        deposit = lot.deposito or notice.importe_deposito
        records.append({
            "external_id": f"{auction.portal_id}_L{lot.lote_num}" if multi else auction.portal_id,
            "url": build_auction_url(auction.portal_id, 3, lot.lote_num) if multi
            else auction.portal_url,
            "portal_id": auction.portal_id,
            "lot": lot.lote_num,
            "title": lot.titulo,
            "auction_value": str(value) if value is not None else None,
            "deposit": str(deposit) if deposit is not None else None,
            "address": bien.direccion if bien else None,
            "cadastral_ref": bien.referencia_catastral if bien else None,
            "municipality": bien.localidad if bien else None,
            "province": bien.provincia if bien else None,
            "description": bien.descripcion if bien else None,
            "property_kind": bien.tipo_bien if bien else None,
            "habitual_residence": bien.vivienda_habitual if bien else None,
            "possession": bien.situacion_posesoria if bien else None,
            "visitable": bien.visitable if bien else None,
            "status": search.status if search else None,
            "concludes": search.conclusion_date if search else notice.fecha_conclusion,
        })
    return records


def offer_from_record(record: dict[str, Any], unit: dict[str, Any] | None = None
                      ) -> NormalizedOffer:
    """La oferta pública de un lote (ADR-0053): sin precio pedido, con el valor de subasta como
    tipo. `unit`: superficie y uso del inmueble en el Catastro, si se pudo pedir."""
    origin = ORIGIN.get(record["portal_id"].split("-")[1][:1], "")
    place = record.get("address") or record.get("title") or record["portal_id"]
    portal = {k: record.get(k) for k in ("property_kind", "habitual_residence", "possession",
                                         "visitable", "status", "concludes")}
    extracted: dict[str, Any] = {"property_type": property_type(record.get("property_kind")),
                                 "portal": portal}
    if unit:
        extracted["catastro"] = unit
    value = record.get("auction_value")
    deposit = record.get("deposit")
    return NormalizedOffer(
        external_id=record["external_id"],
        kind="lote",
        url=record["url"],
        title=" ".join(f"Subasta {origin} · {place}".split()),
        description="\n".join(x for x in (record.get("title"), record.get("description")) if x)
        or None,
        asking_price=None,  # una subasta no tiene precio pedido (search: auction)
        auction_min_bid=Decimal(value) if value else None,
        deposit_required=Decimal(deposit) if deposit else None,
        address=record.get("address"),
        cadastral_ref=record.get("cadastral_ref"),
        municipality=record.get("municipality"),
        province=record.get("province"),
        built_area_m2=Decimal(str(unit["built_area_m2"])) if unit and _area_fits(extracted, unit)
        else None,
        extraction_status="no_aplica",
        extracted=extracted,
    )


def _area_fits(extracted: dict[str, Any], unit: dict[str, Any] | None) -> bool:
    """La superficie del Catastro vale si la referencia es de lo que se subasta: una vivienda con
    una referencia de uso residencial (no la del garaje de la misma finca)."""
    if not unit:
        return False
    return extracted["property_type"] != "vivienda" or str(unit.get("use", "")).lower().startswith(
        "residencial")


def to_normalized_offers(auction: ScrapedAuction) -> list[NormalizedOffer]:
    """Los lotes de la subasta como ofertas públicas, sin datos del Catastro."""
    return [offer_from_record(r) for r in lot_records(auction)]


if __name__ == "__main__":
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(
        description="Scraper y extractor del Portal de Subastas del BOE"
    )
    parser.add_argument("--id", "-i", help="Identificador SUB-... o URL de la subasta")
    parser.add_argument("--search", "-s", action="store_true", help="Buscar subastas activas")
    parser.add_argument(
        "--province", "-p", default="28", help="Código INE de provincia (28=Madrid)"
    )
    parser.add_argument("--docs", "-d", action="store_true", help="Descargar y leer documentos PDF")
    parser.add_argument(
        "--ai", "-a", action="store_true", help="Extraer condiciones y cargas con IA"
    )
    parser.add_argument("--json", action="store_true", help="Salida en formato JSON")

    args = parser.parse_args()

    with make_client() as client:
        if args.search:
            results = search_boe_auctions(client, province=args.province)
            if args.json:
                print(json.dumps([r.__dict__ for r in results], ensure_ascii=False, indent=2))
            else:
                print(f"Encontradas {len(results)} subastas en provincia {args.province}:")
                for r in results:
                    c = r.court or ""
                    p = r.procedure or ""
                    end = r.conclusion_date or ""
                    print(f"- {r.portal_id} | {c} | {p} | {end}")
        elif args.id:
            auction = scrape_auction(client, args.id)
            docs = []
            if args.docs or args.ai:
                docs = download_documents(client, auction)

            ai_result = None
            if args.ai:
                from housefinder.agent.boe_auction_extraction import extract_auction_ai
                from housefinder.agent.llm import llm_from_env

                llm = None
                try:
                    llm = llm_from_env()
                except ValueError:
                    pass
                report = extract_auction_ai(llm, auction, docs)
                ai_result = report.as_dict()

            if args.json:
                data = {
                    "portal_id": auction.portal_id,
                    "url": auction.portal_url,
                    "bidding_state": auction.bidding_state,
                    "highest_bid": str(auction.highest_bid) if auction.highest_bid else None,
                    "bid_status": auction.bid_status,
                    "lot_bids": auction.lot_bids,
                    "notice": auction.notice.__dict__,
                    "authority": auction.authority.__dict__ if auction.authority else None,
                    "lots": [lot.__dict__ for lot in auction.lots],
                    "documents_count": len(docs),
                    "ai_report": ai_result,
                }
                print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
            else:
                print(auction.summary_text())
                if ai_result:
                    print("\n=== ANÁLISIS DE IA ===")
                    print(f"Riesgo: {ai_result['risk_level'].upper()}")
                    print(f"Resumen: {ai_result['executive_summary']}")
                    if ai_result["subsisting_prior_charges"]:
                        total = ai_result["subsisting_charges_total"]
                        print(f"Cargas previas subsistentes ({total} €):")
                        for charge in ai_result["subsisting_prior_charges"]:
                            amt = charge["amount"] or "Importe desconocido"
                            print(f"  * {charge['concept']} [{charge['charge_type']}] - {amt}")
                    if ai_result["warnings"]:
                        print("Alertas:")
                        for w in ai_result["warnings"]:
                            print(f"  ! {w}")
        else:
            parser.print_help()
            sys.exit(1)
