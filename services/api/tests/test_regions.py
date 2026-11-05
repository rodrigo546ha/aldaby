from housefinder.core.regions import province_regions, region_of


def test_comunidad_de_cada_provincia():
    # INE: Barcelona (08) es de Cataluña (09); Bizkaia (48), del País Vasco (16); Melilla (52),
    # de la ciudad autónoma 19
    assert region_of("08019") == "09" and region_of("48") == "16" and region_of("52001") == "19"
    assert region_of("28079") == "13"
    assert len(province_regions()) == 52
    assert region_of("99") is None
