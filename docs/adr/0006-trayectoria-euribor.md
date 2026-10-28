# ADR-0006: Trayectoria esperada del Euríbor a un año

**Estado:** Aceptada · **Fecha:** 2026-10-28 · **Decide:** Rodrigo

## Contexto
Las hipotecas variables y mixtas en España se revisan con el Euríbor a un año. El motor de
hipotecas (`engines/rates.py`) recibe la trayectoria del índice como `RatePath`, y F1.7 pide que
salga de una fuente oficial publicada, como dato con fecha, no como predicción propia.

La investigación (`docs/research/f1-7-trayectoria-euribor.md`) concluye que ninguna fuente oficial
pública da la trayectoria esperada del Euríbor a un año. Las que hay dan el Euríbor a tres meses
con un horizonte de 2–3 años (proyecciones del Eurosistema, encuesta SMA del BCE) o una curva de
deuda soberana AAA que no es Euríbor.

## Decisión

### Fuente
- **Trayectoria a tres meses:** el supuesto técnico de tipos a corto plazo de la última ronda de
  proyecciones del personal del BCE, publicado como datos en la serie trimestral
  `MPD.Q.U2.STN.I.<ronda>.0000` de la API del BCE (rondas `W` marzo, `G` junio, `S` septiembre,
  `A` diciembre; p. ej. `S26`). Está basado en precios de mercado y coincide con la fila
  «Three-month EURIBOR» de la tabla de supuestos publicada.
- **Ancla:** el Euríbor a un año oficial del último mes completo anterior a la fecha de corte de la
  ronda, tal como lo publica el Banco de España en el BOE (resolución mensual de tipos de
  referencia oficiales del mercado hipotecario). Se cita el BOE, no la serie del BCE marcada
  «provided by Refinitiv».

### Conversión de tres meses a un año (transformación propia, declarada)
Con `m3[q]` = Euríbor a tres meses de la ronda en el trimestre `q`, y `q0` = trimestre que contiene
el mes del ancla:

```
prima        = euribor_12m_oficial(mes del ancla) − media(m3[q0], m3[q0+1], m3[q0+2], m3[q0+3])
euribor_12m[q] = media(m3[q], m3[q+1], m3[q+2], m3[q+3]) + prima
```

- Más allá del último trimestre de la ronda, `m3` se mantiene en su último valor.
- La prima es constante en toda la trayectoria y se recalcula con cada ronda.
- Ejemplo con la ronda `S26` (corte 19 de agosto de 2026; ancla, julio de 2026): `m3` = 2.5, 2.7,
  2.9, 3 y luego 3; media de los cuatro primeros = 2,775; con un Euríbor a un año de julio de 2,855,
  prima = 0,080, y la trayectoria a un año queda 2,855 · 2,980 · 3,055 · 3,080 y 3,080 desde
  entonces. (Valor de julio tomado de la serie del BCE; al cargarlo se copia del BOE.)

### Datos y procedencia
- La ronda y el ancla se guardan en `data/params/` (ADR-0005) con su fecha de corte, el código de
  serie, la URL de la API o del BOE y `provisional: false`. Los valores se copian tal cual se
  publican (en porcentaje) y se pasan a tanto por uno al cargarlos, para poder cotejarlos con la
  fuente sin conversiones a mano.
- Toda cifra que use la trayectoria cita tres fuentes: la ronda (`param`), el ancla (`param`) y la
  conversión (`SourceRef(kind="assumption", id="conversion-euribor-3m-12m")`). El tramo más allá del
  horizonte cita además `SourceRef(kind="assumption", id="euribor-constante-tras-horizonte")`.
- Las fechas de calendario de la trayectoria se pasan a meses desde la firma del préstamo fuera de
  `engines/`; el motor sigue recibiendo un `RatePath` en meses.
- El plan muestra siempre la fecha de corte de la ronda.

### Actualización
Una ronda nueva cada trimestre (marzo, junio, septiembre, diciembre): se añade un registro con su
vigencia; las rondas anteriores se conservan para poder rehacer planes antiguos. A mano hasta que
exista la cola de trabajos (F4.7).

## Opciones consideradas
- **Proyecciones del Banco de España:** misma metodología y corte más reciente, pero solo medias
  anuales a dos años y sin fichero de datos. Descartada como fuente; útil para contrastar.
- **Encuesta SMA del BCE:** horizonte más largo y con rango, pero es opinión de analistas, solo se
  publica en PDF y hoy va en sentido contrario al mercado. Descartada como base; posible escenario
  alternativo en el plan.
- **Curva a plazo de deuda soberana AAA (`YC`):** diaria y hasta 30 años, pero no es Euríbor; pasar
  de una a otro exigiría un modelo de diferencial propio. Descartada.
- **Sumar el diferencial observado de un año menos tres meses a la trayectoria a tres meses:** más
  simple, pero ese diferencial ya contiene las subidas esperadas y las contaría dos veces cuando la
  trayectoria sube. Descartada.
- **Usar la trayectoria a tres meses sin convertir:** la cuota saldría por debajo de la real
  mientras el Euríbor a un año esté por encima del de tres meses. Descartada.

## Consecuencias
- Nueva fuente de datos registrada en `docs/DATA_SOURCES.md` (BCE `MPD` y BOE).
- La trayectoria envejece entre rondas (el corte puede tener hasta tres meses); el escenario de
  estrés cubre esa incertidumbre y la del tramo constante tras el horizonte.
- Pendiente de la consulta legal de F0.6: condiciones de reutilización del ECB Data Portal y del
  BOE, y si citar el Euríbor publicado en el BOE evita la licencia de EMMI para uso comercial.
