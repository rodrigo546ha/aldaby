# Fiscalidad foral de Bizkaia para un particular que compra un piso para alquilarlo y lo vende (informe a 2026-11-03)

Todas las cifras salen de textos oficiales que he leído y descargado (PDF consolidados de la Hacienda Foral de Bizkaia, BOB, BOPV, BOE, INE). Donde no pude leer fuente oficial pone PENDIENTE.

## 0. Fuentes y robots.txt

| Dominio | robots.txt | Uso |
|---|---|---|
| www.bizkaia.eus | leído; sin bloqueo a ClaudeBot/Claude-Web/anthropic-ai; los Disallow no afectan a `/documents/` ni `/lehendakaritza/Bao_bob/` | descargas de normas y BOB |
| www.boe.es | leído; sin bloqueo | resoluciones trimestrales de zonas tensionadas |
| www.euskadi.eus | leído; sin bloqueo | BOPV (órdenes de zonas tensionadas y decretos turísticos) |
| www.ine.es | leído; sin bloqueo | diccionario de municipios 2026 |
| www.bilbao.eus | leído: grupo `User-agent: *` con `Disallow: /` | NO descargado. IBI y plusvalía de Bilbao quedan PENDIENTES |
| zonatensionadaeuskadi.eus | sin robots.txt (respuesta vacía); redirige (301) a eremutentsionatua.euskadi.eus | no descargado |

Aviso de método: fiscal-impuestos.com, guiafiscal.es y ey.com los consulté con WebFetch sin leer antes su robots.txt. Solo los usé como pista para localizar fuentes oficiales; ninguna cifra de este informe sale de ellos. El robots.txt de ey.com lo leí después y permite `anthropic-ai`. No toqué el repositorio.

Ficheros oficiales usados (todos descargados y leídos):

- IRPF, Norma Foral 13/2013 (consolidado "Actualizado a fecha de: 01/01/2026"): https://www.bizkaia.eus/documents/880307/15187815/ca_13_2013.pdf/ce52e403-4fca-9ef7-bf85-2505ba29f921?t=1784098584068
- IRPF, Norma Foral 13/2013 (consolidado "Actualizado a fecha de: 18/09/2025", para comparar con 2025): https://www.bizkaia.eus/documents/880307/27501802/ca_13_2013.pdf/99c24b02-2b3e-821f-a6c5-5a62df447e32?t=1770098453680
- Reglamento del IRPF, DF 47/2014 (última modificación 23/03/2026): https://www.bizkaia.eus/documents/880307/15187815/ca_47_2014.pdf/c17e2f7e-e4dd-789c-235e-21add02afe5e?t=1776061527586
- NF 2/2025, de 9 de abril, de revisión fiscal (BOB 22-04-2025): https://www.bizkaia.eus/lehendakaritza/Bao_bob/2025/04/22/I-441_cas.pdf
- NF 7/2025, de 29 de diciembre, de Presupuestos 2026 (BOB núm. 248, 30-12-2025): https://www.bizkaia.eus/fitxategiak/05/ogasuna/presupuestos/pdf/2026/1767079012129_NF%20Pptos%202026%20castellano-euskara.pdf (cve BOB-2025a248-(I-1446))
- DF 133/2025, de 29 de diciembre, reforma del Reglamento del IRPF (BOB 30-12-2025): https://www.bizkaia.eus/lehendakaritza/Bao_bob/2025/12/30/I-1406_cas.pdf
- DF 115/2025, de 4 de diciembre, coeficientes de actualización 2026 (BOB 15-12-2025): https://www.bizkaia.eus/documents/880307/15187815/ca_115_2025.pdf/0d24ed39-496c-f103-c367-393052ab38ac?t=1768024831410
- ITP y AJD, NF 1/2011 (última modificación 20/04/2026): https://www.bizkaia.eus/documents/880307/15187815/ca_1_2011.pdf/50b78491-3852-b68f-f9d5-2db574a48917?t=1777386142905
- Impuesto sobre Sociedades, NF 11/2013 (para el período de amortización de inmuebles; actualizado a 01/01/2025): https://www.bizkaia.eus/documents/880307/27501806/ca_11_2013.pdf/91f33826-13ce-3625-f9e5-e7f2fe2482a1?t=1770098466884
- IBI, NF 4/2016 (última modificación 01/01/2026): https://www.bizkaia.eus/documents/880307/15187815/ca_4_2016.pdf/b4906321-beed-8855-3c54-df87b6e99d21?t=1768551489728
- Plusvalía, NF 8/1989 (última modificación 01/01/2025): https://www.bizkaia.eus/documents/880307/15187815/ca_8_1989.pdf/022bd3c2-b768-cdff-fb26-77d630c61ba5?t=1746526040210

Nota sobre el consolidado: el PDF "18/09/2025" todavía muestra la escala del ahorro antigua (5 tramos), porque la nueva (NF 2/2025, art. 15.Tres) tiene efectos desde 2026. El consolidado "01/01/2026" ya la recoge.

---

## 1. IRPF, estructura y escala general

**Estructura.** Hay una sola escala sobre la base liquidable general, sin tramo estatal y autonómico. Art. 74 NF 13/2013: «la cuota íntegra será la suma de las siguientes cantidades: La resultante de aplicar escala de gravamen del apartado 1 del artículo siguiente a la base liquidable general. Este importe se reducirá conforme a lo previsto en el artículo 77 […] y en ningún caso podrá resultar negativo.» Se suma la escala del ahorro (art. 76).

**Escala general 2026** (art. 75.1 NF 13/2013, redacción del art. 49 NF 7/2025, «Con efectos desde 1 de enero de 2026»). Esto es una deflactación del 2 % sobre 2025.

| Base liquidable general hasta | Cuota íntegra acumulada | Resto hasta | Tipo |
|---|---|---|---|
| 0 | 0 | 18.080 | 23 % |
| 18.080 | 4.158,40 | 18.080 | 28 % |
| 36.160 | 9.220,80 | 18.080 | 35 % |
| 54.240 | 15.548,80 | 23.210 | 40 % |
| 77.450 | 24.832,80 | 29.810 | 45 % |
| 107.260 | 38.247,30 | 35.700 | 46 % |
| 142.960 | 54.669,30 | 65.430 | 47 % |
| 208.390 | 85.421,40 | en adelante | 49 % |

**Escala general 2025** (art. 75.1 en el consolidado a 18/09/2025): tramos 17.720 / 35.440 / 53.160 / 75.910 / 105.130 / 140.130 / 204.270, con los mismos tipos (23, 28, 35, 40, 45, 46, 47, 49 %) y cuotas acumuladas 4.075,60 / 9.037,20 / 15.239,20 / 24.339,20 / 37.488,20 / 53.588,20 / 83.734,00.

**Pendiente de futuro (no vigente).** La prensa indica una deflactación del 3 % para 2027. No la he visto en texto oficial.

---

## 2. IRPF, base del ahorro

**Escala 2026** (art. 76.1 NF 13/2013, redacción del art. 15.Tres NF 2/2025). Efectos: «Lo dispuesto en el apartado Tres del artículo 15 tendrá efectos a partir de 1 de enero de 2026» (Disp. final tercera NF 2/2025). El texto dice «Con efectos desde 1 de enero de 2025» en el encabezado del art. 15, pero la disposición final lo corrige a 2026.

| Base liquidable del ahorro hasta | Cuota íntegra acumulada | Resto hasta | Tipo |
|---|---|---|---|
| 0 | 0 | 7.500 | 19 % |
| 7.500 | 1.425 | 7.500 | 20 % |
| 15.000 | 2.925 | 15.000 | 22 % |
| 30.000 | 6.225 | 20.000 | 24 % |
| 50.000 | 11.025 | 40.000 | 25,5 % |
| 90.000 | 21.225 | 30.000 | 26 % |
| 120.000 | 29.025 | 120.000 | 26,5 % |
| 240.000 | 60.825 | 60.000 | 27 % |
| 300.000 | 77.025 | en adelante | 28 % |

**Escala 2025** (consolidado a 18/09/2025, art. 76): hasta 2.500 al 20 %; 2.500,01–10.000 al 21 %; 10.000,01–15.000 al 22 %; 15.000,01–30.000 al 23 %; más de 30.000 al 25 %.

**Qué rentas van a la base del ahorro** (art. 63 NF 13/2013, íntegro):
- «a) Los rendimientos del capital inmobiliario procedentes de viviendas a las que se refieren los apartados 2, 3, 4 y 5 del artículo 32».
- «b) Los rendimientos del capital mobiliario previstos en los artículos 34, 35 y 36».
- «c) Las ganancias y pérdidas patrimoniales que se pongan de manifiesto con ocasión de transmisiones de elementos patrimoniales».

Por eso el alquiler de vivienda con arrendamiento de la LAU va a la base del ahorro, no a la general. Todo lo que no sea art. 32.2 a 32.5 (art. 32.1 y 32.6) va a la general (art. 62: rentas que no sean del ahorro).

**Integración y compensación en la base del ahorro** (art. 66.1 NF 13/2013). Hay dos compartimentos que no se mezclan:
- Rendimientos (letras a y b del art. 63): un saldo negativo se compensa con saldos positivos de esos mismos rendimientos en los cuatro años siguientes.
- Ganancias y pérdidas patrimoniales (letra c): un saldo negativo se compensa con saldos positivos de ganancias en los cuatro años siguientes.

Base liquidable del ahorro (art. 67.3): la base imponible del ahorro menos el remanente, si lo hay, de la reducción del art. 69 (pensiones compensatorias y alimentos), sin poder ser negativa.

---

## 3. IRPF, mínimos personales y familiares

**No hay un «mínimo personal» como reducción de la base ni como escala sobre el mínimo.** El equivalente del mínimo del contribuyente es una **minoración de cuota** sobre la cuota de la escala general. Art. 77 NF 13/2013 (redacción art. 50 NF 7/2025): «Los y las contribuyentes aplicarán una minoración de cuota de 1.615 euros por cada declaración, conforme a lo previsto en el artículo 74». Según el art. 74 solo reduce el importe de la escala general y «en ningún caso podrá resultar negativo»; no reduce la cuota del ahorro. En 2025 eran 1.583 euros.

**Mínimos familiares: son deducciones en la cuota líquida** (arts. 78 a 83), no reducciones de la base. Art. 78: «cuota líquida la cantidad resultante de minorar la cuota íntegra en el importe de las deducciones […]. En ningún caso la cuota líquida podrá ser negativa». Se aplican contra la cuota íntegra total (general más ahorro); la norma no los limita a la cuota general.

Importes 2026 (NF 7/2025, arts. 51 a 54, efectos 01-01-2026) y 2025 entre paréntesis (consolidado 18/09/2025):

| Concepto | 2026 | 2025 |
|---|---|---|
| Descendientes que conviven, 1.º | 682 | 668 |
| 2.º | 844 | 827 |
| 3.º | 1.421 | 1.393 |
| 4.º | 1.680 | 1.647 |
| 5.º y siguientes | 2.195 | 2.151 |
| Complemento por descendiente menor de 6 años (se suma) | 394 | 386 |
| Ascendiente que convive todo el año (art. 81) | 328 | 321 |
| Edad > 65 años (art. 83.1), con base imponible ≤ 20.000 | 393 | 385 |
| Edad > 75 años (mismo requisito) | 714 | 700 |
| Edad, base imponible entre 20.000 y 30.000 | 393 (o 714) menos 0,0393 (o 0,0714) × (BI − 20.000) | |
| Discapacidad o dependencia (art. 82): ≥33 % y <65 % / ≥65 % o grado I / grado II / grado III | 906 / 1.294 / 1.552 / 1.935 | |
| Reducción por tributación conjunta (art. 73), de la base general | 4.896 | 4.800 |

No existe el tramo «menores de 3 años». Solo existe el de menores de 6. La deducción por descendientes tiene exclusiones (más de 30 años, rentas superiores al SMI, etc.; art. 79.3).

---

## 4. IRPF, alquiler de vivienda (lo más importante)

Norma: art. 32 NF 13/2013 (redacción del art. 3.Uno NF 2/2025, «Con efectos desde 1 de enero de 2025»). El consolidado a 01/01/2026 mantiene el texto. Desarrollo: arts. 36 a 38 del Reglamento, redacción DF 133/2025 (BOB 30-12-2025).

**Cambio de modelo.** Para vivienda alquilada conforme a la LAU no hay gastos deducibles generales, ni amortización, ni reparaciones, ni IBI, ni comunidad, ni seguro de hogar. Se aplica una bonificación sobre el rendimiento íntegro y solo se deducen los intereses. Está en lugar de la reducción del 50/60 % del IRPF común.

**Art. 32.2** (arrendamiento de vivienda «en los términos del artículo 2 de la Ley 29/1994», es decir, arrendamiento de vivienda con la LAU de uso habitual):
- «se aplicará una bonificación del 30 por 100 sobre los rendimientos íntegros obtenidos por cada inmueble».
- «Asimismo, será deducible, exclusivamente: a) El importe de los intereses de los capitales ajenos invertidos en la adquisición, rehabilitación o mejora […] y demás gastos de financiación» (se restan subvenciones exentas recibidas); «b) El importe de las primas de seguros de crédito que cubran total o parcialmente el impago de las rentas […] con el límite de 300 euros».
- «La suma de la bonificación y los gastos deducibles no podrá dar lugar, para cada inmueble, a un rendimiento neto negativo.»

Fórmula: neto = máx(0, íntegro × (1 − 0,30) − intereses y financiación − seguro de impago hasta 300 €). La bonificación es sobre el íntegro (el cobrado del arrendatario sin IVA, art. 30.2), no sobre el neto. No hay límite máximo de intereses. El único límite es que el neto no sea negativo, por inmueble. Un neto negativo no se arrastra: el exceso de intereses se pierde. No encontré en esas normas un arrastre de intereses no deducidos. Es una diferencia importante con el IRPF común, donde el límite de intereses más reparación arrastra el exceso cuatro años.

**Bonificaciones mayores con la misma estructura de gastos:**
- Art. 32.4: arrendamiento LAU «situada en una zona declarada de mercado residencial tensionado y la renta de alquiler se limite a los importes que se correspondan con los índices de referencia»: bonificación del 70 %. Gastos deducibles: los mismos intereses y el seguro de impago hasta 300 €.
- Art. 32.5: la misma regla del 70 % cuando «la persona arrendadora haya limitado la renta de alquiler a los importes que se correspondan con los índices de referencia o precios de intermediación pública» (aunque no esté en zona tensionada). Lo mismo se aplica al art. 32.3.
- Art. 32.3: programas del Gobierno Vasco (Bizigune, ASAP, etc.): bonificación del 70 %; solo intereses deducibles.
- Art. 32.1: viviendas distintas de las anteriores (por ejemplo, no cedidas bajo la LAU) sin actividad económica: bonificación del 20 %; solo intereses deducibles; este rendimiento va a la base GENERAL (art. 63.a no lo incluye).
- Art. 32.6: lo demás (locales, plazas de garaje aisladas y similares): gastos reales necesarios más amortización efectiva (DF 133/2025, art. 37: «todos los gastos necesarios para su obtención y el importe del deterioro»; art. 38.2: amortización hasta el 3 % anual del coste de adquisición sin suelo; mobiliario según tablas del IS); neto no negativo; va a la base general.

**Imputación temporal e irregularidad.** Un rendimiento con período de generación superior a 2 años y no recurrente (art. 30.3, el caso del art. 32.6) se integra al 60 % o 50 %, con límite de 300.000 euros. No es relevante para el alquiler de larga duración.

**Subarrendamiento** (Reglamento art. 43.2, DF 133/2025): bonificación del 30 % sobre la diferencia entre lo cobrado y la renta que se paga.

**Resultado.** El alquiler de larga duración que cumple la LAU tributa en la base del ahorro (19 %–28 % en 2026) sobre el 70 % de la renta cobrada (30 % si se aplica la bonificación del 70 %), menos intereses y seguro de impago.

Observación PENDIENTE: no he encontrado la definición oficial de «índices de referencia» aplicable a Euskadi para la bonificación del 70 %. La prensa indica que el Gobierno Vasco preveía culminar su operatividad en 2026. No confirmado en fuente oficial.

---

## 5. IRPF, ganancia patrimonial por la venta

**Base.** Base del ahorro (art. 63.c NF 13/2013), con la escala del apartado 2 de este informe. No hay reducción por antigüedad, ni exención por tenencia en inmuebles que no sean vivienda habitual.

**Cálculo.** Art. 44.1.a: ganancia = «la diferencia entre los valores de adquisición, actualizado cuando proceda […] y transmisión». Art. 45 NF 13/2013:
- Valor de adquisición: importe real más «el coste de las inversiones y mejoras […] y los gastos y tributos inherentes a la adquisición, excluidos los intereses».
- «Este valor se minorará, cuando proceda, en el importe de las amortizaciones reglamentariamente practicadas, computándose, en todo caso, la amortización mínima.»
- Valor de transmisión: importe real menos los gastos y tributos de la venta pagados por el transmitente (art. 45.3).

Reglamento, art. 47.1: se computa la amortización mínima «con independencia de la efectiva consideración de ésta como gasto […] el porcentaje resultante del período máximo a que se refiere la normativa del Impuesto sobre Sociedades». En la NF del IS (11/2013), art. 17.6: «el período máximo de amortización […] será de 15 años, excepto en el caso de los inmuebles, en que será de 50 años». Lectura literal: 2 % anual como amortización mínima que reduce el valor de adquisición, aunque en el alquiler del art. 32.2 no se haya deducido amortización alguna. PENDIENTE: no he encontrado en fuente oficial sobre qué base se calcula ese 2 % (coste sin suelo o coste total) ni confirmación de la Hacienda Foral de que se aplica también a viviendas del art. 32.2. Debe tratarse como parámetro marcado PROVISIONAL hasta verificar con criterio de la Hacienda Foral.

**Coeficientes de actualización: sí existen** (art. 45.2 NF 13/2013). Se aprueban cada año por Decreto Foral. Para transmisiones de 2026: DF 115/2025, art. 1.Uno. Se aplican «sobre los importes a que se refieren las letras a) y b» según el año en que se satisfizo cada importe; las mejoras con el coeficiente de su año (art. 45.2 y art. 2.Dos del DF para el IS).

| Año de adquisición o pago | Coeficiente 2026 | Año | Coeficiente 2026 |
|---|---|---|---|
| 1994 y anteriores | 2,030 | 2011 | 1,360 |
| 1995 | 2,156 | 2012 | 1,330 |
| 1996 | 2,076 | 2013 | 1,309 |
| 1997 | 2,030 | 2014 | 1,307 |
| 1998 | 1,985 | 2015 | 1,307 |
| 1999 | 1,931 | 2016 | 1,307 |
| 2000 | 1,866 | 2017 | 1,281 |
| 2001 | 1,796 | 2018 | 1,261 |
| 2002 | 1,732 | 2019 | 1,249 |
| 2003 | 1,685 | 2020 | 1,249 |
| 2004 | 1,635 | 2021 | 1,212 |
| 2005 | 1,583 | 2022 | 1,121 |
| 2006 | 1,531 | 2023 | 1,082 |
| 2007 | 1,489 | 2024 | 1,050 |
| 2008 | 1,430 | 2025 | 1,020 |
| 2009 | 1,426 | 2026 | 1,000 |
| 2010 | 1,402 | | |

Regla especial: adquirido el 31-12-1994, coeficiente de 1995 (art. 1.Dos). Entrada en vigor: 1 de enero de 2026. Para ventas en 2027 se requerirá un decreto nuevo (el DF 115/2025 solo vale para 2026).

Exención por reinversión en vivienda habitual (art. 49 NF, reglamento art. 49): no aplica a un piso alquilado.

---

## 6. ITP

NF 1/2011, art. 13 (última modificación 20/04/2026). **No hay un tipo general único para el inmueble de un particular; la vivienda tiene un tipo propio:**
- Art. 13.a): «El 7 por 100 si se trata de la transmisión de bienes inmuebles». Es el tipo para locales, terrenos y demás inmuebles.
- Art. 13.b): «la transmisión de viviendas en general, incluidas las plazas de garaje, con un máximo de dos unidades, y anexos, situados en el mismo edificio, que se transmitan conjuntamente, tributará al 4 por 100». Condición: «el adquirente no sea titular de más de 5 viviendas en un porcentaje superior al 50 por 100 en cada una de ellas» (declaración responsable). Si no se cumple: «tributará al 6 por 100».
- Art. 13.c): 2,5 % para viviendas de hasta 120 m² construidos (y unifamiliares ≤120 m² con parcela ≤300 m²), y para titulares de familia numerosa. Los requisitos del párrafo siguiente («Para la aplicación del tipo del 2,5 por 100 será preciso reunir los siguientes requisitos») incluyen que la vivienda se destine a vivienda habitual del adquirente, y si no «el tipo se incrementará al 4 por 100». Para una compra de inversión se aplica por tanto el 4 % (o el 6 % si tiene más de 5 viviendas).
- Tipo único (no por tramos). Fecha de efectos: texto consolidado vigente a 2026-11-03.

---

## 7. AJD

NF 1/2011, art. 44.1 (cuota gradual): «Las primeras copias de escrituras y actas notariales, tributarán, además, al tipo de gravamen del 0,50 por 100» si tienen objeto valuable, son inscribibles y no están sujetas a ITP-onerosas, operaciones societarias ni Sucesiones. La compra de vivienda nueva con IVA cumple esa condición (el IVA excluye el ITP): tipo único del 0,50 %. No hay tipos por bandas ni tipos reducidos por comunidad. Hipoteca: el art. 13.e fija el 1 % para la constitución de derechos reales de garantía; no estudié sus exenciones ni bonificaciones.

---

## 8. Zonas de mercado residencial tensionado en Bizkaia

El mecanismo es la Ley 12/2023: el Consejero de Vivienda y Agenda Urbana del Gobierno Vasco declara por Orden (BOPV y BOB) y la Secretaría de Estado de Vivienda publica en el BOE una relación trimestral. Vigencia: «Tres años desde el día siguiente a la publicación de la presente resolución» (resoluciones del BOE).

Códigos INE de 5 cifras verificados en el diccionario del INE «a 1 de enero de 2026» (https://www.ine.es/daco/daco42/codmun/diccionario26.xlsx; códigos CPRO 48 + CMUN):

| Municipio | INE | Ámbito | Orden (fecha, BOPV) | BOE |
|---|---|---|---|---|
| Barakaldo | 48013 | municipio entero | Orden de 31-03-2025, BOPV 23-04-2025 | Resolución 29-04-2025, BOE-A-2025-8636 (1T 2025) |
| Galdakao | 48036 | solo el Distrito 2 | Orden de 03-04-2025, BOPV 25-04-2025 | BOE-A-2025-15728 (Resolución 28-07-2025, 2T 2025) |
| Bilbao | 48020 | todo el término municipal | Orden de 21-08-2025, BOPV núm. 167, 04-09-2025 | BOE-A-2025-21901 (Resolución 29-10-2025, BOE 30-10-2025) |
| Basauri | 48015 | municipio entero | Orden de 28-05-2026, BOPV núm. 106, 08-06-2026 | BOE-A-2026-16532 (Resolución 24-07-2026, BOE 29-07-2026) |
| Sopela | 48085 | municipio (ver abajo) | Orden de 27-07-2026, BOPV núm. 154, 14-08-2026 | no localizada (1T-3T 2026) |
| Urduliz | 48089 | municipio (ver abajo) | Orden de 27-07-2026, BOPV núm. 154, 14-08-2026 | no localizada |

URLs: Bilbao https://www.euskadi.eus/bopv2/datos/2025/09/2503749a.pdf (Resuelvo segundo: «Declarar el municipio de Bilbao como zona de mercado residencial tensionado»); BOE https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-21901; Sopela https://www.euskadi.eus/bopv2/datos/2026/08/2603610a.pdf; Urduliz https://www.euskadi.eus/bopv2/datos/2026/08/2603609a.pdf; BOE Basauri https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-16532; BOE Barakaldo https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-8636; BOE Galdakao https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-15728.

Efectos: la Orden de Bilbao aplica el límite del art. 17.7 de la LAU: en inmuebles sin contrato de alquiler en los cinco años anteriores, la renta inicial no puede exceder el índice de referencia. Gran tenedor en Bilbao: más de diez inmuebles urbanos residenciales o más de 1.500 m². En Basauri y otros: cinco o más inmuebles.

Notas:
- De Sopela y Urduliz solo leí la primera página de cada Orden (título y vista); no leí el Resuelvo ni la fecha de entrada en vigor, y no encontré su relación en el BOE. Táchese como PENDIENTE en datos hasta leer el Resuelvo y la resolución del BOE del 3T 2026.
- Están en tramitación (no declarados): Bermeo (Orden de 17-07-2026 de inicio, BOPV 03-08-2026), según la prensa también Gorliz, Lekeitio y Elorrio.
- Bilbao: según el catálogo normativo del Gobierno Vasco hay una Orden de 9 de julio de 2026 que inicia la modificación de la declaración; solo vi el título. PENDIENTE.
- Los resultados de prensa de 11 o 20 municipios vascos declarados no son fuente oficial; la lista de arriba está construida solo con BOE y BOPV leídos.
- El portal oficial eremutentsionatua.euskadi.eus no lo descargué.

---

## 9. Alquiler turístico

Norma autonómica vasca: Ley 13/2016, de 28 de julio, de Turismo, y Decreto 101/2018, de 3 de julio, de viviendas y habitaciones de viviendas particulares para uso turístico (BOPV núm. 143, 26-07-2018): https://www.euskadi.eus/bopv2/datos/2018/07/1803822a.pdf. Modificado por el Decreto 52/2025, de 25 de febrero (BOPV núm. 53, 18-03-2025; deroga la disp. adicional primera, que dejaba fuera el medio rural): https://www.euskadi.eus/bopv2/datos/2025/03/2501233a.pdf.

Requisitos, tal como los he leído:
- Art. 5: declaración responsable previa ante la dirección de turismo del Gobierno Vasco, con referencia catastral; comunicación al propietario si no lo es; conformidad con «las normas municipales relativas a los usos urbanísticos y la edificación» y con la propiedad horizontal. Inscripción en el REATE (art. 7).
- Art. 2.4: se presume actividad habitual (sometida al Decreto) si hay publicidad en un canal de oferta turística o alojamiento por 31 días o menos, dos o más veces en el mismo año.
- Art. 13: capacidad según planeamiento; si no, 25 m² útiles para 1 persona, 33 m² para 2 y 15 m² por persona a partir de 3; «no podrán ofertar más de 8 plazas en total».
- Art. 19: no puede ejercerse si los estatutos inscritos de la comunidad contienen una prohibición expresa.
- Art. 12: cocina, baño y estancia para dormir; un baño por cada cuatro personas.

Bilbao: el PGOU de 2018 (modificación pormenorizada sobre alojamiento turístico, aprobación definitiva 25-01-2018, BOB 13-02-2018) es dato de prensa, no leído en fuente oficial. Hay una nueva modificación del Plan General (alojamientos turísticos y viviendas colectivas, exp. 2HI-060/26-P03-A) que define una «ZACAT (zona de alta concentración de alojamientos turísticos)» y en la que «las HUT pasan a ser ACTIVIDAD ECONÓMICA»; el documento que leí es una ponencia de la Comisión de Ordenación del Territorio del País Vasco de 2026: https://www.euskadi.eus/contenidos/informacion/copu_bizkaia_2026/eu_def/adjuntos/Bilkura%205/26-060-P03-A-BILBAO-usos-turisticos.pdf. La prensa la describe como aprobada provisionalmente en junio de 2026. PENDIENTE: estado de aprobación definitiva, texto normativo y delimitación de las zonas.

---

## 10. IBI y plusvalía municipal de Bilbao (48020)

**Marco foral que sí leí.**

IBI, NF 4/2016 (última modificación 01/01/2026), art. 8: «El tipo de gravamen mínimo será el 0,02 por 100 cuando se trate de bienes de naturaleza urbana […] y el máximo será el 0,60 por 100 para los urbanos». Frente al TRLRHL (mínimo 0,4 % y máximo 1,1 % para urbanos), el máximo foral es 0,60 %. Los tipos se fijan por ordenanza y deben estar publicados antes del 1 de enero (art. 8.6). Un tipo diferenciado por usos solo se aplica «como máximo al 10 por 100 de los bienes inmuebles urbanos» de mayor valor. Hay un recargo potestativo de hasta el 150 % para viviendas desocupadas (art. 10).

Plusvalía, NF 8/1989 (última modificación 01/01/2025), art. 4 y 5:
- Base: valor catastral del terreno multiplicado por un coeficiente según años de generación. Si no hay desglose suelo-construcción, se aplica el valor catastral con reducción del 60 % (art. 4.2.a). El ayuntamiento puede aplicar un coeficiente reductor de hasta el 15 %.
- Coeficientes máximos (los ayuntamientos fijan los suyos sin superarlos): inferior a 1 año 0,16; 1 año 0,15; 2 años 0,15; 3 años 0,15; 4 años 0,16; 5 años 0,18; 6 años 0,20; 7 años 0,22; 8 años 0,23; 9 años 0,21; 10 años 0,16; 11 años 0,13; 12 años 0,11; 13 años 0,10; 14 años 0,10; 15 años 0,10; 16 años 0,10; 17 años 0,12; 18 años 0,16; 19 años 0,22; 20 años o más 0,35. Se actualizan «anualmente mediante Norma Foral»; no vi actualización 2026 en la NF 7/2025 (sin referencia a esta norma en su texto).
- Art. 4.4: si el contribuyente acredita un incremento real inferior, la base es ese incremento.
- Art. 5.1: tipo fijado por cada ayuntamiento, «en ningún caso podrá exceder del 30 por 100».

**Valores de la ordenanza de Bilbao: PENDIENTE.** bilbao.eus tiene `User-agent: *` con `Disallow: /`, así que no descargué sus ordenanzas. En el BOB tampoco localicé el texto. Pistas de terceros, no válidas para datos:
- IBI urbano 2026: 0,183 % (tabla de guiafiscal.es; el Ayuntamiento anunció la congelación de tributos de 2026).
- Plusvalía de Bilbao: una web dice 17 % y otra 25 %; contradictorias. Tampoco sirve su tabla de coeficientes (0,06 a 0,19).

Para cerrar esto hace falta leer la Ordenanza Fiscal n.º 1 (IBI) y la de plusvalía de Bilbao en su publicación en el BOB (un humano puede abrir bilbao.eus).

---

## Resumen para el diseño (≤250 palabras)

Diferencias con el IRPF común que obligan a cambiar el motor:

1. **Una sola escala foral** (8 tramos, 23 %–49 %, 2026) sobre la base general; sin parte estatal ni autonómica. Hay que parametrizar el territorio y el año; los tramos de 2026 son la de 2025 deflactada un 2 %.
2. **Mínimos: no hay escala sobre el mínimo.** Hay una minoración de cuota de 1.615 euros (solo sobre la cuota de la escala general, sin bajar de cero) y deducciones familiares en cuota líquida (descendientes, ascendientes, edad, discapacidad).
3. **Alquiler de vivienda LAU en la base del ahorro**, no en la general: bonificación del 30 % (70 % con índices de referencia, zona tensionada o programas públicos) sobre el íntegro. Solo se deducen intereses y financiación (más seguro de impago hasta 300 euros). Sin IBI, comunidad, reparaciones ni amortización. Neto no negativo por inmueble y sin arrastre de intereses (no encontrado).
4. **Escala del ahorro de 9 tramos** (19 %–28 % en 2026); alquiler y ganancia comparten escala pero se compensan en compartimentos separados (cuatro años).
5. **Ganancia con coeficientes de actualización anuales** (DF 115/2025 para 2026) y amortización mínima del 2 % que reduce el valor de adquisición (parámetro PROVISIONAL).
6. **ITP de vivienda al 4 %** (6 % con más de 5 viviendas); 7 % resto de inmuebles; AJD 0,5 %.
7. **Municipal:** IBI máximo 0,60 %; plusvalía con coeficientes propios, no los del TRLRHL.
