# ADR-0050: Series año a año y desglose del primer año, con fórmula y fuentes

**Estado:** Aceptada · **Fecha:** 2026-11-03 · **Decide:** Rodrigo («sigue con U4», docs/PROPUESTA_UX.md)

## Contexto
Las gráficas del plan (ADR-0048) solo pueden dibujar cifras que calcule la API. Tres que propone
docs/PROPUESTA_UX.md no tenían datos:
- la cascada del cash flow: `compute_cashflow` calcula renta, vacío, gestión, comunidad, IBI, seguros,
  mantenimiento, cuotas e impuesto, pero solo devuelve los totales;
- la evolución de la hipoteca: `amortization_schedule` da el cuadro mes a mes, pero no sale de la API;
- el cash flow y el precio de cada año: `yearly_cashflows` y `projected_sale_price` ya se usan para la
  TIR, pero solo sale el resultado final.

Calcularlos en la web rompería la regla de oro 1.

## Decisión
1. **`Series`** en `core/figures.py`, hermano de `Figure`: `key`, `unit` del valor, `x_unit` ("año"),
   `points` (pares año–valor en `Decimal`), `formula` y `sources`, con `provisional` igual que una cifra.
   Una serie no es una suma de cifras: cada punto sale del mismo motor que la cifra equivalente.
2. **Desglose del primer año** en `CashflowResult.breakdown`: una `Figure` por componente en €/año, los
   gastos con signo negativo (`cashflow.breakdown.rent`, `.vacancy`, `.management`, `.community`, `.ibi`,
   `.insurance`, `.maintenance`, `.interest`, `.principal`, `.tax`), y el total
   `cashflow.annual_after_tax` = cash flow operativo − impuesto, el mismo numerador que la cifra mensual.
   El capital amortizado va aparte de los intereses: sale del bolsillo pero se queda en el inmueble.
   Cada componente se redondea a céntimos; la suma puede diferir del total en algún céntimo.
3. **Series del plan**, calculadas en `planning/simulate.py` (el único camino de cálculo, D4):
   - `mortgage.balance_by_year`, `mortgage.interest_by_year` y `mortgage.principal_by_year` del cuadro
     de amortización;
   - `cashflow.after_tax_by_year` de `yearly_cashflows`, con el arrastre de intereses de cada año;
   - `valuation.price_by_year` (escenario base) y `valuation.price_by_year_<escenario>` para los otros
     escenarios de revalorización, con `projected_sale_price`.
4. **API:** `series` y `breakdown` en la respuesta del simulador y del plan, fuera del diccionario de
   cifras, para que las secciones y las comparaciones con reglas pendientes no cambien.

## Alternativas descartadas
- **Series como listas de `Figure`:** una clave por año llenaría el plan y el agente de cifras sueltas.
- **Mandar el cuadro mensual entero:** 360 filas por plan para dibujar 30 puntos.

## Consecuencias
- La web dibuja la cascada del primer año y las líneas de hipoteca, cash flow y precio sin calcular nada.
- Una serie nueva se añade en `planning/simulate.py` con su test; la web la dibuja si la recibe.
