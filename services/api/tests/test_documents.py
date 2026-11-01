"""Documentos del usuario (F6.3, ADR-0021): lectura en memoria, OCR local y campos con cita.

Todos los documentos son sintéticos y se generan aquí; los reales, si los hay, van en
tests/fixtures/private/ (fuera de git).
"""

import io
import shutil
from datetime import date
from decimal import Decimal

import pytest

from housefinder.agent.documents import (
    BankStatementExtraction,
    LoanPayment,
    PayslipExtraction,
    TaxReturnExtraction,
    check_document,
)
from housefinder.agent.extraction import Quoted
from housefinder.documents.reader import UnreadableDocument, read_document
from housefinder.profiles.interview import DraftField, State, apply_document

TODAY = date(2026, 10, 31)
NONE = Quoted(value=None, evidence=None)
needs_ocr = pytest.mark.skipif(shutil.which("tesseract") is None, reason="sin Tesseract")


def text_pdf(lines: list[str]) -> bytes:
    """PDF mínimo con una página de texto (Helvetica), escrito a mano para no depender de nada."""
    body = "BT /F1 12 Tf 50 750 Td 16 TL " + " ".join(
        "(" + line.replace("(", r"\(").replace(")", r"\)") + ") '" for line in lines) + " ET"
    stream = body.encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for number, obj in enumerate(objects, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % number + obj + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    out.writelines(b"%010d 00000 n \n" % o for o in offsets)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
              % (len(objects) + 1, xref))
    return out.getvalue()


def scanned(lines: list[str], fmt: str) -> bytes:
    """Imagen con texto, como un escaneo (PNG) o un PDF escaneado sin capa de texto."""
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1600, 140 + 70 * len(lines)), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=44)
    for i, line in enumerate(lines):
        draw.text((60, 60 + 70 * i), line, fill="black", font=font)
    out = io.BytesIO()
    image.save(out, fmt, resolution=300)
    return out.getvalue()


PAYSLIP = ["NOMINA OCTUBRE 2026", "Salario base 2.100,00", "Prorrata pagas extra 350,00",
           "Liquido a percibir 1.850,32"]


def test_pdf_con_texto_sin_ocr():
    read = read_document(text_pdf(PAYSLIP))
    assert read.method == "pdf" and read.pages == 1
    assert "Liquido a percibir 1.850,32" in read.text


@needs_ocr
def test_foto_y_pdf_escaneado_con_ocr():
    photo = read_document(scanned(PAYSLIP, "PNG"))
    assert photo.method == "ocr" and "1.850,32" in photo.text
    pdf = read_document(scanned(PAYSLIP, "PDF"))
    assert pdf.method == "ocr" and "1.850,32" in pdf.text


def test_formatos_que_no_se_leen():
    with pytest.raises(UnreadableDocument, match="PDF, JPG y PNG"):
        read_document(b"GIF89a....")
    with pytest.raises(UnreadableDocument, match="10 MB"):
        read_document(b"%PDF" + b"0" * (11 * 1024 * 1024))


def test_nomina_con_prorrata_y_etiqueta_obligatoria():
    text = "\n".join(PAYSLIP)
    good = check_document("nomina", text, PayslipExtraction(
        net_pay=Quoted(value="1850.32", evidence="Liquido a percibir 1.850,32"),
        extra_pay_prorated=True, extra_pay_prorated_evidence="Prorrata pagas extra 350,00"))
    assert good.verified("net_pay") == Decimal("1850.32")
    state = apply_document(State(), good, "pdf", TODAY)
    assert state.draft["net_monthly_income"].value == "1850.32"  # ya incluye las extra
    assert state.draft["net_monthly_income"].source == "documento"
    assert state.documents == [{"kind": "nomina", "method": "pdf",
                                "fields": ["net_monthly_income"], "truncated": False}]
    # Un importe de otra línea no pasa por el líquido: la cita no lleva su etiqueta
    wrong = check_document("nomina", text, PayslipExtraction(
        net_pay=Quoted(value="2100", evidence="Salario base 2.100,00"),
        extra_pay_prorated=False, extra_pay_prorated_evidence=None))
    assert wrong.fields["net_pay"].reason == "la cita no lleva su etiqueta"
    assert apply_document(State(), wrong, "pdf", TODAY).issues[0].startswith("No he encontrado")


def test_nomina_sin_prorrata_supone_catorce_pagas_y_lo_dice():
    text = "Liquido a percibir 1.800,00"
    checked = check_document("nomina", text, PayslipExtraction(
        net_pay=Quoted(value="1800", evidence=text), extra_pay_prorated=False,
        extra_pay_prorated_evidence=None))
    field = apply_document(State(), checked, "ocr", TODAY).draft["net_monthly_income"]
    assert field.value == "2100.00"  # 1.800 × 14 / 12
    assert "catorce pagas" in field.note and "el OCR puede leer mal" in field.note


def test_declaracion_bases_y_descendientes():
    text = ("Ejercicio 2025\nBase liquidable general sometida a gravamen 38.420,55\n"
            "Base liquidable del ahorro sometida a gravamen 1.210,00\n"
            "Descendiente 1 Fecha de nacimiento 14/03/2016\n"
            "Descendiente 2 Fecha de nacimiento 02/09/2020")
    checked = check_document("declaracion", text, TaxReturnExtraction(
        fiscal_year=Quoted(value="2025", evidence="Ejercicio 2025"),
        taxable_base=Quoted(value="38420.55",
                            evidence="Base liquidable general sometida a gravamen 38.420,55"),
        savings_base=Quoted(value="1210",
                            evidence="Base liquidable del ahorro sometida a gravamen 1.210,00"),
        descendant_birth_years=[Quoted(value="2016", evidence="Fecha de nacimiento 14/03/2016"),
                                Quoted(value="2020", evidence="Fecha de nacimiento 02/09/2020")]))
    draft = apply_document(State(), checked, "pdf", TODAY).draft
    assert draft["taxable_base"].value == "38420.55"
    assert "Ejercicio 2025" in draft["taxable_base"].note
    assert draft["savings_base"].value == "1210.00"
    assert draft["descendant_birth_years"].value == ["2016", "2020"]


def test_extracto_saldo_cuotas_sin_signo_y_datos_tapados():
    text = ("Titular X1234567L  Cuenta ES91 2100 0418 4502 0005 1332\n"
            "01/10 PRESTAMO PERSONAL 0123 -180,50\n01/10 RECIBO HIPOTECA -620,00\n"
            "01/09 PRESTAMO PERSONAL 0123 -180,50\nSaldo final 23.410,77")
    checked = check_document("extracto", text, BankStatementExtraction(
        closing_balance=Quoted(value="23410.77", evidence="Saldo final 23.410,77"),
        loan_payments=[
            LoanPayment(concept=Quoted(value="PRESTAMO PERSONAL 0123",
                                       evidence="PRESTAMO PERSONAL 0123"),
                        amount=Quoted(value="-180.50", evidence="PRESTAMO PERSONAL 0123 -180,50")),
            LoanPayment(concept=Quoted(value="RECIBO HIPOTECA", evidence="RECIBO HIPOTECA"),
                        amount=Quoted(value="620", evidence="RECIBO HIPOTECA -620,00")),
            LoanPayment(concept=Quoted(value="PRESTAMO PERSONAL 0123",  # el mes anterior
                                       evidence="PRESTAMO PERSONAL 0123"),
                        amount=Quoted(value="180.50", evidence="PRESTAMO PERSONAL 0123 -180,50")),
        ]))
    draft = apply_document(State(), checked, "pdf", TODAY).draft
    assert draft["existing_monthly_debt"].value == "800.50"  # 180,50 + 620, una por concepto
    assert draft["available_savings"].value == "23410.77"
    assert "dedicarías" in draft["available_savings"].note
    tapped = check_document("extracto", text, BankStatementExtraction(
        closing_balance=Quoted(value="23410.77",
                               evidence="Titular X1234567L  Cuenta ES91 2100 0418 4502 0005 1332"),
        loan_payments=[]))
    assert tapped.fields["closing_balance"].status == "rechazado"
    assert "X1234567L" not in str(tapped.fields["closing_balance"].evidence)
    assert "ES91" not in str(tapped.fields["closing_balance"].evidence)


def test_el_documento_pisa_lo_dicho_en_la_conversacion():
    before = State(draft={"net_monthly_income": DraftField("2000.00", "unos 2.000", "respuesta")})
    checked = check_document("nomina", "Liquido a percibir 1.850,32", PayslipExtraction(
        net_pay=Quoted(value="1850.32", evidence="Liquido a percibir 1.850,32"),
        extra_pay_prorated=False, extra_pay_prorated_evidence=None))
    after = apply_document(before, checked, "pdf", TODAY)
    assert after.draft["net_monthly_income"].source == "documento"


def test_lo_que_se_le_paso_a_qwen3_sale_del_texto():
    # Prueba real con qwen3:14b (2026-10-31): no vio la prorrata ni el saldo final
    payslip = "Prorrata pagas extraordinarias 408,33\nLIQUIDO TOTAL A PERCIBIR 2.283,35"
    checked = check_document("nomina", payslip, PayslipExtraction(
        net_pay=Quoted(value="2283.35", evidence="LIQUIDO TOTAL A PERCIBIR 2.283,35"),
        extra_pay_prorated=False, extra_pay_prorated_evidence=None))
    assert checked.verified("extra_pay_prorated") == "sí"
    income = apply_document(State(), checked, "pdf", TODAY).draft["net_monthly_income"]
    assert income.value == "2283.35"  # ya prorrateado: no × 14 / 12 (que daría 2.663,91)

    statement = ("Saldo anterior 12.000,00\n15/10 BIZUM -40,00 24.557,80\n"
                 "Saldo final a 31/10/2026 24.557,80")
    checked = check_document("extracto", statement, BankStatementExtraction(
        closing_balance=NONE, loan_payments=[]))
    assert checked.verified("closing_balance") == Decimal("24557.80")  # no la fecha
    assert checked.fields["closing_balance"].evidence == "Saldo final a 31/10/2026 24.557,80"
