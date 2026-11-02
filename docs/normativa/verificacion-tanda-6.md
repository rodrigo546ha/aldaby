# Verificación de la tanda 6: Andalucía, Cataluña y Comunitat Valenciana

**Cargadas:** 2026-11-03 · **Estado:** con `verified: false` · **Revisa:** Rodrigo
**Ficheros:** `services/api/data/rules/andalucia.yaml`, `cataluna.yaml` y `comunitat_valenciana.yaml`

## Contexto
- Son las tres comunidades con más compraventas de vivienda de septiembre de 2025 a agosto de 2026
  (INE, ETDP, tabla 6150): Andalucía 142.297, Cataluña 113.175 y Comunitat Valenciana 106.339. Madrid,
  ya cargada, tuvo 77.629.
- Las redactó un agente por comunidad, leyendo la norma oficial. Cada regla dice en `notes` la norma, el
  artículo y la redacción vigente. Lo que el agente no pudo leer en la fuente oficial no se ha cargado.
- El ITP admite ya tramos (ADR-0043): progresivos, como en Cataluña, o con el tipo del tramo sobre todo el
  precio (`whole_value`), como en la Comunitat Valenciana.
- Mientras sigan sin verificar, los planes de estas comunidades salen con cifras provisionales.

## 1. Andalucía (ES-01)

- [ ] `andalucia-itp-inmuebles-2021` (impuesto_compra_segunda_mano, ES-01, 2021-10-27 → sin fin)
  - Cargado: `{"rate": 0.07}`
  - Fuente: https://www.boe.es/eli/es-an/l/2021/10/20/5/con
  - Nota: Ley 5/2021, de 20 de octubre, de Tributos Cedidos de la Comunidad Autónoma de Andalucía (BOE-A-2021-17915), art. 41: en las transmisiones de bienes inmuebles y en la constitución y cesión de derechos reales (salvo de garantía), tipo del 7 % sobre la base liquidada, único para todo el valor (no por tramos).
- [ ] `andalucia-ajd-compra-vivienda-2021` (ajd_compra_vivienda, ES-01, 2021-10-27 → sin fin)
  - Cargado: `{"bands": [{"up_to": null, "rate": 0.012}], "cap_jumps": false}`
  - Fuente: https://www.boe.es/eli/es-an/l/2021/10/20/5/con
  - Nota: Ley 5/2021 de Andalucía, art. 49: primeras copias de escrituras inscribibles con cantidad o cosa valuable, no sujetas a Sucesiones y Donaciones ni a TPO/IVA del art. 1.1 y 1.2 del TRLITPAJD, tributan además de la cuota fija al 1,2 %. No incluye los reducidos del art. 50 (política social de vivienda). Persona jurídica: mismo tipo (no hay tipo propio).
- [ ] `andalucia-irpf-escala-general-2022` (escala_irpf_general_autonomica, ES-01, 2022-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.095}, {"from": 13000, "rate": 0.12}, {"from": 21100, "rate": 0.15}, {"from": 35200, "rate": 0.185}, {"from": 60000, "rate": 0.225}]}`
  - Fuente: https://www.boe.es/eli/es-an/l/2021/10/20/5/con
  - Nota: Ley 5/2021 de Andalucía, art. 23 (redacción del Decreto-ley 7/2022, efectos 01/01/2022): 9,5 % hasta 13.000 €; 12 % hasta 21.100 €; 15 % hasta 35.200 €; 18,5 % hasta 60.000 €; 22,5 % en adelante. Fuente del decreto-ley: https://www.juntadeandalucia.es/boja/2022/182/1
- [ ] `andalucia-irpf-minimo-contribuyente-2022` (minimo_contribuyente, ES-01, 2022-01-01 → sin fin)
  - Cargado: `{"general": 5790, "over_65_extra": 1200, "over_75_extra": 1460}`
  - Fuente: https://www.boe.es/eli/es-an/l/2021/10/20/5/con
  - Nota: Ley 5/2021 de Andalucía, art. 23 bis.1 (añadido por el Decreto-ley 7/2022, efectos 01/01/2022), al amparo del art. 46.1 de la Ley 22/2009: 5.790 € con carácter general; +1.200 € si mayor de 65 años; +1.460 € adicionales si mayor de 75.
- [ ] `andalucia-irpf-minimo-descendientes-2022` (minimo_descendientes, ES-01, 2022-01-01 → sin fin)
  - Cargado: `{"first": 2510, "second": 2820, "third": 4170, "fourth_and_more": 4700, "under_3_extra": 2920}`
  - Fuente: https://www.boe.es/eli/es-an/l/2021/10/20/5/con
  - Nota: Ley 5/2021 de Andalucía, art. 23 bis.2 (añadido por el Decreto-ley 7/2022, efectos 01/01/2022): 2.510 €, 2.820 €, 4.170 € y 4.700 € por el primer, segundo, tercer y cuarto y siguientes descendientes; +2.920 € si el descendiente es menor de tres años.
- [ ] `andalucia-zonas-tensionadas` (zona_tensionada, ES-01, 2023-05-26 → sin fin)
  - Cargado: `{"declared": false, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Ley 12/2023, art. 18: la declaración corresponde a la comunidad autónoma; el Ministerio publica la relación cada trimestre.
- [ ] `andalucia-alquiler-turistico` (regimen_alquiler_turistico, ES-01, 2024-02-22 → sin fin)
  - Cargado: `{"regime": "Vivienda de uso turístico en Andalucía (Decreto 28/2016): declaración responsable e inscripción en el Registro de Turismo de Andalucía antes de iniciar la actividad", "requirements": [{"code": "declaracion-responsable", "description": "Declaración responsable electrónica ante la Consejer…`
  - Fuente: https://www.juntadeandalucia.es/boja/2024/24/50
  - Nota: Redacción del Decreto 28/2016 según el Decreto 31/2024 (BOJA núm. 24, 02/02/2024). Fecha de inicio calculada: veinte días tras la publicación. Pendiente comprobar posibles modificaciones posteriores a 2024 en el texto consolidado del Decreto 28/2016.
- [ ] `sevilla-plusvalia-tipo` (tipo_plusvalia, ES-01-41091, 2023-12-28 → sin fin)
  - Cargado: `{"rate": 0.2653}`
  - Fuente: https://www.sevilla.org/servicios/agencia-tributaria-de-sevilla/ordenanzas-fiscales/2024/1-5-ordenanza-fiscal-impuesto_sobre_el_incremento_del_valor_de_los_terrenos_de_naturaleza_urbana
  - Nota: Ordenanza Fiscal del IIVTNU del Ayuntamiento de Sevilla, art. 12.1: «un tipo impositivo del 26,53%». No se ha leído el BOP ni la ordenanza de 2026 (el Ayuntamiento anunció congelación del resto de impuestos locales para 2026); fecha de inicio tomada de la página de plusvalía de la Agencia Tributaria de Sevilla.
- [ ] `malaga-plusvalia-tipo` (tipo_plusvalia, ES-01-29067, 2025-04-08 → sin fin)
  - Cargado: `{"rate": 0.29}`
  - Fuente: https://www.malaga.eu/visorcontenido/NRMDocumentDisplayer/804/DocumentoNormativa804
  - Nota: Ordenanza Fiscal nº 5 del Ayuntamiento de Málaga, art. 8: «el tipo de gravamen del 29 por 100, que será único». Texto vigente tras la modificación del Pleno de 30/01/2025 (BOP de Málaga de 08/04/2025) y la parcial del Pleno de 22/12/2025 (BOP de 26/03/2026). Fecha de inicio = BOP de 08/04/2025; el 29 % puede venir de antes (por verificar).

**Pendiente o dudoso:**
- Zona tensionada: no se leyó la resolución del Ministerio del 2.º trimestre de 2024 ni la del 3.er trimestre de 2026, si ya está publicada.
- Plusvalía de Sevilla: no se leyó el BOP ni la ordenanza de 2026; la fecha de inicio (2023-12-28) sale de la web de la Agencia Tributaria de Sevilla.
- Plusvalía de Málaga: la fecha de inicio (2025-04-08) es la del BOP de la versión leída; el 29 % puede venir de antes.
- Alquiler turístico: faltan las limitaciones urbanísticas municipales de Sevilla y Málaga (no se encontró la fuente oficial), y comprobar si el Decreto 28/2016 cambió después de 2024.
- Los mínimos autonómicos los recoge el art. 23 bis; el texto cita el art. 46.1.a) de la Ley 22/2009.

## 2. Cataluña (ES-09)

- [ ] `cataluna-itp-inmuebles-2024` (impuesto_compra_segunda_mano, ES-09, 2024-03-15 → 2025-06-27)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.1}, {"from": 1000000, "rate": 0.11}]}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2024-6951#a6-85
  - Nota: Código tributario de Cataluña, libro sexto, art. 641-1.a) en la redacción original del Decreto Legislativo 1/2024: tarifa de inmuebles 10 % hasta 1.000.000 € y 11 % por el exceso (tipo medio, cada tipo sobre su tramo). Vigente hasta el 26/06/2025.
- [ ] `cataluna-itp-inmuebles-2025` (impuesto_compra_segunda_mano, ES-09, 2025-06-27 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.1}, {"from": 600000, "rate": 0.11}, {"from": 900000, "rate": 0.12}, {"from": 1500000, "rate": 0.13}]}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2025-10270
  - Nota: Código tributario de Cataluña, libro sexto, art. 641-1.1, redacción del art. 5.1 del Decreto-ley 5/2025 (en vigor desde el 27/06/2025): 10 % hasta 600.000 €, 11 % de 600.000 a 900.000 €, 12 % de 900.000 a 1.500.000 € y 13 % por encima; tipo medio (cada tipo sobre el exceso de su tramo). Gran tenedor y edificios enteros: 20 % sobre todo el valor (art. 641-1.5 y 6), no modelado.
- [ ] `cataluna-ajd-compra-vivienda-2024` (ajd_compra_vivienda, ES-09, 2024-03-15 → sin fin)
  - Cargado: `{"bands": [{"up_to": null, "rate": 0.015}], "cap_jumps": false}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2024-6951#a6-95
  - Nota: Código tributario de Cataluña, libro sexto, art. 642-1.d), 1,5 % de cuota variable en otros documentos notariales (texto refundido, Decreto Legislativo 1/2024); la letra a), elevada al 3,5 % por el Decreto-ley 5/2025 desde el 27/06/2025, no afecta a la vivienda nueva sujeta a IVA sin renuncia a la exención.
- [ ] `cataluna-irpf-escala-general-2024` (escala_irpf_general_autonomica, ES-09, 2024-01-01 → 2025-01-01)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.105}, {"from": 12450, "rate": 0.12}, {"from": 17707.2, "rate": 0.14}, {"from": 21000, "rate": 0.15}, {"from": 33007.2, "rate": 0.188}, {"from": 53407.2, "rate": 0.215}, {"from": 90000, "rate": 0.235}, {"from": 120000, "rate": 0.245}, {"from": 175000, "rate": 0.255…`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2024-6951
  - Nota: Código tributario de Cataluña, libro sexto, art. 611-1, redacción original del Decreto Legislativo 1/2024 (BOE-A-2024-6951).
- [ ] `cataluna-irpf-escala-general-2025` (escala_irpf_general_autonomica, ES-09, 2025-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.095}, {"from": 12500, "rate": 0.125}, {"from": 22000, "rate": 0.16}, {"from": 33000, "rate": 0.19}, {"from": 53000, "rate": 0.215}, {"from": 90000, "rate": 0.235}, {"from": 120000, "rate": 0.245}, {"from": 175000, "rate": 0.255}]}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2024-6951#a6
  - Nota: Código tributario de Cataluña, libro sexto, art. 611-1, redacción del art. 3.1 del Decreto-ley 5/2025, con efectos del 1 de enero de 2025 (BOE-A-2025-10270). Sin cambios posteriores en el texto consolidado leído el 2026-11-03, por lo que rige también el periodo 2026.
- [ ] `barcelona-plusvalia-2025` (tipo_plusvalia, ES-09-08019, 2025-01-01 → sin fin)
  - Cargado: `{"rate": 0.3}`
  - Fuente: https://www.barcelona.cat/hisenda/sites/default/files/normativa/2022-06/1.3-ordenanca-iivtnu-plusvalua.pdf
  - Nota: Ordenança fiscal núm. 1.3 del Ayuntamiento de Barcelona (IIVTNU), art. 7: «El tipus impositiu és del 30%». Aprobada definitivamente el 20/12/2024, BOPB de 23/12/2024 (CVE 202410197054), en vigor el 1 de enero de 2025 y vigente mientras no se modifique. La relación de modificaciones de 2026 que publica Hisenda no incluye la 1.3 (a comprobar en el BOPB).
- [ ] `cataluna-alquiler-turistico` (regimen_alquiler_turistico, ES-09, 2023-11-09 → sin fin)
  - Cargado: `{"regime": "Habitatge d'ús turístic en Cataluña: cesión onerosa de la vivienda entera, por estancias de temporada (31 días como máximo), con comunicación previa al ayuntamiento e inscripción en el Registro de Turismo de Cataluña", "requirements": [{"code": "comunicacion-previa-ayuntamiento", "descri…`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2024-281
  - Nota: Decreto-ley 3/2023, art. 1: licencia urbanística previa; art. 2: la relación de municipios del anexo tiene vigencia de cinco años desde su entrada en vigor o hasta la orden que la sustituya. El municipio de cada inmueble debe comprobarse en el anexo.
- [ ] `cataluna-zonas-tensionadas` (zona_tensionada, ES-09, 2023-05-26 → sin fin)
  - Cargado: `{"declared": false, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Ley 12/2023, art. 18. Resoluciones trimestrales del Ministerio revisadas hasta la del segundo trimestre de 2026 (BOE-A-2026-16532, de 29/07/2026): las únicas con municipios de Cataluña son BOE-A-2024-5214 y BOE-A-2024-20576. PENDIENTE: las Resoluciones TER/3739/2026 (prórroga de 118 municipios) y TER/3740/2026 (53 nuevos), de 16/10/2026, aún sin resolución del Ministerio.
- [ ] **271 municipios declarados zona tensionada** (`declared: true`), de: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2024-20576, https://www.boe.es/diario_boe/txt.php?id=BOE-A-2024-5214. Comprobar la lista contra las resoluciones y los códigos INE.

**Pendiente o dudoso:**
- ITP: la escala anterior se ha fechado desde el 2024-03-15 (entrada en vigor del Decreto Legislativo 1/2024); comprobar que no hay otra redacción entre medias.
- Escala del IRPF anterior: fechada desde el 2024-01-01 aunque la refundición entró en vigor el 15/03/2024. Esa fecha no se ha leído en la norma.
- Mínimos: no se han cargado. Cataluña fija solo el mínimo general (5.550 €, art. 611-2), sin los aumentos por edad que pide el esquema, y no tiene mínimo por descendientes: se aplican los estatales. ¿Bien así?
- Zona tensionada: las Resoluciones TER/3739/2026 (prórroga de 118 municipios) y TER/3740/2026 (53 nuevos), de 16/10/2026, siguen sin resolución del Ministerio. Cuando salga, 22 municipios dejan la zona y entran otros.
- Zona tensionada: las reglas municipales llevan `effective_to: null`, pero cada declaración dura tres años (vence en marzo y en octubre de 2027).
- ITP: el 20 % para grandes tenedores y edificios enteros queda solo en `notes`; un inversor con más de 10 viviendas (5 en zona tensionada) pagaría eso.
- Plusvalía de Barcelona: confirmar en el BOPB que las modificaciones de 2026 no tocan el 30 %.
- Alquiler turístico: el texto leído del Decreto 159/2012 está consolidado a marzo de 2017.

## 3. Comunitat Valenciana (ES-10)

- [ ] `cv-itp-inmuebles-2023` (impuesto_compra_segunda_mano, ES-10, 2023-01-01 → 2026-06-01)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.1}, {"from": 1000000.01, "rate": 0.11}], "whole_value": true}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-1998-8202#a13
  - Nota: Ley 13/1997 de la Generalitat Valenciana, art. 13.Uno, redacción consolidada con vigencia desde el 01/01/2023 (10 % general; 11 % si el valor supera 1.000.000 €, sobre todo el valor). Dejó de aplicarse a los hechos imponibles devengados desde el 01/06/2026 (Ley 5/2025, art. 33). La fecha de inicio es la de la versión consolidada del BOE (tramo del 11 % introducido en la ley de medidas de 2022, BOE-A-2023-5482); falta leer el artículo de esa ley.
- [ ] `cv-itp-inmuebles-2026` (impuesto_compra_segunda_mano, ES-10, 2026-06-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.09}, {"from": 1000000.01, "rate": 0.11}], "whole_value": true}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-1998-8202#a13
  - Nota: Ley 13/1997 de la Generalitat Valenciana, art. 13.Uno, redacción del art. 33 de la Ley 5/2025, de 30 de mayo (BOE-A-2025-11959), «con efectos para los hechos imponibles devengados desde el 1 de junio de 2026 inclusive»: 9 % general; 11 % si el valor supera 1.000.000 €, sobre todo el valor.
- [ ] `cv-ajd-compra-vivienda-2020` (ajd_compra_vivienda, ES-10, 2020-01-01 → 2026-06-01)
  - Cargado: `{"bands": [{"up_to": null, "rate": 0.015}], "cap_jumps": false}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-1998-8202#a14
  - Nota: Ley 13/1997 de la Generalitat Valenciana, art. 14.Cuatro, «En los demás casos, el 1,5 por 100» (versión consolidada con vigencia desde el 01/01/2020, BOE-A-2020-1010; 1,5 % desde la versión de 2013). Hasta los hechos imponibles devengados el 31/05/2026.
- [ ] `cv-ajd-compra-vivienda-2026` (ajd_compra_vivienda, ES-10, 2026-06-01 → sin fin)
  - Cargado: `{"bands": [{"up_to": null, "rate": 0.014}], "cap_jumps": false}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-1998-8202#a14
  - Nota: Ley 13/1997 de la Generalitat Valenciana, art. 14.Cuatro, redacción del art. 34 de la Ley 5/2025, de 30 de mayo (BOE-A-2025-11959), «con efectos para los hechos imponibles devengados desde el 1 de junio de 2026 inclusive»: «En los demás casos, el 1,4 por 100». No se carga legal_person_rate: la ley valenciana no distingue por tipo de sujeto.
- [ ] `cv-irpf-escala-general-2023` (escala_irpf_general_autonomica, ES-10, 2023-01-01 → 2026-01-01)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.09}, {"from": 12000, "rate": 0.12}, {"from": 22000, "rate": 0.15}, {"from": 32000, "rate": 0.175}, {"from": 42000, "rate": 0.2}, {"from": 52000, "rate": 0.225}, {"from": 62000, "rate": 0.25}, {"from": 72000, "rate": 0.265}, {"from": 100000, "rate": 0.275}, {"from"…`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-1998-8202#a2
  - Nota: Ley 13/1997 de la Generalitat Valenciana, art. 2.1 (tramos 0 / 12.000 / 22.000 / 32.000 / 42.000 / 52.000 / 62.000 / 72.000 / 100.000 / 150.000 / 200.000 €), redacción vigente en la versión consolidada de 2023 a 2025.
- [ ] `cv-irpf-escala-general-2026` (escala_irpf_general_autonomica, ES-10, 2026-01-01 → 2027-01-01)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.088}, {"from": 12000, "rate": 0.117}, {"from": 22000, "rate": 0.146}, {"from": 32000, "rate": 0.17}, {"from": 42000, "rate": 0.194}, {"from": 52000, "rate": 0.219}, {"from": 62000, "rate": 0.244}, {"from": 72000, "rate": 0.261}, {"from": 100000, "rate": 0.2735}, {…`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-1998-8202#a2
  - Nota: Ley 13/1997 de la Generalitat Valenciana, art. 2.1, redacción de la Ley 5/2026, de 31 de julio, art. 18 (BOE-A-2026-19331), con efectos desde el 1 de enero de 2026.
- [ ] `cv-irpf-escala-general-2027` (escala_irpf_general_autonomica, ES-10, 2027-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.087}, {"from": 12000, "rate": 0.116}, {"from": 22000, "rate": 0.145}, {"from": 32000, "rate": 0.169}, {"from": 42000, "rate": 0.193}, {"from": 52000, "rate": 0.218}, {"from": 62000, "rate": 0.243}, {"from": 72000, "rate": 0.26}, {"from": 100000, "rate": 0.2725}, {…`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-1998-8202#a2
  - Nota: Ley 13/1997 de la Generalitat Valenciana, art. 2.1, redacción de la disposición transitoria tercera de la Ley 5/2026, de 31 de julio (BOE-A-2026-19331), con efectos desde el 1 de enero de 2027.
- [ ] `cv-irpf-minimo-contribuyente-2023` (minimo_contribuyente, ES-10, 2023-01-01 → sin fin)
  - Cargado: `{"general": 6105, "over_65_extra": 1265, "over_75_extra": 1540}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-1998-8202#a2-2
  - Nota: Ley 13/1997 de la Generalitat Valenciana, art. 2 bis.1: 6.105 € con carácter general; +1.265 € si es mayor de 65 años y +1.540 € adicionales si es mayor de 75.
- [ ] `cv-irpf-minimo-descendientes-2023` (minimo_descendientes, ES-10, 2023-01-01 → sin fin)
  - Cargado: `{"first": 2640, "second": 2970, "third": 4400, "fourth_and_more": 4950, "under_3_extra": 3080}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-1998-8202#a2-2
  - Nota: Ley 13/1997 de la Generalitat Valenciana, art. 2 bis.2: 2.640 € (primero), 2.970 € (segundo), 4.400 € (tercero), 4.950 € (cuarto y siguientes); +3.080 € por descendiente menor de tres años (art. 58.2 de la Ley 35/2006).
- [ ] `cv-zonas-tensionadas` (zona_tensionada, ES-10, 2023-05-26 → sin fin)
  - Cargado: `{"declared": false, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Ley 12/2023, art. 18: la declaración corresponde a la comunidad autónoma; el Ministerio publica la relación cada trimestre.
- [ ] `cv-alquiler-turistico` (regimen_alquiler_turistico, ES-10, 2024-08-08 → sin fin)
  - Cargado: `{"regime": "Vivienda de uso turístico en la Comunitat Valenciana: inmueble completo cedido por precio, con fines turísticos, por 10 días o menos a un mismo arrendatario; inscripción en el Registro de Turismo con validez de 5 años", "requirements": [{"code": "declaracion-responsable", "description": …`
  - Fuente: https://dogv.gva.es/datos/2024/08/07/pdf/2024_8209_es.pdf
  - Nota: Decreto-ley 9/2024, de 2 de agosto, del Consell (DOGV 07/08/2024; entra en vigor el día siguiente). Está por verificar si el Decreto-ley se convalidó o se sustituyó por ley y si el art. 23 del Decreto 10/2021 tiene modificaciones posteriores a 2024; se ha leído solo el texto del DOGV de 07/08/2024.
- [ ] `valencia-plusvalia-2024` (tipo_plusvalia, ES-10-46250, 2024-01-01 → sin fin)
  - Cargado: `{"rate": 0.297}`
  - Fuente: https://sede.valencia.es/sede/descarga/doc/DOCUMENT_1_20250007835054
  - Nota: Ordenanza fiscal reguladora del IIVTNU del Ayuntamiento de València, art. 9.1: «El tipo de gravamen de este impuesto queda fijado en el 29,70%», para todos los periodos de generación. Leído el texto consolidado de la sede electrónica, no el anuncio del BOP; falta contrastar con el BOP y con la fecha de aplicación del tipo.
- [ ] `alicante-plusvalia-2023` (tipo_plusvalia, ES-10-03014, 2023-06-01 → sin fin)
  - Cargado: `{"rate": 0.3}`
  - Fuente: https://www.alicante.es/sites/default/files/documentos/202306/ord-ivtnu.pdf
  - Nota: Ordenanza fiscal del IIVTNU del Ayuntamiento de Alicante, art. 12 (Tipo impositivo): «el tipo del 30 por 100», texto publicado en el BOP núm. 105 de 01/06/2023, que entra en vigor el día de su publicación. Leído el PDF municipal, no el BOP; la prensa informa de litigios del TSJ sobre la validez de la ordenanza (sin leer la sentencia).

**Pendiente o dudoso:**
- ITP: por encima de 1.000.000 € el 11 % va sobre todo el valor (`whole_value: true`), no solo sobre el exceso. Es lo que dice el art. 13.Uno: compruébalo, porque cambia mucho la cuota.
- ITP: la fecha de inicio del tramo del 11 % (2023-01-01) sale de la versión consolidada del BOE; falta leer el artículo de la Ley 8/2022 que lo introdujo.
- IRPF: la escala de 2027 (disposición transitoria tercera de la Ley 5/2026) se ha cargado ya, con vigencia desde el 2027-01-01.
- Mínimos: fechados desde el 2023-01-01; no se ha comprobado si el Decreto-ley 14/2022 los aplicaba ya a 2022.
- Alquiler turístico: no se sabe si el Decreto-ley 9/2024 se convalidó o se sustituyó por una ley, ni si el art. 23 del Decreto 10/2021 cambió después de 2024.
- Plusvalías: València leída en la sede municipal y Alicante en el PDF del Ayuntamiento, no en el anuncio del BOP. Hay litigios del TSJ sobre la ordenanza de Alicante (prensa; no se ha leído ninguna sentencia).
