# Fiscalidad foral de Álava/Araba para un particular que compra un piso, lo alquila (vivienda habitual, larga duración) y lo vende

Fecha de la consulta: 2026-11-03. Todo sale de textos oficiales leídos por mí (descargados a un directorio temporal, fuera del repositorio). Webs de terceros solo se usaron para localizar la fuente.

## 0. Fuentes oficiales y robots.txt

robots.txt leído en un comando aparte antes de la primera descarga de cada dominio. Ninguno bloquea ClaudeBot, Claude-Web ni anthropic-ai (todos usan `User-agent: *`).

| Dominio | Restricciones relevantes | Qué se descargó |
|---|---|---|
| www.boe.es | no `/datos/pdfs/`, no `xml.php`, no `lang=` no castellano | `/boe/dias/2025/10/30/pdfs/BOE-A-2025-21901.pdf` (permitido) |
| www.araba.eus | no `/*?`, no `/botha/Busquedas/`, no `/cs/` | PDF de BOTHA directos, sin query string |
| web.araba.eus | no `*q=*`, `*keywords*`, `/c`, etc. | `/documents/d/araba/...` (permitido) |
| www.vitoria-gasteiz.org | no `/docs/a25/`, no `/a24-02w/` | `/docs/wb021/.../105986.pdf` (permitido) |
| www.euskadi.eus | no `/*/bopv2/datos/*.pdf`; permitido `/web01-*` | NO se descargó ningún `bopv2/datos/*.pdf`; el BOPV se leyó por la versión HTML `/web01-bopv/.../*.shtml` |

Textos usados (todos oficiales):

- NF 33/2013 del IRPF de Álava, texto consolidado de la Diputación con notas hasta la NF 21/2025: https://web.araba.eus/documents/d/araba/indice_norma-foral_irpf_cas-7-pdf (y `..._cas-4-pdf`, idéntico en contenido). Citado como «IRPF consolidado».
- NF 21/2025, de 19 de diciembre, medidas tributarias 2026 (BOTHA nº 147, 29-12-2025): https://www.araba.eus/BOTHA/Boletines/2025/147/2025_147_03861_C.pdf
- NF 3/2025, de 9 de abril, revisión de impuestos (BOTHA nº 44, 16-4-2025): https://www.araba.eus/BOTHA/Boletines/2025/044/2025_044_01182_C.pdf
- NF 19/2024, de 20 de diciembre, medidas 2025 (BOTHA nº 147, 30-12-2024): https://www.araba.eus/BOTHA/Boletines/2024/147/2024_147_04143_C.pdf
- NF 26/2023, de 22 de diciembre, medidas 2024 (BOTHA nº 150, 29-12-2023): https://www.araba.eus/BOTHA/Boletines/2023/150/2023_150_03770_C.pdf
- Decreto Foral 41/2025, de 16 de diciembre, coeficientes de actualización 2026 (BOTHA nº 146, 26-12-2025): https://www.araba.eus/botha/Boletines/2025/146/2025_146_03735_C.pdf
- Reglamento del IRPF (DF 40/2014), consolidado con notas hasta DF 42/2025: https://web.araba.eus/documents/d/araba/indice-reglamento_irpf_cas-2-pdf
- NF 11/2003 del ITP y AJD, consolidada con notas hasta el Decreto Normativo de Urgencia Fiscal 2/2026 (BOTHA nº 45, 20-4-2026): https://web.araba.eus/documents/d/araba/indice_norma-foral-itp-ajd-cas-2-pdf
- Ordenanzas fiscales 2026 de Vitoria-Gasteiz (compilación oficial del Ayuntamiento): https://www.vitoria-gasteiz.org/docs/wb021/contenidosEstaticos/adjuntos/es/59/86/105986.pdf
- Orden de 18-9-2025 del consejero de Vivienda y Agenda Urbana (BOPV nº 184, 29-9-2025, doc. 4056), versión HTML: https://www.euskadi.eus/web01-bopv/es/bopv2/datos/2025/09/2504056a.shtml
- Resolución de 29-10-2025 de la Secretaría de Estado de Vivienda y Agenda Urbana (BOE nº 261, 30-10-2025, BOE-A-2025-21901): https://www.boe.es/boe/dias/2025/10/30/pdfs/BOE-A-2025-21901.pdf
- Decreto 101/2018 (BOPV nº 143, 26-7-2018) y Decreto 52/2025 (BOPV nº 53, 18-3-2025), leídos por HTML en `euskadi.eus/web01-bopv/...` (1803822a.shtml y 2501233a.shtml).

Nota de método: la herramienta de lectura web devolvió resúmenes de los HTML del BOPV (no el texto literal). Para BOPV marco como «lectura por resumen» lo que no pude contrastar literalmente.

---

## 1. IRPF, estructura

Sí: una sola escala foral sobre la base liquidable general (no hay tramo estatal ni autonómico). Cuota íntegra = escala general (menos la minoración general, que no puede dejarla negativa) + escala del ahorro sobre la base liquidable del ahorro (+ DA 20ª cuando proceda).

Cita (art. 74, IRPF consolidado): «La resultante de aplicar la escala de gravamen del apartado 1 del artículo siguiente a la base liquidable general. Este importe se reducirá conforme a lo previsto en el artículo 77 de esta Norma Foral y en ningún caso podrá resultar negativo.»

### Escala general 2026 (art. 75.1, redacción NF 21/2025, apartado «Cuarto», número Cuatro, con efectos 1-1-2026)

Cita: «La base liquidable general será gravada a los tipos que se indican en la siguiente escala».

| Base liquidable general hasta (€) | Cuota íntegra (€) | Resto hasta (€) | Tipo |
|---|---|---|---|
| 0,00 | 0,00 | 18.080,00 | 23 % |
| 18.080,00 | 4.158,40 | 18.080,00 | 28 % |
| 36.160,00 | 9.220,80 | 18.080,00 | 35 % |
| 54.240,00 | 15.548,80 | 23.210,00 | 40 % |
| 77.450,00 | 24.832,80 | 29.810,00 | 45 % |
| 107.260,00 | 38.247,30 | 35.700,00 | 46 % |
| 142.960,00 | 54.669,30 | 65.430,00 | 47 % |
| 208.390,00 | 85.421,40 | en adelante | 49 % |

Norma: NF 21/2025, BOTHA nº 147 de 29-12-2025, pág. 10/38 del PDF; mismo cuadro en el IRPF consolidado, art. 75.

### Escala general 2025 (difiere de 2026)

El art. 75 no tiene nota de modificación posterior a la NF 26/2023 salvo la 37 (NF 21/2025), así que en 2025 rigió la escala de la NF 26/2023 (apartado «Diez», efectos 30-12-2023, es decir la de 2024 y 2025):

| Base liquidable general hasta (€) | Cuota íntegra (€) | Resto hasta (€) | Tipo |
|---|---|---|---|
| 0,00 | 0,00 | 17.720,00 | 23 % |
| 17.720,00 | 4.075,60 | 17.720,00 | 28 % |
| 35.440,00 | 9.037,20 | 17.720,00 | 35 % |
| 53.160,00 | 15.239,20 | 22.750,00 | 40 % |
| 75.910,00 | 24.339,20 | 29.220,00 | 45 % |
| 105.130,00 | 37.488,20 | 35.000,00 | 46 % |
| 140.130,00 | 53.588,20 | 64.140,00 | 47 % |
| 204.270,00 | 83.734,00 | en adelante | 49 % |

Fuente: https://www.araba.eus/BOTHA/Boletines/2023/150/2023_150_03770_C.pdf (BOTHA nº 150, 29-12-2023). La NF 19/2024 (2025) no toca el art. 75 (lo comprobé buscando «artículo 75» en su texto: no aparece). Inferencia mía: deflactación del 2 % en 2026 (17.720 x 1,02 = 18.074; la norma fija 18.080). El porcentaje de deflactación no lo dice la norma que leí; es solo la comparación de tablas.

Tipo medio y regla de ganancias de actividades económicas (art. 75.2 y 75.3): no relevantes para alquiler de particulares.

## 2. IRPF, base del ahorro

### Escala del ahorro (art. 76.1, NF 3/2025, artículo 11, apartado Cuatro; efectos 1-1-2026 según su disposición final primera)

Cita de la disposición final: «Lo dispuesto en el apartado 1 del artículo 76 de la Norma Foral 33/2013 ... contenido en el apartado cuatro del artículo 11, surtirá efectos a partir de 1 de enero de 2026.»

| Base liquidable del ahorro hasta (€) | Cuota íntegra (€) | Resto hasta (€) | Tipo |
|---|---|---|---|
| 0,00 | 0,00 | 7.500,00 | 19 % |
| 7.500,00 | 1.425,00 | 7.500,00 | 20 % |
| 15.000,00 | 2.925,00 | 15.000,00 | 22 % |
| 30.000,00 | 6.225,00 | 20.000,00 | 24 % |
| 50.000,00 | 11.025,00 | 40.000,00 | 25,5 % |
| 90.000,00 | 21.225,00 | 30.000,00 | 26 % |
| 120.000,00 | 29.025,00 | 120.000,00 | 26,5 % |
| 240.000,00 | 60.825,00 | 60.000,00 | 27 % |
| 300.000,00 | 77.025,00 | en adelante | 28 % |

Escala anterior a 2026 (la que rige hasta el periodo 2025): PENDIENTE. En las fuentes oficiales que leí solo aparece como referencia la exposición de motivos de la NF 33/2013 («una tributación de un 25 por ciento a partir de 30.000 euros»), y el art. 76 no tiene más modificaciones que la 35 (NF 3/2025). El texto original de la NF 33/2013 (BOTHA nº 140, suplemento, 9-12-2013) no lo descargué. Para 2026 no hace falta.

### Qué rentas van a la base del ahorro (art. 63, consolidado)

Cita:

- «a) (35) Los rendimientos del capital inmobiliario procedentes de viviendas a las que se refieren los apartados 1 y 2 del artículo 32 de esta Norma Foral.» (letra a) redactada por NF 3/2025, artículo 3, apartado Cinco, con efectos 1-1-2025.)
- «b) ... Los rendimientos del capital mobiliario previstos en los artículos 34, 35, 36 y en la letra e) del artículo 37 ...»
- «c) (34) Las ganancias y pérdidas patrimoniales que se pongan de manifiesto con ocasión de transmisiones de elementos patrimoniales ...»

Es decir: en Álava el alquiler de vivienda (LAU art. 2, apartados 32.1 y 32.2) y la ganancia por vender el piso tributan los dos en la base del ahorro. El resto de rentas inmobiliarias (arts. 32.3 y 32.4) van a la base general (art. 62).

Integración y compensación de la base del ahorro (art. 66): los rendimientos de capital (a) y las ganancias/pérdidas por transmisión (b) se compensan solo dentro de su propio bloque; un saldo negativo de cada bloque se compensa solo con saldo positivo del mismo bloque en los cuatro años siguientes. («su importe sólo se podrá compensar con el saldo positivo de los rendimientos a que se refiere esta letra a) ... durante los cuatro años siguientes»; igual para la letra b).)

## 3. IRPF, mínimos personales y familiares

No son reducciones de la base. Son:

(a) una «minoración general de cuota» (art. 77) que resta de la cuota de la escala general (nunca de la del ahorro), sin poder dejarla negativa, y
(b) deducciones en la cuota (arts. 79 a 83, deducciones familiares y personales, Título VII), que restan de la cuota íntegra total (general + ahorro) para llegar a la cuota líquida, que no puede ser negativa.

Citas: art. 77.1: «Las y los contribuyentes aplicarán una minoración de cuota de 1.615,00 euros por cada autoliquidación» (redacción NF 21/2025, apartado «Cuarto», número Cinco, efectos 1-1-2026). Art. 78: «se entenderá por cuota líquida la cantidad resultante de minorar la cuota íntegra en el importe de las deducciones ... En ningún caso la cuota líquida podrá ser negativa.» La exposición de motivos de la NF 33/2013 lo explica: la deducción general «sólo se aplicará a los contribuyentes que apliquen la tarifa correspondiente a la base liquidable general ... sólo disminuye la cuota íntegra general sin permitir que como consecuencia de su aplicación resulte negativa».

La minoración es por autoliquidación (no por persona; en tributación conjunta, una por autoliquidación). No hay mínimo del contribuyente por edad dentro del art. 77; la edad va por la deducción del art. 83.

| Concepto | 2026 | 2025 | Norma 2026 / 2025 |
|---|---|---|---|
| Minoración general de cuota (art. 77.1) | 1.615,00 € | 1.583,00 € | NF 21/2025 / NF 19/2024 (apartado Diez) |
| Minoración por residencia en núcleos con ≤500 hab. (art. 77.2) | 200,00 € | 200,00 € | consolidado / NF 19/2024 |
| Reducción base por tributación conjunta (art. 73) | 4.896,00 € | PENDIENTE (no lo leí) | NF 21/2025 |
| Descendiente 1.º (art. 79.1.a) | 734,80 € | 734,80 € | consolidado (NF 19/2024, apartado Once) |
| 2.º | 909,70 € | 909,70 € | idem |
| 3.º | 1.532,30 € | 1.532,30 € | idem |
| 4.º | 1.811,70 € | 1.811,70 € | idem |
| 5.º y siguientes | 2.366,10 € | 2.366,10 € | idem |
| Complementaria por descendiente menor de 6 años (art. 79.2) | 424,60 € | 424,60 € | idem |
| Complementaria, de 6 a 15 años cumplidos (incompatible con la anterior) | 68,20 € | 68,20 € | idem |
| Recargo +15 % si residencia en municipio alavés <4.000 hab. (art. 79.2 bis) | 15 % | 15 % | consolidado |
| Ascendiente conviviente (art. 81.1) | 423,72 € | 423,72 € | consolidado (NF 19/2024, Once bis) |
| Edad >65 (art. 83.1), si base imponible ≤20.000 € | 393,00 € | 385,00 € | NF 21/2025 / NF 26/2023 |
| Edad >75 | 714,00 € | 700,00 € | idem |
| Edad: tramo 20.000–30.000 € de base imponible | 393 − 0,0393 × (BI − 20.000) (>65); 714 − 0,0714 × (BI − 20.000) (>75) | 385 − 0,0385 × ...; 700 − 0,0700 × ... | idem |

Descendientes (art. 79.1): «Por cada descendiente que conviva con la o el contribuyente se practicará la siguiente deducción». No se aplica si el descendiente tiene más de 30 años (salvo discapacidad), obtiene rentas superiores al SMI o presenta autoliquidación (art. 79.3). Con varios ascendientes se prorratea por partes iguales (art. 79.4).

Los importes de descendientes de 2025 salen de la NF 19/2024; la NF 21/2025 no modifica el art. 79 (no aparece «artículo 79» en su texto), así que 2026 = 2025. Para 2024 eran 668 / 827 / 1.393 / 1.647 / 2.151 y 386 / 62 (NF 26/2023), por si hace falta serie.

## 4. IRPF, ALQUILER DE VIVIENDA (lo más importante)

Texto vigente del art. 32 (redacción NF 3/2025, artículo 3, apartado Dos, efectos 1-1-2025; la NF 21/2025 solo cambia, con efectos 2025, el encabezado del quinto párrafo del apartado 1: «Asimismo, en los supuestos previstos en los tres primeros párrafos de este apartado 1, serán deducibles, exclusivamente, los siguientes gastos»).

### 4.1 A qué base va

A la base del ahorro (art. 63.a, arriba) cuando es vivienda arrendada conforme al art. 2 de la LAU (arrendamiento de vivienda habitual de larga duración) y se aplica el art. 32.1, y también las viviendas cedidas a programas públicos (art. 32.2: Bizigune, ASAP, etc.). Tributa con la escala del ahorro del punto 2 (19 % a 28 %), no con la general.

Si el contrato no es «arrendamiento de vivienda» del art. 2 LAU (p. ej. temporada, uso distinto), va al art. 32.3 (viviendas no incluidas en los dos apartados anteriores, sin actividad económica) o al 32.4, y esos rendimientos van a la base general.

### 4.2 Bonificación del rendimiento (art. 32.1)

Cita: «se aplicará una bonificación del 30 por ciento sobre los rendimientos íntegros obtenidos por cada inmueble. Este porcentaje será del 35 por ciento cuando la vivienda se encuentre ubicada en alguna de las zonas o núcleos a que se refiere la Disposición Adicional Trigésimo cuarta de esta Norma Foral.»

- Se aplica sobre el rendimiento íntegro (ingresos), no sobre el neto. Porcentaje 30 %; 35 % para los núcleos rurales en riesgo de despoblación de la DA 34ª (en el municipio de Vitoria-Gasteiz figuran solo ámbitos rurales como Abetxuko (zona rural), Aberasturi, Amarita, Andagoia... no el casco urbano; la lista completa está en la DA 34ª del IRPF consolidado, pág. 184 y ss.).
- 70 % si la vivienda está en zona declarada de mercado residencial tensionado y la renta se limita a los índices de referencia. Cita: «siempre que la renta de alquiler se limite a los importes que se correspondan con los índices de referencia, la bonificación a la que se refiere el párrafo anterior será del 70 por ciento.» También aplica si la renta pactada se ha limitado voluntariamente en función de los índices de referencia o de precios de intermediación pública, con prueba suficiente ante la Administración.
- 70 % también para viviendas cedidas a Bizigune, ASAP u otros programas autonómicos, forales o municipales similares (art. 32.2), con deducibles solo los intereses y gastos de financiación.
- 20 % para el resto de viviendas del art. 32.3 (renta a la base general).
- Condición para el 70 % por zona tensionada en Vitoria: ver punto 8. El índice de referencia de Álava: PENDIENTE (no lo he encontrado en fuente oficial; las noticias dicen que dependía de datos de Eustat y de Hacienda Foral y que se esperaba en el primer semestre de 2026, sin confirmar que esté publicado).

### 4.3 Gastos deducibles (art. 32.1, tercer y cuarto bloque): lista cerrada

Cita: «serán deducibles, exclusivamente, los siguientes gastos: a) El importe de los intereses de los capitales ajenos invertidos en la adquisición, rehabilitación o mejora de los bienes ... y demás gastos de financiación ... b) El importe de las primas de seguros que cubran total o parcialmente el impago de las rentas ... con un máximo de 300,00 euros anuales.»

- Intereses y gastos de financiación: deducibles, sin tope propio (no hay límite «intereses + reparación»; no hay arrastre de exceso), restando subvenciones exentas recibidas para pagarlos.
- Seguro de impago de rentas: máximo 300 euros anuales.
- NO son deducibles en el régimen del art. 32.1: IBI, tasas, comunidad, seguros de hogar o de responsabilidad civil, reparación y conservación, suministros, servicios de terceros, ni amortización. La palabra «exclusivamente» cierra la lista. (Los arts. 36 y 37 del Reglamento, que sí enumeran IBI, comunidad, reparación y amortización del 3 %, se refieren a «apartado 2 del artículo 32», numeración anterior a la NF 3/2025; con la numeración actual esa amortización solo aplica a la lista abierta del art. 32.4, y para el 32.1 la ley es la que manda. Esto lo marco como inferencia mía: conviene confirmarlo con Hacienda Foral.)
- Reparación y conservación de gran importe, mejoras: no se deducen del rendimiento, pero sí aumentan el valor de adquisición para la ganancia (art. 45.1.b, punto 5).

### 4.4 Rendimiento negativo

Cita: «La suma de la bonificación y de los gastos deducibles no podrá dar lugar, para cada inmueble, a rendimiento neto negativo.» El rendimiento neto de cada inmueble se corta en cero. No hay pérdida arrastrable por este concepto en la práctica (art. 66.1.a: un saldo negativo de la base del ahorro de capital solo se compensa en cuatro años con rendimientos del mismo bloque, pero con este corte por inmueble casi no puede generarse).

Resumen de la fórmula por inmueble (art. 32.1): neto = máx(0; ingresos − 30 % × ingresos − intereses − seguro de impago ≤300). Con bonificación 70 %: neto = máx(0; 0,30 × ingresos − intereses − seguro).

### 4.5 Qué cambió en 2025

La NF 3/2025 (BOTHA nº 44, 16-4-2025), con efectos 1-1-2025, reescribió el art. 32 y la letra a) del art. 63. Cita de la mención de efectos: «Con efectos a partir del 1 de enero de 2025, se introducen las siguientes modificaciones en la Norma Foral 33/2013». Régimen anterior a 2025 (porcentajes y gastos que aplicaban antes, y si ya iba al ahorro): PENDIENTE, no leí la versión anterior. Hay una nota (23) de la NF 31/2021 sobre el apartado 1.

Disposición final primera, NF 3/2025: el nuevo apartado 8 del art. 86 (deducción del inquilino) aplica a contratos suscritos o prorrogados desde 1-1-2026; no afecta al propietario.

### 4.6 Subarrendamiento (no es el caso, por completitud)

Art. 39.2, tercer párrafo (NF 3/2025): deducible solo el alquiler pagado, y bonificación del 30 % sobre la diferencia.

### 4.7 Otro: recargo del IBI en Vitoria si la vivienda está vacía (ver punto 10): no aplica si se alquila al menos seis meses.

## 5. IRPF, ganancia patrimonial por la venta

- Base: base imponible del ahorro (art. 63.c y 66.1.b), escala del punto 2.
- Pérdidas: se compensan con ganancias del mismo bloque en cuatro años (art. 66.1.b).
- Cálculo (arts. 44 y 45):
  - Cita art. 44.1.a: «la diferencia entre los valores de adquisición, actualizado cuando proceda ... y transmisión».
  - Valor de adquisición (art. 45.1): suma de a) el importe real de la adquisición y b) el coste de inversiones y mejoras y «los gastos y tributos inherentes a la adquisición, excluidos los intereses», pagados por el adquirente (ITP o IVA no deducible, AJD, notaría, registro, comisiones). Cita: «Este valor se minorará, cuando proceda, en el importe de las amortizaciones reglamentariamente practicadas, computándose, en todo caso, la amortización mínima.»
  - Reglamento art. 44.1: «El valor de adquisición ... se minorará, cuando proceda, en el importe de las amortizaciones fiscalmente deducibles, computándose en todo caso la amortización mínima, con independencia de la efectiva consideración de ésta como gasto.» Amortización mínima: «la cantidad resultante de aplicar ... el porcentaje resultante del período máximo a que se refiere la normativa del Impuesto sobre Sociedades».
  - Interpretación para el alquiler 32.1 (en el que no se deduce amortización): PENDIENTE. El texto dice «computándose en todo caso» incluso sin deducirse, lo que apunta a restar la amortización mínima aunque no se haya deducido, pero «cuando proceda» y «fiscalmente deducibles» dejan margen. No he leído la tabla del período máximo de amortización de edificios (NF 37/2013 del Impuesto sobre Sociedades, art. 21), así que el porcentaje mínimo también queda PENDIENTE. Necesita confirmación del asesor o de Hacienda Foral antes de cablearlo.
  - Valor de transmisión (art. 45.3): importe real de la enajenación, menos los gastos y tributos de la letra b) del apartado 1 que pague el transmitente; no puede ser inferior al normal de mercado.
- Coeficientes de actualización: sí existen. Se aplican al valor de adquisición (art. 45.2) «sobre los importes a que se refieren las letras a) y b) ... atendiendo al año en que se hayan satisfecho» y sobre las amortizaciones «atendiendo al año al que correspondan». Los fija un decreto foral cada año. Transmisiones de 2026 (DF 41/2025, artículo 1):

| Ejercicio de pago | Coef. | Ejercicio | Coef. | Ejercicio | Coef. |
|---|---|---|---|---|---|
| 1994 y anteriores | 2,030 | 2005 | 1,583 | 2016 | 1,307 |
| 1995 | 2,156 | 2006 | 1,531 | 2017 | 1,281 |
| 1996 | 2,076 | 2007 | 1,489 | 2018 | 1,261 |
| 1997 | 2,030 | 2008 | 1,430 | 2019 | 1,249 |
| 1998 | 1,985 | 2009 | 1,426 | 2020 | 1,249 |
| 1999 | 1,931 | 2010 | 1,402 | 2021 | 1,212 |
| 2000 | 1,866 | 2011 | 1,360 | 2022 | 1,121 |
| 2001 | 1,796 | 2012 | 1,330 | 2023 | 1,082 |
| 2002 | 1,732 | 2013 | 1,309 | 2024 | 1,050 |
| 2003 | 1,685 | 2014 | 1,307 | 2025 | 1,020 |
| 2004 | 1,635 | 2015 | 1,307 | 2026 | 1,000 |

Nota del propio decreto: «cuando el elemento patrimonial hubiese sido adquirido el 31 de diciembre de 1994, será de aplicación el coeficiente de actualización correspondiente a 1995.» Cada año hay un decreto nuevo, así que el dato debe ser versionado por año de transmisión (ventas posteriores a 2026: PENDIENTE hasta que se publique). Para el mismo ejercicio de transmisión el coeficiente es 1,000, y el de un año de compra intermedio es el ya publicado, así que una compra en 2026 y venta en 2031 usará el decreto de 2031.

- Exenciones y reinversión: la reinversión del art. 49 (cambio de vivienda habitual) no aplica a un piso alquilado; art. 49 reescrito por NF 3/2025 con efectos para viviendas habituales adquiridas desde 1-1-2026.

## 6. ITP (NF 11/2003, art. 43, consolidada hasta el DNUF 2/2026)

No es tipo único ni por tramos de base: depende del tipo de inmueble y del adquirente.

- Transmisión de inmuebles en general (incl. locales, suelo): 7 %. Cita art. 43.Uno.a): «El 7 por ciento si se trata de la transmisión de inmuebles, así como la constitución y cesión de derechos reales que recaigan sobre los mismos, excepto los derechos reales de garantía.»
- Vivienda (letra b): 4 %, incluyendo hasta dos garajes y dos anexos en el mismo edificio y transmitidos conjuntamente. Cita: «la transmisión de viviendas en general ... tributarán al 4 por ciento». Es el tipo general para un inversor particular que compra una vivienda usada.
- Condición para el 4 %: «La aplicación del tipo impositivo previsto en esta letra requerirá que la o el adquirente no sea titular de más de 5 viviendas en un porcentaje superior al 50 por ciento» (declaración responsable). Si no se cumple: «la transmisión de la vivienda tributará al 6 por ciento». Redacción de la NF 3/2025 (nota 50). Un inversor que ya tenga más de 5 viviendas paga 6 %. Fecha de efectos del 4 % / 6 %: la nota 50 remite a NF 3/2025; no he localizado el artículo concreto de efectos en la NF 3/2025, así que PENDIENTE la fecha exacta.
- Reducidos (no se aplican al inversor): 2,5 % (vivienda habitual ≤120 m² o familia numerosa, requisito de residencia habitual y de no tener otra vivienda >25 % en el municipio) y 1,5 % en zonas de la DA 34ª; son para vivienda habitual.
- Base: valor real; la norma habla de comprobación de valores (arts. 71 y siguientes), no leídos aquí.

## 7. AJD (misma norma, art. 56.2)

Cita: «Las primeras copias de escrituras y actas notariales, cuando tengan por objeto cantidad o cosa valuable, contengan actos o contratos inscribibles en los Registros de la Propiedad ... tributarán, además, al tipo de gravamen del 0,5%». Es el tipo de las escrituras de compra de vivienda nueva sujeta a IVA (la compraventa con IVA no tributa por ITP; solo AJD, 0,5 % sobre la base, más papel timbrado por folio, 0,300506 €). Para segunda mano con ITP, la misma escritura no queda sujeta a esta cuota gradual porque está sujeta a ITP, sin perjuicio de la regla del artículo. (Esta última línea es mi lectura del artículo, que excluye los actos sujetos a los conceptos 1.º y 2.º del apartado 1 del art. 1.) Hipoteca: art. 43.Uno.e) lo fija en 1 % para derechos reales de garantía como concepto ITP; la regla exacta de AJD de la escritura de hipoteca (sujeto pasivo y exenciones por préstamos hipotecarios) no la leí: PENDIENTE.

## 8. Zonas de mercado residencial tensionado

- Declaradas en Álava: solo Vitoria-Gasteiz (código INE 01059, comprobado en INE: «01059 Vitoria-Gasteiz» en las tablas de población de Araba/Álava).
- Declaración autonómica: Orden de 18-9-2025 del consejero de Vivienda y Agenda Urbana (Gobierno Vasco), art. 18.2 de la Ley 12/2023, publicada en BOPV nº 184 de 29-9-2025 (doc. 4056). Ámbito: el municipio entero, excepto «la zona rural constituida por entidades locales menores no incluida en la trama urbana» (la propia orden no enumera esas entidades). Vigencia de tres años prorrogables anualmente (lectura por resumen del HTML del BOPV).
- Publicación estatal: Resolución de 29-10-2025 de la Secretaría de Estado de Vivienda y Agenda Urbana, BOE nº 261 de 30-10-2025, BOE-A-2025-21901. Cita del BOE: tabla del Anexo con «Vitoria-Gasteiz, excepto la zona rural constituida por entidades locales menores no incluida en la trama urbana», plazo «Tres años desde el día siguiente a la publicación de la presente resolución» (es decir, efectos desde 31-10-2025 hasta 30-10-2028). Gran tenedor en Vitoria: titular de cinco o más inmuebles urbanos de uso residencial en el municipio, sin contar garajes y trasteros (con excepciones de vivienda pública).
- No es por barrios: municipio completo salvo entidades locales menores rurales.
- Municipios alaveses candidatos que no figuran en la resolución: no he encontrado ninguna declaración de otro municipio de Álava a 2026-11-03 (Alegría-Dulantzi fue citada como candidata en noticias; no hay orden). Los trimestres posteriores a 2025-T3 los revisé solo por búsqueda; PENDIENTE confirmar en el BOE de cada resolución trimestral que no haya nueva declaración en Álava.
- Índice de referencia del alquiler para Álava (condición del 70 % del IRPF): PENDIENTE (ver 4.2).

## 9. Alquiler turístico

- Norma autonómica: Decreto 101/2018, de 3 de julio, de viviendas y habitaciones de viviendas particulares para uso turístico (BOPV nº 143, 26-7-2018), modificado por el Decreto 52/2025, de 25 de febrero (BOPV nº 53, 18-3-2025), que deroga la DA 1.ª (la exclusión del medio rural). Lectura por resumen del HTML:
  - Declaración responsable e inscripción en el Registro de Empresas y Actividades Turísticas de Euskadi antes de empezar (arts. 5 y 7); informe municipal preceptivo y vinculante (arts. 8 y 9); número de registro en toda publicidad (art. 20).
  - Requisitos de la vivienda (art. 12 a 17): cocina, baño y dormitorio; máximo 8 plazas (art. 13.3); seguro de responsabilidad civil de al menos 35.000 € por plaza (art. 17); distintivo exterior e interior; atención telefónica de 08:00 a 22:00.
  - Comunidad de propietarios: no puede ejercerse si los estatutos inscritos lo prohíben expresamente (art. 19).
  - Habitualidad (art. 2.4): se presume si se promociona en un canal turístico o se aloja por periodos continuos de hasta 31 días dos o más veces al año.
- Capital: Vitoria-Gasteiz: PENDIENTE. Solo encontré fuentes de prensa y un escrito de alegaciones (2019-2020, 2024) sobre una modificación estructural del PGOU que limitaría las viviendas de uso turístico por plantas (planta primera / baja) y sobre el PERI del Casco Medieval; no he leído ningún acuerdo de aprobación definitiva ni publicación en BOTHA. No se puede afirmar vigente.
- Fiscalidad: el alquiler turístico no entra en el art. 32.1 (no es arrendamiento de vivienda del art. 2 LAU); quedaría en art. 32.3 / 32.4 (base general). Interpretación mía, no verificada con la Hacienda Foral.

## 10. IBI y plusvalía municipal de Vitoria-Gasteiz (ordenanzas 2026, compilación oficial)

### IBI (Ordenanza nº 1, art. 16)

- Cita: «El tipo de gravamen será el 0,345 por ciento cuando se trate de bienes urbanos, en general, exceptuando el tipo diferenciado del 0,441 por ciento que se aplicará a los usos que se señalan en la tabla anexa» (usos no residenciales, solo al 10 % de mayor valor catastral). Vivienda: 0,345 %. Rústico 0,528 %; bienes de características especiales 0,703 %.
- Recargo del 50 % sobre la cuota líquida para vivienda desocupada (art. 16 bis). Cita: «Aquellos bienes inmuebles de uso residencial que no constituyan la residencia habitual del sujeto pasivo o de terceras personas en virtud de arrendamiento o cesión de su uso, quedan sujetos a un recargo sobre la cuota líquida del Impuesto del 50%.» Se excluye, entre otras, la vivienda alquilada: «viviendas que hayan sido cedidas en alquiler en un mínimo de seis meses en el año anterior al devengo ... También estarán exentas las viviendas alquiladas a fecha de devengo ..., siempre que el contrato de arrendamiento sea indefinido o, como mínimo, por un plazo previsto de seis meses», previa solicitud y aportando el contrato. Por tanto un piso comprado para alquilar no lo paga si cumple ese requisito; un piso vacío sí (+50 %).
- URL: https://www.vitoria-gasteiz.org/docs/wb021/contenidosEstaticos/adjuntos/es/59/86/105986.pdf (págs. 74-76 de la compilación). La fecha de aprobación definitiva y publicación en BOTHA de la ordenanza: PENDIENTE (la compilación no la indica en lo que leí).
- Máximo/estructura de la norma foral del IBI (NF 42/1989 y su texto refundido): PENDIENTE; no descargué el texto refundido. Lo que sé de fuente oficial es que la ordenanza usa tipo propio, que por normativa foral los entes locales fijan sus tipos, y que el recargo de vivienda desocupada es potestad municipal foral. No afirmo límites numéricos.

### Plusvalía municipal (Ordenanza nº 4, arts. 7 a 10)

- Base (art. 7): «valor del terreno en el momento del devengo ... por el coeficiente que corresponda» (valor catastral del suelo, art. 8). Si el sujeto pasivo prueba que el incremento real es menor, se toma el incremento real (art. 7.2).
- Coeficientes propios (art. 10.1), por años completos de generación: <1: 0,15; 1: 0,15; 2: 0,14; 3: 0,14; 4: 0,16; 5: 0,18; 6: 0,19; 7: 0,18; 8: 0,15; 9: 0,12; 10: 0,10; 11–15: 0,09 cada año; 16: 0,10; 17: 0,13; 18: 0,17; 19: 0,23; ≥20: 0,40.
- Tipo (art. 10.2): «tipo de gravamen, tipo que será del 30,00 por ciento.»
- Los coeficientes son los de la ordenanza (propios, no los máximos de la ley estatal). Los máximos de la norma foral del IIVTNU de Álava: PENDIENTE (no leí la norma foral).
- Pagado por el vendedor; es un gasto inherente a la transmisión que la ordenanza no declara deducible en el IRPF; la norma foral dice (art. 45.3) que de la enajenación se deducen los gastos y tributos de la letra b) del apartado 1 satisfechos por el transmitente: si incluye la plusvalía municipal, PENDIENTE de confirmar (la letra b) habla de «gastos y tributos inherentes a la adquisición», no a la transmisión).

---

## Otros puntos útiles

- Retención y pago a cuenta del alquiler: no estudiado.
- Tributación conjunta (art. 73 y 97) aumenta la reducción general a 4.896 € por autoliquidación en 2026.
- La NF 3/2025 modificó ITP y IRPF «para vivienda»; leer el Título II completo antes de implementar bonificaciones al inquilino si el producto las modela.

---

## Resumen para el diseño (≤250 palabras)

Diferencias con el IRPF común que obligan a cambiar el motor:

1. Una sola escala foral de 8 tramos (23 a 49 %) sobre la base general; no hay estatal + autonómica. La cuota general baja con una minoración de 1.615 € (2026), no con una escala sobre el mínimo, y el resto de mínimos son deducciones sobre la cuota total: descendientes 734,80 / 909,70 / 1.532,30 / 1.811,70 / 2.366,10 €, más 424,60 € si es menor de 6.
2. El alquiler de vivienda (LAU art. 2) va a la base del ahorro, no a la general. Escala del ahorro de 9 tramos, 19 a 28 %. La regla de reducción es una bonificación del 30 % (35 % en núcleos rurales de la DA 34ª; 70 % en zona tensionada con renta limitada al índice, o programas públicos) sobre el íntegro, y los gastos son una lista cerrada: intereses y financiación, y seguro de impago hasta 300 €. IBI, comunidad, reparaciones y amortización no se deducen. Neto por inmueble ≥ 0; no hay límite ni arrastre de intereses.
3. La ganancia por venta va también a la base del ahorro, con la misma escala foral. Valor de adquisición con gastos y mejoras, actualizado con los coeficientes del decreto foral de cada año (2026: de 2,030 a 1,000). Falta confirmar si se resta amortización mínima aunque no se haya deducido.
4. ITP 4 % vivienda (6 % si el comprador tiene más de 5 viviendas, 7 % otros inmuebles); AJD 0,5 %.
5. Datos por año: la escala de 2025 era otra (17.720 €…).

Pendiente de modelar: índice de referencia de Álava (70 %), amortización mínima en la ganancia.
