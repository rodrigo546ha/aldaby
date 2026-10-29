# Verificación de la tanda 5: duración y prórroga del alquiler de vivienda (RDL 28/2026)

**Cargadas:** 2026-10-29 · **Estado:** con `verified: false` · **Revisa:** Rodrigo
**Fichero:** `services/api/data/rules/alquiler.yaml` · **Origen:** tarea de la vigilancia del BOE
(BOE-A-2026-20822, publicado el 07/10/2026).

## Contexto
- El RDL 27/2026 (29/09/2026) ya cambiaba la prórroga del alquiler; el Congreso lo derogó el 02/10/2026
  ([BOE-A-2026-20527](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-20527)) junto con el 26/2026.
- El RDL 28/2026 lo vuelve a aprobar el 06/10/2026, el mismo día que el RDL 29/2026. **Entra en vigor el
  15/11/2026** (disposición final segunda) y está **pendiente de convalidación**: el Congreso debe
  pronunciarse «en el plazo de los treinta días siguientes a su promulgación»
  ([Constitución, art. 86.2](https://www.boe.es/buscar/act.php?id=BOE-A-1978-31229#a86)). Lo normal es
  que se sepa antes de que entre en vigor.

## 1. Base · `prorroga-alquiler-habitual-ley-12-2023`
- **Fuentes:** [LAU, art. 9.1](https://www.boe.es/buscar/act.php?id=BOE-A-1994-26003#a9) y
  [art. 10](https://www.boe.es/buscar/act.php?id=BOE-A-1994-26003#a10) en la redacción de la Ley 12/2023
  (desde el 26/05/2023).
- **Cargada:** duración mínima de 5 años (7 si el arrendador es persona jurídica); después, prórrogas
  tácitas anuales hasta 3 años más; preaviso de 4 meses el arrendador y 2 el arrendatario; sin
  indemnización.
- **Comprobado:** el RDL 29/2026 (art. 3.Ocho) reescribe el art. 10 con el mismo contenido y solo añade
  «de arrendamiento de vivienda habitual» al apartado 1 (lo he comparado frase a frase).
- [ ] Los plazos de la base.
- [ ] Las prórrogas extraordinarias (1 año por vulnerabilidad, obligatoria para el gran tenedor; hasta
      3 años en zona tensionada) quedan en `notes`, no como parámetros. ¿Basta?

## 2. RDL 28/2026 · `prorroga-alquiler-habitual-rdl-28-2026`
- **Fuente:** [RDL 28/2026, artículo único](https://www.boe.es/buscar/act.php?id=BOE-A-2026-20822#au)
  (nuevo art. 10 de la LAU).
- **Cargada:**
  - Tras los 5 años (7 persona jurídica), prórrogas tácitas **sucesivas de 5 años (7)**, sin límite.
  - Preaviso de **6 meses** el arrendador (2 el arrendatario).
  - Si el arrendador no prorroga, **indemnización**: la mayor de 12 mensualidades o 1 por año de
    residencia, calculadas con el valor superior del rango individualizado de la vivienda en el sistema
    estatal de referencia de precios del alquiler (o la renta vigente si no hay valor).
  - Sin indemnización si: el arrendador persona física necesita la vivienda; el arrendatario no la ha
    habitado más de 6 de los 12 meses anteriores; tiene otra vivienda en el municipio; se firma un
    contrato nuevo; o rechaza una oferta de contrato nuevo de 5 años (7) con renta según el art. 17.6.
- [ ] Los plazos y la indemnización.
- [ ] Los códigos de las excepciones (`exceptions`) frente al apartado 2.
- [ ] **Régimen transitorio** (disposición transitoria única): se aplica a los contratos vigentes desde
      su siguiente vencimiento; los que estén en la prórroga anual del art. 10.1 anterior la terminan con
      esa redacción; las comunicaciones de no prórroga anteriores al 07/10/2026 no dan indemnización. No
      está modelado: hoy el motor no simula la vida del contrato.

## Qué cambia para un inversor
- Salir de un piso alquilado deja de ser «esperar al vencimiento»: después de 5 años, el contrato se
  renueva por 5 más salvo preaviso de 6 meses y, en general, indemnización.
- La indemnización la paga quien sea el arrendador al terminar, también el comprador que se subrogue:
  afecta al precio de venta de un piso alquilado.
- `engines/lease.py` calcula la indemnización con los parámetros de la regla; todavía no entra en el
  plan (la TIR supone la venta al horizonte y no modela la desocupación).
