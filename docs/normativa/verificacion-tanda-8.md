# Verificación de la tanda 8: Aragón, Asturias, Illes Balears, Cantabria, Extremadura y La Rioja

**Cargadas:** 2026-11-03 · **Estado:** con `verified: false` · **Revisa:** Rodrigo
**Ficheros:** `services/api/data/rules/aragon.yaml`, `asturias.yaml`, `baleares.yaml`, `cantabria.yaml`, `extremadura.yaml` y `la_rioja.yaml`

## Contexto
- Las comunidades de régimen común que faltaban después de las tandas 6 y 7 (ADR-0043).
- Un agente por comunidad, leyendo la norma oficial; lo que no pudo leer en la fuente oficial no se ha
  cargado. Cada regla dice en `notes` la norma, el artículo y la redacción vigente.
- Ceuta y Melilla se cargaron después, con sus bonificaciones y su deducción del IRPF (ADR-0045): ver la sección 9.
- En ninguna de las seis hay resolución de zona tensionada del segundo trimestre de 2024 leída, ni del tercero de 2026 (no publicada aún).
- Mientras sigan sin verificar, los planes de estas comunidades salen con cifras provisionales.

## 1. Aragón (ES-02)

- [ ] `aragon-itp-inmuebles-2016` (impuesto_compra_segunda_mano, ES-02, 2016-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.08}, {"from": 400000, "rate": 0.085}, {"from": 450000, "rate": 0.09}, {"from": 500000, "rate": 0.095}, {"from": 750000, "rate": 0.1}]}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOA-d-2005-90006#a1-4
  - Nota: Decreto Legislativo 1/2005 de Aragón, art. 121-1, redacción del art. 2.1 de la Ley 10/2015, de 28 de diciembre (efectos desde el 01/01/2016, disp. final 2.2). Escala: 8 % hasta 400.000 €; 8,5 % de 400.000 a 450.000; 9 % de 450.000 a 500.000; 9,5 % de 500.000 a 750.000; 10 % desde 750.000. Cuota íntegra acumulada de la tabla: 32.000, 36.250 y 40.750 y 64.500 € en 400.000, 450.000, 500.000 y 750.000 € (coincide con progresiva). «Determinados así los tipos procedentes, se aplicarán sobre la base liquidable en la misma proporción que sobre el valor del bien».
- [ ] `aragon-ajd-compra-vivienda-2016` (ajd_compra_vivienda, ES-02, 2016-01-01 → sin fin)
  - Cargado: `{"bands": [{"up_to": null, "rate": 0.015}], "cap_jumps": false}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOA-d-2005-90006#a1-10
  - Nota: Decreto Legislativo 1/2005 de Aragón, art. 122-1.1, redacción del art. 2.8 de la Ley 10/2015, de 28 de diciembre (efectos desde el 01/01/2016): «tipo general del 1,5 por 100 en las primeras copias de escrituras y actas notariales sujetas como Documentos notariales». Persona jurídica: mismo tipo (no hay tipo propio).
- [ ] `aragon-irpf-escala-general-2023` (escala_irpf_general_autonomica, ES-02, 2023-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.095}, {"from": 13072.5, "rate": 0.12}, {"from": 21210, "rate": 0.15}, {"from": 36960, "rate": 0.185}, {"from": 52500, "rate": 0.205}, {"from": 60000, "rate": 0.23}, {"from": 80000, "rate": 0.24}, {"from": 90000, "rate": 0.25}, {"from": 130000, "rate": 0.255}]}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOA-d-2005-90006#a1
  - Nota: Decreto Legislativo 1/2005 de Aragón, art. 110-1, redacción de la Ley 17/2023 (efectos 01/01/2023): 9,5 % hasta 13.072,50 €; 12 % hasta 21.210; 15 % hasta 36.960; 18,5 % hasta 52.500; 20,5 % hasta 60.000; 23 % hasta 80.000; 24 % hasta 90.000; 25 % hasta 130.000; 25,5 % en adelante. Los tramos se leen de la columna «Base liquidable hasta» de la tabla del BOE (el «resto base liquidable hasta» es la anchura de cada tramo; ambas columnas coinciden).
- [ ] `aragon-zonas-tensionadas` (zona_tensionada, ES-02, 2023-05-26 → sin fin)
  - Cargado: `{"declared": false, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Ley 12/2023, art. 18: la declaración corresponde a la comunidad autónoma; el Ministerio publica la relación cada trimestre. La del segundo trimestre de 2026 (Resolución de 24/07/2026, BOE núm. 184 de 29/07/2026) solo recoge Asturias, Galicia y País Vasco.
- [ ] `aragon-alquiler-turistico` (regimen_alquiler_turistico, ES-02, 2025-04-03 → sin fin)
  - Cargado: `{"regime": "Vivienda de uso turístico en Aragón (Decreto 1/2023): declaración responsable previa e inscripción informativa en el Registro de Turismo de Aragón", "requirements": [{"code": "declaracion-responsable", "description": "Declaración responsable previa al inicio de la actividad ante la Direc…`
  - Fuente: https://www.aragon.es/tramitador/-/tramite/declaracion-responsable-viviendas-turistico
  - Nota: Fecha de inicio = entrada en vigor de la modificación de la LPH (03/04/2025); la entrada en vigor del Decreto 1/2023 y su texto en el BOA no se han leído (por verificar). Se presume sujeta al reglamento la cesión por un mes o menos por usuario o comercializada en canales turísticos. El art. 15.2.f del decreto (declaración de que los estatutos no la prohíben) queda desplazado por el acuerdo expreso, según la Administración.
- [ ] `zaragoza-plusvalia-tipo` (tipo_plusvalia, ES-02-50297, 2026-02-06 → sin fin)
  - Cargado: `{"rate": 0.28}`
  - Fuente: https://www.zaragoza.es/sede/servicio/normativa/3465
  - Nota: Ordenanza Fiscal nº 9 del Ayuntamiento de Zaragoza, art. 13: «el tipo de gravamen único del 28%». Fecha de inicio = BOPZ nº 29 (06/02/2026); el 28 % puede venir de antes (según fuentes secundarias, rebaja del 30 % a 28 % por propuesta de Vox en las ordenanzas anteriores; no leído en el BOPZ). La sede muestra además una modificación del art. 14.2 aprobada inicialmente el 29/09/2026 (BOPZ 02/10/2026), que no toca el tipo.
- [ ] `huesca-plusvalia-tipo` (tipo_plusvalia, ES-02-22125, 2026-01-01 → sin fin)
  - Cargado: `{"rate": 0}`
  - Fuente: https://www.huesca.es/documents/20126/142542/OF+3+Reguladora+del+impuesto+sobre+el+incremento+del+valor+de+los+terrenos+de+naturaleza+urbana.pdf/5f645207-4efc-3c31-3d73-1f443ce24303?t=1735898410723
  - Nota: Ordenanza Fiscal nº 3 del Ayuntamiento de Huesca: «derogada íntegramente por Acuerdo del Excmo. Ayuntamiento Pleno, en sesión celebrada el 22 de diciembre de 2025, con efectos a partir del día 1 de enero de 2026». Es la leyenda que publica la sede en el PDF de la ordenanza; no se ha leído el acuerdo ni el BOP de Huesca. Las transmisiones anteriores a 2026 siguen la ordenanza antigua (su tipo no consta).

**Pendiente o dudoso:**
- ITP progresivo: 8 % hasta 400.000 €, 8,5 %, 9 %, 9,5 % y 10 % por encima de 750.000 €; la cuota acumulada de la tabla del art. 121-1 solo cuadra si cada tipo va sobre su tramo.
- Sin mínimos propios: el DL 1/2005 solo tiene escala y deducciones.
- Las fechas de inicio del ITP, el AJD y la escala son las de la redacción leída; no se han cargado las reglas anteriores (el IRPF cambió en 2022; el ITP y el AJD, antes de 2016).
- Plusvalía de Zaragoza: la fecha (2026-02-06) es la del BOPZ leído; fuentes secundarias dicen que el 28 % es anterior. Hay una modificación del art. 14.2 aprobada inicialmente el 29/09/2026 que no toca el tipo.
- Plusvalía de Huesca con tipo 0 desde 2026: la sede muestra la ordenanza fiscal n.º 3 como derogada por el Pleno de 22/12/2025. Solo se ha leído la leyenda del PDF, no el acuerdo ni el BOP. Confirmar antes de nada.
- Turismo: fecha de inicio por la modificación de la Ley de Propiedad Horizontal; no se ha leído el Decreto 1/2023 en el BOA. Falta el régimen urbanístico de Zaragoza y Huesca.

## 2. Principado de Asturias (ES-03)

- [ ] `asturias-itp-inmuebles-2014` (impuesto_compra_segunda_mano, ES-03, 2014-10-30 → sin fin)
  - Cargado: `{"whole_value": true, "brackets": [{"from": 0, "rate": 0.08}, {"from": 300000.01, "rate": 0.09}, {"from": 500000.01, "rate": 0.1}]}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2015-945#a26
  - Nota: Decreto Legislativo 2/2014 de Asturias, art. 26, sin modificaciones en el texto consolidado a 31/12/2025: «el tipo de gravamen que resulte de la siguiente tarifa atendiendo al valor íntegro del bien o derecho»: 8 % entre 0 y 300.000 €; 9 % entre 300.000,01 y 500.000 €; 10 % por encima de 500.000 €. Es un tipo único por tramo sobre TODO el valor (no progresivo): un precio de 300.000,01 € paga el 9 % sobre los 300.000,01 €. Fecha de inicio = entrada en vigor del texto refundido (30/10/2014); la tarifa puede venir de antes (por verificar en la ley que la introdujo).
- [ ] `asturias-ajd-compra-vivienda-2014` (ajd_compra_vivienda, ES-03, 2014-10-30 → sin fin)
  - Cargado: `{"bands": [{"up_to": null, "rate": 0.012}], "cap_jumps": false}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2015-945#a34
  - Nota: Decreto Legislativo 2/2014 de Asturias, art. 34: «Con carácter general se aplicará el tipo del 1,2 por ciento en las primeras copias de escrituras y actas notariales sujetas como documentos notariales.» No incluye el 1,5 % de la renuncia a la exención del IVA (art. 36) ni los de VPP (art. 35) o vivienda destinada a alquiler (art. 38). Fecha de inicio = entrada en vigor del texto refundido (30/10/2014); por verificar si el 1,2 % ya regía antes.
- [ ] `asturias-irpf-escala-general-2015` (escala_irpf_general_autonomica, ES-03, 2015-01-01 → 2025-01-01)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.1}, {"from": 12450, "rate": 0.12}, {"from": 17707.2, "rate": 0.14}, {"from": 33007.2, "rate": 0.185}, {"from": 53407.2, "rate": 0.215}, {"from": 70000, "rate": 0.225}, {"from": 90000, "rate": 0.25}, {"from": 175000, "rate": 0.255}]}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2015-1764#a39
  - Nota: Decreto Legislativo 2/2014 de Asturias, art. 2, redacción del art. 39.Uno de la Ley 11/2014, de 29 de diciembre (BOE-A-2015-1764; «a partir del ejercicio 2015», en vigor el 01/01/2015): 10 % hasta 12.450 €; 12 % hasta 17.707,20 €; 14 % hasta 33.007,20 €; 18,5 % hasta 53.407,20 €; 21,5 % hasta 70.000 €; 22,5 % hasta 90.000 €; 25 % hasta 175.000 €; 25,5 % en adelante. Sustituida por la Ley 3/2025 para el periodo 2025.
- [ ] `asturias-irpf-escala-general-2025` (escala_irpf_general_autonomica, ES-03, 2025-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.09}, {"from": 12450, "rate": 0.12}, {"from": 17707.2, "rate": 0.14}, {"from": 33007.2, "rate": 0.192}, {"from": 53407.2, "rate": 0.215}, {"from": 70000, "rate": 0.225}, {"from": 90000, "rate": 0.25}, {"from": 175000, "rate": 0.26}]}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2015-945#a2
  - Nota: Decreto Legislativo 2/2014 de Asturias, art. 2, redacción del art. único.1 de la Ley 3/2025, de 19 de noviembre (BOE-A-2025-25707; BOPA núm. 232, 02/12/2025; en vigor el 03/12/2025): 9 % hasta 12.450 €; 12 % hasta 17.707,20 €; 14 % hasta 33.007,20 €; 19,2 % hasta 53.407,20 €; 21,5 % hasta 70.000 €; 22,5 % hasta 90.000 €; 25 % hasta 175.000 €; 26 % en adelante. Aplicación al periodo 2025 deducida de la exposición de motivos (la ley no lo dice en su articulado): por verificar.
- [ ] `asturias-irpf-minimo-contribuyente-2025` (minimo_contribuyente, ES-03, 2025-01-01 → sin fin)
  - Cargado: `{"general": 6105, "over_65_extra": 1265, "over_75_extra": 1540}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2015-945#a2-2
  - Nota: Decreto Legislativo 2/2014 de Asturias, art. 2 bis, añadido por el art. único.2 de la Ley 3/2025 (en vigor el 03/12/2025): 6.105 € con carácter general; +1.265 € si mayor de 65 años; +1.540 € adicionales si mayor de 75. La exposición de motivos los eleva «un 10 %, el máximo permitido por la normativa estatal» y los aplica al ejercicio 2025 (por verificar).
- [ ] `asturias-irpf-minimo-descendientes-2025` (minimo_descendientes, ES-03, 2025-01-01 → sin fin)
  - Cargado: `{"first": 2640, "second": 2970, "third": 4400, "fourth_and_more": 4950, "under_3_extra": 3080}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2015-945#a2-3
  - Nota: Decreto Legislativo 2/2014 de Asturias, art. 2 ter, añadido por el art. único.2 de la Ley 3/2025: 2.640 €, 2.970 €, 4.400 € y 4.950 € por el primer, segundo, tercer y cuarto y siguientes descendientes (menores de 25 años o con discapacidad, que convivan y con rentas de hasta 8.000 €); +3.080 € si el descendiente es menor de tres años.
- [ ] `asturias-zonas-tensionadas` (zona_tensionada, ES-03, 2023-05-26 → sin fin)
  - Cargado: `{"declared": false, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Ley 12/2023, art. 18: la declaración corresponde a la comunidad autónoma; el Ministerio publica la relación cada trimestre. Sin declaración de ámbito autonómico: solo ámbitos de los municipios de Avilés, Cabrales, Gijón, Gozón y Llanes (reglas ES-03-33004, 33008, 33024, 33025 y 33036).
- [ ] `asturias-zona-tensionada-33004` (zona_tensionada, ES-03-33004, 2026-07-30 → 2029-07-30)
  - Cargado: `{"declared": true, "checked_through": "2026-07-29", "area": "barrio de La Magdalena"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Avilés: SOLO el barrio de La Magdalena (Resolución de 15/05/2026, BOPA núm. 96, 21/05/2026, https://miprincipado.asturias.es/bopa/2026/05/21/2026-04107.pdf), no el resto del concejo. Vigencia de tres años desde el día siguiente a la publicación de la resolución del Ministerio (29/07/2026). Gran tenedor: más de diez inmuebles o más de 1.500 m². Aplica la limitación del art. 17.7 de la LAU.
- [ ] `asturias-zona-tensionada-33008` (zona_tensionada, ES-03-33008, 2026-07-30 → 2029-07-30)
  - Cargado: `{"declared": true, "checked_through": "2026-07-29", "area": "núcleos de Arenas y Poo"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Cabrales: SOLO los núcleos de Arenas y de Poo (Resolución de 24/04/2026, BOPA núm. 82, 30/04/2026, https://miprincipado.asturias.es/bopa/2026/04/30/2026-03383.pdf, y Resolución de 11/05/2026, BOPA núm. 96, 21/05/2026, https://miprincipado.asturias.es/bopa/2026/05/21/2026-04016.pdf), no el resto del concejo. Vigencia de tres años desde el día siguiente a la publicación de la resolución del Ministerio (29/07/2026). Gran tenedor: más de diez inmuebles o más de 1.500 m². Aplica la limitación del art. 17.7 de la LAU.
- [ ] `asturias-zona-tensionada-33024` (zona_tensionada, ES-03-33024, 2026-07-30 → 2029-07-30)
  - Cargado: `{"declared": true, "checked_through": "2026-07-29", "area": "barrios de La Arena y Cimadevilla"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Gijón/Xixón: SOLO los barrios de La Arena y Cimadevilla (Resolución de 14/05/2026, BOPA núm. 96, 21/05/2026, https://miprincipado.asturias.es/bopa/2026/05/21/2026-04106.pdf), no el resto del municipio. Vigencia de tres años desde el día siguiente a la publicación de la resolución del Ministerio (29/07/2026). Gran tenedor: más de diez inmuebles o más de 1.500 m². Aplica la limitación del art. 17.7 de la LAU.
- [ ] `asturias-zona-tensionada-33025` (zona_tensionada, ES-03-33025, 2026-07-30 → 2029-07-30)
  - Cargado: `{"declared": true, "checked_through": "2026-07-29", "area": "Luanco"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Gozón: SOLO Luanco (Resolución de 21/05/2026, BOPA núm. 100, 27/05/2026, https://miprincipado.asturias.es/bopa/2026/05/27/2026-04318.pdf), no el resto del concejo. Vigencia de tres años desde el día siguiente a la publicación de la resolución del Ministerio (29/07/2026). Gran tenedor: más de diez inmuebles o más de 1.500 m². Aplica la limitación del art. 17.7 de la LAU.
- [ ] `asturias-zona-tensionada-33036` (zona_tensionada, ES-03-33036, 2026-07-30 → 2029-07-30)
  - Cargado: `{"declared": true, "checked_through": "2026-07-29", "area": "núcleos de Llanes, Posada de Llanes, Nueva, Poo, Barro y Celorio"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Llanes: SOLO los núcleos urbano de Llanes y de Posada de Llanes (Resoluciones de 24/04/2026 y 11/05/2026, mismas que Cabrales) y los de Nueva, Poo, Barro y Celorio (Resolución de 01/06/2026, BOPA núm. 109, 09/06/2026, https://miprincipado.asturias.es/bopa/2026/06/09/2026-04627.pdf), no el resto del concejo. Vigencia de tres años desde el día siguiente a la publicación de la resolución del Ministerio (29/07/2026). Gran tenedor: más de diez inmuebles o más de 1.500 m². Aplica la limitación del art. 17.7 de la LAU.
- [ ] `asturias-alquiler-turistico` (regimen_alquiler_turistico, ES-03, 2026-03-03 → sin fin)
  - Cargado: `{"regime": "Vivienda de uso turístico (en edificio de propiedad horizontal) y vivienda vacacional en Asturias (Decreto 48/2016): declaración responsable previa e inscripción en el Registro de Empresas y Actividades Turísticas", "requirements": [{"code": "declaracion-responsable", "description": "Dec…`
  - Fuente: https://miprincipado.asturias.es/bopa/2026/02/11/2026-01087.pdf
  - Nota: Decreto 4/2026 (BOPA núm. 28, 11/02/2026), arts. 1, 2, 3, 5, 7, 12, 13, 14, 15, 17, 27, 29, 30 y 31 del Decreto 48/2016. Fecha de inicio calculada: veinte días tras la publicación. Las viviendas ya inscritas tienen doce meses (arts. 7.2, 13.1.e, 13.4 y 13.5) o seis meses (resto) para adaptarse (disposición transitoria única). Se excluyen los arrendamientos por más de cuatro meses seguidos a un mismo arrendatario (art. 1.3).
- [ ] `oviedo-plusvalia-tipo` (tipo_plusvalia, ES-03-33044, 2025-01-01 → sin fin)
  - Cargado: `{"rate": 0.2}`
  - Fuente: https://www.oviedo.es/documents/35133/0d707f1c-50d5-4d05-a2e9-fd2436fb3f68
  - Nota: Ordenanza Fiscal nº 404 del Ayuntamiento de Oviedo, art. 12.1: «El tipo de gravamen del impuesto será del 20 por 100.» Disposición final: modificada por acuerdo del Pleno de 03/12/2024, en vigor el día de su publicación en el BOPA y de aplicación desde el 01/01/2025. No se ha leído el BOPA de publicación; hay fuentes divulgativas que dan el 26 % para Oviedo (guiafiscal.es), que contradicen la ordenanza oficial leída.

**Pendiente o dudoso:**
- ITP por tramos sobre TODO el valor (`whole_value: true`): 8 % hasta 300.000 €, 9 % hasta 500.000 € y 10 % por encima.
- Zonas tensionadas solo en parte de cinco concejos (Avilés, Cabrales, Gijón, Gozón y Llanes), desde el 30/07/2026: cada regla lleva `area` con los barrios o núcleos de su resolución del BOPA. Oviedo no está declarado.
- La escala y los mínimos de la Ley 3/2025 se aplican al periodo 2025 por la exposición de motivos, no por el articulado: confirmar.
- Plusvalía de Gijón: cargada con un tipo por años de tenencia (`gijon-plusvalia-tipo`); ver la sección final.
- Plusvalía de Oviedo: la ordenanza oficial dice 20 %; guiafiscal.es dice 26 %. No se ha leído el BOPA de publicación.
- El ITP del 20 % para grandes tenedores (art. 31 bis, desde el 03/12/2025) no se modela.
- La fecha de inicio del ITP y el AJD (2014-10-30) es la del texto refundido; los tipos pueden venir de antes.

## 3. Illes Balears (ES-04)

- [ ] `baleares-itp-inmuebles-2023` (impuesto_compra_segunda_mano, ES-04, 2023-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.08}, {"from": 400000, "rate": 0.09}, {"from": 600000, "rate": 0.1}, {"from": 1000000, "rate": 0.12}, {"from": 2000000, "rate": 0.13}]}`
  - Fuente: https://www.boe.es/eli/es-ib/dlg/2014/06/06/1/con
  - Nota: Decreto Legislativo 1/2014 de las Illes Balears, art. 10.a, redacción de la Ley 11/2022 (en vigor el 01/01/2023; el texto consolidado a 13/06/2026 no la cambia: la Ley 12/2023 y la Ley 4/2026 solo tocan las letras c y d): 8 % hasta 400.000 €; 9 % de 400.000,01 a 600.000 €; 10 % hasta 1.000.000 €; 12 % hasta 2.000.000 €; 13 % en adelante. Tarifa progresiva por tramos, no el tipo del tramo sobre todo el valor.
- [ ] `baleares-ajd-compra-vivienda-2023` (ajd_compra_vivienda, ES-04, 2023-01-01 → sin fin)
  - Cargado: `{"bands": [{"up_to": 999999.99, "rate": 0.015}, {"up_to": null, "rate": 0.02}], "cap_jumps": false}`
  - Fuente: https://www.boe.es/eli/es-ib/dlg/2014/06/06/1/con
  - Nota: Decreto Legislativo 1/2014 de las Illes Balears, art. 15 (1,5 %, redacción de la Ley 19/2019) y art. 17 bis (2 % si el valor real o declarado del inmueble es igual o superior a 1.000.000 €; añadido por la Ley 11/2022 y modificado por la Ley 12/2023 solo para excluir los derechos reales de garantía). La banda del 1,5 % llega hasta 999.999,99 € porque el 2 % se aplica desde 1.000.000 € inclusive.
- [ ] `baleares-irpf-escala-general-2015` (escala_irpf_general_autonomica, ES-04, 2015-12-31 → 2024-01-01)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.095}, {"from": 10000, "rate": 0.1175}, {"from": 18000, "rate": 0.1475}, {"from": 30000, "rate": 0.1775}, {"from": 48000, "rate": 0.1925}, {"from": 70000, "rate": 0.22}, {"from": 90000, "rate": 0.23}, {"from": 120000, "rate": 0.24}, {"from": 175000, "rate": 0.25}]}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2014-6925&tn=1&p=20230314
  - Nota: Decreto Legislativo 1/2014 de las Illes Balears, art. 1, redacción de la Ley 12/2015 (BOE-A-2016-824) leída en la versión consolidada vigente el 14/03/2023: 9,5 % hasta 10.000 €; 11,75 % hasta 18.000 €; 14,75 % hasta 30.000 €; 17,75 % hasta 48.000 €; 19,25 % hasta 70.000 €; 22 % hasta 90.000 €; 23 % hasta 120.000 €; 24 % hasta 175.000 €; 25 % en adelante. Sustituida por la Ley 12/2023 desde el 01/01/2024. Inicio tomado de los efectos desde el 31/12/2015 que declara la exposición de motivos de la Ley 12/2015.
- [ ] `baleares-irpf-escala-general-2024` (escala_irpf_general_autonomica, ES-04, 2024-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.09}, {"from": 10000, "rate": 0.1125}, {"from": 18000, "rate": 0.1425}, {"from": 30000, "rate": 0.175}, {"from": 48000, "rate": 0.19}, {"from": 70000, "rate": 0.2175}, {"from": 90000, "rate": 0.2275}, {"from": 120000, "rate": 0.2375}, {"from": 175000, "rate": 0.247…`
  - Fuente: https://www.boe.es/eli/es-ib/dlg/2014/06/06/1/con
  - Nota: Decreto Legislativo 1/2014 de las Illes Balears, art. 1, redacción de la Ley 12/2023, de 29 de diciembre (BOE-A-2024-1569, DF 2.1; entra en vigor el 01/01/2024): 9 % hasta 10.000 €; 11,25 % hasta 18.000 €; 14,25 % hasta 30.000 €; 17,5 % hasta 48.000 €; 19 % hasta 70.000 €; 21,75 % hasta 90.000 €; 22,75 % hasta 120.000 €; 23,75 % hasta 175.000 €; 24,75 % en adelante.
- [ ] `baleares-zonas-tensionadas` (zona_tensionada, ES-04, 2023-05-26 → sin fin)
  - Cargado: `{"declared": false, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Ley 12/2023, art. 18: la declaración corresponde a la comunidad autónoma; el Ministerio publica la relación cada trimestre.
- [ ] `baleares-alquiler-turistico-2025` (regimen_alquiler_turistico, ES-04, 2025-04-16 → 2026-06-14)
  - Cargado: `{"regime": "Comercialización de estancias turísticas en viviendas de uso residencial (Ley 8/2012, arts. 49 a 52): declaración responsable ante la administración turística insular, solo en zonas aptas, con plazas turísticas y sin nuevas declaraciones en viviendas en propiedad horizontal", "requiremen…`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2012-10610
  - Nota: Ley 8/2012, de 19 de julio, del turismo de las Illes Balears (BOE-A-2012-10610), texto consolidado a 13/06/2026, arts. 50 a 52; Decreto-ley 4/2025, de 11 de abril (BOE-A-2025-14462), DA 2.ª y DT 2.ª. Los apartados 2 y 20 del art. 50 vienen de la Ley 7/2024 y los apartados 12, 13 y 23 de la Ley 1/2025 y del Decreto-ley 4/2025. Redacción de los apartados anterior a 2025-04-16 y requisitos reglamentarios (Decreto 20/2015) no leídos. Cada isla tiene además su plan de intervención en ámbitos turísticos y su techo de plazas; no leídos.
- [ ] `baleares-alquiler-turistico-2026` (regimen_alquiler_turistico, ES-04, 2026-06-14 → sin fin)
  - Cargado: `{"regime": "Comercialización de estancias turísticas en viviendas de uso residencial (Ley 8/2012, arts. 49 a 52): declaración responsable ante la administración turística insular, solo en zonas aptas, con plazas turísticas y sin nuevas declaraciones en viviendas en propiedad horizontal", "requiremen…`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2026-15579
  - Nota: Ley 4/2026, de 11 de junio (BOE-A-2026-15579; BOIB núm. 74, 13/06/2026; en vigor al día siguiente), disposición final 22.ª, que modifica la DA 2.ª del Decreto-ley 4/2025. Resto: Ley 8/2012 (BOE-A-2012-10610), texto consolidado a 13/06/2026, arts. 50 a 52. Requisitos reglamentarios (Decreto 20/2015), planes insulares y techo de plazas por isla no leídos. Palma: el Ayuntamiento declara sus zonas aptas (art. 50.20); la prohibición municipal de nuevas plazas en todo el término (prensa, 28/05/2026) está pendiente de fuente oficial.
- [ ] `palma-plusvalia-tipo-2025` (tipo_plusvalia, ES-04-07040, 2025-01-01 → 2026-01-01)
  - Cargado: `{"rate": 0.215}`
  - Fuente: https://www.palma.es/documents/39058/12928460/Ordenanzas+fiscales+a%C3%B1o+en+curso.pdf/2f559a13-22ab-05ac-2e32-5e77464b66ea
  - Nota: Ordenanza fiscal del IIVTNU del Ayuntamiento de Palma, art. 8: «del 21,5% a partir del 1 de enero de 2025, y del 18% a partir del 1 de enero de 2026 y posteriores». Texto leído en el PDF «Ordenanzas fiscales y de precios públicos año 2026» de palma.es (publicada en el BOIB núm. 165 de 17/12/2024; el BOIB no se ha leído directamente).
- [ ] `palma-plusvalia-tipo-2026` (tipo_plusvalia, ES-04-07040, 2026-01-01 → sin fin)
  - Cargado: `{"rate": 0.18}`
  - Fuente: https://www.palma.es/documents/39058/12928460/Ordenanzas+fiscales+a%C3%B1o+en+curso.pdf/2f559a13-22ab-05ac-2e32-5e77464b66ea
  - Nota: Ordenanza fiscal del IIVTNU del Ayuntamiento de Palma, art. 8: «del 21,5% a partir del 1 de enero de 2025, y del 18% a partir del 1 de enero de 2026 y posteriores». Texto leído en el PDF «Ordenanzas fiscales y de precios públicos año 2026» de palma.es (publicada en el BOIB núm. 165 de 17/12/2024; el BOIB no se ha leído directamente). No se ha comprobado si el Pleno la modificó después para 2026 o 2027.

**Pendiente o dudoso:**
- ITP progresivo: 8 % hasta 400.000 €, 9 %, 10 %, 12 % y 13 % por encima de 2 M €. La ley aplica el tipo medio de la tarifa a todo el valor, que da la misma cuota salvo el redondeo del tipo medio a dos decimales.
- AJD: 1,5 %, y 2 % sobre todo el valor desde 1.000.000 € incluido (art. 17 bis).
- Turismo: la regla vigente desde el 14/06/2026 prohíbe nuevas declaraciones en edificios de propiedad horizontal, con las excepciones de la Ley 4/2026. La prohibición de Palma en todo el municipio (Pleno de 28/05/2026) solo se ha visto en prensa: sin regla.
- Plusvalía de Eivissa sin cargar: la sede prohíbe el acceso automático en su robots.txt y la web no enlaza la ordenanza.
- Plusvalía de Palma: 21,5 % en 2025 y 18 % desde 2026, leído en el PDF de palma.es, no en el BOIB. Antes de 2025, sin fuente.
- El agente hizo unas pocas descargas de caib.es/eboibfront antes de ver que su robots.txt lo prohíbe; no hizo más.
- Sin mínimos propios completos (el art. 2 solo sube un 10 % algunos importes estatales).

## 4. Cantabria (ES-06)

- [ ] `cantabria-itp-inmuebles-2018` (impuesto_compra_segunda_mano, ES-06, 2018-01-01 → 2024-01-01)
  - Cargado: `{"rate": 0.1}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOCT-c-2008-90028#a9
  - Nota: Decreto Legislativo 62/2008 de Cantabria, art. 9.1.A (Tipo general), versión en vigor el 01/01/2018 (Ley 9/2017, BOE-A-2018-856) hasta el 31/12/2023: «tipo del 10 por ciento» en la transmisión de bienes inmuebles y constitución y cesión de derechos reales salvo los de garantía. Tipo único sobre todo el valor (no por tramos). En 2016-2017 el tipo general era el 8 % (no se escribe: anterior a 2024).
- [ ] `cantabria-itp-inmuebles-2024` (impuesto_compra_segunda_mano, ES-06, 2024-01-01 → sin fin)
  - Cargado: `{"rate": 0.09}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOCT-c-2008-90028#a9
  - Nota: Decreto Legislativo 62/2008 de Cantabria, art. 9.1.A, redacción de la Ley 3/2023 (BOE-A-2024-1373, en vigor el 01/01/2024): «se aplicará el tipo del 9 por ciento». Tipo único sobre todo el valor (no por tramos): la escala 7 % hasta 300.000 € y 9 % por el exceso del art. 9.2 es solo para vivienda habitual. La Ley 5/2026 (BOE-A-2026-10431, en vigor el 01/05/2026) modificó los apartados 2, 3.c), 4 y 7 del art. 9, no el tipo general.
- [ ] `cantabria-ajd-compra-vivienda-2016` (ajd_compra_vivienda, ES-06, 2016-01-01 → sin fin)
  - Cargado: `{"bands": [{"up_to": null, "rate": 0.015}], "cap_jumps": false}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOCT-c-2008-90028#a13
  - Nota: Decreto Legislativo 62/2008 de Cantabria, art. 13.3 (redacción de la Ley 3/2023 desde el 01/01/2024; en las versiones de 2016 a 2023 también 1,5 %): primeras copias de escrituras y actas notariales inscribibles, no sujetas a Sucesiones y Donaciones ni a TPO/IVA, tributan además al 1,5 %. Persona jurídica: mismo tipo (no hay tipo propio). Vivienda habitual: 1 %, y 0,1 % con requisitos (art. 13.4), no aplicables a un inversor.
- [ ] `cantabria-irpf-escala-general-2016` (escala_irpf_general_autonomica, ES-06, 2016-01-01 → 2024-01-01)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.095}, {"from": 12450, "rate": 0.12}, {"from": 20200, "rate": 0.15}, {"from": 34000, "rate": 0.185}, {"from": 46000, "rate": 0.195}, {"from": 60000, "rate": 0.245}, {"from": 90000, "rate": 0.255}]}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOCT-c-2008-90028#a1
  - Nota: Decreto Legislativo 62/2008 de Cantabria, art. 1, redacción de la Ley 6/2015 (BOE-A-2016-478), versión vigente hasta el 31/12/2023: 9,5 % hasta 12.450 €; 12 % hasta 20.200 €; 15 % hasta 34.000 €; 18,5 % hasta 46.000 €; 19,5 % hasta 60.000 €; 24,5 % hasta 90.000 €; 25,5 % en adelante.
- [ ] `cantabria-irpf-escala-general-2024` (escala_irpf_general_autonomica, ES-06, 2024-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.085}, {"from": 13000, "rate": 0.11}, {"from": 21000, "rate": 0.145}, {"from": 35200, "rate": 0.18}, {"from": 60000, "rate": 0.225}, {"from": 90000, "rate": 0.245}]}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOCT-c-2008-90028#a1
  - Nota: Decreto Legislativo 62/2008 de Cantabria, art. 1, redacción de la Ley 3/2023 (BOE-A-2024-1373, en vigor el 01/01/2024): 8,5 % hasta 13.000 €; 11 % hasta 21.000 €; 14,5 % hasta 35.200 €; 18 % hasta 60.000 €; 22,5 % hasta 90.000 €; 24,5 % en adelante. El art. 1 no se ha modificado después (texto consolidado a 30/04/2026), por lo que rige también en 2025 y 2026.
- [ ] `cantabria-zonas-tensionadas` (zona_tensionada, ES-06, 2023-05-26 → sin fin)
  - Cargado: `{"declared": false, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Ley 12/2023, art. 18: la declaración corresponde a la comunidad autónoma; el Ministerio publica la relación cada trimestre.
- [ ] `cantabria-alquiler-turistico` (regimen_alquiler_turistico, ES-06, 2025-07-25 → sin fin)
  - Cargado: `{"regime": "Vivienda de uso turístico en Cantabria (Decreto 50/2025): declaración responsable ante la Dirección General de Turismo antes de iniciar la actividad, con inscripción de oficio en el Registro General de Empresas Turísticas de Cantabria", "requirements": [{"code": "declaracion-responsable"…`
  - Fuente: https://boc.cantabria.es/boces/verAnuncioAction.do?idAnuBlob=423179
  - Nota: Decreto 50/2025, de 24 de julio (BOC extraordinario núm. 15, 24/07/2025), arts. 1, 3, 4, 5 y 6; disposición final segunda (entrada en vigor al día siguiente de su publicación). Disposición transitoria única: las viviendas ya inscritas o con declaración anterior al 03/04/2025 quedan exentas del art. 6.1.d (aprobación de la comunidad) y deben presentar el Anexo V en 8 meses. Pendiente comprobar modificaciones posteriores al 24/07/2025.
- [ ] `santander-plusvalia-tipo` (tipo_plusvalia, ES-06-39075, 2022-05-10 → sin fin)
  - Cargado: `{"rate": 0.21}`
  - Fuente: https://www.santander.es/system/files/5i_-_iivtnu_2026.pdf
  - Nota: Ordenanza Fiscal nº 5-I del Ayuntamiento de Santander (texto del ejercicio 2026 publicado en santander.es; Pleno de 24/02/2022, BOC núm. 88 de 09/05/2022), art. 6: «el tipo único del 21 por l00». Disposición final segunda: efectos desde el día siguiente a su publicación definitiva (10/05/2022). No se ha leído el BOC de la aprobación del tipo ni el de modificaciones posteriores; webs no oficiales hablan de un 28 %, que no coincide con la ordenanza leída.
- [ ] `torrelavega-plusvalia-tipo` (tipo_plusvalia, ES-06-39087, 2022-06-02 → sin fin)
  - Cargado: `{"rate": 0.3}`
  - Fuente: https://boc.cantabria.es/boces/verAnuncioAction.do?idAnuBlob=372719
  - Nota: Ordenanza Fiscal reguladora del IIVTNU del Ayuntamiento de Torrelavega (aprobación definitiva, BOC núm. 106 de 02/06/2022, CVE-2022-4145), art. 12.1: «El tipo de gravamen del Impuesto será el 30 por ciento». Entra en vigor en el momento de su publicación íntegra en el BOC. La modificación de ordenanzas para 2024 (BOC 27/12/2023, CVE-2023-10867) no toca este impuesto; no se han leído las de 2025 y 2026.

**Pendiente o dudoso:**
- ITP: 10 % de 2018 a 2023 y 9 % desde 2024 (Ley 3/2023), tipo único. Que el 10 % rija desde 2018-01-01 sale del consolidado; no se ha leído la disposición final de la Ley 9/2017. El 8 % de 2016–2017 no se ha cargado.
- Sin mínimos propios.
- Plusvalía de Santander: 21 % del texto de la ordenanza de 2026; webs no oficiales dicen 28 %. La fecha de inicio (2022-05-10) se deduce del BOC n.º 88 de 2022.
- Plusvalía de Torrelavega: no se han comprobado modificaciones de 2025 y 2026.
- Turismo: Decreto 50/2025; falta el régimen urbanístico de Santander y Torrelavega y comprobar cambios posteriores al 24/07/2025.

## 5. Extremadura (ES-11)

- [ ] `extremadura-itp-inmuebles-2018` (impuesto_compra_segunda_mano, ES-11, 2018-05-24 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.08}, {"from": 360000, "rate": 0.1}, {"from": 600000, "rate": 0.11}]}`
  - Fuente: https://www.boe.es/eli/es-ex/dlg/2018/04/10/1/con
  - Nota: Decreto Legislativo 1/2018, de 10 de abril, de Extremadura (BOE-A-2018-8159), art. 36: tarifa progresiva, 8 % hasta 360.000 €, 10 % entre 360.000,01 y 600.000 € y 11 % por encima; el apartado 2 dice que la cuota es la suma de las cuotas de cada escalón con su tipo propio, es decir, PROGRESIVA por porción (no whole_value).
- [ ] `extremadura-ajd-compra-vivienda-2018` (ajd_compra_vivienda, ES-11, 2018-05-24 → sin fin)
  - Cargado: `{"bands": [{"up_to": null, "rate": 0.015}], "cap_jumps": false}`
  - Fuente: https://www.boe.es/eli/es-ex/dlg/2018/04/10/1/con
  - Nota: Decreto Legislativo 1/2018 de Extremadura, art. 46: «tipo general del 1,50 %» en las primeras copias de escrituras y actas notariales sujetas como Documentos Notariales. Persona jurídica: mismo tipo (no hay tipo propio). Texto idéntico en las versiones consolidadas de 2018 a 2026 (la Ley 2/2026 no toca el art. 46).
- [ ] `extremadura-irpf-escala-general-2023` (escala_irpf_general_autonomica, ES-11, 2023-01-01 → 2026-01-01)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.08}, {"from": 12450, "rate": 0.1}, {"from": 20200, "rate": 0.16}, {"from": 24200, "rate": 0.175}, {"from": 35200, "rate": 0.21}, {"from": 60000, "rate": 0.235}, {"from": 80200, "rate": 0.24}, {"from": 99200, "rate": 0.245}, {"from": 120200, "rate": 0.25}]}`
  - Fuente: https://www.boe.es/eli/es-ex/dl/2023/09/12/4
  - Nota: Decreto Legislativo 1/2018, art. 1, redacción del Decreto-ley 4/2023 (BOE-A-2023-21669; efectos 01/01/2023). Tipos y tramos leídos en la versión consolidada de 15/09/2023 a 07/04/2025, idéntica en la escala. Hasta el 31/12/2022 el primer tramo era 9,5 % y el segundo 12,5 %.
- [ ] `extremadura-irpf-escala-general-2026` (escala_irpf_general_autonomica, ES-11, 2026-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.0775}, {"from": 12450, "rate": 0.0975}, {"from": 20200, "rate": 0.16}, {"from": 24200, "rate": 0.175}, {"from": 35200, "rate": 0.21}, {"from": 60000, "rate": 0.235}, {"from": 80200, "rate": 0.24}, {"from": 99200, "rate": 0.245}, {"from": 120200, "rate": 0.25}]}`
  - Fuente: https://www.boe.es/eli/es-ex/l/2026/08/03/2
  - Nota: Ley 2/2026, de 3 de agosto, de Presupuestos Generales de Extremadura para 2026 (BOE-A-2026-17839), disposición final segunda, apartado uno (art. 1 del Decreto Legislativo 1/2018): 7,75 % hasta 12.450 €; 9,75 % hasta 20.200 €; 16 % hasta 24.200 €; 17,5 % hasta 35.200 €; 21 % hasta 60.000 €; 23,5 % hasta 80.200 €; 24 % hasta 99.200 €; 24,5 % hasta 120.200 €; 25 % en adelante. El proyecto de presupuestos de 2027 (no aprobado) propondría bajar de nuevo los dos primeros tramos; no se ha leído.
- [ ] `extremadura-zonas-tensionadas` (zona_tensionada, ES-11, 2023-05-26 → sin fin)
  - Cargado: `{"declared": false, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Ley 12/2023, art. 18: la declaración corresponde a la comunidad autónoma; el Ministerio publica la relación cada trimestre. Resolución de 24/07/2026 de la Secretaría de Estado de Vivienda y Agenda Urbana (segundo trimestre de 2026).
- [ ] `extremadura-alquiler-turistico` (regimen_alquiler_turistico, ES-11, 2012-09-14 → sin fin)
  - Cargado: `{"regime": "Apartamento turístico en Extremadura (Decreto 182/2012): declaración responsable ante la Dirección General de Turismo e inscripción de oficio en el Registro General de Empresas y Actividades Turísticas", "requirements": [{"code": "declaracion-responsable", "description": "Declaración res…`
  - Fuente: https://www.juntaex.es/w/5826
  - Nota: Requisitos tal como los publica la sede de la Junta (ficha actualizada el 13/10/2026). Decreto 182/2012, de 7 de septiembre (DOE núm. 178, 13/09/2012; en vigor al día siguiente, de ahí el inicio). La ficha no menciona expresamente «viviendas de uso turístico»: por verificar con la Dirección General de Turismo si una vivienda particular encaja siempre en el trámite de apartamento turístico. No se han leído los requisitos técnicos de clasificación por categorías del decreto.
- [ ] `badajoz-plusvalia-tipo` (tipo_plusvalia, ES-11-06015, 2022-07-01 → sin fin)
  - Cargado: `{"rate": 0.2574}`
  - Fuente: https://www.aytobadajoz.es/files/archivos/ayto/2026_10/ordenanzas-fiscales-2026.pdf
  - Nota: Ordenanza Fiscal reguladora del IIVTNU del Ayuntamiento de Badajoz, art. 7.1: «El tipo de gravamen del Impuesto es del 25,74 (veinticinco con setenta y cuatro) por ciento.» Leída en la compilación de ordenanzas fiscales firmada el 06/10/2026. La disposición final dice que entra en vigor el día de su publicación en el BOP; la fecha de inicio 01/07/2022 procede de un sitio secundario (guiafiscal.es) y no se ha comprobado en el BOP.
- [ ] `caceres-plusvalia-tipo` (tipo_plusvalia, ES-11-10037, 2022-07-21 → sin fin)
  - Cargado: `{"rate": 0.3}`
  - Fuente: https://www.ayto-caceres.es/publicaciones/ordenanzas/ordenanzas-fiscales/ordenanza-fiscal-reguladora-del-impuesto-sobre-el-incremento-del-valor-de-los-terrenos-de-naturaleza-urbana/?download=90729
  - Nota: Ordenanza Fiscal reguladora del IIVTNU del Ayuntamiento de Cáceres, art. 8.1: «El tipo de gravamen del Impuesto es del 30 %.» Leída en la sede municipal el 2026-11-03. La disposición final fija la entrada en vigor el día siguiente a la publicación en el BOP de Cáceres, cuya fecha no se ha encontrado: la fecha de inicio 2022-07-21 es la del Pleno (cota inferior); el tipo del 30 % puede venir de antes (por verificar).

**Pendiente o dudoso:**
- ITP progresivo: 8 % hasta 360.000 €, 10 % hasta 600.000 € y 11 % por encima (art. 36.2: la cuota es la suma de cada escalón).
- Escala del IRPF: 2023–2025 y la de 2026 (Ley 2/2026), que baja los dos primeros tramos al 7,75 % y al 9,75 %. La de 2023 se ha leído en el consolidado, no en el decreto-ley.
- Sin mínimos propios.
- Turismo: no hay decreto de vivienda de uso turístico; la regla trata la vivienda como apartamento turístico (Decreto 182/2012), y eso hay que confirmarlo con la Dirección General de Turismo.
- Plusvalía de Badajoz (25,74 %): fecha de inicio 2022-07-01 por fuente secundaria. Cáceres (30 %): 2022-07-21, fecha del Pleno; el tipo puede ser anterior.
- Zona tensionada: solo se han leído las dos resoluciones de 2026.

## 6. La Rioja (ES-17)

- [ ] `la-rioja-itp-inmuebles-2017` (impuesto_compra_segunda_mano, ES-17, 2017-10-31 → sin fin)
  - Cargado: `{"rate": 0.07}`
  - Fuente: https://www.boe.es/eli/es-ri/l/2017/10/27/10/con
  - Nota: Ley 10/2017, de 27 de octubre, de La Rioja (BOE-A-2017-13750), art. 44.1: tipo del 7 % en las transmisiones de bienes inmuebles y en la constitución y cesión de derechos reales sobre ellos, salvo los de garantía. Tipo único sobre toda la base liquidable, sin tramos. Fecha de inicio = entrada en vigor de la ley consolidadora (31/10/2017); el 7 % puede venir de normas anteriores que la ley consolida (por verificar).
- [ ] `la-rioja-ajd-compra-vivienda-2017` (ajd_compra_vivienda, ES-17, 2017-10-31 → sin fin)
  - Cargado: `{"bands": [{"up_to": null, "rate": 0.01}], "cap_jumps": false}`
  - Fuente: https://www.boe.es/eli/es-ri/l/2017/10/27/10/con
  - Nota: Ley 10/2017 de La Rioja, art. 48: las primeras copias de escrituras con cantidad o cosa valuable, inscribibles y no sujetas a Sucesiones y Donaciones ni a los números 1 y 2 del art. 1 del TRLITPAJD, tributan además de la cuota fija al 1 %. No incluye el 0,1 % de vivienda habitual de determinados sujetos pasivos (art. 49) ni el 1,5 % cuando se renuncia a la exención del IVA (art. 52, no aplica a vivienda nueva con IVA). Persona jurídica: mismo tipo (no hay tipo propio). Fecha de inicio como en el ITP (por verificar).
- [ ] `la-rioja-irpf-escala-general-2018` (escala_irpf_general_autonomica, ES-17, 2018-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.08}, {"from": 12450, "rate": 0.106}, {"from": 20200, "rate": 0.136}, {"from": 35200, "rate": 0.178}, {"from": 40000, "rate": 0.183}, {"from": 50000, "rate": 0.19}, {"from": 60000, "rate": 0.245}, {"from": 120000, "rate": 0.27}]}`
  - Fuente: https://www.boe.es/eli/es-ri/l/2017/10/27/10/con
  - Nota: Ley 10/2017 de La Rioja, art. 31 (texto consolidado a 29/10/2026): 8 % hasta 12.450 €; 10,6 % hasta 20.200 €; 13,6 % hasta 35.200 €; 17,8 % hasta 40.000 €; 18,3 % hasta 50.000 €; 19 % hasta 60.000 €; 24,5 % hasta 120.000 €; 27 % en adelante. El art. 31 ter prevé deflactarla si el IPC de La Rioja de diciembre supera el 3 %, mediante proyecto de ley que no consta aplicado. Fecha de inicio = primer periodo impositivo tras la entrada en vigor de la ley consolidadora; la misma escala puede venir de antes (por verificar).
- [ ] `la-rioja-zonas-tensionadas` (zona_tensionada, ES-17, 2023-05-26 → sin fin)
  - Cargado: `{"declared": false, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Ley 12/2023, art. 18: la declaración corresponde a la comunidad autónoma; el Ministerio publica la relación cada trimestre.
- [ ] `la-rioja-alquiler-turistico` (regimen_alquiler_turistico, ES-17, 2018-12-01 → sin fin)
  - Cargado: `{"regime": "Vivienda de uso turístico en La Rioja (Decreto 10/2017): comunicación de inicio de actividad a la Dirección General de Turismo e inscripción en el Registro de Proveedores de Servicios Turísticos; sin licencia autonómica", "requirements": [{"code": "comunicacion-inicio", "description": "C…`
  - Fuente: https://ias1.larioja.org/boletin/Bor_Boletin_visor_Servlet?referencia=8916193-1-PDF-520959-X
  - Nota: Redacción del Decreto 10/2017 según el Decreto 40/2018 (BOR núm. 141, 30/11/2018; disposición final: en vigor el día siguiente). No se ha leído el Decreto 15/2021 (BOR 2021, en vigor 20/02/2021), que también modifica el Decreto 10/2017; no consta que toque estos artículos. Pendiente comprobar el texto consolidado vigente y la ordenanza o plan municipal de Logroño.
- [ ] `logrono-plusvalia-tipo` (tipo_plusvalia, ES-17-26089, 2026-01-01 → sin fin)
  - Cargado: `{"rate": 0.3}`
  - Fuente: https://logrono.es/documents/20121/1744171/ORDENANZAS+FISCALES+2026.pdf/156442a9-310a-e851-95da-3d66209b8ab6?t=1772784854868
  - Nota: Ordenanza Fiscal reguladora del Impuesto sobre el Incremento del Valor de los Terrenos de Naturaleza Urbana del Ayuntamiento de Logroño, art. 7.1: «El tipo impositivo será del 30 por 100.» Texto íntegro de las ordenanzas fiscales actualizadas a 1 de enero de 2026 (modificaciones publicadas en el BOR núm. 250, 26/12/2025, y núm. 252, 30/12/2025). Fecha de inicio = ejercicio 2026 (primer texto leído); el 30 % puede venir de antes (por verificar). Código INE 26089 comprobado en el diccionario de municipios del INE 2026.

**Pendiente o dudoso:**
- ITP: 7 %, tipo único.
- Sin mínimos propios (solo sube un 10 % el mínimo por discapacidad de descendientes).
- Las fechas de inicio son las de la Ley 10/2017; los valores pueden ser anteriores.
- Turismo: no se ha leído el Decreto 15/2021, que también modifica el Decreto 10/2017. El régimen municipal de Logroño (licencia previa y moratoria, según la prensa) no se ha leído en fuente oficial.

## 7. Plusvalía con un tipo por años de tenencia

`tipo_plusvalia` admite ahora `by_years`: un tipo por periodo de generación (TRLRHL, art. 108.1).

- [ ] `gijon-plusvalia-tipo` (tipo_plusvalia, ES-03-33024, 2022-05-11 → sin fin)
  - Cargado: 25 % de 0 a 5 años, 22 % de 6 a 19 y 18 % desde 20.
  - Fuente: https://drupal.gijon.es/sites/default/files/2026-02/ORDENANZAS%202026_1.pdf (Ordenanza 1.03, art. 8.1, págs. 83–84)
  - Dudoso: no se ha localizado el BOPA que publicó la modificación del Pleno de 10/05/2022; la fecha de inicio es una cota inferior.
- [ ] `toledo-plusvalia-tipo` (tipo_plusvalia, ES-08-45168, 2022-03-12 → sin fin)
  - Cargado: 29,88 % de 0 a 5 años, 28,88 % de 6 a 10, 26,89 % de 11 a 15 y 25,90 % de 16 en adelante.
  - Fuente: https://www.toledo.es/wp-content/uploads/2016/11/of-no-02-impuesto-sobre-el-incremento-del-valor-de-los-terrenos-de-naturaleza-urbana-2024.pdf (Ordenanza n.º 2, art. 11)
  - Dudoso: la fecha de inicio supone el BOP de Toledo n.º 49 de 11/03/2022. El agente lo descargó antes de ver que el robots.txt del BOP lo prohíbe; lo borró y no lo usó. Hay que confirmarla a mano, igual que si hubo cambios después.
- Guadalajara: el tipo viene ahora del libro de Hacienda (`plusvalia_hacienda.yaml`, ADR-0044): 30 % hasta 18 años, 25 % a los 19 y 18 % desde 20. guadalajara.es bloquea a los agentes de Anthropic en su robots.txt; el agente descargó la ordenanza con curl y no se ha usado. Para contrastarla a mano: Ordenanza fiscal n.º 7, art. 11, https://www.guadalajara.es/recursos/doc/portal/2023/12/28/07-ordenanza-fiscal-reguladora-del-impuesto-sobre-el-incremento-del-valor-de-los90546.pdf

## 8. Contraste con el libro de Hacienda de 2026 (ADR-0044)

Las 25 reglas de plusvalía leídas en ordenanzas (tandas 6 a 8) coinciden con el libro de Hacienda de 2026, incluidos los tipos por años de Gijón y Toledo. Huesca (tipo 0, ordenanza derogada) no figura entre los municipios con el impuesto, como se esperaba.

## 9. Ceuta (ES-18) y Melilla (ES-19)

Cargadas con las bonificaciones de la cuota y la deducción del IRPF como reglas propias (ADR-0045).

- [ ] `ceuta-itp-inmuebles-2002` (impuesto_compra_segunda_mano, ES-18, 2002-01-01 → sin fin)
  - Cargado: `{"rate": 0.06}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-1993-25359#a11
  - Nota: Real Decreto Legislativo 1/1993 (TRLITPAJD), art. 11.1.a, redacción de la Ley 21/2001 (en vigor desde 01/01/2002): tipo supletorio del 6 % a la transmisión de inmuebles, único para todo el valor (no por tramos). BONIFICACIÓN (regla aparte, ADR-0045): art. 57 bis.3.a (añadido por la Ley 53/2002, en vigor desde 01/01/2003), las cuotas de TPO tienen derecho a una bonificación del 50 % en las «transmisiones y arrendamiento de inmuebles situados en Ceuta o Melilla»; tipo efectivo del 3 %.
- [ ] `melilla-itp-inmuebles-2002` (impuesto_compra_segunda_mano, ES-19, 2002-01-01 → sin fin)
  - Cargado: `{"rate": 0.06}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-1993-25359#a11
  - Nota: Real Decreto Legislativo 1/1993 (TRLITPAJD), art. 11.1.a, redacción de la Ley 21/2001 (en vigor desde 01/01/2002): tipo supletorio del 6 % a la transmisión de inmuebles, único para todo el valor (no por tramos). BONIFICACIÓN (regla aparte, ADR-0045): art. 57 bis.3.a (añadido por la Ley 53/2002, en vigor desde 01/01/2003), las cuotas de TPO tienen derecho a una bonificación del 50 % en las «transmisiones y arrendamiento de inmuebles situados en Ceuta o Melilla»; tipo efectivo del 3 %.
- [ ] `ceuta-ajd-compra-vivienda-2003` (ajd_compra_vivienda, ES-18, 2003-01-01 → sin fin)
  - Cargado: `{"bands": [{"up_to": null, "rate": 0.005}], "cap_jumps": false, "legal_person_rate": 0.005}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-1993-25359#a31
  - Nota: Real Decreto Legislativo 1/1993 (TRLITPAJD), art. 31.2, redacción de la Ley 53/2002 (en vigor desde 01/01/2003): tipo supletorio del 0,50 % sobre todo el valor en las primeras copias de escrituras con cantidad o cosa valuable. BONIFICACIÓN (regla aparte, ADR-0045): art. 57 bis.1, «la cuota gradual de documentos notariales [...] se bonificará en un 50 por 100 cuando el Registro en el que se deba proceder a la inscripción o anotación de los bienes o actos radique en Ceuta o Melilla»; tipo efectivo del 0,25 %. Por verificar si la primera entrega sujeta a IPSI (no a IVA) tributa por AJD o por TPO (arts. 7.5 y 31.2 hablan de IVA).
- [ ] `melilla-ajd-compra-vivienda-2003` (ajd_compra_vivienda, ES-19, 2003-01-01 → sin fin)
  - Cargado: `{"bands": [{"up_to": null, "rate": 0.005}], "cap_jumps": false, "legal_person_rate": 0.005}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-1993-25359#a31
  - Nota: Real Decreto Legislativo 1/1993 (TRLITPAJD), art. 31.2, redacción de la Ley 53/2002 (en vigor desde 01/01/2003): tipo supletorio del 0,50 % sobre todo el valor en las primeras copias de escrituras con cantidad o cosa valuable. BONIFICACIÓN (regla aparte, ADR-0045): art. 57 bis.1, «la cuota gradual de documentos notariales [...] se bonificará en un 50 por 100 cuando el Registro en el que se deba proceder a la inscripción o anotación de los bienes o actos radique en Ceuta o Melilla»; tipo efectivo del 0,25 %. Por verificar si la primera entrega sujeta a IPSI (no a IVA) tributa por AJD o por TPO (arts. 7.5 y 31.2 hablan de IVA).
- [ ] `ceuta-ipsi-vivienda-nueva-2019` (iva_vivienda_nueva, ES-18, 2019-01-30 → sin fin)
  - Cargado: `{"rate": 0.04}`
  - Fuente: https://www.2006.isotools.org/centros/27/gdocumental/l30_a51_c1/4._ORDENANZA_FISCAL_REGULADORA_IPSI_-_2024_reformado.pdf
  - Nota: ESTO ES IPSI, NO IVA. Ordenanza del IPSI de la Ciudad Autónoma de Ceuta, art. 33.Tres: «La construcción y primera transmisión de bienes inmuebles, así como la ejecución de obra inmobiliaria, tributarán con carácter general al tipo del 4 %», con las excepciones de la transmisión de viviendas de protección oficial de régimen especial o de promoción pública (2 %) y de las obras públicas con el sector público (10 %); ninguna aplica a un inversor. Texto consolidado publicado en la sede tributaria de la Ciudad (tributosceuta.org), con modificaciones hasta 2024; el art. 33.Tres no cambia desde el texto refundido del BOCCE de 30/01/2019 (fecha de inicio tomada de esa publicación; la entrada en vigor y el origen del 4 % por verificar).
- [ ] `melilla-ipsi-vivienda-nueva-2021` (iva_vivienda_nueva, ES-19, 2021-05-05 → sin fin)
  - Cargado: `{"rate": 0.04}`
  - Fuente: https://bomemelilla.es/bome/descargar/BOME-P-2021-1300.pdf
  - Nota: ESTO ES IPSI, NO IVA. Ordenanza del IPSI (operaciones interiores) de la Ciudad Autónoma de Melilla, anexo 1, apartado tercero, redacción del Decreto 584 de 30/04/2021 (BOME núm. 5857, 04/05/2021; entra en vigor al día siguiente de su publicación): «La entrega de Bienes Inmuebles, tributarán al tipo del 4 %», salvo la primera transmisión de viviendas de protección oficial por el promotor (0,5 %) y la construcción y ejecución de obras (10 %, con excepciones del 0,5 % y del 4 %); ninguna aplica a la primera entrega de vivienda libre a un inversor. El mismo 4 % figura ya en el texto del BOME núm. 5625 (12/02/2019).
- [ ] `ceuta-irpf-escala-general-2015` (escala_irpf_general_autonomica, ES-18, 2015-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.095}, {"from": 12450, "rate": 0.12}, {"from": 20200, "rate": 0.15}, {"from": 35200, "rate": 0.185}, {"from": 60000, "rate": 0.225}]}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764#a65
  - Nota: Ley 35/2006, disposición adicional 32.ª (añadida por la Ley 2/2011, modificada por el RDL 9/2015 con efectos 01/01/2015): «La escala autonómica aplicable a los contribuyentes que tengan su residencia habitual en Ceuta o Melilla será la prevista en el artículo 65». Art. 65, redacción de la Ley 26/2014 (en vigor desde 01/01/2015): 9,5 % hasta 12.450 €; 12 % hasta 20.200 €; 15 % hasta 35.200 €; 18,5 % hasta 60.000 €; 22,5 % en adelante. DEDUCCIÓN (regla aparte, ADR-0045): art. 68.4.1.º, el 60 % de la parte de la suma de las cuotas íntegras estatal y autonómica que corresponda a rentas obtenidas en Ceuta o Melilla, con residencia habitual y efectiva allí. No hay mínimos propios (rigen los estatales).
- [ ] `melilla-irpf-escala-general-2015` (escala_irpf_general_autonomica, ES-19, 2015-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.095}, {"from": 12450, "rate": 0.12}, {"from": 20200, "rate": 0.15}, {"from": 35200, "rate": 0.185}, {"from": 60000, "rate": 0.225}]}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764#a65
  - Nota: Ley 35/2006, disposición adicional 32.ª (añadida por la Ley 2/2011, modificada por el RDL 9/2015 con efectos 01/01/2015): «La escala autonómica aplicable a los contribuyentes que tengan su residencia habitual en Ceuta o Melilla será la prevista en el artículo 65». Art. 65, redacción de la Ley 26/2014 (en vigor desde 01/01/2015): 9,5 % hasta 12.450 €; 12 % hasta 20.200 €; 15 % hasta 35.200 €; 18,5 % hasta 60.000 €; 22,5 % en adelante. DEDUCCIÓN (regla aparte, ADR-0045): art. 68.4.1.º, el 60 % de la parte de la suma de las cuotas íntegras estatal y autonómica que corresponda a rentas obtenidas en Ceuta o Melilla, con residencia habitual y efectiva allí. No hay mínimos propios (rigen los estatales).
- [ ] `ceuta-zonas-tensionadas` (zona_tensionada, ES-18, 2023-05-26 → sin fin)
  - Cargado: `{"declared": false, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Ley 12/2023, art. 18: la declaración corresponde a la comunidad autónoma (aquí, a la Ciudad con Estatuto de Autonomía); el Ministerio publica la relación cada trimestre. Ceuta no aparece en ninguna de las nueve resoluciones leídas.
- [ ] `melilla-zonas-tensionadas` (zona_tensionada, ES-19, 2023-05-26 → sin fin)
  - Cargado: `{"declared": false, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Ley 12/2023, art. 18: la declaración corresponde a la comunidad autónoma (aquí, a la Ciudad con Estatuto de Autonomía); el Ministerio publica la relación cada trimestre. Melilla no aparece en ninguna de las nueve resoluciones leídas.
- [ ] `ceuta-alquiler-turistico` (regimen_alquiler_turistico, ES-18, 2025-06-28 → sin fin)
  - Cargado: `{"regime": "Alquiler turístico de corta duración en Ceuta: código de registro asignado por la Consejería de Comercio, Turismo, Empleo y Deporte, requisito imprescindible para ejercer la actividad (Decreto 1/2025)", "requirements": [{"code": "codigo-de-registro", "description": "Asignación previa del…`
  - Fuente: https://www.ceuta.es/ceuta/component/jdownloads/finish/1956-junio/22846-bocce-6525-27-06-2025?Itemid=534
  - Nota: Decreto 1/2025, de 17 de junio, del Consejo de Gobierno de la Ciudad Autónoma de Ceuta, en aplicación del Real Decreto 1312/2024, de 23 de diciembre (BOCCE núm. 6525, 27/06/2025, anuncio 388); disposición final única: entra en vigor al día siguiente de su publicación. El decreto dice que el registro está «habilitado provisionalmente». Faltan los requisitos materiales de la vivienda de uso turístico (el Reglamento de Turismo de 2010 solo regula apartamentos en el texto leído) y la situación del Real Decreto 1312/2024.
- [ ] `ceuta-plusvalia-tipo` (tipo_plusvalia, ES-18-51001, 2022-05-25 → sin fin)
  - Cargado: `{"rate": 0.27}`
  - Fuente: http://www.2006.isotools.org/centros/27/gdocumental/l25_a46_c3/IMPUESTO_SOBRE_EL_INCREMENTO_DEL_VALOR_DE_LOS_TERRENOS_DE_NATURALEZA_URBANA_2022.pdf
  - Nota: Ordenanza del IIVTNU de la Ciudad de Ceuta, art. 8.º: «La cuota de este Impuesto será el resultado de aplicar a la base imponible el tipo impositivo del 27 por 100». Texto íntegro adaptado al RDL 26/2021 (BOCCE de 24/05/2022, aprobado por el Pleno el 28/02/2022; entra en vigor al día siguiente de su publicación), enlazado desde tributosceuta.org. BONIFICACIÓN (regla aparte, ADR-0045): art. 9.º.1, «las cuotas tributarias de este Impuesto serán objeto de una bonificación del 50 por 100» (TRLRHL, art. 159.2); además, 95 % en transmisiones mortis causa a familiares (art. 9.º.2). Fecha de inicio calculada a partir del BOCCE de 24/05/2022 (por verificar).
- [ ] `melilla-plusvalia-tipo` (tipo_plusvalia, ES-19-52001, 2022-05-07 → sin fin)
  - Cargado: `{"rate": 0.29}`
  - Fuente: https://bomemelilla.es/bome/descargar/BOME-P-2022-1374.pdf
  - Nota: Ordenanza del IIVTNU de la Ciudad Autónoma de Melilla, art. 9: «La cuota de este impuesto será la resultante de aplicar a la Base imponible el tipo de gravamen del 29 %». Texto íntegro publicado por el Decreto 450 de 29/04/2022 (BOME núm. 5962, 06/05/2022); su disposición final fija la entrada en vigor al día siguiente de la publicación y deroga la ordenanza del BOME de 06/05/2014. La ordenanza no recoge el 50 % del TRLRHL, art. 159.2 (BONIFICACIÓN EN REGLA APARTEDA, aplicable por ley a los impuestos municipales de Melilla); su art. 10 solo da el 95 % en transmisiones mortis causa. Una orden de 2025 (BOME núm. 6246) solo actualiza coeficientes.
- [ ] `ceuta-bonificacion-itp` (bonificacion_itp, ES-18, 2003-01-01 → sin fin)
  - Cargado: `{"rate": 0.5}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-1993-25359#a57bis
  - Nota: TRLITPAJD, art. 57 bis.3.a): las cuotas de transmisiones patrimoniales onerosas «tendrán derecho a la aplicación de una bonificación del 50 por 100» en las «transmisiones y arrendamiento de inmuebles situados en Ceuta o Melilla». Añadido por el art. 5.5 de la Ley 53/2002, en vigor a partir del 01/01/2003 (nota del texto consolidado del BOE).
- [ ] `ceuta-bonificacion-ajd` (bonificacion_ajd, ES-18, 2003-01-01 → sin fin)
  - Cargado: `{"rate": 0.5}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-1993-25359#a57bis
  - Nota: TRLITPAJD, art. 57 bis.1: «La cuota gradual de documentos notariales del gravamen de actos jurídicos documentados se bonificará en un 50 por 100 cuando el Registro en el que se deba proceder a la inscripción o anotación de los bienes o actos radique en Ceuta o Melilla». Se aplica por el territorio del inmueble, cuyo Registro está en la ciudad. Añadido por la Ley 53/2002, en vigor a partir del 01/01/2003.
- [ ] `ceuta-bonificacion-ibi` (bonificacion_ibi, ES-18, 2004-03-10 → sin fin)
  - Cargado: `{"rate": 0.5}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2004-4214#a159
  - Nota: TRLRHL, art. 159.2: «Las cuotas tributarias correspondientes a los impuestos municipales regulados en esta ley serán objeto de una bonificación del 50 por ciento». Fecha de inicio: entrada en vigor del texto refundido (RDLeg 2/2004); la bonificación puede venir de antes.
- [ ] `ceuta-bonificacion-plusvalia` (bonificacion_plusvalia, ES-18, 2004-03-10 → sin fin)
  - Cargado: `{"rate": 0.5}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2004-4214#a159
  - Nota: TRLRHL, art. 159.2: bonificación del 50 % de las cuotas de los impuestos municipales, la plusvalía entre ellos. Fecha de inicio: entrada en vigor del texto refundido; la bonificación puede venir de antes.
- [ ] `ceuta-deduccion-irpf-rentas` (deduccion_irpf_rentas_territorio, ES-18, 2018-01-01 → sin fin)
  - Cargado: `{"rate": 0.6}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764#a68
  - Nota: Ley 35/2006 del IRPF, art. 68.4: el contribuyente, resida o no en Ceuta (1.º y 2.º), «se deducirá el 60 por ciento de la parte de la suma de las cuotas íntegras estatal y autonómica que proporcionalmente corresponda» a las rentas obtenidas allí, entre ellas los rendimientos de inmuebles situados en la ciudad (3.º.b) y las ganancias patrimoniales que procedan de ellos (3.º.d). Apartados 4.1 y 4.2 en la redacción de la Ley 6/2018, con efectos desde el 01/01/2018. El motor aplica la proporción de la renta del inmueble en la base y supone que el resto de la base se obtiene fuera de la ciudad (ADR-0045).
- [ ] `melilla-bonificacion-itp` (bonificacion_itp, ES-19, 2003-01-01 → sin fin)
  - Cargado: `{"rate": 0.5}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-1993-25359#a57bis
  - Nota: TRLITPAJD, art. 57 bis.3.a): las cuotas de transmisiones patrimoniales onerosas «tendrán derecho a la aplicación de una bonificación del 50 por 100» en las «transmisiones y arrendamiento de inmuebles situados en Ceuta o Melilla». Añadido por el art. 5.5 de la Ley 53/2002, en vigor a partir del 01/01/2003 (nota del texto consolidado del BOE).
- [ ] `melilla-bonificacion-ajd` (bonificacion_ajd, ES-19, 2003-01-01 → sin fin)
  - Cargado: `{"rate": 0.5}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-1993-25359#a57bis
  - Nota: TRLITPAJD, art. 57 bis.1: «La cuota gradual de documentos notariales del gravamen de actos jurídicos documentados se bonificará en un 50 por 100 cuando el Registro en el que se deba proceder a la inscripción o anotación de los bienes o actos radique en Ceuta o Melilla». Se aplica por el territorio del inmueble, cuyo Registro está en la ciudad. Añadido por la Ley 53/2002, en vigor a partir del 01/01/2003.
- [ ] `melilla-bonificacion-ibi` (bonificacion_ibi, ES-19, 2004-03-10 → sin fin)
  - Cargado: `{"rate": 0.5}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2004-4214#a159
  - Nota: TRLRHL, art. 159.2: «Las cuotas tributarias correspondientes a los impuestos municipales regulados en esta ley serán objeto de una bonificación del 50 por ciento». Fecha de inicio: entrada en vigor del texto refundido (RDLeg 2/2004); la bonificación puede venir de antes.
- [ ] `melilla-bonificacion-plusvalia` (bonificacion_plusvalia, ES-19, 2004-03-10 → sin fin)
  - Cargado: `{"rate": 0.5}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2004-4214#a159
  - Nota: TRLRHL, art. 159.2: bonificación del 50 % de las cuotas de los impuestos municipales, la plusvalía entre ellos. Fecha de inicio: entrada en vigor del texto refundido; la bonificación puede venir de antes.
- [ ] `melilla-deduccion-irpf-rentas` (deduccion_irpf_rentas_territorio, ES-19, 2018-01-01 → sin fin)
  - Cargado: `{"rate": 0.6}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764#a68
  - Nota: Ley 35/2006 del IRPF, art. 68.4: el contribuyente, resida o no en Melilla (1.º y 2.º), «se deducirá el 60 por ciento de la parte de la suma de las cuotas íntegras estatal y autonómica que proporcionalmente corresponda» a las rentas obtenidas allí, entre ellas los rendimientos de inmuebles situados en la ciudad (3.º.b) y las ganancias patrimoniales que procedan de ellos (3.º.d). Apartados 4.1 y 4.2 en la redacción de la Ley 6/2018, con efectos desde el 01/01/2018. El motor aplica la proporción de la renta del inmueble en la base y supone que el resto de la base se obtiene fuera de la ciudad (ADR-0045).

**Pendiente o dudoso:**
- Si la primera entrega de vivienda nueva sujeta a IPSI tributa por AJD (como se modela) o por TPO: los arts. 7.5 y 31.2 del TRLITPAJD solo hablan del IVA.
- IPSI de Ceuta: copia consolidada con cambios hasta 2024; IPSI de Melilla: solo el anexo 1 del BOME de 04/05/2021.
- Deducción del IRPF: el motor supone que el resto de la base del usuario se obtiene fuera de la ciudad (prudente) y calcula la proporción sobre la base liquidable.
- Fechas de inicio de las bonificaciones municipales: la del texto refundido de 2004; pueden venir de antes.
- Alquiler turístico de Melilla sin norma localizada; el de Ceuta depende del RD 1312/2024, cuya posible anulación por el Supremo hay que comprobar.
- Zonas tensionadas: falta la resolución del segundo trimestre de 2024.
