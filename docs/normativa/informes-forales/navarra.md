# Fiscalidad foral de Navarra para un particular que compra un piso, lo alquila y lo vende

Fecha de la investigación: 2026-11-03. Todo sale de textos oficiales leídos en esta sesión.
Fuentes principales:
- Texto consolidado del IRPF (Decreto Foral Legislativo 4/2008): lexnavarra, https://www.lexnavarra.navarra.es/detalle.asp?r=29657
- Reglamento del IRPF (Decreto Foral 174/1999): lexnavarra, https://www.lexnavarra.navarra.es/detalle.asp?r=10615
- Texto refundido del ITP y AJD (Decreto Foral Legislativo 129/1999): lexnavarra, https://www.lexnavarra.navarra.es/detalle.asp?r=28044
- Ley Foral 2/1995 de Haciendas Locales: lexnavarra, https://www.lexnavarra.navarra.es/detalle.asp?r=540
- Leyes forales modificadoras, en el BOE: Ley Foral 22/2023 (BOE-A-2024-1694) y Ley Foral 17/2025 (BOE-A-2026-3910).

Robots.txt (cada uno leído en un comando aparte antes de descargar):
- boe.es: sin bloqueo a ClaudeBot, Claude-Web ni anthropic-ai.
- lexnavarra.navarra.es: fichero vacío (200, 0 bytes).
- bon.navarra.es: solo bloquea `/texto/` y listados. La URL `/es/anuncio/-/texto/...` no está bloqueada.
- pamplona.es: solo bloquea rutas técnicas.
- ine.es: solo bloquea `/cgi-bin/`, `/buscar/` y similares.
- navarra.es: devuelve una página HTML, no un robots.txt.
- iustel.com: tiene señales de contenido restrictivas. No he descargado nada de él (ver punto 1, sobre la imagen de la escala).

El texto consolidado de lexnavarra ya incorpora la Ley Foral 17/2025 (por ejemplo, los tramos de mínimo personal `c'), d') y e')`). Lo tomo como vigente a 2026-11-03.
No he encontrado ninguna ley foral posterior que cambie IRPF, ITP ni Haciendas Locales. No lo he podido descartar con certeza por el BON.

---

## 1. IRPF, estructura: una sola escala foral

No hay parte estatal y autonómica. La cuota íntegra es la suma de una escala sobre la base liquidable general y otra sobre la base liquidable especial del ahorro.

Cita, artículo 58 del TR: «La cuota íntegra del impuesto se obtendrá por la suma de las cuotas resultantes de la aplicación de lo dispuesto en los artículos 59 y 60 de esta Ley Foral.»

Escala general: artículo 59.1, redacción de la Ley Foral 22/2023, artículo «Ocho», con efectos desde 2024-01-01 (BOE-A-2024-1694, pág. 11162).
- La consolidada de lexnavarra la publica como imagen alojada en iustel.com. Por eso la tabla está transcrita del BOE, que reproduce el texto oficial del BON (BON n.º 269, de 29-12-2023).
- La Ley Foral 17/2025 no toca el artículo 59 de este texto. Hacienda no ha publicado otra tarifa que yo haya encontrado.
- La escala vale, por tanto, para 2024, 2025 y 2026, salvo que exista una modificación que no he localizado.

| Base liquidable hasta (€) | Cuota íntegra (€) | Resto base hasta (€) | Tipo (%) |
|---|---|---|---|
| 0 | 0 | 4.458 | 13,00 |
| 4.458 | 579,54 | 5.572 | 22,00 |
| 10.030 | 1.805,38 | 11.145 | 25,00 |
| 21.175 | 4.591,63 | 14.488 | 28,00 |
| 35.663 | 8.648,27 | 15.603 | 36,50 |
| 51.266 | 14.343,37 | 15.603 | 41,50 |
| 66.869 | 20.818,61 | 22.290 | 44,00 |
| 89.159 | 30.626,21 | 50.151 | 47,00 |
| 139.310 | 54.197,18 | 55.724 | 49,00 |
| 195.034 | 81.501,94 | 139.310 | 50,50 |
| 334.344 | 151.853,49 | resto de base | 52,00 |

Detalles del artículo 59:
- Apartado 2: el tipo medio se expresa con dos decimales.
- Apartado 3: anualidades por alimentos a hijos. La escala se aplica por separado a la anualidad y al resto de la base. Límite de 6.000 € por hijo (8.000 € si discapacidad ≥ 33 %).

## 2. IRPF, base del ahorro

Artículo 60 (texto consolidado de lexnavarra): «La base liquidable especial del ahorro se gravará a los tipos que se indican en la siguiente escala»

| Base hasta (€) | Cuota íntegra (€) | Resto hasta (€) | Tipo (%) |
|---|---|---|---|
| 0 | 0 | 6.000 | 20 |
| 6.000 | 1.200 | 4.000 | 22 |
| 10.000 | 2.080 | 5.000 | 24 |
| 15.000 | 3.280 | 185.000 | 26 |
| 200.000 | 51.380 | 100.000 | 27 |
| 300.000 | 78.380 | resto | 28 |

Es la misma escala para 2025 y 2026. No he localizado la ley que fijó el 28 % del último tramo.

Qué va a la base del ahorro (artículo 54.1):
- a) Rendimientos del capital mobiliario de los artículos 28 y 29, y los apartados 1.º y 2.º y la letra e) del 3 del artículo 30.
- b) «Por los incrementos y disminuciones de patrimonio que se pongan de manifiesto con ocasión de transmisiones de elementos patrimoniales.»
- También las subvenciones en capital por adquisición o rehabilitación de vivienda habitual.

Compensación (artículo 54.2):
- Un saldo negativo de una letra se compensa con el saldo positivo de la otra con el límite del 25 % de ese saldo positivo.
- El resto se arrastra 4 años.

## 3. IRPF, mínimos personales y familiares: son deducciones de la cuota, no reducciones de la base

Son «deducciones personales y familiares» del artículo 62.9. Se restan de la cuota íntegra, y la cuota líquida no puede ser negativa (artículo 61: «La cuota líquida del impuesto se obtendrá practicando en la íntegra las deducciones que procedan [...] sin que en ningún caso pueda resultar negativa»).

No hay «escala sobre el mínimo». Son importes fijos en euros. No hay un orden de aplicación entre cuota general y del ahorro: la cuota íntegra es única.

Fuente: artículo 62.9 del TR, consolidado de lexnavarra. Los tramos `c'), d') y e')` vienen de la Ley Foral 17/2025, art. «Catorce», efectos 2026-01-01 según su preámbulo.

Mínimo personal (62.9.a), «La deducción por mínimo personal será con carácter general de 1.084 euros anuales por sujeto pasivo.» Incrementos:
- a') 264 € si edad ≥ 65. 585 € si edad ≥ 75.
- b') 766 € si discapacidad ≥ 33 % y < 65 %. 2.757 € si ≥ 65 %.
- c') 1.280 € si las rentas no superan 17.500 €.
- d') 1.280 € menos 0,0904 × (rentas − 17.500) si las rentas están entre 17.500,01 y 30.000 €.
- e') 150 € menos 0,075 × (rentas − 30.000) si las rentas están entre 30.000,01 y 32.000 €.
- «Rentas»: concepto del artículo 64.5. Incluye rendimientos netos, incrementos y disminuciones, sin las reducciones de los artículos 17.2, 25.2 y 25.3, entre otros. La reducción del alquiler NO se tiene en cuenta para este umbral.

Mínimos familiares (62.9.b):
- Ascendiente conviviente con rentas ≤ IPREM: 264 € (≥ 65 años) o 585 € (≥ 75 años).
- Descendiente soltero menor de 30 años, conviviente, con rentas ≤ IPREM:

| Descendiente | € por año |
|---|---|
| 1.º | 483 |
| 2.º | 512 |
| 3.º | 732 |
| 4.º | 981 |
| 5.º | 1.111 |
| 6.º y siguientes | 1.286 |

- Además, 644 € por descendiente menor de 3 años. Adopción internacional: 1.170 €.
- 2.º) Incremento sobre la cuantía del descendiente (62.9.b.b'.2.º):
  - Rentas del sujeto pasivo hasta 20.000 €: +40 %.
  - Entre 20.000,01 y 30.000 €: 40 % menos 50 × (exceso sobre 20.000 / 20.000).
  - Solo si las rentas, incluidas las exentas, no superan 30.000 €.
- Discapacidad del descendiente o ascendiente (c'): 674 € (33–64 %), 2.360 € (≥ 65 %).
- Hay prorrateo por partes iguales entre sujetos pasivos, salvo el incremento 2.º.
- No existe tramo de «menores de 6 años».

Otros límites: artículo 64.1 limita las deducciones de los apartados 4, 6, 8, 12, 13 y 14 del artículo 62 al 25 % de la base liquidable. No afecta a los mínimos.

## 4. IRPF, alquiler de vivienda (lo más importante)

### 4.1 A qué base va

El rendimiento neto del capital inmobiliario no está en el artículo 54 (base del ahorro). Por tanto va a la parte general, artículo 53.a (consolidado de lexnavarra): «El saldo resultante de sumar, sin limitación alguna, en cada periodo impositivo los rendimientos y las imputaciones de renta [...]»

### 4.2 Rendimiento neto y límite de gastos (artículo 25.1 TR)

«El importe total a deducir no podrá exceder, para cada bien o derecho, de la cuantía de los respectivos rendimientos íntegros obtenidos por el arrendamiento o cesión del inmueble o derecho. El exceso se podrá deducir en los cuatro años inmediatos y sucesivos, conjuntamente con los del periodo impositivo correspondiente, y con el límite señalado en este apartado.»

- El límite es TODOS los gastos, incluida la amortización. No solo intereses y reparación.
- El rendimiento neto nunca es negativo. El exceso se arrastra 4 años.
- Si el exceso concurre con gastos del año, «éstos se aplicarán en primer lugar».
- En el Reglamento (artículo 12.2) hay además un límite específico para intereses y gastos de reparación y conservación: no pueden superar los rendimientos íntegros por bien. El exceso va a 4 años.

### 4.3 Reducciones del rendimiento neto positivo (artículo 25.2 TR)

Redacción vigente: Ley Foral 20/2024 (la reducción del 50 %) y Ley Foral 17/2025, art. «Siete», efectos 2025-01-01 (el requisito de registro).

«a) Un 70 por ciento, cuando proceda del arrendamiento de viviendas intermediado a través de la sociedad pública instrumental regulada en el artículo 13 de la Ley Foral 10/2010 [...] El porcentaje [...] será el 90 por ciento cuando el contrato de arrendamiento recaiga sobre viviendas situadas en una zona de mercado residencial tensionado.»

«b) Un 50 por ciento, cuando la vivienda esté situada en una zona de mercado residencial tensionado y el rendimiento proceda del arrendamiento con destino a vivienda permanente regulado en el artículo 2 de la Ley 29/1994 [...] excluyéndose, a estos efectos, los arrendamientos por habitaciones.»

Condición común: «A fecha de devengo del impuesto, el contrato de arrendamiento esté debidamente registrado en el Registro de Contratos de Arrendamiento de Vivienda de Navarra [...] (artículo 90 de la Ley Foral 10/2010)». También: «Las reducciones sólo resultarán aplicables respecto de los rendimientos declarados por el sujeto pasivo.»

Resumen:
- Fuera de zona tensionada y sin intermediación pública: NO hay reducción.
- Zona tensionada, vivienda permanente (LAU art. 2), contrato registrado: reducción del 50 % del rendimiento NETO positivo.
- Intermediado por la sociedad pública: 70 %, o 90 % en zona tensionada.
- El 50 % se aplica sobre el rendimiento NETO (tras gastos), no sobre el íntegro.

Reducción por rendimientos irregulares (25.3): 30 %, tope de 300.000 € de rendimientos íntegros. Se aplica tras la anterior. No es relevante para un alquiler normal.

Antecedente: el Reglamento 13.bis conserva la antigua reducción del 40 % para viviendas arrendadas a 31-12-2017 con contrato terminado antes de 2021. Ya no es aplicable.

### 4.4 Gastos deducibles (artículos 12 y 13 del Reglamento, Decreto Foral 174/1999)

Lista del artículo 12.1:
- a) Intereses de capitales ajenos invertidos en la adquisición o mejora, y demás gastos de financiación.
- b) Tributos y recargos no estatales ni forales, y tasas y contribuciones especiales, si inciden sobre el rendimiento o el bien. Entra el IBI/Contribución Territorial.
- c) Servicios de terceros: administración, vigilancia, portería.
- d) Formalización del arrendamiento y defensa jurídica.
- e) Saldos de dudoso cobro. Se entiende justificado si hay concurso o han pasado más de 6 meses desde la primera gestión de cobro.
- f) Conservación y reparación. No son deducibles las ampliaciones o mejoras.
- g) Primas de seguros (responsabilidad civil, incendio, robo, etc.).
- h) Servicios y suministros.
- i) Amortización.

Amortización (artículo 13.1.a): «cuando, en cada año, no exceda del resultado de aplicar el 3 por 100 sobre el coste de adquisición o mejora satisfecho, sin incluir en el cómputo el del suelo. Cuando no se conozca el valor del suelo, éste se estimará en un 25 por 100 del coste de adquisición satisfecho.»

- La base es el COSTE de adquisición satisfecho, no el valor catastral.
- En el artículo 13 no he visto que incluya los gastos y tributos de la compra. Tampoco los excluye. Ese punto no está resuelto en la fuente leída.
- Mobiliario: tabla de amortizaciones del artículo 26 del Reglamento. No la he extraído.
- El 3 % es un máximo («no exceda»), pero el artículo 27.a del Reglamento considera la amortización mínima como «el importe resultante de la aplicación de los artículos 13 y 18». Es decir, para el valor de adquisición en la venta se resta la del artículo 13 (ver punto 5).

## 5. IRPF, ganancia patrimonial por la venta

Va a la base del ahorro (artículo 54.1.b, cita en el punto 2). Se grava con la escala del artículo 60: 20 % a 28 %.

Valor de adquisición (artículo 41.1 TR): suma de
- a) «El importe real por el que dicha adquisición se hubiere efectuado.»
- b) «El coste de las inversiones y mejoras efectuadas en los bienes adquiridos y los gastos y tributos inherentes a la adquisición, excluidos los intereses, que hubieren sido satisfechos por el adquirente.»
- Y se aplica: «El valor así obtenido se minorará, cuando proceda, en el importe de las amortizaciones que reglamentariamente se determinen.»

Valor de transmisión (artículo 41.2): importe real menos los gastos y tributos de la letra b) satisfechos por el transmitente.

Amortizaciones, Reglamento artículo 39.1: «El valor de adquisición de los elementos patrimoniales transmitidos se minorará en el importe de las amortizaciones fiscalmente deducibles, computándose en todo caso la amortización mínima a que se refiere el artículo 27 de este Reglamento, con independencia de la efectiva consideración de ésta como gasto.»

- Sí se restan las amortizaciones. Se restan aunque no se hubieran deducido.
- Coeficientes de actualización: NO hay para adquisiciones posteriores a 1994. El TR solo regula la disposición transitoria para elementos adquiridos antes de 31-12-1994, y no la he desarrollado por irrelevante.
- Compensación entre signos: ver punto 2 (25 % cruzado, arrastre 4 años).
- Exención por reinversión (artículo 45) y vivienda habitual (Reglamento 40): no aplican a un piso de inversión.

## 6. ITP

Artículo 8.1.a) del TR del ITP: «El 6 por ciento, si se trata de transmisiones de bienes inmuebles, así como la constitución y cesión de los derechos reales que recaigan sobre los mismos, excepto los derechos reales de garantía.»

- Tipo único del 6 %, sin tramos.
- Reducidos de vivienda (no aplican al caso general): 5 % (familia con dos o más hijos, base máxima 180.304 €) y 4 % (vivienda habitual en municipio en riesgo de despoblación).
- Constitución de derechos de garantía, préstamos y fianzas: 1 % (artículo 8.1.d). Bienes muebles: 4 %.
- La Ley Foral 17/2025, artículo quinto, solo toca valoraciones de pensiones y exenciones de alojamientos colaborativos. No cambia los tipos.
- Fecha de efectos: no la he extraído; el tipo es el del texto consolidado vigente.

## 7. AJD, escritura de compra de vivienda nueva sujeta a IVA

Artículo 22.2 del TR del ITP y AJD: «Las primeras copias de escrituras y actas notariales, cuando tengan por objeto cantidad o cosa valuable, contengan actos o contratos inscribibles en los Registros [...] y no sujetos al Impuesto sobre Sucesiones y Donaciones o a los conceptos comprendidos en los números 1.º y 2.º del apartado 1 del artículo 1 [...] tributarán, además, al tipo de gravamen del 0,5 por 100.»

- Compra de vivienda nueva con IVA repercutido: 0,5 %.
- Excepción en el mismo artículo: si se ha renunciado a la exención del IVA (artículo 17.2 de la Ley Foral del IVA), el tipo es del 1 %. No es el caso de una vivienda nueva que ya está sujeta y no exenta.
- Además, papel timbrado de 0,15 € por folio (artículo 22.1).

## 8. Zonas de mercado residencial tensionado

Declaración: Orden Foral 157E/2025, de 19 de mayo, de la consejera de Vivienda, Juventud y Políticas Migratorias. BON n.º 118, de 13-06-2025. URL: https://bon.navarra.es/es/anuncio/-/texto/2025/118/36

Cita, apartado 2.º: «Declarar los municipios de Pamplona / Iruña, Tudela, Valle de Egüés / Eguesibar, Burlada / Burlata, Barañáin / Barañain, Zizur Mayor, Estella-Lizarra, Aranguren, Berriozar, Tafalla, Ansoáin / Antsoain, Villava / Atarrabia, Corella, Valle de Elorz / Elortzibar, Cintruénigo, Baztan, Altsasu / Alsasua, Huarte / Uharte, Berrioplano / Berriobeiti, San Adrián, Peralta / Azkoien como zona de mercado residencial tensionado en Navarra [...]»

Vigencia, apartado 5.º: tres años desde el día siguiente a su publicación en el BON (13-06-2025, por tanto desde 14-06-2025). Prórroga por periodos anuales si persisten las circunstancias.

Resolución del Ministerio (Secretaría de Estado de Vivienda y Agenda Urbana), de 28-07-2025: BOE n.º 181, de 29-07-2025 (BOE-A-2025-15728). Recoge la declaración, con vigencia de «tres años desde el día siguiente a la publicación de la presente resolución» y la limitación del artículo 17.7 de la LAU («Sí, conforme a la Orden Foral 157E/2025»). Esto da un plazo que acaba hacia 2028-07-30. Hay discrepancia de unos 6 semanas entre el cómputo del BON (desde junio) y el del BOE (desde julio). No lo he resuelto.

Códigos INE (comprobados en el diccionario del INE «diccionario26.xlsx», https://www.ine.es/daco/daco42/codmun/diccionario26.xlsx):

| Municipio | INE |
|---|---|
| Altsasu/Alsasua | 31010 |
| Ansoáin/Antsoain | 31016 |
| Aranguren | 31023 |
| Baztan | 31050 |
| Burlada/Burlata | 31060 |
| Cintruénigo | 31072 |
| Corella | 31077 |
| Valle de Egüés/Eguesibar | 31086 |
| Valle de Elorz/Elortzibar | 31088 |
| Estella-Lizarra | 31097 |
| Huarte/Uharte | 31122 |
| Pamplona/Iruña | 31201 |
| Peralta/Azkoien | 31202 |
| San Adrián | 31215 |
| Tafalla | 31227 |
| Tudela | 31232 |
| Villava/Atarrabia | 31258 |
| Barañáin/Barañain | 31901 |
| Berrioplano/Berriobeiti | 31902 |
| Berriozar | 31903 |
| Zizur Mayor/Zizur Nagusia | 31907 |

Son 21. Ámbito: municipio completo, no barrios. El anexo de la propia orden, que responde a una alegación sobre desglose por barrios de Pamplona, defiende el análisis a nivel de término municipal completo (apartado 4.7 del anexo).

Gran tenedor (apartado 3.º de la orden): más de diez inmuebles urbanos residenciales o más de 1.500 m² de uso residencial, o cinco o más inmuebles residenciales dentro de la zona (según la reproducción del BOE).

No he comprobado si hay modificaciones posteriores a la orden (ampliaciones o bajas). No he encontrado ninguna.

Importante para el cálculo: los municipios con el 50 % de reducción del punto 4.3 son estos 21. Pamplona entra.

## 9. Alquiler turístico

- Norma: Decreto Foral 230/2011, de 26 de octubre, Reglamento de ordenación de los apartamentos turísticos. https://www.lexnavarra.navarra.es/detalle.asp?r=25034 Desarrolla la Ley Foral 7/2003, de 14 de febrero, de Turismo.
- Artículo 3, modalidad «Vivienda Turística»: «a) Superficie útil mínima de 90 m². b) Acceso independiente. c) Segregación vertical.»
- Estancia de temporada: ocupación continua igual o inferior a tres meses (artículo 2).
- Inscripción previa en el Registro de Turismo de Navarra mediante declaración responsable.
- No he comprobado que la página de lexnavarra sea la versión consolidada. No he comprobado si una norma posterior sustituye a la Ley Foral 7/2003. Queda PENDIENTE.
- Capital: la modificación del artículo 28 del Plan Municipal de Pamplona (y de los artículos 87 y 88 del PEPRI del Casco Antiguo) sobre «residencia eventual». Solo tengo la nota de prensa municipal de 2019 (https://www.pamplona.es/en/node/31044), con estos criterios: no más de un establecimiento de residencia eventual por edificio y suma de superficies no superior a 200 m² en edificios residenciales colectivos con acceso compartido. PENDIENTE: el texto aprobado y su fecha de publicación en el BON no los he leído.
- Una modificación puntual del PEPRI del Casco Antiguo de 2024 se menciona en una página municipal. No la he leído. PENDIENTE.

## 10. IBI y plusvalía de Pamplona/Iruña (INE 31201)

### Contribución Territorial (equivalente al IBI)

- Marco foral, Ley Foral 2/1995, artículo 139.2: «El tipo de gravamen deberá estar comprendido entre el 0,25 y el 0,50 por 100. El tipo de gravamen será único para todo el término municipal.»
- Pamplona, Ordenanza fiscal n.º 1, publicada en 2025-12 (https://www.pamplona.es/sites/default/files/2025-12/Ordenanza%201.pdf), artículo 4: «Tipo de gravamen: 0,25%.» Es el mínimo legal. No distingue uso residencial. Es único.
- Base imponible: valor catastral (Ley Foral 2/1995, artículo 138). Comparación con el TRLRHL estatal: no leído en esta sesión, PENDIENTE.
- Fecha de efectos: ejercicio 2026. La publicación en el BON de la ordenanza (fechas de diciembre de 2025) no la he leído en el BON. PENDIENTE.

### Plusvalía municipal (Impuesto sobre el Incremento del Valor de los Terrenos)

- Ordenanza fiscal n.º 4 de Pamplona (https://www.pamplona.es/sites/default/files/2025-12/Ordenanza%204%20.pdf).
- Tipo, Anexo de tarifas: «TIPO DE GRAVAMEN: 17,35%.»
- Coeficientes, artículo 6 y anexo: son «los coeficientes máximos permitidos para cada periodo de generación y vigentes en cada momento de acuerdo con el artículo 175.2 de la Ley Foral 2/1995». Es decir, los máximos forales.
- Base imponible: valor del terreno según la Ponencia de Valores por el coeficiente del periodo de generación (artículo 5). Periodo máximo de 20 años, años completos.
- No sujeción si no hay incremento real (artículo 2.4). Se compara valor de adquisición y de transmisión sin gastos ni tributos. Y opción de la base real más baja (artículo 5.7).
- Marco foral, Ley Foral 2/1995, artículo 176.2: «La escala de gravamen será fijada por el Ayuntamiento, sin que el tipo mínimo pueda ser inferior al 8 por 100 ni el tipo máximo pueda superar el 25 por 100.» El 17,35 % de Pamplona queda dentro.
- Coeficientes máximos del artículo 175.2, tal como constan en el texto consolidado de lexnavarra. La tabla tiene una apariencia irregular (no es monótona) y puede ser la tabla base sin actualizar:

| Periodo de generación | Coeficiente |
|---|---|
| Inferior a 1 año | 0,06 |
| 1 año | 0,16 |
| 2 años | 0,13 |
| 3 años | 0,26 |
| 4 años | 0,35 |
| 5 años | 0,37 |
| 6 años | 0,35 |
| 7 años | 0,41 |
| 8 años | 0,47 |
| 9 años | 0,52 |
| 10 años | 0,58 |
| 11 años | 0,53 |
| 12 años | 0,42 |
| 13 años | 0,37 |
| 14 años | 0,31 |
| 15 años | 0,26 |
| 16 años | 0,25 |
| 17 años | 0,15 |
| 18 años | 0,06 |
| 19 años | 0,06 |
| 20 años o más | 0,16 |

- El mismo artículo dice: «Estos coeficientes máximos serán actualizados anualmente con arreglo a lo establecido en el artículo 58.2». No he encontrado la norma foral que los actualiza para 2026. PENDIENTE: confirmar los máximos de 2026 en el BON o en la web de Hacienda de Navarra. Si la ordenanza usa «los máximos vigentes», la cifra de 2026 puede diferir de esta tabla.
- Fuente de la tabla: https://www.lexnavarra.navarra.es/detalle.asp?r=540, artículo 175, con nota de vigencia.

## 11. Extra: estructura de la Ley Foral de Haciendas Locales frente al TRLRHL estatal

Resumen de lo leído, solo de la Ley Foral 2/1995:
- La contribución territorial (artículo 133 y siguientes) usa un único tipo por municipio entre 0,25 % y 0,50 % (art. 139.2). El valor catastral viene del Catastro foral.
- Reducciones de la base si la Ponencia sube el promedio más de un 25 % (artículo 138.2 a 138.7): el Pleno puede aprobar una reducción lineal de máximo tres años.
- Bonificación del 90 % de la cuota para inmuebles de empresas de urbanización, construcción y promoción que no sean inmovilizado (artículo 140.1).
- La plusvalía (artículos 172 a 178): periodo máximo de 20 años, coeficiente por años completos, tipo o escala municipal entre 8 % y 25 %, y la regla de no sujeción cuando no hay incremento real, incorporadas tras la STC 182/2021 por la Ley Foral 20/2021.
- Pamplona usa el mínimo del IBI (0,25 %) y un 17,35 % en la plusvalía, con los coeficientes máximos forales.

---

## Lo que no he podido leer en fuente oficial (PENDIENTE)

1. Imagen de la escala del artículo 59: en lexnavarra es una imagen de iustel.com. Transcrita del BOE (Ley Foral 22/2023). No he descargado nada de iustel.
2. Que no exista ninguna ley foral de 2026 que modifique el IRPF: no lo he podido comprobar en el BON.
3. Texto aprobado del artículo 28 del Plan Municipal de Pamplona sobre alquiler turístico y su publicación en el BON.
4. Coeficientes máximos 2026 de la plusvalía y la norma que los actualiza.
5. Fecha de publicación en el BON de las ordenanzas fiscales de Pamplona 2026.
6. Comparación con el TRLRHL estatal del IBI: no leído.
7. Si la base de amortización del Reglamento (artículo 13) incluye los gastos y tributos de la compra: no lo aclara el texto leído.
8. Tabla de amortización de mobiliario (artículo 26 del Reglamento): no extraída.
9. Normativa turística posterior a la Ley Foral 7/2003 y consolidación del Decreto Foral 230/2011: no verificada.

---

## Resumen para el diseño

Diferencias con el IRPF común que obligan a cambiar el motor:

1. **Una sola escala foral**, de 11 tramos (13 % a 52 %) sobre la base liquidable general. No hay suma de escala estatal y autonómica. Hay que parametrizar «estructura de escalas» como lista de escalas con su cuota íntegra, no como par fijo estatal + autonómica.

2. **Mínimos: deducciones fijas en euros de la cuota**, no «escala sobre el mínimo». Mínimo personal de 1.084 € más incrementos por edad, discapacidad y un tramo por renta (hasta 32.000 €). Mínimos familiares por orden de descendiente (483, 512, 732, 981, 1.111, 1.286), con incremento porcentual por renta. El «umbral de renta» excluye la reducción del alquiler.

3. **Alquiler**: sigue en la base general, pero la reducción NO es del 50/60 % general. Solo hay reducción del 50 % del neto en zona tensionada (21 municipios, vivienda permanente, contrato inscrito en el Registro de Navarra) o 70 %/90 % con intermediación pública. Fuera de eso: ninguna. Hace falta una entrada «zona tensionada» y «contrato registrado» por oferta.

4. **Límite de gastos**: el tope es el rendimiento íntegro de ese inmueble sobre TODOS los gastos, incluida la amortización (no solo intereses + reparación). El neto no puede ser negativo. El exceso se arrastra 4 años. Además hay un tope específico para intereses y reparación (Reglamento 12.2). Amortización del 3 % sobre el coste sin suelo (suelo 25 % si no se conoce).

5. **Ganancia en la base del ahorro** con una única escala foral del 20 % al 28 % (no estatal + autonómica). Valor de adquisición con gastos y tributos y restando la amortización mínima aunque no se dedujera. Sin coeficientes de actualización. Compensación cruzada con la base general al 25 %.

6. **Impuestos de compra**: ITP al 6 % único. AJD de vivienda nueva con IVA al 0,5 %.

7. **Locales**: la Contribución Territorial (tipo único municipal, 0,25 %–0,50 %) y la plusvalía (tipo 8 %–25 % y coeficientes de los artículos 175–176) tienen estructura propia.
