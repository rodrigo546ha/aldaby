# ADR-0007: El IRPF del alquiler es la cuota incremental

**Estado:** Aceptada · **Fecha:** 2026-10-28 · **Decide:** Rodrigo

## Contexto
El motor de cash flow calcula hoy el impuesto del alquiler como
`máx(0, rendimiento neto reducido) × tipo marginal`, con el tipo marginal dado por el usuario.
Eso falla en tres casos:

- Si el rendimiento del alquiler hace saltar de tramo al contribuyente, una parte tributa a otro tipo.
- Si el rendimiento es negativo, se integra en la base liquidable general y baja el IRPF del resto de
  rentas; con `máx(0, …)` ese ahorro desaparece.
- El tipo marginal es un dato que el usuario suele no saber, y el diferenciador del producto es
  «la rentabilidad del usuario, con su IRPF» (D-G2-1 en `docs/PLAN_DISENO.md`).

## Decisión
El impuesto atribuible al alquiler en un año es la **cuota incremental**:

```
impuesto_alquiler = cuota(base_sin_alquiler + rendimiento_neto_reducido) − cuota(base_sin_alquiler)
```

donde `cuota(base)` es la suma de la parte estatal y la autonómica, cada una calculada como manda la
Ley del IRPF (arts. 63.1 y 74.1, leídos en el BOE el 2026-10-28):

```
cuota_parte(base) = escala_parte(base) − escala_parte(mínimo_personal_y_familiar_parte)
```

- **Escalas:** la estatal (`ES`) y la autonómica de la comunidad de **residencia del contribuyente**
  (no la del inmueble). Son tipos de regla distintos (`escala_irpf_general_estatal` y
  `escala_irpf_general_autonomica`), para que una comunidad sin escala cargada dé un error y no
  herede la estatal por error.
- **Mínimo personal y familiar:** suma del mínimo del contribuyente y los mínimos por descendientes
  (arts. 56–58). La parte autonómica usa los importes de la comunidad si los ha aprobado (art. 56.3;
  en Madrid, arts. 2 y 2 bis del DL 1/2010) y, si no, los estatales: aquí sí vale heredar de `ES`.
- **Rendimiento neto:** ingresos − gastos deducibles, con el **límite de intereses y gastos de
  reparación y conservación** en los rendimientos íntegros y el exceso a los cuatro años siguientes
  (art. 23.1.a.1.º), menos amortización; después, la reducción del art. 23.2 si es positivo.
- **Entradas del usuario:** la base liquidable general sin el alquiler (de su última declaración), su
  edad y sus descendientes que dan derecho a mínimo. Son datos personales: cifrados y fuera de logs
  (regla de oro 5).
- **Sin la base del usuario,** el motor puede seguir usando el tipo marginal, pero como supuesto
  provisional y avisándolo.

## Fuera de alcance (por ahora)
Mínimos por ascendientes y discapacidad (arts. 59–60), anualidades por alimentos (arts. 64 y 75),
tributación conjunta, deducciones de la cuota (incluida la de Madrid para arrendadores, art. 8 bis del
DL 1/2010) y la base del ahorro. Se añaden como reglas y casos cuando hagan falta.

## Opciones consideradas
- **Tipo marginal dado por el usuario:** simple, pero falla en los tres casos de arriba. Se queda solo
  como alternativa provisional.
- **Cuota incremental (elegida):** exacta para el alquiler sin simular la declaración entera.
- **Simulador completo de la declaración:** más exacto con deducciones y otras rentas, pero mucho más
  trabajo y más datos personales. Descartada para el MVP.

## Consecuencias
- Nuevas reglas (tanda 2 de F2.3): escalas estatal y de Madrid, mínimos del contribuyente y por
  descendientes estatales y de Madrid, y el límite de intereses y reparación.
- El motor de cash flow cambia: el impuesto deja de ser `máx(0, …) × tipo` y puede ser negativo
  (ahorro fiscal) cuando el rendimiento es negativo.
- El límite de intereses con arrastre a cuatro años hace que el impuesto de un año dependa de los
  anteriores: la TIR (`engines/irr.py`) tiene que llevar ese arrastre de año en año.
