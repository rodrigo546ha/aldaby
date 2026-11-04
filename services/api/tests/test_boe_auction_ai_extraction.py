"""Tests de la extracción con IA de condiciones y documentación de subastas del BOE.

Comprueba la verificación estricta de citas literales, la detección de cargas previas subsistentes,
la situación posesoria y el extractor heurístico de reserva.
"""

from decimal import Decimal
from pathlib import Path

from housefinder.agent.boe_auction_extraction import (
    AuctionConditionsExtraction,
    FullAuctionExtractionSchema,
    OccupancyAndPossessionExtraction,
    PriorChargeItem,
    RegistryAndChargesExtraction,
    RiskAssessmentExtraction,
    extract_auction_ai,
)
from housefinder.agent.extraction import Quoted
from housefinder.agent.llm import FakeLLMClient
from housefinder.documents.reader import read_document
from housefinder.offers.boe_portal import (
    DownloadedDocument,
    parse_auction_tab1,
    parse_auction_tab2,
    parse_auction_tab3,
    parse_auction_tab4,
    parse_auction_tab5,
)

FIXTURES = Path(__file__).parent / "fixtures" / "boe" / "portal"


def load_fixture_auction():
    v1 = (FIXTURES / "single_ver1.html").read_text(encoding="utf-8")
    v2 = (FIXTURES / "single_ver2.html").read_text(encoding="utf-8")
    v3 = (FIXTURES / "single_ver3.html").read_text(encoding="utf-8")
    v4 = (FIXTURES / "single_ver4.html").read_text(encoding="utf-8")
    v5 = (FIXTURES / "single_ver5.html").read_text(encoding="utf-8")

    notice = parse_auction_tab1(v1, "SUB-JA-2026-267866")
    auth = parse_auction_tab2(v2)
    lots = parse_auction_tab3(v3)
    creds = parse_auction_tab4(v4)
    bid, status, state, lot_bids = parse_auction_tab5(v5)

    from housefinder.offers.boe_portal import ScrapedAuction

    return ScrapedAuction(
        portal_id="SUB-JA-2026-267866",
        portal_url="https://subastas.boe.es/detalleSubasta.php?idSub=SUB-JA-2026-267866",
        notice=notice,
        authority=auth,
        lots=lots,
        creditors=creds,
        highest_bid=bid,
        bid_status=status,
        bidding_state=state,
        lot_bids=lot_bids,
    )


def load_fixture_edicto_doc() -> DownloadedDocument:
    pdf_bytes = (FIXTURES / "edicto_sample.pdf").read_bytes()
    doc_text = read_document(pdf_bytes)
    return DownloadedDocument(
        id_doc="1-0a54b03f7ea893a2640bd31f452993bf",
        title="EDICTO",
        content_bytes=pdf_bytes,
        text=doc_text.text,
        pages=doc_text.pages,
        method=doc_text.method,
    )


def test_rule_based_fallback():
    auction = load_fixture_auction()
    edicto = load_fixture_edicto_doc()

    report = extract_auction_ai(None, auction, [edicto])

    assert report.portal_id == "SUB-JA-2026-267866"
    assert report.procedure_reference == "Ejecución Hipotecaria 119/2024"
    assert report.auction_value == Decimal("130560.00")
    assert report.claimed_debt == Decimal("29766.05")
    assert report.deposit_required == Decimal("6528.00")
    assert report.debtor_habitual_residence == "No"
    assert report.finca_registral == "23778"
    assert report.cru_idufir == "28177001763770"
    assert report.cadastral_reference == "9402504VK3790C0005KT"
    assert report.risk_level in ("bajo", "medio")
    assert any("No es vivienda habitual" in w for w in report.warnings)


def test_llm_structured_extraction_with_verified_evidence():
    auction = load_fixture_auction()
    edicto = load_fixture_edicto_doc()

    # Preparamos una respuesta del LLM con citas literales tomadas del edicto
    mock_response = FullAuctionExtractionSchema(
        conditions=AuctionConditionsExtraction(
            procedural_type=Quoted(
                value="Ejecución Hipotecaria",
                evidence="procedimiento Ejecución Hipotecaria que se sigue en este Juzgado",
            ),
            court_or_authority=Quoted(
                value="Sección Civil del Tribunal de Instancia de Madrid. Plaza nº 31",
                evidence="SECCION CIVIL DEL TRIBUNAL DE INSTANCIA DE MADRID. PLAZA Nº 31",
            ),
            procedure_reference=Quoted(
                value="119/2024", evidence="Procedimiento: Ejecución Hipotecaria 119/2024"
            ),
            auction_value=Quoted(
                value="130560.00",
                evidence="tipo a efectos de subasta de la finca hipotecada es de 130.560,00",
            ),
            appraisal_value=Quoted(value=None, evidence=None),
            claimed_debt=Quoted(value="29766.05", evidence="Cantidad reclamada: 29766.05 €"),
            deposit_required=Quoted(value="6528.00", evidence="Depósito: 6528.00 €"),
            deposit_percentage=Quoted(
                value="5 %", evidence="consignar una cantidad equivalente al 5 por ciento del valor"
            ),
            minimum_bid=Quoted(value=None, evidence=None),
            bid_increment=Quoted(value="2620.00", evidence="Tramos: 2620.00 €"),
            debtor_habitual_residence=Quoted(
                value="No", evidence="Vivienda habitual del demandado: NO"
            ),
            payment_period_days=Quoted(value="40", evidence=None),
            third_party_bid_assignment=Quoted(
                value="No",
                evidence="Solo el ejecutante o los acreedores posteriores podrán hacer postura",
            ),
            special_conditions=[
                Quoted(
                    value="Inspección del inmueble con reducción de deuda",
                    evidence="Tribunal inspeccionar el inmueble",
                ),
            ],
        ),
        registry_charges=RegistryAndChargesExtraction(
            property_registry=Quoted(
                value="Registro de la Propiedad nº 53 de Madrid",
                evidence="Registro de la Propiedad nº 53 de Madrid, inscripción 4ª",
            ),
            finca_registral=Quoted(
                value="23778",
                evidence="Finca Registral 23778 trasladada de la Finca Registral 17175",
            ),
            cru_idufir=Quoted(value="28177001763770", evidence="CRU: 28177001763770"),
            cadastral_reference=Quoted(
                value="9402504VK3790C0005KT", evidence="Referencia catastral: 9402504VK3790C0005KT"
            ),
            registered_owner=Quoted(
                value="Herencia Yacente de Gerardo Sanchez Jimenez",
                evidence="HERENCIA YACENTE DE D. GERARDO SANCHEZ JIMENEZ",
            ),
            owner_matches_debtor=Quoted(value="Sí", evidence="propiedad del ejecutado:"),
            executed_charge=Quoted(
                value="Hipoteca", evidence="procedimiento Ejecución Hipotecaria"
            ),
            subsisting_prior_charges=[
                PriorChargeItem(
                    concept=Quoted(
                        value="Cargas o gravámenes anteriores",
                        evidence="Las cargas o gravámenes anteriores",
                    ),
                    charge_type="otra",
                    amount=Quoted(value=None, evidence=None),
                    status_and_notes=Quoted(
                        value="El licitador los admite y queda subrogado",
                        evidence="el licitador los admite y queda subrogado",
                    ),
                )
            ],
            posterior_charges_summary=Quoted(value="Se cancelan tras remate", evidence=None),
            community_debt=Quoted(value=None, evidence=None),
            tax_debt_ibi=Quoted(value=None, evidence=None),
        ),
        occupancy=OccupancyAndPossessionExtraction(
            occupancy_status=Quoted(
                value="no_consta",
                evidence="No se puede hacer constar la situación posesoria actual de la finca",
            ),
            occupant_details=Quoted(value=None, evidence=None),
            lease_contract=Quoted(value=None, evidence=None),
            judicial_eviction_status=Quoted(value=None, evidence=None),
            moratorium_warning=Quoted(
                value="Suspensión de lanzamiento",
                evidence="no procederá el lanzamiento cuando en un proceso",
            ),
            visitable=Quoted(
                value="Bajo consentimiento del poseedor",
                evidence="inspeccionar el inmueble o inmuebles ejecutados",
            ),
        ),
        risk_assessment=RiskAssessmentExtraction(
            risk_level="medio",
            warnings=[
                Quoted(
                    value="Cargas anteriores subsistirán",
                    evidence="Las cargas o gravámenes anteriores",
                ),
            ],
            executive_summary="Subasta de vivienda en Madrid con cargas anteriores subsistentes.",
        ),
    )

    fake_llm = FakeLLMClient(lambda inst, doc, out: mock_response)
    report = extract_auction_ai(fake_llm, auction, [edicto])

    assert report.portal_id == "SUB-JA-2026-267866"
    assert report.procedural_type == "Ejecución Hipotecaria"
    assert report.auction_value == Decimal("130560.00")
    assert report.debtor_habitual_residence == "No"
    assert report.finca_registral == "23778"
    assert report.cru_idufir == "28177001763770"
    assert len(report.subsisting_prior_charges) == 1
    assert report.subsisting_prior_charges[0].verified is True
    assert report.risk_level == "medio"
    assert len(report.warnings) == 1


def test_evidence_rejection_on_hallucinated_data():
    auction = load_fixture_auction()
    edicto = load_fixture_edicto_doc()

    hallucinated_response = FullAuctionExtractionSchema(
        conditions=AuctionConditionsExtraction(
            procedural_type=Quoted(
                value="Subasta Voluntaria Falsa",
                evidence="Texto que jamás existe en el documento 12345XYZ",
            ),
            court_or_authority=Quoted(
                value="Juzgado Inventado", evidence="Juzgado de lo Imposible nº 99"
            ),
            procedure_reference=Quoted(value="999/9999", evidence="Autos 999/9999 inventados"),
            auction_value=Quoted(
                value="500000.00", evidence="Valor tasado 500.000 euros no existente"
            ),
            appraisal_value=Quoted(value=None, evidence=None),
            claimed_debt=Quoted(value=None, evidence=None),
            deposit_required=Quoted(value=None, evidence=None),
            deposit_percentage=Quoted(value=None, evidence=None),
            minimum_bid=Quoted(value=None, evidence=None),
            bid_increment=Quoted(value=None, evidence=None),
            debtor_habitual_residence=Quoted(value=None, evidence=None),
            payment_period_days=Quoted(value=None, evidence=None),
            third_party_bid_assignment=Quoted(value=None, evidence=None),
            special_conditions=[],
        ),
        registry_charges=RegistryAndChargesExtraction(
            property_registry=Quoted(value=None, evidence=None),
            finca_registral=Quoted(value=None, evidence=None),
            cru_idufir=Quoted(value=None, evidence=None),
            cadastral_reference=Quoted(value=None, evidence=None),
            registered_owner=Quoted(value=None, evidence=None),
            owner_matches_debtor=Quoted(value=None, evidence=None),
            executed_charge=Quoted(value=None, evidence=None),
            subsisting_prior_charges=[],
            posterior_charges_summary=Quoted(value=None, evidence=None),
            community_debt=Quoted(value=None, evidence=None),
            tax_debt_ibi=Quoted(value=None, evidence=None),
        ),
        occupancy=OccupancyAndPossessionExtraction(
            occupancy_status=Quoted(value=None, evidence=None),
            occupant_details=Quoted(value=None, evidence=None),
            lease_contract=Quoted(value=None, evidence=None),
            judicial_eviction_status=Quoted(value=None, evidence=None),
            moratorium_warning=Quoted(value=None, evidence=None),
            visitable=Quoted(value=None, evidence=None),
        ),
        risk_assessment=RiskAssessmentExtraction(
            risk_level="alto",
            warnings=[],
            executive_summary="Resumen de prueba",
        ),
    )

    fake_llm = FakeLLMClient(lambda inst, doc, out: hallucinated_response)
    report = extract_auction_ai(fake_llm, auction, [edicto])

    # El valor inventado fue rechazado porque su evidencia no existe
    assert report.procedural_type is None
    assert report.court_name is None
    assert report.auction_value is None
    assert report.fields["procedural_type"].status == "rechazado"
    assert report.fields["court_or_authority"].status == "rechazado"
    assert report.fields["auction_value"].status == "rechazado"


def test_as_dict_serializable():
    auction = load_fixture_auction()
    edicto = load_fixture_edicto_doc()

    report = extract_auction_ai(None, auction, [edicto])
    d = report.as_dict()

    assert isinstance(d, dict)
    assert d["portal_id"] == "SUB-JA-2026-267866"
    assert d["auction_value"] == "130560.00"
    assert isinstance(d["warnings"], list)
    assert isinstance(d["fields"], dict)
