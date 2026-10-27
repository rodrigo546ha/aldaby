# ADR-0005: Parámetros con fecha como datos (`ParamBook`)

**Estado:** Aceptada · **Fecha:** 2026-10-27 · **Decide:** Rodrigo

## Contexto
Los criterios bancarios (LTV máximo, ratio de endeudamiento, edad máxima al final del préstamo,
plazo máximo) estaban escritos como valores por defecto de `BankCriteria` en
`engines/mortgage.py`, marcados `PROVISIONAL`. Eso choca con la regla «no escribir criterios
bancarios como constantes» y no deja constancia de su fuente ni de su fecha. La trayectoria del
Euríbor (F1.7) tiene la misma forma: un valor con fuente, vigencia y estado.

No son normativa: en `RuleBook`, `verified: true` significa «Rodrigo leyó la fuente oficial», y un
criterio bancario no tiene fuente oficial; viene de un banco, de un intermediario o de una serie
publicada.

## Decisión
- Los parámetros con fecha viven en `services/api/data/params/*.yaml` y los carga `ParamBook`
  (`housefinder/params/`).
- Cada registro tiene `id`, `kind`, `territory`, `effective_from`, `effective_to`, `params`,
  `source` (de dónde salen los valores, en una frase), `source_url` opcional y `provisional`.
- `provisional: true` mientras no haya fuente documentada. Un parámetro provisional se usa y se
  avisa: la `SourceRef` que lo cita sale `provisional=True` y contagia a las cifras (ADR-0004).
- `RuleBook` y `ParamBook` comparten el lector de registros con fecha (`core/dated.py`): lectura
  de YAML, fechas, territorio jerárquico y elección del registro más específico y más reciente.
- `BankCriteria` deja de tener valores por defecto: siempre llega de un `ParamBook` o, en tests,
  construido a mano con su `SourceRef`.

## Opciones consideradas
- **Guardarlos en `RuleBook`:** menos código, pero mezcla «verificado contra la fuente oficial»
  con «calibrado con un banco». Descartada.
- **Variables de entorno o configuración de la aplicación:** sin fecha, sin territorio y sin
  historial; un plan antiguo no se podría rehacer con los criterios de su día. Descartada.
- **`ParamBook` separado con lector común (elegida).**

## Consecuencias
- Calibrar los criterios (F1.5) = añadir un registro con nueva vigencia, `provisional: false` y su
  fuente; ningún cambio de código.
- La huella de `data/params/` entra en la reproducibilidad del plan (D9 de `docs/PLAN_DISENO.md`).
- Un `id` repetido en `data/params/` es un error de carga.
