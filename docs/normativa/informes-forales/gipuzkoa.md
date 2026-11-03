# Fiscalidad foral de Gipuzkoa para un particular que compra un piso, lo alquila y lo vende

Fecha de la investigación: 2026-11-03. Redactado para HouseFinder/Aldaby.

## 0. Límite de acceso (leer primero)

El `robots.txt` de **www.gipuzkoa.eus**, **egoitza.gipuzkoa.eus** y **www.gipuzkoa.net** bloquea a `ClaudeBot`. Esos tres hosts alojan el BOG, la Hacienda Foral y las normas forales. Según la regla del encargo no descargué nada de ellos con ningún otro agente de usuario.

También quedaron fuera por `robots.txt` o por no resolver:
- `iberley.es` bloquea `anthropic-ai`.
- `cuatrecasas.com` solo permite a `ClaudeBot` ciertas secciones y no sus PDF.
- `ogasun`, `jjggg.eus` y otros subdominios no resuelven.

Lo que sí pude leer en fuente oficial:

| Dominio | Qué contiene | `robots.txt` |
|---|---|---|
| boe.es | Resoluciones de zonas tensionadas | permite |
| euskadi.eus | BOPV y Zergak (revista de la Hacienda vasca) | permite |
| donostia.eus | Ordenanzas municipales | permite |
| ine.es | Códigos de municipio | permite |

**Consecuencia: los puntos 1 a 7 y la parte del IBI de Donostia quedan en «PENDIENTE» como lectura de norma vigente.**
- Para varios puntos hay una fuente oficial secundaria, el artículo de Zergak de un jefe de servicio de la propia Diputación Foral. Describe el *proyecto* de norma foral de diciembre de 2024, no el texto aprobado. Cada cita indica si es proyecto.
- Las cifras de webs de terceros que salieron en la búsqueda se anotan solo como pista, marcadas «NO OFICIAL, sin verificar», y no deben entrar en `data/rules` sin leer el BOG.

URL pendientes de lectura, a abrir a mano o con un agente de usuario permitido por la Diputación:
- Norma Foral 3/2014 consolidada, IRPF: <https://www.gipuzkoa.eus/documents/2456431/null/NF%203-2014%20(31-12-2021)%202.pdf/f57832da-7bd7-0d4e-8642-3b2ae7e83889>. Está actualizada a 31-12-2021, así que además hay que leer sus modificaciones posteriores.
- Norma Foral 6/2025, de 19 de diciembre, de Presupuestos 2026. Se publicó en el BOG el 31-12-2025, según un resultado de búsqueda no oficial.
- La norma foral de reforma del sistema tributario de Gipuzkoa de 2025. Su número exacto es PENDIENTE.
- Norma Foral 18/1987, ITP y AJD.
- Página «Deducción por alquiler» de la Hacienda Foral: <https://www.gipuzkoa.eus/es/web/ogasuna/-/deduccion-por-alquiler>.
- Guía de renta (capital inmobiliario), ejercicio 2021: <https://www.gipuzkoa.eus/documents/2456431/27853246/Renta2021+-+03+Rend+Cap+Inmobiliario.pdf/4e8a510f-659c-a538-06f3-4e5dd88100f8>. Hay que buscar la del ejercicio 2025 o 2026.

---

## 1. IRPF, estructura y escala general

**PENDIENTE.** Fuente oficial bloqueada.

Pista NO OFICIAL, sin verificar (resultados de búsqueda de webs de terceros):
- Escala general de ocho tipos marginales: 23, 28, 35, 40, 45, 46, 47 y 49 %.
- Tramos hasta 18.080, 36.160, 54.240, 77.450 y 107.260 euros, y el último desde 204.270 euros.
- Se atribuye a la deflactación del 2 % de la Norma Foral 6/2025 (presupuestos 2026).
- Esas fuentes contradicen entre sí qué ejercicio cubre cada tabla.

Estructura, solo lo que sé por fuente oficial: la norma regulatoria es la NF 3/2014, de 17 de enero (citada en Zergak, p. 20 y ss.). Se habla de «base imponible general» y «base imponible del ahorro» de la norma foral, con una única escala del territorio. No leí el artículo de la escala ni el de la cuota, así que que no exista parte estatal y autonómica no lo tengo verificado en el texto de la norma.

## 2. IRPF, base del ahorro

**PENDIENTE.** Escala y rentas que integran la base. Pista NO OFICIAL: de 19 a 28 % con nueve tramos desde 2026, frente a una escala de cinco tramos del 20 al 25 % en 2025.

## 3. IRPF, mínimos personales y familiares

**PENDIENTE.** Importes y mecánica sin fuente oficial leída.

Pista NO OFICIAL, 2026, atribuida a la NF 6/2025:

| Concepto | Importe anual |
|---|---|
| Descendientes | 682, 844, 1.421, 1.680 y 2.195 euros (1.º a 5.º y siguientes) |
| Ascendiente conviviente | 328 euros |
| Mínimo personal | 1.615 euros más el 2 %, dato dudoso |

Esa misma pista dice que los mínimos se aplican como deducción de la cuota. Es el cambio de diseño más importante, pero falta la lectura oficial.

Fuente oficial parcial, Zergak: para el régimen especial de menores de 36 años, el proyecto cita la «deducción por descendientes» como deducción. Por tanto es una deducción en la cuota, no una reducción de la base. Cita literal: «deducción por descendientes, deducción por alquiler de vivienda habitual y, finalmente, deducción por adquisición de vivienda habitual» (p. 24).

## 4. IRPF, alquiler de vivienda

### Fuente oficial leída: Zergak n.º 68 (2-2024), artículo de Rodrigo Llano-Ponte Babace

URL: <https://www.euskadi.eus/contenidos/informacion/zergak68/es_def/adjuntos/Zergak_Art2_LLano_CAST.pdf>

El autor es jefe de servicio de Desarrollo Normativo y Asesoramiento Jurídico de la Diputación Foral de Gipuzkoa. El PDF es de febrero de 2025.

Describe el «Proyecto de Norma Foral por la que se aprueban la reforma del sistema tributario del Territorio Histórico de Gipuzkoa, y otras modificaciones tributarias», aprobado por el Consejo de Gobierno Foral el 27-12-2024.

**Es un proyecto. Hay que contrastarlo con la norma foral aprobada, que no pude leer.** La disposición final segunda del proyecto fija efectos desde 2025 o 2026 según la medida.

Cambios en el artículo 32 de la NF 3/2014 (pp. 21-22):

1. **Apartado 1: vivienda sin actividad económica y no incluida en los demás.** Es el arrendamiento de temporada y de vivienda turística.
   - Cita: «A los rendimientos íntegros se le aplicará una bonificación del 20 por ciento y serán deducibles como gasto únicamente los intereses por capitales ajenos […] y demás gastos de financiación. El rendimiento neto positivo obtenido por cada inmueble se integrará en la base imponible general.»
2. **Apartado 2: arrendamiento de vivienda habitual según el artículo 2 de la LAU.**
   - Cita: «la bonificación se incrementa del 20 por ciento actual al 30 por ciento y se incluye como gasto deducible las primas de seguro para impago, total o parcial, con el límite de 300 euros anuales.»
   - Se mantienen los intereses y demás gastos de financiación.
   - Cita: «el rendimiento neto positivo obtenido por cada inmueble se integrará en la base imponible del ahorro.»
3. **Apartado 3: programas públicos ASAP y Bizigune.** Bonificación del 50 % del rendimiento íntegro. Solo son deducibles intereses y gastos de financiación. El neto va a la base del ahorro.
4. **Apartado 4: vivienda habitual en zona de mercado residencial tensionado, arrendada por primera vez o no arrendada en los últimos cinco años.**
   - Cita: «la bonificación se incrementa hasta el 50 por ciento».
   - Se admite la prima de seguro de impago (hasta 300 euros anuales) y los intereses y gastos de financiación.
   - El neto va a la base del ahorro.
5. **Apartado 5: demás rendimientos inmobiliarios.** Sin bonificación. Se deducen los gastos necesarios, incluida la amortización.
   - Cita: «se permite deducir el importe del deterioro sufrido por el uso o el transcurso del tiempo».
   - El neto va a la base general.

Resumen para el motor, si el proyecto se aprobó tal cual:
- La bonificación es sobre el rendimiento íntegro, no sobre el neto.
- Los gastos deducibles de la vivienda habitual son solo intereses y gastos de financiación, más el seguro de impago hasta 300 euros.
- **No hay deducción de IBI, comunidad, reparaciones ni amortización** en los apartados 1 a 4. La amortización solo existe en el apartado 5.
- El neto de la vivienda habitual va a la base del ahorro.

Pista NO OFICIAL, no verificada: una fuente de terceros dice que «la suma de la bonificación y de los gastos deducibles no podrá dar lugar, para cada inmueble, a un rendimiento neto negativo». Esto coincide con el cuadro de la Diputación de 2010 (ver abajo): «El rendimiento neto no puede ser negativo». Falta leer la norma vigente.

### Fuente oficial antigua, solo como contraste histórico

«Fiscalidad vivienda», Gobierno Vasco, creado el 30-04-2010: <https://www.euskadi.eus/contenidos/informacion/ovv_administracion143/es_ovv_admi/adjuntos/Fiscalidad_vivienda.pdf>

Decía: «Gastos deducibles: 20% de bonificación sobre rendimientos íntegros + intereses de la financiación ajena […]. El rendimiento neto no puede ser negativo». No es vigente. Sirve para ver que el esquema (bonificación sobre el íntegro, solo intereses, neto no negativo) es antiguo en Gipuzkoa.

Para tu motor actual, que usa «reducción del 50 % (60 % ahora) y gastos con límite intereses + reparación», la mecánica foral es distinta: ver «Resumen para el diseño».

## 5. IRPF, ganancia patrimonial por la venta

**PENDIENTE.** Ni la base a la que va, ni el cálculo del valor de adquisición, ni los coeficientes de actualización los pude leer en fuente oficial.

Lo que sí consta en Zergak: el artículo 49 de la NF 3/2014 regula la exención por reinversión en vivienda habitual. Eso no aplica a un piso de alquiler.

Pista NO OFICIAL: la ganancia va a la base del ahorro. Los coeficientes de actualización en Gipuzkoa los aprueba la norma foral de presupuestos de cada año, pero no hay lectura oficial de su tabla.

## 6. ITP, tipo general de transmisión de inmuebles

Fuente oficial parcial, Zergak p. 25:
- Se modifica «la letra a) de la letra c) del artículo 11.1 de la Norma Foral 18/1987» para flexibilizar el tipo reducido del 2,5 % de vivienda habitual.
- En el mismo texto: «tipo ITP del 4%, operación sujeta a IVA o adquirida por sucesión o donación».
- Eso apunta a que el tipo ordinario de vivienda es **el 4 %**, y el 2,5 % es el reducido de vivienda habitual.

El texto de la norma foral vigente y el tipo para un inmueble que no es vivienda quedan **PENDIENTES**.

Contraste antiguo (2010, no vigente): «Transmisión de viviendas, general: 4%; 2,5% […] vivienda habitual».

## 7. AJD, vivienda nueva sujeta a IVA

**PENDIENTE.** Sin fuente oficial vigente leída.

Dato de 2010, no vigente: «Adquisición de vivienda nueva: vivienda libre: 0,5%».

## 8. Zonas de mercado residencial tensionado

Competencia: Gobierno Vasco, Departamento de Vivienda y Agenda Urbana, artículo 18.2 de la Ley 12/2023. La declaración dura tres años y es prorrogable. El Ministerio publica cada trimestre la relación en el BOE.

**Ámbito de Donostia: el municipio entero.** Cita de la Orden de 2 de mayo de 2025 (BOPV n.º 96, 23-05-2025):
«Declarar el municipio de Donostia / San Sebastián como Zona de mercado residencial tensionado».
<https://www.euskadi.eus/web01-bopv/es/bopv2/datos/2025/05/2502228a.shtml>

La misma orden dice que se aplica a los contratos de alquiler la limitación de renta del artículo 17.7 de la LAU «sobre inmuebles en los que no hubiese estado vigente ningún contrato de arrendamiento en los últimos cinco años».

**Gran tenedor en Donostia:** titular de cinco o más inmuebles urbanos de uso residencial en el municipio, excluidos garajes y trasteros.

Cada resolución del BOE dice «Tres años desde el día siguiente a la publicación de la presente resolución» y «Esta resolución surtirá efectos desde el día siguiente al de su publicación». Los efectos y el fin de vigencia son:

| Municipio | Código INE (comprobado) | Orden de declaración | Resolución BOE y fecha | Efectos desde | Vence |
|---|---|---|---|---|---|
| Errenteria | 20067 | Orden 1-10-2024, BOPV 202 de 16-10-2024 | BOE-A-2025-1721, BOE 30-01-2025 | 2025-01-31 | 2028-01-31 |
| Lasarte-Oria | 20902 | Orden 18-3-2025, BOPV 69 de 9-4-2025 | BOE-A-2025-8636, BOE 30-04-2025 | 2025-05-01 | 2028-05-01 |
| Zumaia | 20081 | Orden 18-3-2025, BOPV 69 de 9-4-2025 | BOE-A-2025-8636 | 2025-05-01 | 2028-05-01 |
| Irun | 20045 | Orden 31-3-2025, BOPV 76 de 23-4-2025 | BOE-A-2025-8636 | 2025-05-01 | 2028-05-01 |
| **Donostia/San Sebastián** | **20069** | Orden 2-5-2025, BOPV 96 de 23-5-2025 | BOE-A-2025-15728, BOE 29-07-2025 | 2025-07-30 | 2028-07-30 |
| Astigarraga | 20903 | Orden 21-8-2025, BOPV 173 de 12-9-2025 | BOE-A-2025-21901, BOE 30-10-2025 | 2025-10-31 | 2028-10-31 |
| Usurbil | 20073 | Orden 21-8-2025, BOPV 173 de 12-9-2025 | BOE-A-2025-21901 | 2025-10-31 | 2028-10-31 |
| Hernani | 20040 | Orden 18-11-2025, BOPV 229 de 27-11-2025 | BOE-A-2026-2448, BOE 02-02-2026 | 2026-02-03 | 2029-02-03 |
| Lezo | 20053 | Orden 11-12-2025, BOPV 251 de 30-12-2025 | BOE-A-2026-2448 | 2026-02-03 | 2029-02-03 |
| Tolosa | 20071 | Orden 11-12-2025, BOPV 251 de 30-12-2025 | BOE-A-2026-2448 | 2026-02-03 | 2029-02-03 |
| Pasaia | 20064 | Orden 17-2-2026, BOPV 39 de 26-2-2026 | BOE-A-2026-9175, BOE 27-04-2026 | 2026-04-28 | 2029-04-28 |
| Zestoa | 20027 | Orden 17-2-2026, BOPV 39 de 26-2-2026 | BOE-A-2026-9175 | 2026-04-28 | 2029-04-28 |
| Arrasate/Mondragón | 20055 | Orden 3-3-2026, BOPV 49 de 12-3-2026 | BOE-A-2026-9175 | 2026-04-28 | 2029-04-28 |

Notas:
- Los códigos INE salen del diccionario oficial del INE a 1-1-2026: <https://www.ine.es/daco/daco42/codmun/diccionario26.xlsx>.
  - Hay códigos de 5 cifras que no coinciden con los que se suelen recordar. Por ejemplo, Pasaia es 20064 y Errenteria es 20067.
  - Los 13 nombres de la tabla se buscaron en ese fichero. Nombre INE de Donostia: «Donostia/San Sebastián».
- Las fechas «Efectos desde» y «Vence» las calculo yo como «día siguiente al de la publicación en el BOE» más tres años, tal como dicen las resoluciones. Los municipios de la tabla con «gran tenedor» y limitación del art. 17.7: todos dicen «Sí, conforme a la Orden…».
- Umbrales de gran tenedor que difieren: Pasaia «más de cinco inmuebles […] o una superficie construida de más de 1.500 m²»; Zestoa «más de diez inmuebles […] o 1.500 m²». El resto, cinco o más inmuebles.
- Resoluciones del BOE leídas:
  - <https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-1721>
  - <https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-8636>
  - <https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-15728>
  - <https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-21901>
  - <https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-2448>
  - <https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-9175>
- La del segundo trimestre de 2026, BOE-A-2026-16532 (BOE 29-07-2026), no recoge ningún municipio de Gipuzkoa (solo Basauri en el País Vasco).
- **Aún no encontré la del tercer trimestre de 2026.** Debería publicarse hacia finales de octubre o noviembre de 2026. Revisar el BOE.
- Los municipios con expediente en trámite (por ejemplo Orio) no están en la tabla y no cuentan.
- BOE-A-2025-20246 es una corrección de erratas de la resolución de julio de 2025 (la de Donostia). No la leí; verificar qué corrige.
- Una corrección de erratas posterior no cambia lo anterior sin lectura. Pendiente.

## 9. Alquiler turístico

### Nivel autonómico, norma del Gobierno Vasco (leída)

**Decreto 101/2018, de 3 de julio, de viviendas y habitaciones de viviendas particulares para uso turístico** (BOPV n.º 143, 26-07-2018): <https://www.euskadi.eus/bopv2/datos/2018/07/1803822a.pdf>

- Definición, art. 1.2: vivienda para uso turístico es la que se ofrece o cede temporalmente «en su totalidad, como alojamiento por motivos turísticos, de modo reiterado o habitual, a cambio de contraprestación económica, en condiciones de inmediata disponibilidad».
- Declaración responsable, art. 7.1: «La presentación completa de la declaración responsable de inicio de actividad habilita desde ese momento para el desarrollo de la actividad y tiene como efecto inmediato su inscripción en el Registro de Empresas y Actividades Turísticas de Euskadi».
- Normativa urbanística, art. 12.1: «Además de cumplir la normativa urbanística y sobre edificación de carácter general que les sea aplicable».
- Seguro, art. 17.2: «35.000 euros por plaza».
- Propiedad horizontal, art. 19: no puede ejercerse «si los estatutos o normas que regulen la comunidad de propietarios, debidamente inscritos en el Registro de la Propiedad, contienen una prohibición expresa al efecto».
- Número de registro en toda comercialización, art. 20.1.

**Decreto 52/2025, de 25 de febrero**, que modifica el anterior (BOPV n.º 53, 18-03-2025): <https://www.euskadi.eus/web01-bopv/es/bopv2/datos/2025/03/2501233a.shtml>. Entra en vigor el día siguiente al de su publicación (19-03-2025). Deroga la disposición adicional primera, que excluía el medio rural, y da seis meses de adecuación a las viviendas inscritas en núcleos rurales o suelo no urbanizable.

### Donostia (fuente oficial: censo municipal de datos abiertos)

<https://www.donostia.eus/datosabiertos/catalogo/censo-viviendas-turisticas>

- «Modificación del PGOU (2023)»: moratoria desde el 19-04-2023, de un año inicialmente. En 2024 la aprobación inicial alargó la suspensión otros dos años.
- «en febrero de 2026 se aprobó por unanimidad la modificación definitiva del PGOU que blinda el uso residencial frente al turístico. El nuevo PGOU impide la concesión de nuevas licencias para viviendas de uso turístico.»
- La ordenanza anterior (VUT-APP, 2018) dividía la ciudad en zonas A, B y C y prohibía nuevas viviendas turísticas en la zona saturada (A).
- Fecha exacta de aprobación definitiva y publicación en el BOG: **PENDIENTE**. Una búsqueda apunta al pleno del 29-01-2026, pero no lo verifiqué.

### Impuesto turístico de Donostia (relacionado)

<https://donostia.eus/es/actualidad/aprobacion-impuesto-turistico>: aprobación inicial; las viviendas de uso turístico pagarían 6,5 euros por noche desde el 1-1-2027, con tope de seis noches por estancia. Estado definitivo: PENDIENTE.

## 10. IBI y plusvalía municipal de Donostia/San Sebastián

### Marco legal

Las ordenanzas citan la Norma Foral 12/1989, de 5 de julio, del IBI, y la Norma Foral 16/1989, de 5 de julio, de plusvalía. La ordenanza de Donostia fija el tope de la NF para el tipo incrementado (art. 18.2 de la ordenanza):
- «Uno, de carácter general, hasta el límite del 4 por 1000.»
- «Otro, hasta el límite del 6 por 1000» para suelo industrial o terciario.
- Para rústica, «hasta el límite del 1,1 por 100».

Esa estructura difiere del TRLRHL estatal (que da un tipo mínimo y máximo por tramos de municipio): aquí el Ayuntamiento fija el tipo en el anexo y puede incrementarlo con topes.

### IBI

Ordenanza IBI 2026: <https://www.donostia.eus/Ordenanzas.nsf/vListadoId/2266144632629339C1258CAF002BB07B?OpenDocument=&id=C671670&idioma=cas>

- Art. 18.1: «Los tipos de gravamen los fija el Ayuntamiento, y constan en el anexo a esta Ordenanza.»
- Diligencia: última modificación aprobada por el Pleno el 25-09-2025 y publicada en el BOG n.º 236 de 10-12-2025.
- Recargo (arts. 20-23): se aplica a la vivienda que no es residencia habitual; la cuantía va en el anexo. Art. 23 lo exceptúa, por ejemplo, para alojamiento turístico y alquiler a estudiantes. El texto completo de las exenciones no lo leí.
- **Tipo de gravamen vigente: PENDIENTE.** El anexo es una imagen que no pude localizar: el enlace a los anexos de la página del IBI viene vacío. Sí localicé la del impuesto de plusvalía (ver abajo).
- Proyecto de acuerdo para 2026: «incrementar el tipo impositivo un 2%» desde el 1-1-2026 (<https://www.donostia.eus/Ordenanzas.nsf/vListadoIdAnexos/85351F3E0DA0CD15C1258D1400373FFF?OpenDocument=&id=&idioma=cas>). Es un borrador sin tipo base.
- Propuesta 2027: «subida general moderada del 2,3%» (<https://www.donostia.eus/es/actualidad/noticia-ordenanzas-fiscales-2027>). Aprobada por la Junta de Gobierno el 19-05-2026. Un registro de plenos citado en una búsqueda sitúa la aprobación inicial de la ordenanza del IBI el 24-09-2026. Estado final: PENDIENTE.
- Pista NO OFICIAL, sin verificar: una web de terceros da 0,208872 % para 2026. No usar.

### Plusvalía municipal (leída del anexo oficial)

Ordenanza: <https://www.donostia.eus/Ordenanzas.nsf/vListadoId/18248C51D10DA186C1258CAF002BC2BC?OpenDocument=&sf=1&id=C671670&idioma=cas>

Anexo a regir desde el 1-1-2026 (imagen del propio sitio): <https://www.donostia.eus/Ordenanzas.nsf/0/1975d41452f39a0ec1258caf002bc668/Body/0.92?OpenElement&FieldElemFormat=gif>

Título del anexo: «PORCENTAJE ANUAL PARA DETERMINAR EL INCREMENTO DE VALOR PARA UN PERIODO DE:».

| Periodo de generación | Coeficiente |
|---|---|
| Inferior a 1 año | 0,16 |
| 1 año | 0,15 |
| 2 años | 0,15 |
| 3 años | 0,15 |
| 4 años | 0,16 |
| 5 años | 0,18 |
| 6 años | 0,20 |
| 7 años | 0,22 |
| 8 años | 0,23 |
| 9 años | 0,21 |
| 10 años | 0,16 |
| 11 años | 0,13 |
| 12 años | 0,11 |
| 13 a 16 años | 0,10 |
| 17 años | 0,12 |
| 18 años | 0,16 |
| 19 años | 0,22 |
| Igual o superior a 20 años | 0,35 |

Nota del anexo, literal: «alguno de los coeficientes aprobados por la vigente ordenanza fiscal, resultará ser superior al correspondiente nuevo máximo legal, se aplicará éste directamente hasta que entre en vigor la nueva ordenanza fiscal que corrija dicho exceso.»

**Tipo de gravamen** («en función de los periodos en transmisiones de terrenos en los que se aplique el valor a efectos del impuesto sobre bienes inmuebles resultante de las nuevas ponencias de valoración»):

| Periodo | Tipo (%) |
|---|---|
| Hasta 5 años | 17,809200 |
| Hasta 10 años | 16,136400 |
| Hasta 15 años | 14,463600 |
| Hasta 20 años | 13,351800 |

Otras reglas, de la ordenanza:
- El periodo máximo es de veinte años y se cuentan años completos.
- Para periodos inferiores a un año se prorratea por meses completos.
- La última modificación se aprobó el 25-09-2025 y se publicó en el BOG n.º 236 de 10-12-2025.
- Hay una bonificación del 95 % de la cuota en transmisiones mortis causa a descendientes, cónyuge y pareja de hecho, entre otros.
- Para 2027 la propuesta municipal sube un 2,3 %. Un pleno del 23-07-2026 trata una modificación de la ordenanza. Su resultado es PENDIENTE.
- Nota STC 46/2024, de 12 de marzo (BOE-A-2024-8189): anuló preceptos de la NF 16/1989 de Gipuzkoa que establecían la base imponible objetiva de aplicación imperativa. Hay que comprobar cómo incide en el cálculo vigente (si se puede probar pérdida o se aplica el método más favorable). No leí esa sentencia entera.

---

## Pistas extra detectadas, sin leer

- **Real Decreto-ley 29/2026, de 6 de octubre**, medidas urgentes para la función social de la vivienda (BOE-A-2026-20823). Es estatal y no se aplica a los tributos forales, pero conviene revisar si afecta a arrendamientos urbanos (LAU) en zonas tensionadas.
- STC 46/2024 (plusvalía), mencionada arriba.
- Resumen de la reforma 2025 «Norma Foral 1/2025» según una web de terceros. Falta el número y el texto del BOG.

---

## Resumen para el diseño

Con la reserva de que el texto de la norma vigente no pude leerlo (solo el proyecto de Zergak), las diferencias con el IRPF común que obligan a cambiar el motor son:

1. **Una sola escala foral, sin parte estatal y autonómica.** Hay dos escalas: general y ahorro. Los tramos de 2026 siguen PENDIENTES de lectura oficial.
2. **Mínimos como deducción en cuota, no como «escala sobre el mínimo».** Parece que los mínimos y las deducciones por descendientes se restan de la cuota. Verificarlo en la NF 3/2014 y en la norma de presupuestos.
3. **Alquiler: bonificación sobre el íntegro, no reducción del neto.**
   - Vivienda habitual (LAU): bonificación del 30 %. En zona tensionada con vivienda no alquilada en cinco años: 50 %. Programas ASAP y Bizigune: 50 %.
   - Vivienda de temporada o turística: 20 %.
4. **Gastos deducibles muy reducidos.** En los cuatro regímenes con bonificación solo se deducen intereses y demás gastos de financiación, más el seguro de impago hasta 300 euros anuales. **No hay límite «intereses + reparación», ni amortización, ni IBI, ni comunidad.** La amortización solo existe en el apartado 5, sin bonificación.
5. **Base del neto.** El neto de la vivienda habitual va a la **base del ahorro** (no a la general). El de temporada o turística va a la general.
6. **Hay que modelar la zona tensionada.** La lista de la sección 8 con fechas de vigencia es un dato con vigencia por municipio y fecha.
7. **Plusvalía municipal con coeficientes propios por año de tenencia** (tabla del anexo) y tipo que baja con los años. Ya hay soporte para «tipo por años de tenencia».
8. **ITP**: tipo ordinario de vivienda del 4 %, según Zergak, frente al de la comunidad común. Falta leer la norma. **AJD**: pendiente.
9. **Venta**: ganancia y actualización del valor PENDIENTES. No asumir la mecánica estatal.
10. **Fechas de efectos.** Algunas medidas del proyecto empiezan el 1-1-2025 o 1-1-2026 según la disposición final segunda. Hay que fijar la fecha de efectos de cada una.
