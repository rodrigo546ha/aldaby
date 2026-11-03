# Verificación de la tanda 7: Castilla y León, Castilla-La Mancha, Murcia, Galicia y Canarias

**Cargadas:** 2026-11-03 · **Estado:** con `verified: false` · **Revisa:** Rodrigo
**Ficheros:** `services/api/data/rules/castilla_y_leon.yaml`, `castilla_la_mancha.yaml`, `murcia.yaml`, `galicia.yaml` y `canarias.yaml`

## Contexto
- Las siguientes cinco comunidades por compraventas de vivienda de septiembre de 2025 a agosto de 2026
  (INE, ETDP, tabla 6150), después de la tanda 6 (ADR-0043). El País Vasco, con su IRPF foral, queda fuera.
- Un agente por comunidad, leyendo la norma oficial; lo que no pudo leer en la fuente oficial no se ha
  cargado. Cada regla dice en `notes` la norma, el artículo y la redacción vigente.
- Mientras sigan sin verificar, los planes de estas comunidades salen con cifras provisionales.

## 1. Castilla y León (ES-07)

- [ ] `castilla-y-leon-itp-inmuebles-2013` (impuesto_compra_segunda_mano, ES-07, 2013-09-19 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.08}, {"from": 250000, "rate": 0.1}]}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOCL-h-2013-90254#a25
  - Nota: Decreto Legislativo 1/2013 de Castilla y León, art. 24.1.a): tipo general del 8 % en la transmisión de inmuebles; art. 25.1: «se aplicará el tipo general a esta cantidad [250.000 €] y un tipo incrementado del 10 por 100 a la parte de la base que exceda esta cantidad». Es progresivo: cada tipo solo sobre su tramo (el 10 % no se aplica a todo el valor). Texto original en vigor el 19/09/2013, sin cambios en estos apartados.
- [ ] `castilla-y-leon-ajd-compra-vivienda-2013` (ajd_compra_vivienda, ES-07, 2013-09-19 → sin fin)
  - Cargado: `{"bands": [{"up_to": null, "rate": 0.015}], "cap_jumps": false}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOCL-h-2013-90254#a24
  - Nota: Decreto Legislativo 1/2013 de Castilla y León, art. 24.2: «se aplicará el tipo general del 1,5 por 100» a las primeras copias de escrituras y actas notariales sujetas como documentos notariales a AJD, único para todo el valor (sin bandas ni salto de banda). Persona jurídica: el mismo tipo.
- [ ] `castilla-y-leon-irpf-escala-general-2022` (escala_irpf_general_autonomica, ES-07, 2022-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.09}, {"from": 12450, "rate": 0.12}, {"from": 20200, "rate": 0.14}, {"from": 35200, "rate": 0.185}, {"from": 53407.2, "rate": 0.215}]}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOCL-h-2013-90254#a1
  - Nota: Decreto Legislativo 1/2013 de Castilla y León, art. 1, redacción de la Ley 2/2022 (BOE-A-2022-21578), efectos 01/01/2022: 9 % hasta 12.450 €; 12 % hasta 20.200 €; 14 % hasta 35.200 €; 18,5 % hasta 53.407,20 €; 21,5 % en adelante.
- [ ] `castilla-y-leon-irpf-minimo-contribuyente-2015` (minimo_contribuyente, ES-07, 2015-01-01 → sin fin)
  - Cargado: `{"general": 5550, "over_65_extra": 1150, "over_75_extra": 1400}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOCL-h-2013-90254#a1bis
  - Nota: Decreto Legislativo 1/2013 de Castilla y León, art. 1 bis.1 (Ley 10/2014, BOE-A-2015-1117): 5.550 € con carácter general; +1.150 € si mayor de 65 años; +1.400 € adicionales si mayor de 75. Idénticos a los importes estatales.
- [ ] `castilla-y-leon-irpf-minimo-descendientes-2015` (minimo_descendientes, ES-07, 2015-01-01 → sin fin)
  - Cargado: `{"first": 2400, "second": 2700, "third": 4000, "fourth_and_more": 4500, "under_3_extra": 2800}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOCL-h-2013-90254#a1bis
  - Nota: Decreto Legislativo 1/2013 de Castilla y León, art. 1 bis.2 (Ley 10/2014): 2.400 €, 2.700 €, 4.000 € y 4.500 € por el primer, segundo, tercer y cuarto y siguientes descendientes; +2.800 € si el descendiente es menor de tres años. Idénticos a los importes estatales.
- [ ] `castilla-y-leon-zonas-tensionadas` (zona_tensionada, ES-07, 2023-05-26 → sin fin)
  - Cargado: `{"declared": false, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Ley 12/2023, art. 18: la declaración corresponde a la comunidad autónoma; el Ministerio publica la relación cada trimestre.
- [ ] `castilla-y-leon-alquiler-turistico` (regimen_alquiler_turistico, ES-07, 2017-02-18 → sin fin)
  - Cargado: `{"regime": "Vivienda de uso turístico en Castilla y León (Decreto 3/2017): declaración responsable antes de iniciar la actividad e inscripción de oficio en el Registro de Turismo de Castilla y León", "requirements": [{"code": "declaracion-responsable", "description": "Declaración responsable por cad…`
  - Fuente: https://bocyl.jcyl.es/eli/es-cl/d/2017/02/16/3/dof/spa/pdf
  - Nota: Decreto 3/2017 de Castilla y León, texto original (BOCYL 17/02/2017), sin las modificaciones posteriores salvo la derogación del art. 3.2 por la Orden CYT/1318/2019 (según la sede electrónica de la Junta). Habitualidad: más de un mes al año (art. 4.c). Pendiente comprobar otras modificaciones y la entrada en vigor de la Orden.
- [ ] `valladolid-plusvalia-tipo` (tipo_plusvalia, ES-07-47186, 2022-01-01 → sin fin)
  - Cargado: `{"rate": 0.2176}`
  - Fuente: https://www.valladolid.es/es/ayuntamiento/organizacion-administrativa/areas/area-hacienda-personal-modernizacion-administrativa/utilidad/ordenanzas-fiscales/ordenanzas-fiscales-2026
  - Nota: Ordenanza Fiscal del IIVTNU del Ayuntamiento de Valladolid, art. 16: «La cuota de este impuesto será la resultante de aplicar a la base imponible el tipo del 21,76 %.» Leído en el texto íntegro 2026 (BOP núm. 238, 15/12/2025) y, con la misma cifra, en los de 2022 y 2025. Fecha de inicio = ejercicio 2022 (primer texto leído con este tipo); vigencia exacta por verificar.
- [ ] `burgos-plusvalia-tipo` (tipo_plusvalia, ES-07-09059, 2026-01-09 → sin fin)
  - Cargado: `{"rate": 0.21}`
  - Fuente: https://www.aytoburgos.es/documents/38509/0/24.-+publicaci%C3%B3n+BOPBUR+aprobacion+definitiva+Ordenanza+Fiscal+n%C2%BA+503+IIVTNU.pdf/4cc582ec-d15b-0840-462e-d7e53d7a4e92
  - Nota: Ordenanza Fiscal nº 503 del Ayuntamiento de Burgos, art. 8.1: «El tipo de gravamen del impuesto sobre el incremento de valor de los terrenos de naturaleza urbana será del 21%.» Texto del BOP de Burgos núm. 4, 08/01/2026 (modificación del Pleno de 05/09/2025; disposición final sexta: en vigor al día siguiente de su publicación). El 21 % puede venir de versiones anteriores (por verificar).

**Pendiente o dudoso:**
- ITP progresivo: 8 % y 10 % solo sobre la parte que pasa de 250.000 € (art. 24.1.a y 25.1 del DL 1/2013).
- Los mínimos propios son idénticos a los estatales: se cargan porque son propios, pero el resultado no cambia.
- El BOE consolida el DL 1/2013 hasta mayo de 2024: falta mirar en el BOCYL si hay leyes de 2025 o 2026 que cambien la escala o los mínimos.
- Turismo: Decreto 3/2017 leído en su texto original del BOCYL. La Orden CYT/1318/2019, que derogó el art. 3.2, solo se ha leído en la sede de la Junta; su fecha de entrada en vigor está sin comprobar.
- Plusvalía de Valladolid: el 21,76 % sale igual en los textos de 2022, 2025 y 2026; la fecha de inicio (2022-01-01) no se ha visto en la norma.
- Plusvalía de Burgos: la fecha de inicio es el día siguiente al BOP de 08/01/2026; el 21 % puede venir de antes.
- Falta el régimen urbanístico municipal del alquiler turístico de Valladolid y Burgos.

## 2. Castilla-La Mancha (ES-08)

- [ ] `castilla-la-mancha-itp-inmuebles-2016` (impuesto_compra_segunda_mano, ES-08, 2016-06-01 → sin fin)
  - Cargado: `{"rate": 0.09}`
  - Fuente: https://docm.jccm.es/portaldocm/descargarArchivo.do?ruta=1385469263266160074.doc&tipo=rutaCodigoLegislativo
  - Nota: Ley 8/2013, de 21 de noviembre, de Medidas Tributarias de Castilla-La Mancha, art. 19.1, redacción de la Ley 3/2016, de 5 de mayo (BOE-A-2016-6725): a las transmisiones de inmuebles y a la constitución y cesión de derechos reales sobre ellos (salvo de garantía) «con carácter general, el tipo de gravamen del 9 por ciento». Tipo único para todo el valor, no por tramos.
- [ ] `castilla-la-mancha-ajd-compra-vivienda-2016` (ajd_compra_vivienda, ES-08, 2016-06-01 → sin fin)
  - Cargado: `{"bands": [{"up_to": null, "rate": 0.015}], "cap_jumps": false}`
  - Fuente: https://docm.jccm.es/portaldocm/descargarArchivo.do?ruta=1385469263266160074.doc&tipo=rutaCodigoLegislativo
  - Nota: Ley 8/2013 de Castilla-La Mancha, art. 21.1, redacción de la Ley 3/2016 (BOE-A-2016-6725, art. 11.Siete): «con carácter general, el tipo de gravamen del 1,50 por ciento». Sin modificaciones posteriores del apartado 1 en el texto actualizado a 30/03/2026.
- [ ] `castilla-la-mancha-irpf-escala-general-2015` (escala_irpf_general_autonomica, ES-08, 2015-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.095}, {"from": 12450, "rate": 0.12}, {"from": 20200, "rate": 0.15}, {"from": 35200, "rate": 0.185}, {"from": 60000, "rate": 0.225}]}`
  - Fuente: https://www.boe.es/boe/dias/2015/02/18/pdfs/BOE-A-2015-1628.pdf
  - Nota: Ley 8/2013 de Castilla-La Mancha, art. 13 bis, añadido por la Ley 9/2014, de 4 de diciembre (BOE-A-2015-1628; entrada en vigor 01/01/2015, disposición final tercera): 9,5 % hasta 12.450 €; 12 % hasta 20.200 €; 15 % hasta 35.200 €; 18,5 % hasta 60.000 €; 22,5 % en adelante. Coinciden las cuotas íntegras de la tabla (1.182,75; 2.112,75; 4.362,75; 8.950,75 €).
- [ ] `castilla-la-mancha-zonas-tensionadas` (zona_tensionada, ES-08, 2023-05-26 → sin fin)
  - Cargado: `{"declared": false, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Ley 12/2023, art. 18: la declaración corresponde a la comunidad autónoma; el Ministerio publica la relación cada trimestre. Búsqueda por «Castilla-La Mancha» y por las cinco capitales de provincia sin resultados en las resoluciones citadas.
- [ ] `castilla-la-mancha-alquiler-turistico` (regimen_alquiler_turistico, ES-08, 2018-07-01 → sin fin)
  - Cargado: `{"regime": "Vivienda de uso turístico en Castilla-La Mancha (Decreto 36/2018): declaración responsable de inicio de actividad e inscripción en el Registro de empresas y establecimientos turísticos antes de anunciarla", "requirements": [{"code": "declaracion-responsable", "description": "Declaración …`
  - Fuente: https://docm.jccm.es/portaldocm/descargarArchivo.do?ruta=1528111832347830497.doc&tipo=rutaCodigoLegislativo
  - Nota: Decreto 36/2018, de 29 de mayo, de ordenación de los apartamentos turísticos y las viviendas de uso turístico en Castilla-La Mancha, texto de la sede del DOCM sin notas de modificación. Pendiente comprobar si lo ha modificado alguna norma posterior (informes de prensa mencionan un anteproyecto de ley que exigiría la declaración responsable antes de anunciar; sin fuente oficial leída) y las limitaciones urbanísticas municipales.

**Pendiente o dudoso:**
- Sin mínimos propios: la Ley 8/2013 no los regula y se aplican los estatales.
- Las cifras salen del texto de la sede de la Junta actualizado a 30/03/2026; el consolidado del BOE está desactualizado desde el 31/01/2023.
- Plusvalía de Toledo: cargada después con un tipo por años de tenencia (`toledo-plusvalia-tipo`); ver la sección final de `verificacion-tanda-8.md`.
- Plusvalía de Guadalajara sin cargar: guadalajara.es bloquea a los agentes de Anthropic en su robots.txt; la URL de la ordenanza, para leerla a mano, está en `castilla_la_mancha.yaml`.
- Turismo: no se ha comprobado si el Decreto 36/2018 cambió después; la prensa habla de un anteproyecto de ley.

## 3. Región de Murcia (ES-14)

- [ ] `murcia-itp-inmuebles-2013` (impuesto_compra_segunda_mano, ES-14, 2013-07-11 → 2025-07-25)
  - Cargado: `{"rate": 0.08}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2011-10542#a6
  - Nota: Decreto Legislativo 1/2010 de la Región de Murcia, art. 6.1, redacción de la Ley 6/2013 (publicada el 10/07/2013, en vigor el 11/07/2013): tipo del 8 % para la transmisión de bienes inmuebles, único para todo el valor (no por tramos). Leído en la versión histórica del BOE.
- [ ] `murcia-itp-inmuebles-2025` (impuesto_compra_segunda_mano, ES-14, 2025-07-25 → sin fin)
  - Cargado: `{"rate": 0.0775}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2025-16147
  - Nota: Decreto Legislativo 1/2010 de la Región de Murcia, art. 6.1, redacción del art. 55.Catorce de la Ley 3/2025, de 23 de julio, de Presupuestos Generales de la Región de Murcia para 2025 (BOE-A-2025-16147; entra en vigor el día siguiente a su publicación en el BORM, 24/07/2025): «será del 7,75 %», con vigencia indefinida. Tipo único para todo el valor (no por tramos). Texto consolidado: https://www.boe.es/buscar/act.php?id=BOE-A-2011-10542#a6
- [ ] `murcia-ajd-compra-vivienda-2011` (ajd_compra_vivienda, ES-14, 2011-02-01 → sin fin)
  - Cargado: `{"bands": [{"up_to": null, "rate": 0.015}], "cap_jumps": false}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2011-10542#a7
  - Nota: Decreto Legislativo 1/2010 de la Región de Murcia, art. 7.1: primeras copias de escrituras y actas notariales inscribibles, con cantidad o cosa valuable y no sujetas a Sucesiones y Donaciones ni a TPO/IVA del art. 1.1 y 1.2 del TRLITPAJD, tributan además de la cuota fija «al tipo de gravamen del 1,5 %», salvo los tipos de los apartados 2 a 9 (0,1 %, 0,5 %, 1,5 % y 2,5 % para supuestos concretos: jóvenes, familia numerosa, discapacidad, etc.), que no se incluyen. Persona jurídica: mismo tipo.
- [ ] `murcia-irpf-escala-general-2012` (escala_irpf_general_autonomica, ES-14, 2012-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.095}, {"from": 12450, "rate": 0.112}, {"from": 20200, "rate": 0.133}, {"from": 34000, "rate": 0.179}, {"from": 60000, "rate": 0.225}]}`
  - Fuente: https://www.boe.es/buscar/act.php?id=BOE-A-2011-10542#a2
  - Nota: Decreto Legislativo 1/2010 de la Región de Murcia, art. 2, al amparo del art. 46.1.b) de la Ley 22/2009: 9,50 % hasta 12.450 €; 11,20 % hasta 20.200 €; 13,30 % hasta 34.000 €; 17,90 % hasta 60.000 €; 22,50 % en adelante. Coincide con la escala complementaria estatal supletoria. Fecha de inicio: primera versión del BOE comprobada (en vigor el 01/01/2012); puede ser anterior.
- [ ] `murcia-zonas-tensionadas` (zona_tensionada, ES-14, 2023-05-26 → sin fin)
  - Cargado: `{"declared": false, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Ley 12/2023, art. 18: la declaración corresponde a la comunidad autónoma; el Ministerio publica la relación cada trimestre.
- [ ] `murcia-alquiler-turistico` (regimen_alquiler_turistico, ES-14, 2019-11-08 → sin fin)
  - Cargado: `{"regime": "Vivienda de uso turístico en la Región de Murcia (Decreto 256/2019): declaración responsable ante el Instituto de Turismo de la Región de Murcia antes de prestar el servicio", "requirements": [{"code": "declaracion-responsable", "description": "Declaración responsable de clasificación tu…`
  - Fuente: https://www.borm.es/services/anuncio/780550/pdf
  - Nota: Decreto 256/2019 de la Región de Murcia (BORM núm. 242, 19/10/2019). Fecha de inicio calculada: veinte días tras la publicación. Si se cede por habitaciones, el titular debe ser persona física empadronada y residente en la vivienda (art. 5.2). Excluida la cesión sometida a la LAU (art. 1.2.b). Pendiente comprobar posibles modificaciones posteriores a 2019 y los requisitos urbanísticos municipales y de estatutos de la comunidad.
- [ ] `murcia-plusvalia-tipo` (tipo_plusvalia, ES-14-30030, 2025-01-01 → sin fin)
  - Cargado: `{"rate": 0.3}`
  - Fuente: https://amt.murcia.es/sites/amt/files/2026-01/3.5%20Impuesto-Plusval%C3%ADa-2026.pdf
  - Nota: Ordenanza reguladora del IIVTNU del Ayuntamiento de Murcia, art. 9: «el tipo impositivo del TREINTA por ciento». Texto vigente en 2026 (modificada por el Pleno de 26/12/2024, BORM de 28/12/2024, efectos 01/01/2025). Fecha de inicio = esa modificación; el 30 % puede venir de antes (por verificar). No se ha leído el BORM.
- [ ] `cartagena-plusvalia-tipo` (tipo_plusvalia, ES-14-30016, 2022-05-30 → sin fin)
  - Cargado: `{"rate": 0.3}`
  - Fuente: https://www.cartagena.es/gestion/documentos/acuerdosynormativas/92684.pdf
  - Nota: Ordenanza reguladora del IIVTNU del Ayuntamiento de Cartagena, art. 9.1: «El tipo de gravamen de este impuesto es del 30 por 100». Redacción del edicto del BORM núm. 123, 30/05/2022 (https://www.borm.es/services/anuncio/ano/2022/numero/2764/pdf?id=806518), en vigor el día de su publicación; confirmado en el texto de las ordenanzas de Cartagena para 2026 (entrada en vigor 01/01/2026, texto revisado a 27/01/2026). Los edictos de 2024 y 2025 (BORM 11/12/2024 y 03/11/2025) solo cambian coeficientes.

**Pendiente o dudoso:**
- ITP: 8 % hasta el 2025-07-25 y 7,75 % desde entonces (Ley 3/2025, art. 55.Catorce).
- Sin mínimos propios: rigen los estatales.
- El consolidado del BOE llega hasta el 24/07/2025: mirar en el BORM si la ley de presupuestos de 2026 cambió el ITP o la escala.
- El BORM puso un captcha a las descargas directas; no se saltó y esos PDF se leyeron por otra vía. Conviene releer en el BORM las fuentes marcadas.
- Las fechas de inicio de la escala (2012) y del AJD (2011) son las de la primera versión comprobada en el BOE; pueden ser anteriores.
- Plusvalía de Murcia: la fecha de inicio es la de la modificación de 2025; el 30 % puede venir de antes.
- Turismo: faltan los requisitos urbanísticos municipales de Murcia y Cartagena y comprobar si el Decreto 256/2019 cambió.

## 4. Galicia (ES-12)

- [ ] `galicia-itp-inmuebles-2022` (impuesto_compra_segunda_mano, ES-12, 2022-01-01 → 2024-01-01)
  - Cargado: `{"rate": 0.09}`
  - Fuente: https://www.boe.es/eli/es-ga/dlg/2011/07/28/1/con/20221230
  - Nota: Decreto legislativo 1/2011 de Galicia, art. 14.Uno.1, redacción de la Ley 18/2021, de 27 de diciembre, de medidas fiscales y administrativas (BOE-A-2022-3415; entrada en vigor el 01/01/2022): tipo del 9 % en la transmisión de bienes inmuebles y constitución y cesión de derechos reales, salvo los de garantía. Tipo único sobre todo el valor, no por tramos.
- [ ] `galicia-itp-inmuebles-2024` (impuesto_compra_segunda_mano, ES-12, 2024-01-01 → sin fin)
  - Cargado: `{"rate": 0.08}`
  - Fuente: https://www.boe.es/eli/es-ga/dlg/2011/07/28/1/con
  - Nota: Decreto legislativo 1/2011 de Galicia, art. 14.Uno.1, redacción del art. 4 de la Ley 10/2023, de 28 de diciembre, de medidas fiscales y administrativas (BOE-A-2024-2777; DOG núm. 246, 29/12/2023; entra en vigor el 01/01/2024): «el tipo de gravamen aplicable a la transmisión de bienes inmuebles, así como en la constitución y cesión de derechos reales que recaigan sobre ellos, excepto los derechos reales de garantía, será del 8 %». Tipo único para todo el valor (no por tramos). El texto consolidado a 27/03/2026 lo mantiene.
- [ ] `galicia-ajd-compra-vivienda-2013` (ajd_compra_vivienda, ES-12, 2013-03-01 → sin fin)
  - Cargado: `{"bands": [{"up_to": null, "rate": 0.015}], "cap_jumps": false}`
  - Fuente: https://www.boe.es/eli/es-ga/dlg/2011/07/28/1/con
  - Nota: Decreto legislativo 1/2011 de Galicia, art. 15.Uno: «en las primeras copias de escrituras o actas notariales sujetas a la modalidad de actos jurídicos documentados, cuota variable de los documentos notariales [...] el tipo de gravamen aplicable será del 1,5 %». No incluye los reducidos de vivienda habitual (1 %, art. 15.Dos), discapacidad (0,5 %, art. 15.Tres) ni familias numerosas (art. 15.Cuatro). Fecha de inicio: la redacción de 1,5 % aparece en la versión consolidada publicada el 28/02/2013 (antes, 1 %); una fuente secundaria la atribuye a la Ley 2/2013, de presupuestos de Galicia, en vigor el 01/03/2013: por verificar en el DOG.
- [ ] `galicia-irpf-escala-general-2022` (escala_irpf_general_autonomica, ES-12, 2022-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.09}, {"from": 12985.35, "rate": 0.1165}, {"from": 21068.6, "rate": 0.149}, {"from": 35200, "rate": 0.184}, {"from": 60000, "rate": 0.225}]}`
  - Fuente: https://www.boe.es/eli/es-ga/dlg/2011/07/28/1/con
  - Nota: Decreto legislativo 1/2011 de Galicia, art. 4, redacción del art. 1 de la Ley 7/2022 (efectos 01/01/2022): 9 % hasta 12.985,35 €; 11,65 % hasta 21.068,60 €; 14,90 % hasta 35.200 €; 18,40 % hasta 60.000 €; 22,50 % en adelante. Escala anterior (2021): 9,4 % hasta 12.450 €.
- [ ] `galicia-irpf-minimo-contribuyente-2022` (minimo_contribuyente, ES-12, 2022-01-01 → sin fin)
  - Cargado: `{"general": 5789, "over_65_extra": 1199, "over_75_extra": 1460}`
  - Fuente: https://www.boe.es/eli/es-ga/dlg/2011/07/28/1/con
  - Nota: Decreto legislativo 1/2011 de Galicia, art. 4 bis.1, añadido por el art. 2 de la Ley 7/2022 (efectos 01/01/2022): 5.789 € con carácter general; +1.199 € si mayor de 65 años; +1.460 € adicionales si mayor de 75.
- [ ] `galicia-irpf-minimo-descendientes-2022` (minimo_descendientes, ES-12, 2022-01-01 → sin fin)
  - Cargado: `{"first": 2503, "second": 2816, "third": 4172, "fourth_and_more": 4694, "under_3_extra": 2920}`
  - Fuente: https://www.boe.es/eli/es-ga/dlg/2011/07/28/1/con
  - Nota: Decreto legislativo 1/2011 de Galicia, art. 4 bis.2, añadido por el art. 2 de la Ley 7/2022 (efectos 01/01/2022): 2.503 €, 2.816 €, 4.172 € y 4.694 € por el primer, segundo, tercer y cuarto y siguientes descendientes; +2.920 € si el descendiente es menor de tres años.
- [ ] `galicia-zonas-tensionadas` (zona_tensionada, ES-12, 2023-05-26 → sin fin)
  - Cargado: `{"declared": false, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Ley 12/2023, art. 18: la declaración corresponde a la comunidad autónoma; el Ministerio publica la relación cada trimestre. Sin declaración de ámbito autonómico: solo municipios concretos (reglas ES-12-15030 y ES-12-15078).
- [ ] `galicia-zona-tensionada-15030` (zona_tensionada, ES-12-15030, 2025-07-30 → 2028-07-30)
  - Cargado: `{"declared": true, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-15728
  - Nota: A Coruña. Resolución de 30/05/2025 de la presidenta del Instituto Gallego de la Vivienda y Suelo (declaración a solicitud del ayuntamiento); efectos desde el día siguiente a la publicación de la resolución del Ministerio en el BOE (29/07/2025) y vigencia de tres años desde ese día siguiente. Gran tenedor particularizado: más de diez inmuebles urbanos de uso residencial o más de 1.500 m² construidos de uso residencial, sin garajes ni trasteros. Aplica la limitación del art. 17.7 de la LAU (contratos sobre inmuebles sin contrato en los últimos cinco años). Corrección de erratas de enlaces: BOE-A-2025-20246.
- [ ] `galicia-zona-tensionada-15078` (zona_tensionada, ES-12-15078, 2026-07-30 → 2029-07-30)
  - Cargado: `{"declared": true, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Santiago de Compostela. Resolución de 24/04/2026 de la presidenta del Instituto Gallego de la Vivienda y Suelo (declaración a solicitud del ayuntamiento; cdn.mivau.gob.es/portal-web-mivau/vivienda/alquila/20260424_Resolucion_ZMRT_Santiago_Cast.pdf); efectos desde el día siguiente a la publicación de la resolución del Ministerio en el BOE (29/07/2026) y vigencia de tres años desde ese día siguiente. Gran tenedor particularizado: cinco o más inmuebles urbanos de uso residencial en el término municipal. Aplica la limitación del art. 17.7 de la LAU.
- [ ] `galicia-alquiler-turistico` (regimen_alquiler_turistico, ES-12, 2017-05-11 → sin fin)
  - Cargado: `{"regime": "Vivienda de uso turístico en Galicia (Decreto 12/2017): cesión de la vivienda completa por estancias de menos de 30 días, de forma reiterada (dos o más veces al año), con declaración responsable previa ante la Axencia Turismo de Galicia", "requirements": [{"code": "declaracion-responsabl…`
  - Fuente: https://www.lex.gal/es/normativa/detalle/3031/pdf/
  - Nota: Decreto 12/2017, arts. 5, 39, 41 a 43, según el texto «Última versión» de Lex.gal (informativo). Fecha de inicio calculada: tres meses desde el DOG de 10/02/2017 (fuente secundaria: vLex da 11/05/2017); por verificar en el DOG. No se ha comprobado si el decreto tuvo modificaciones posteriores.
- [ ] `coruna-plusvalia-tipo` (tipo_plusvalia, ES-12-15030, 2024-01-01 → sin fin)
  - Cargado: `{"rate": 0.25}`
  - Fuente: https://www.coruna.gal/descarga/1453911757238/libro-ordenanzas-2026-v2.pdf
  - Nota: Ordenanza fiscal nº 53 del Concello da Coruña (libro de ordenanzas fiscales 2026), art. 7.1: «A cota do imposto será a que resulte de aplicar á base impoñible o tipo do 25%». Disposición final: aprobada por el Pleno el 28/12/2023, entra en vigor el 01/01/2024. Bonificación del art. 7.2 (transmisiones mortis causa de vivienda habitual) no incluida.
- [ ] `vigo-plusvalia-tipo` (tipo_plusvalia, ES-12-36057, 2022-03-31 → sin fin)
  - Cargado: `{"rate": 0.3}`
  - Fuente: http://cdixital.vigo.org/expedientes/tramites/getarchivo.jsp?id=26&tipo=ordenanzas&lang=ga
  - Nota: Ordenanza nº 6 del Concello de Vigo (texto enlazado desde la página de plusvalía de hoxe.vigo.org), art. 8.1: «o tipo de gravame do 30%». Entra en vigor al día siguiente de su publicación en el BOP; la última publicación listada es la de 30/03/2022, de donde sale la fecha de inicio (el 30 % puede venir de antes). No se ha comprobado si el paquete de ordenanzas para 2025 o 2026 la modificó.

**Pendiente o dudoso:**
- Zona tensionada: A Coruña (desde el 30/07/2025, BOE-A-2025-15728) y Santiago de Compostela (desde el 30/07/2026, BOE-A-2026-16532), tres años cada una.
- AJD: la fecha de inicio (2013-03-01) sale de una fuente secundaria que lo atribuye a la Ley 2/2013; confirmar en el DOG.
- Turismo: Decreto 12/2017 con fecha de inicio por fuente secundaria; no se sabe si tuvo cambios después, y falta el régimen municipal de A Coruña, Vigo y Santiago.
- Plusvalía de Vigo: el 30 % y la fecha salen del último BOP que lista la ordenanza (30/03/2022); no se ha comprobado si las ordenanzas de 2025 o 2026 lo cambiaron.
- Los mínimos gallegos por ascendientes y discapacidad (art. 4 bis.3 y 4) no caben en el esquema y no se han cargado.

## 5. Canarias (ES-05)

- [ ] `canarias-itp-inmuebles-2018` (impuesto_compra_segunda_mano, ES-05, 2018-12-05 → sin fin)
  - Cargado: `{"rate": 0.065}`
  - Fuente: https://www.gobiernodecanarias.org/boc/2025/256/4414.html
  - Nota: Decreto Legislativo 1/2009 de Canarias, art. 31.1.a, redacción de la Ley 9/2025, de 23 de diciembre (BOC núm. 256, 29/12/2025, DF undécima, apartado diecinueve): transmisión de bienes inmuebles, con carácter general el 6,5 %, único para todo el valor (no por tramos). El 5 % exige vivienda habitual, base de hasta 200.000 € y no ser propietario de otra vivienda. Fecha de inicio = Ley 4/2018 según la copia de Hacienda del DL 1/2009 (art. 31 «en vigor desde 5 de diciembre de 2018»); el tipo general no ha cambiado.
- [ ] `canarias-ajd-compra-vivienda-2016` (ajd_compra_vivienda, ES-05, 2016-01-01 → sin fin)
  - Cargado: `{"bands": [{"up_to": null, "rate": 0.01}], "cap_jumps": false, "legal_person_rate": 0.01}`
  - Fuente: https://www.hacienda.gob.es/DocLeyes/onlinelt/C13.13.tributos_cedidos_canarias.htm
  - Nota: Decreto Legislativo 1/2009 de Canarias, art. 36, redacción de la Ley 11/2015 (en vigor desde 01/01/2016): 0,75 % en documentos notariales con carácter general y 1 % en los relativos a operaciones sujetas al IGIC o al IVA. Texto leído en la copia de Hacienda (Normadoc, 2019); la Ley 5/2024 y la Ley 9/2025 no modifican el art. 36 y Hacienda (Tributación autonómica 2026) sigue dando el 0,75 % general. Persona jurídica: mismo tipo. Por verificar que la entrega de vivienda nueva en IGIC no esté exenta de IGIC (en ese caso el tipo sería 0,75 %).
- [ ] `canarias-igic-vivienda-nueva-2025` (iva_vivienda_nueva, ES-05, 2025-10-21 → sin fin)
  - Cargado: `{"rate": 0.07}`
  - Fuente: https://www.boe.es/buscar/pdf/2025/BOC-j-2025-90249-consolidado.pdf
  - Nota: ESTO ES IGIC, NO IVA. Decreto Legislativo 1/2025, de 13 de octubre (BOC núm. 207, 20/10/2025; en vigor el día siguiente), art. 32.1: tipo general del IGIC del 7 %, aplicable a lo que no tenga otro tipo; no hay tipo específico para la primera entrega de vivienda libre. El art. 38 solo da tipo cero (VPO y promoción pública, entidades de arrendamiento del régimen especial del IS) y el 3 % superreducido (vivienda habitual del adquirente que sea persona de 40 años o menos, familia numerosa, discapacidad ≥65 %, víctima de violencia de género, familia monoparental o renta familiar de hasta 46.455 €, base de hasta 200.000 € y sin otra vivienda): ninguno aplica a un inversor. Fecha de inicio = entrada en vigor del texto refundido; el 7 % general viene de antes (por verificar desde cuándo).
- [ ] `canarias-irpf-escala-general-2024` (escala_irpf_general_autonomica, ES-05, 2024-01-01 → 2025-01-01)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.09}, {"from": 13465, "rate": 0.115}, {"from": 19022, "rate": 0.14}, {"from": 35185, "rate": 0.185}, {"from": 56382, "rate": 0.235}, {"from": 91350, "rate": 0.25}, {"from": 121200, "rate": 0.26}]}`
  - Fuente: https://sede.gobiernodecanarias.org/boc/boc-a-2024-260-4427.pdf
  - Nota: Decreto Legislativo 1/2009 de Canarias, art. 18 bis, redacción de la Ley 5/2024, de 26 de diciembre (BOC núm. 260, 30/12/2024, DF décima, apartado veintitrés; efectos desde 01/01/2024): 9 % hasta 13.465 €; 11,5 % hasta 19.022 €; 14 % hasta 35.185 €; 18,5 % hasta 56.382 €; 23,5 % hasta 91.350 €; 25 % hasta 121.200 €; 26 % en adelante. Escalas anteriores a 2024 no cargadas.
- [ ] `canarias-irpf-escala-general-2025` (escala_irpf_general_autonomica, ES-05, 2025-01-01 → sin fin)
  - Cargado: `{"brackets": [{"from": 0, "rate": 0.09}, {"from": 13748, "rate": 0.115}, {"from": 19422, "rate": 0.14}, {"from": 35924, "rate": 0.185}, {"from": 57566, "rate": 0.235}, {"from": 93268, "rate": 0.25}, {"from": 123745, "rate": 0.26}]}`
  - Fuente: https://www.gobiernodecanarias.org/boc/2025/256/4414.html
  - Nota: Decreto Legislativo 1/2009 de Canarias, art. 18 bis, redacción de la Ley 9/2025, de 23 de diciembre (BOC núm. 256, 29/12/2025, DF undécima, apartado diecisiete; efectos desde 01/01/2025): 9 % hasta 13.748 €; 11,5 % hasta 19.422 €; 14 % hasta 35.924 €; 18,5 % hasta 57.566 €; 23,5 % hasta 93.268 €; 25 % hasta 123.745 €; 26 % en adelante.
- [ ] `canarias-irpf-minimo-contribuyente-2024` (minimo_contribuyente, ES-05, 2024-01-01 → sin fin)
  - Cargado: `{"general": 5606, "over_65_extra": 1162, "over_75_extra": 1414}`
  - Fuente: https://sede.gobiernodecanarias.org/boc/boc-a-2024-260-4427.pdf
  - Nota: Decreto Legislativo 1/2009 de Canarias, art. 18 ter.Uno, añadido por la Ley 5/2024 (BOC núm. 260, 30/12/2024; efectos 01/01/2024), en sustitución del art. 57 de la Ley 35/2006: 5.606 € con carácter general; +1.162 € si mayor de 65 años; +1.414 € adicionales si mayor de 75.
- [ ] `canarias-irpf-minimo-descendientes-2024` (minimo_descendientes, ES-05, 2024-01-01 → sin fin)
  - Cargado: `{"first": 2424, "second": 2727, "third": 4040, "fourth_and_more": 4545, "under_3_extra": 2828}`
  - Fuente: https://sede.gobiernodecanarias.org/boc/boc-a-2024-260-4427.pdf
  - Nota: Decreto Legislativo 1/2009 de Canarias, art. 18 ter.Dos, añadido por la Ley 5/2024 (BOC núm. 260, 30/12/2024; efectos 01/01/2024), en sustitución del art. 58 de la Ley 35/2006: 2.424 €, 2.727 €, 4.040 € y 4.545 € por el primer, segundo, tercer y cuarto y siguientes descendientes; +2.828 € si el descendiente es menor de tres años.
- [ ] `canarias-zonas-tensionadas` (zona_tensionada, ES-05, 2023-05-26 → sin fin)
  - Cargado: `{"declared": false, "checked_through": "2026-07-29"}`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532
  - Nota: Ley 12/2023, art. 18: la declaración corresponde a la comunidad autónoma; el Ministerio publica la relación cada trimestre. Ley 6/2025 de Canarias, arts. 5.1.b y 10.2: una declaración de zona tensionada suspende la habilitación de nuevas viviendas de uso turístico.
- [ ] `canarias-alquiler-turistico` (regimen_alquiler_turistico, ES-05, 2025-12-13 → sin fin)
  - Cargado: `{"regime": "Uso turístico de hospedaje en vivienda en Canarias (Ley 6/2025): declaración responsable ante el cabildo insular, inscripción en el Registro General Turístico y habilitación expresa del planeamiento urbanístico", "requirements": [{"code": "declaracion-responsable", "description": "Declar…`
  - Fuente: https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-26358
  - Nota: Ley 6/2025, de 10 de diciembre, de Ordenación Sostenible del Uso Turístico de Viviendas (BOE-A-2025-26358). Sin perjuicio de la Ley 14/2019 en El Hierro, La Gomera y La Palma. Faltan el régimen transitorio (usos ya consolidados), los límites por sección electoral y las ordenanzas municipales de Las Palmas de Gran Canaria y Santa Cruz de Tenerife.
- [ ] `las-palmas-plusvalia-tipo` (tipo_plusvalia, ES-05-35016, 2022-06-01 → sin fin)
  - Cargado: `{"rate": 0.3}`
  - Fuente: https://www.laspalmasgc.es/export/sites/laspalmasgc/.galleries/documentos-normativa/Ordenanza-Impuesto-Incremento-Valor-Terrenos-N.-Urbana.pdf
  - Nota: Ordenanza Fiscal del IIVTNU del Ayuntamiento de Las Palmas de Gran Canaria, art. 8.1: «El tipo de gravamen del impuesto será del 30 %». Texto vigente tras la aprobación definitiva de 27/05/2022 (BOP de Las Palmas núm. 66, 01/06/2022, en vigor el 01/06/2022); las modificaciones posteriores (BOP 2023, 2024 y 2025) solo actualizan los coeficientes. Fecha de inicio = BOP de 01/06/2022; el 30 % puede venir de antes (por verificar).
- [ ] `santa-cruz-tenerife-plusvalia-tipo` (tipo_plusvalia, ES-05-38038, 2022-07-05 → sin fin)
  - Cargado: `{"rate": 0.3}`
  - Fuente: https://sede.santacruzdetenerife.es/fileadmin/user_upload/Sede/normativas/Ordenanzas_fiscales/OF_PLUSVALIA_CONSOLIDADO_2022.pdf
  - Nota: Ordenanza Fiscal del IIVTNU del Ayuntamiento de Santa Cruz de Tenerife, art. 7: «el tipo impositivo de un 30 por 100». Texto consolidado tras la modificación cuya aprobación definitiva se publicó en el BOP de Santa Cruz de Tenerife núm. 80 (04/07/2022); la ordenanza entra en vigor al día siguiente de su publicación. No se ha comprobado que no haya modificaciones posteriores a 2022.

**Pendiente o dudoso:**
- Vivienda nueva: en Canarias no hay IVA sino IGIC, 7 %, cargado como `iva_vivienda_nueva` en ES-05 con una nota. No se ha encontrado desde cuándo rige el 7 %.
- AJD del 1 %: depende de que la entrega de vivienda nueva no esté exenta de IGIC; si lo estuviera, sería el 0,75 %.
- No hay texto consolidado oficial del DL 1/2009 posterior a 2019: los arts. 31 y 36 salen de la copia de Hacienda (2019) más las leyes que los reforman.
- Escala del IRPF anterior a 2024 sin cargar.
- Turismo: faltan el régimen transitorio, los límites por sección electoral y las ordenanzas municipales de la Ley 6/2025.
- Plusvalías: las fechas de inicio son las de publicación (el 30 % puede venir de antes); en Santa Cruz no se han comprobado cambios después de 2022.
