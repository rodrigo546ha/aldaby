# ADR-0004: Contrato `Figure` v2 y fuentes tipadas

**Estado:** Aceptada · **Fecha:** 2026-10-27 · **Decide:** Rodrigo

## Contexto
`Figure` (ADR-0001) guarda valor, unidad, fórmula, fuentes y fecha. Con el uso aparecen cuatro huecos:

- Las fuentes son cadenas libres (`"escenario-estres"`, `"tasa-enviada-por-cliente"`): no se
  distingue una regla verificada de un parámetro provisional, un dato del INE o una entrada del usuario.
- Lo `PROVISIONAL` no se propaga: el precio máximo calculado con `BankCriteria` provisional no lo
  dice, y la web no podría avisar (regla de oro 4).
- No hay clave estable para referirse a una cifra, y F6.9 exige comprobar que toda cifra del texto
  del agente está en el plan.
- No hay rango, y los modelos estadísticos de F5 deben dar intervalo (P25–P75).

Además, `gross_yield` y `cash_on_cash` salen multiplicados por 100, contra la convención de
porcentajes en tanto por uno.

## Decisión
- `SourceRef(kind, id, provisional)` con `kind` ∈ `rule`, `param`, `dataset`, `model`,
  `user_input`, `assumption`.
- `Figure(key, value, unit, formula, sources, as_of, low, high)`:
  - `key` estable con forma `dominio.nombre` (`cashflow.monthly_after_tax`).
  - `sources` es una tupla de `SourceRef`. Una cifra derivada cita las fuentes de todas sus entradas.
  - `provisional` es una propiedad derivada: verdadera si alguna fuente lo es.
  - `low` y `high` van juntos o no van; si están, `low ≤ value ≤ high`.
- Los motores devuelven proporciones en tanto por uno con unidad `"ratio"`, redondeadas con
  `ratio()` a cuatro decimales (una centésima de punto porcentual). Formatear como `%` es cosa de la
  web y del PDF.

## Opciones consideradas
- **Mantener `Figure` y añadir convenciones** (prefijos en las cadenas de fuente, sufijos en las
  claves): sin cambio de contrato, pero nada lo comprueba. Descartada.
- **`Figure` v2 ahora (elegida):** solo afecta a dos motores, un endpoint y sus tests. Cuando haya
  planes guardados y una web que los lea, cambiarlo exigiría migrar datos.

## Consecuencias
- Las entradas de los motores (`BankCriteria`, `TaxParams`, `RentalAssumptions`,
  `InvestmentInputs`) llevan sus `SourceRef` para que las salidas puedan citarlas.
- `plans.rule_ids` se obtiene de las fuentes con `kind == "rule"`.
- La web marca `PROVISIONAL` leyendo un solo campo, sin lógica propia.
- La serialización JSON cambia: `sources` pasa a ser una lista de objetos y aparecen `key`,
  `provisional`, `low` y `high`.
