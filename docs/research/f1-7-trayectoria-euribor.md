# F1.7 · Qué serie pública da la trayectoria esperada del Euríbor

**Fecha:** 2026-10-28 · **Estado:** propuesta para decidir · **Decide:** Rodrigo

## Pregunta

Las hipotecas variables y mixtas en España se revisan con el **Euríbor a un año**. El motor
(`engines/rates.py`, `RatePath`) necesita su trayectoria esperada durante el plazo del préstamo,
como dato con fecha y fuente oficial, no como predicción propia (ROADMAP F1.7).

## Resumen

**Ninguna fuente oficial pública publica una trayectoria esperada del Euríbor a un año.** Las que
existen dan el **Euríbor a tres meses** con un horizonte de 2–3 años, o una curva de bonos
soberanos que no es Euríbor.

**Propuesta:** usar el supuesto técnico de tipos a corto plazo de las proyecciones del Eurosistema
publicado como datos por el BCE (`MPD.Q.U2.STN.I.<ronda>.0000`), y pasarlo a Euríbor a un año con
una conversión documentada, anclada al dato oficial del mes de corte publicado en el BOE. Más
allá del horizonte de la ronda, tipo constante, declarado como supuesto.

## Candidatas

Todo lo marcado ✔ está leído en la fuente primaria; los valores están copiados tal cual.

### A. Supuesto técnico de las proyecciones del BCE (datos: dataset `MPD`) — recomendada

- ✔ Qué es: la fila «Three-month EURIBOR (percentage per annum)» de la tabla de supuestos de las
  proyecciones del personal del BCE. Septiembre de 2026: `2.2  2.4  3.0  3.0` para 2025–2028.
  Corte: «based on market expectations, with a cut-off date of 19 August 2026».
  [Proyecciones de septiembre de 2026](https://www.ecb.europa.eu/press/projections/html/ecb.projections202609_ecbstaff~8e340fc69d.en.html)
- ✔ Como datos: la API del BCE publica la misma serie **trimestral** como
  `MPD.Q.U2.STN.I.S26.0000` («short term interest rates – September 2026 staff macroeconomic
  projections», unidad `PA`). La anual `MPD.A.U2.STN.I.S26.0000` coincide con la tabla
  (2.2, 2.4, 3, 3). Valores trimestrales consultados el 2026-10-28:

  | 2026T3 | 2026T4 | 2027T1 | 2027T2 | 2027T3 | 2027T4 | 2028T1–T4 |
  | --- | --- | --- | --- | --- | --- | --- |
  | 2.5 | 2.7 | 2.9 | 3 | 3 | 3 | 3 |

  `https://data-api.ecb.europa.eu/service/data/MPD/Q.U2.STN.I.S26.0000?format=csvdata`
- ✔ Hay una serie por ronda (`W` marzo, `G` junio, `S` septiembre, `A` diciembre; p. ej.
  `G26`, `A25`), así que cada ronda queda guardada con su fecha.
- **A favor:** oficial, basada en precios de mercado (no en opinión), legible por máquina,
  trimestral, histórica por ronda.
- **En contra:** es el Euríbor a **3 meses**; horizonte de unos 2,5 años; se actualiza cada
  trimestre, así que el corte puede tener hasta tres meses de antigüedad.

### B. Supuestos de las proyecciones del Banco de España

- ✔ Fila «Short-term interest rate (3-month EURIBOR; level) (e)»: `2,2  2,5  3,6` para 2025–2027.
  Nota: «These assumptions are based on futures market prices or on proxies thereof and should
  not be interpreted as a Eurosystem prediction». Corte: 24 de septiembre.
  [Proyecciones del tercer trimestre de 2026](https://www.bde.es/wbe/en/publicaciones/analisis-economico-investigacion/proyecciones-macro-informe-trimestral/proyecciones-e-informe-trimestral-de-la-economia-espanola-tercer-trimestre-2026.html)
- **A favor:** misma metodología del Eurosistema y corte más reciente.
- **En contra:** solo medias anuales y dos años; sin fichero de datos para esta tabla.
- **Dato importante:** para 2027 da **3,6** frente al **3,0** del BCE. Las dos rondas se separan
  cinco semanas, y en ese tiempo el mercado se movió. Cualquier fuente de este tipo envejece
  rápido: el plan debe mostrar la fecha de corte.

### C. Encuesta a analistas monetarios del BCE (SMA)

- ✔ Variables del cuestionario de octubre de 2026: DFR, MRO, MLF, €STR y «3-month EURIBOR», por
  reunión hasta Sep-27, por trimestre hasta 2029T4 y «Long run». **No incluye el Euríbor a un año.**
- ✔ Resultados de septiembre de 2026 (69 respuestas), mediana del Euríbor a 3 meses: Sep-2026
  2.55; 2027T4 2.43; 2028T4 2.32; 2029T3 2.18. Publica también P25 y P75.
  [Resultados de septiembre de 2026 (PDF)](https://www.ecb.europa.eu/stats/ecb_surveys/sma/shared/pdf/ecb.smar260911_september.en.pdf)
- **A favor:** horizonte más largo, trae un rango (P25–P75) y un valor de largo plazo.
- **En contra:** es opinión de analistas, no mercado; solo en PDF (el código de serie que imprime
  el PDF no existe en la API); y va **en sentido contrario** al mercado: bajando hasta 2,18
  frente a subir hasta 3,0. Útil como escenario alternativo, no como base.

### D. Curva a plazo de la deuda pública AAA de la zona del euro (dataset `YC`)

- ✔ «The forward curve shows the short-term (instantaneous) interest rate for future periods
  implied in the yield curve.» Diaria desde el 6 de septiembre de 2004, vencimientos de 3 meses a
  30 años, método de Svensson, solo bonos soberanos.
  [Metodología](https://data.ecb.europa.eu/methodology/yield-curves)
- ✔ Por API: `YC.B.U2.EUR.4F.G_N_A.SV_C_YM.IF_1Y` = 3.1366 y `…IF_5Y` = 3.3272 el 2026-10-26.
- **A favor:** diaria, hasta 30 años, legible por máquina.
- **En contra:** **no es Euríbor**: es deuda soberana AAA, con otro riesgo de crédito. Pasarla a
  Euríbor exige estimar un diferencial que cambia con el tiempo y el plazo. Eso sería modelo
  propio, justo lo que F1.7 quiere evitar.

### E. Euríbor a un año observado (punto de partida, no trayectoria)

- ✔ BOE, resolución mensual del Banco de España, septiembre de 2026: «Tres meses. 2,635» y
  «Un año. 3,247». Definición en el anejo 8 de la Circular 5/2012. Disponible también en XML.
  [BOE-A-2026-20519](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-20519)
- ✔ La misma media mensual está en la API del BCE (`FM.M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA`: julio
  2.855087, agosto 2.9536667, septiembre 3.247), pero viene marcada «provided by Refinitiv».
  **El BOE es la fuente a citar.**
- EMMI (administrador del Euríbor) exige licencia para el uso comercial de los datos de su web.
  Usar la publicación oficial del BOE evita depender de EMMI, pero conviene confirmarlo en la
  consulta legal de F0.6.

## Propuesta

1. **Fuente de la trayectoria:** `MPD.Q.U2.STN.I.<ronda>.0000` de la última ronda publicada
   (A). Se guarda en `data/params/` con `kind: trayectoria_euribor`, la ronda, la fecha de corte
   y la URL de la API. `provisional: false`, porque la fuente es oficial y está documentada.
2. **De 3 meses a un año:** el Euríbor a un año en el trimestre *t* ≈ media de los cuatro
   trimestres de la trayectoria a 3 meses desde *t* + una prima constante. La prima se mide una
   vez por ronda: Euríbor a un año del BOE en el mes de corte − media de los cuatro primeros
   trimestres de la trayectoria. Es una transformación nuestra, simple y declarada: va como
   `SourceRef(kind="assumption")` en cada cifra.
   - Alternativa más simple: sumar el diferencial observado de un año menos tres meses (0,612 en
     septiembre de 2026). **No la recomiendo:** ese diferencial ya incluye las subidas
     esperadas, así que sumarlo a una trayectoria que sube las contaría dos veces.
3. **Más allá del horizonte** (desde 2029): último valor constante, como `assumption`. El
   escenario de estrés (+N puntos) cubre la incertidumbre de ese tramo.
4. **SMA (C) como escenario alternativo** opcional en el plan («si los analistas aciertan»),
   no como base.
5. **Actualización:** cuatro veces al año, con cada ronda de proyecciones (marzo, junio,
   septiembre, diciembre). En F4.7 será un trabajo programado; hasta entonces, a mano.

## Qué hace falta decidir

- ¿Aceptas la fuente A y la conversión del punto 2? Si sí, va a un ADR antes de implementarse,
  porque es una fuente de datos nueva.
- ¿Prefieres, en cambio, no convertir y aplicar el diferencial de la oferta sobre el Euríbor a
  3 meses? Es más simple, pero la cuota saldría por debajo de la real mientras el Euríbor a un
  año esté por encima del de 3 meses (hoy, 0,6 puntos).

## No verificado

- Las condiciones de reutilización propias del ECB Data Portal (leí el aviso legal general del
  BCE: uso libre citando al BCE como fuente) y las del BOE.
- La fila 2029T4 y el largo plazo del SMA de septiembre (no leí la página 5 del PDF).
