from datetime import date

from housefinder.ingestion.boe import property_sale_items

# Estructura mínima para probar el filtro de subastas (F4). La estructura real del sumario
# se prueba con tests/fixtures/boe/ en test_watch.py.
PAYLOAD = {
    "data": {
        "sumario": {
            "diario": [
                {
                    "seccion": [
                        {
                            "item": [
                                {
                                    "identificador": "BOE-B-2026-0001",
                                    "titulo": "Resolución de la Tesorería General de la Seguridad "
                                    "Social por la que se anuncia subasta pública de inmuebles",
                                    "url_pdf": {"texto": "https://www.boe.es/x.pdf"},
                                },
                                {
                                    "identificador": "BOE-B-2026-0002",
                                    "titulo": "Anuncio de licitación de servicio de limpieza",
                                },
                            ]
                        }
                    ]
                }
            ]
        }
    }
}


def test_filtra_subastas_de_inmuebles():
    items = property_sale_items(PAYLOAD, date(2026, 10, 27))
    assert [i.identifier for i in items] == ["BOE-B-2026-0001"]
    assert items[0].url_pdf == "https://www.boe.es/x.pdf"
