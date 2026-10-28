# Inventario de reglas para un plan de Madrid (F2.2)

**Fecha:** 2026-10-28 · **Estado:** tanda 1 cargada sin verificar (1.1, 2.1, 2.2, 2.7); ver
`docs/normativa/verificacion-tanda-1.md`.

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
| 1.3 | AJD de la compra de vivienda nueva | por definir | ES-13 | gastos de compra | DL 1/2010 de la Comunidad de Madrid, art. 32 | pendiente: el tipo depende del valor y se aplica al total |
| 1.4 | Quién paga los gastos de la hipoteca (notaría, registro, AJD de la escritura de préstamo, gestoría) | por definir | ES | gastos de compra: qué parte paga el comprador | Ley 5/2019 de contratos de crédito inmobiliario; TR de la Ley del ITP y AJD | pendiente |
| 1.5 | Arancel notarial de la compraventa | por definir | ES | gastos de compra | Real Decreto 1426/1989 (aranceles de los notarios) | pendiente |
| 1.6 | Arancel registral de la compraventa | por definir | ES | gastos de compra | Real Decreto 1427/1989 (aranceles de los registradores) | pendiente |

Para 1.1 y 1.3 hay que comprobar si existen tipos reducidos o bonificaciones según el
comprador o el inmueble, y si alguno aplica a un inversor. Para 1.5 y 1.6, la escala depende del
valor y del número de folios: decidir al leerla si se calcula o se toma como estimación con rango.

## 2. Tenencia y alquiler (IRPF y tributos locales)

| # | Regla | `kind` | Territorio | Alimenta | Fuente candidata | Esquema |
| --- | --- | --- | --- | --- | --- | --- |
| 2.1 | Reducción del rendimiento neto del alquiler de vivienda, por casos | `reduccion_irpf_alquiler` | ES | `TaxParams.rental_income_reduction` | Ley 35/2006 del IRPF, art. 23.2: redacción de la Ley 12/2023 y del RDL 29/2026 (pendiente de convalidación) | ✔ |
| 2.2 | Amortización fiscal del inmueble alquilado y su base | `amortizacion_inmueble_alquiler` | ES | `TaxParams.depreciation_rate`; base de la amortización | Ley 35/2006 del IRPF, art. 23.1.b; Reglamento del IRPF, art. 14.2.a | ✔ (tasa); la base, por definir |
| 2.3 | Límite de la deducción de intereses y gastos de reparación y conservación | por definir | ES | cálculo del rendimiento neto en `engines/cashflow.py` (hoy deduce los intereses sin límite) | Ley 35/2006 del IRPF (art. 23) | pendiente |
| 2.4 | Escala estatal de la base general | `escala_irpf_general` | ES | impuesto incremental del alquiler (D-G2-1) | Ley 35/2006 del IRPF | ✔ |
| 2.5 | Escala autonómica de Madrid de la base general | `escala_irpf_general` | ES-13 | impuesto incremental del alquiler (D-G2-1) | Texto refundido de tributos cedidos de la Comunidad de Madrid | ✔ |
| 2.6 | Mínimo personal y familiar, estatal y de Madrid | por definir | ES, ES-13 | impuesto incremental del alquiler | Ley 35/2006 del IRPF; tributos cedidos de la Comunidad de Madrid | pendiente |
| 2.7 | Tipo del IBI del municipio de Madrid | `tipo_ibi` | ES-13-28079 | `RentalAssumptions.ibi_annual` (con el valor catastral) | Ordenanza fiscal del IBI del Ayuntamiento de Madrid | ✔ |

Con el tipo marginal actual (`TaxParams.marginal_rate`) bastarían 2.1 y 2.2. Las filas 2.4 a 2.6
solo son necesarias si se decide calcular la **cuota incremental** del IRPF (D-G2-1 en
`docs/PLAN_DISENO.md`), que es lo recomendado.

## 3. Venta (TIR, F1.9)

| # | Regla | `kind` | Territorio | Alimenta | Fuente candidata | Esquema |
| --- | --- | --- | --- | --- | --- | --- |
| 3.1 | Escala de la base del ahorro (ganancia patrimonial) | `escala_irpf_ahorro` | ES, ES-13 | `capital_gains_tax_rate` de `investment_irr` | Ley 35/2006 del IRPF | ✔ |
| 3.2 | Cálculo de la ganancia: valor de adquisición, mejoras, amortizaciones | por definir | ES | fórmula de la ganancia en `engines/irr.py` (hoy, aproximada) | Ley 35/2006 del IRPF (arts. 33–35) | pendiente |
| 3.3 | Impuesto sobre el incremento de valor de los terrenos (plusvalía municipal) | por definir | ES-13-28079 | gastos de venta | Real Decreto Legislativo 2/2004 (Haciendas Locales); ordenanza fiscal de Madrid | pendiente |

## 4. Fuera de F2.2

- **Regulación del alquiler (F2.4):** zonas tensionadas, alquiler de temporada, por habitaciones
  y turístico. Afecta al tipo de alquiler recomendado, no a las cifras del plan; tiene su propio
  inventario en F2.4.
- **No son reglas legales:** tasación, gestoría, comisiones de agencia, seguros y comunidad.
  Son precios de mercado: van como parámetros o supuestos con su fuente, no en `data/rules/`.

## Siguiente paso (F2.3)

1. Elegir el orden de carga. Propuesta: 1.1, 2.1, 2.2 y 2.7 primero (bastan para un plan de
   segunda mano con el tipo marginal); después 2.3; después 2.4–2.6 y 3.x.
2. Para cada regla: leer la fuente, definir el esquema en `regulation/kinds.py` si es «por
   definir», cargarla con `verified: false` y pasarla a `verified: true` con `verified_by` y
   `verified_on` tras la lectura de Rodrigo.
3. `make rules-check` en verde en cada paso.
