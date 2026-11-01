"""Marca del profesional (F7.3, ADR-0030): logotipo reescrito, color con contraste y textos."""

import io
from decimal import Decimal
from uuid import uuid4

import pytest
from PIL import Image

from housefinder.branding.logo import LogoError, clean_logo
from housefinder.branding.service import BrandingError, check_color, contrast_on_white

psycopg = pytest.importorskip("psycopg")


def image(fmt: str, size=(1200, 400)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, (31, 95, 139)).save(out, format=fmt)
    return out.getvalue()


def test_el_logotipo_se_reduce_y_se_reescribe_en_png():
    cleaned = clean_logo(image("JPEG"))
    with Image.open(io.BytesIO(cleaned)) as logo:
        assert logo.format == "PNG" and logo.size == (600, 200)


def test_logotipos_que_no_valen():
    with pytest.raises(LogoError, match="PNG o JPEG"):
        clean_logo(image("GIF"))
    with pytest.raises(LogoError, match="No se puede leer"):
        clean_logo(b"<svg xmlns='http://www.w3.org/2000/svg'></svg>")
    with pytest.raises(LogoError, match="2 MB"):
        clean_logo(b"0" * (2 * 1024 * 1024 + 1))


def test_contraste_sobre_blanco():
    # Valores de referencia de WCAG: #767676 es el gris más claro que pasa 4,5:1
    assert contrast_on_white("#000000") == Decimal("21")
    assert contrast_on_white("#767676") > Decimal("4.5") > contrast_on_white("#777777")
    assert check_color(" #1F5F8B ") == "#1f5f8b"
    assert check_color("") is None
    with pytest.raises(BrandingError, match="demasiado claro"):
        check_color("#ffcc00")
    with pytest.raises(BrandingError, match="#RRGGBB"):
        check_color("azul")


@pytest.mark.db
def test_guardar_y_leer_la_marca(migrated_database):
    from housefinder.branding import service
    from housefinder.db.profiles import create_organization

    with psycopg.connect(migrated_database) as conn:
        org = create_organization(conn, f"Marca {uuid4()}", "profesional")
        assert service.load(conn, org).empty
        service.save_texts(conn, org, "  Asesoría   Ana ", "ana@ejemplo.es · 600 000 000",
                           "#1f5f8b", "Te acompaño\n\n en la compra.  ")
        service.save_logo(conn, org, image("PNG", (300, 100)))
        brand = service.load(conn, org)
        assert (brand.display_name, brand.color) == ("Asesoría Ana", "#1f5f8b")
        assert brand.intro == "Te acompaño\n\nen la compra."
        assert brand.logo_png.startswith(b"\x89PNG") and not brand.empty
        with pytest.raises(BrandingError, match="80 caracteres"):
            service.save_texts(conn, org, "x" * 81, None, None, None)
        service.save_logo(conn, org, None)
        assert service.load(conn, org).logo_png is None


@pytest.mark.db
def test_api_de_la_marca(migrated_database):
    import base64

    from fastapi.testclient import TestClient

    from housefinder.api.deps import get_db, get_org
    from housefinder.api.main import app
    from housefinder.db.profiles import create_organization

    with psycopg.connect(migrated_database) as conn:
        org = create_organization(conn, f"Marca API {uuid4()}", "profesional")
        conn.commit()

    def db():
        with psycopg.connect(migrated_database) as conn:
            yield conn

    app.dependency_overrides.update({get_db: db, get_org: lambda: org})
    try:
        api = TestClient(app)
        assert api.get("/branding").json()["has_logo"] is False
        assert api.get("/branding/logo").status_code == 404
        saved = api.put("/branding", json={"display_name": "Asesoría Ana", "color": "#1f5f8b"})
        assert saved.status_code == 200 and saved.json()["color"] == "#1f5f8b"
        light = api.put("/branding", json={"color": "#ffcc00"})
        assert light.status_code == 422 and "demasiado claro" in light.json()["detail"]
        logo = api.put("/branding/logo",
                       json={"content_base64": base64.b64encode(image("PNG")).decode()})
        assert logo.json()["has_logo"] is True
        served = api.get("/branding/logo")
        assert served.headers["content-type"] == "image/png"
        assert served.content.startswith(b"\x89PNG")
        bad = api.put("/branding/logo", json={"content_base64": base64.b64encode(
            b"<svg/>").decode()})
        assert bad.status_code == 422
        assert api.delete("/branding/logo").json()["has_logo"] is False
    finally:
        app.dependency_overrides.clear()
