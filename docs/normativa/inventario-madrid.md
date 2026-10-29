# Inventario de reglas para un plan de Madrid (F2.2)

**Fecha:** 2026-10-29 · **Estado:** tanda 1 (1.1, 2.1, 2.2, 2.7), tanda 2 (2.3–2.6) y tanda 4 (1.2–1.6,
3.1, 3.3) cargadas sin verificar; ver `docs/normativa/verificacion-tanda-1.md`, `-2.md` y `-4.md`.

Qué reglas legales necesita el motor para calcular un plan de inversión en Madrid
(`ES-13`, municipio de Madrid `ES-13-28079`). **Aquí no hay valores**: cada regla se carga en
F2.3 desde su fuente oficial, y solo pasa a `verified: true` después de que Rodrigo la lea.

Las fuentes de la columna «Fuente candidata» son la referencia por la que empezar a buscar, no
una cita comprobada: en F2.3 hay que confirmar la norma, el artículo y la versión vigente en el
BOE o el BOCM, y anotar la URL exacta en `source_url`.

## 1. Compra

| # | Regla | `kind` | Territorio | Alimenta | Fuente candidata | Esquema |
| --- | --- | --- | --- | --- | --- | --- |
| 1.1 | ITP de vivienda usada | `impuesto_compra_segunda_mano` | ES-13 | gastos de compra → capacidad de compra, dinero aportado | Texto refundido de tributos cedidos de la Comunidad de Madrid; Texto refundido de la Ley del ITP y AJD | ✔ |
| 1.2 | IVA de vivienda nueva | `iva_vivienda_nueva` | ES | gastos de compra | Ley 37/1992 del IVA | ✔ |
| 1.3 | AJD de la compra de vivienda nueva | `ajd_compra_vivienda` | ES-13 | gastos de compra | DL 1/2010 de la Comunidad de Madrid, arts. 32 y 37 | ✔ |
| 1.4 | Quién paga los gastos de la hipoteca (notaría, registro, AJD de la escritura de préstamo, gestoría) | sin regla de cálculo | ES | gastos de compra: qué parte paga el comprador | Ley 5/2019, art. 14.1.e; TR de la Ley del ITP y AJD, art. 29 | ✔ resuelto: el comprador solo paga la tasación y sus copias (precios de mercado) |
| 1.5 | Arancel notarial de la compraventa y quién lo paga | `arancel_notarial`, `pagador_escritura_compraventa` | ES | gastos de compra y de venta | RD 1426/1989, anexo I, número 2; Código Civil, art. 1455 | ✔ |
| 1.6 | Arancel registral de la compraventa (con el IVA de los aranceles, `iva_tipo_general`) | `arancel_registral` | ES | gastos de compra | RD 1427/1989, anexo I, número 2 | ✔ |

Para 1.1 y 1.3 hay que comprobar si existen tipos reducidos o bonificaciones según el
comprador o el inmueble, y si alguno aplica a un inversor. Para 1.5 y 1.6, la escala depende del
valor y del número de folios: decidir al leerla si se calcula o se toma como estimación con rango.

## 2. Tenencia y alquiler (IRPF y tributos locales)

| # | Regla | `kind` | Territorio | Alimenta | Fuente candidata | Esquema |
| --- | --- | --- | --- | --- | --- | --- |
| 2.1 | Reducción del rendimiento neto del alquiler de vivienda, por casos | `reduccion_irpf_alquiler` | ES | `TaxParams.rental_income_reduction` | Ley 35/2006 del IRPF, art. 23.2: redacción de la Ley 12/2023 y del RDL 29/2026 (pendiente de convalidación) | ✔ |
| 2.2 | Amortización fiscal del inmueble alquilado y su base | `amortizacion_inmueble_alquiler` | ES | `TaxParams.depreciation_rate`; base de la amortización | Ley 35/2006 del IRPF, art. 23.1.b; Reglamento del IRPF, art. 14.2.a | ✔ (tasa); la base, por definir |
| 2.3 | Límite de la deducción de intereses y gastos de reparación y conservación | `limite_intereses_reparacion` | ES | cálculo del rendimiento neto en `engines/cashflow.py` (hoy deduce los intereses sin límite) | Ley 35/2006 del IRPF (art. 23.1.a.1.º) | ✔ |
| 2.4 | Escala estatal de la base general | `escala_irpf_general_estatal` | ES | impuesto incremental del alquiler (D-G2-1) | Ley 35/2006 del IRPF | ✔ |
| 2.5 | Escala autonómica de Madrid de la base general | `escala_irpf_general_autonomica` | ES-13 | impuesto incremental del alquiler (D-G2-1) | Texto refundido de tributos cedidos de la Comunidad de Madrid | ✔ |
| 2.6 | Mínimo personal y familiar, estatal y de Madrid | `minimo_contribuyente`, `minimo_descendientes` | ES, ES-13 | impuesto incremental del alquiler | Ley 35/2006 del IRPF, arts. 56–58; DL 1/2010 de Madrid, arts. 2 y 2 bis | ✔ (contribuyente y descendientes; ascendientes y discapacidad, pendientes) |
| 2.7 | Tipo del IBI del municipio de Madrid | `tipo_ibi` | ES-13-28079 | `RentalAssumptions.ibi_annual` (con el valor catastral) | Ordenanza fiscal del IBI del Ayuntamiento de Madrid | ✔ |
| 2.8 | Deducción autonómica por gastos del arrendamiento de viviendas (10 %, con límite anual) | por definir | ES-13 | cuota autonómica del arrendador | DL 1/2010 de Madrid, art. 8 bis | pendiente (fuera del ADR-0007 por ahora) |

Decidido calcular la **cuota incremental** del IRPF (ADR-0007): las filas 2.3 a 2.6 son necesarias.

## 3. Venta (TIR, F1.9)

| # | Regla | `kind` | Territorio | Alimenta | Fuente candidata | Esquema |
| --- | --- | --- | --- | --- | --- | --- |
| 3.1 | Escala de la base del ahorro (ganancia patrimonial) | `escala_irpf_ahorro_estatal`, `escala_irpf_ahorro_autonomica` | ES (las dos, art. 76) | cuota incremental de la ganancia en `investment_irr` | Ley 35/2006 del IRPF, arts. 66 y 76 | ✔ |
| 3.2 | Cálculo de la ganancia: valor de adquisición, mejoras, amortizaciones | sin regla de cálculo | ES | fórmula de la ganancia en `engines/irr.py` | Ley 35/2006 del IRPF, art. 35 (leído: la fórmula del motor coincide) | pendiente: amortización mínima (art. 40 del Reglamento) y reforma como mejora |
| 3.3 | Impuesto sobre el incremento de valor de los terrenos (plusvalía municipal) | `coeficientes_plusvalia`, `tipo_plusvalia` | ES, ES-13-28079 | gastos de venta | TRLRHL, arts. 104.5 y 107; ordenanza fiscal de Madrid, arts. 10 y 17 | ✔ |

## 4. Fuera de F2.2

- **Regulación del alquiler (F2.4): cargada sin verificar** en `data/rules/alquiler.yaml`
  (ver `verificacion-tanda-3.md`): zona tensionada (ninguna en la Comunidad de Madrid), y régimen y
  requisitos de los alquileres de vivienda habitual, temporada, habitaciones y turístico, con la LAU
  anterior como base y el RDL 29/2026 como escenario.
- **RDL 28/2026 (prórroga del alquiler de vivienda habitual), cargado sin verificar** como pendiente
  desde el 15/11/2026, con la base de la Ley 12/2023 (`prorroga_alquiler_habitual`); ver
  `verificacion-tanda-5.md`. Lo detectó la vigilancia del BOE (F2.6).
- **RDL 29/2026, revisado:** art. 10 (coeficientes máximos de la plusvalía) cargado como pendiente;
  arts. 7 y 8 (IVA de alquileres amueblados de hasta 30 noches y obras de renovación; recargos del IBI
  a viviendas vacías o turísticas) anotados en `verificacion-tanda-4.md`, sin efecto en el plan de un
  alquiler de larga duración. Art. 1 (compras por debajo del 70 % del valor), anotado en la tanda 3.
- **No son reglas legales:** tasación, gestoría, comisiones de agencia, seguros y comunidad.
  Son precios de mercado: van como parámetros o supuestos con su fuente, no en `data/rules/`.

## Siguiente paso (F2.3)

1. Elegir el orden de carga. Propuesta: 1.1, 2.1, 2.2 y 2.7 primero (bastan para un plan de
   segunda mano con el tipo marginal); después 2.3; después 2.4–2.6 y 3.x.
2. Para cada regla: leer la fuente, definir el esquema en `regulation/kinds.py` si es «por
   definir», cargarla con `verified: false` y pasarla a `verified: true` con `verified_by` y
   `verified_on` tras la lectura de Rodrigo.
3. `make rules-check` en verde en cada paso.
