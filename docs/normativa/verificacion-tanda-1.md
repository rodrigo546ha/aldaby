# Verificación de la tanda 1 de reglas (F2.3)

**Cargadas:** 2026-10-28 · **Estado:** todas con `verified: false` · **Revisa:** Rodrigo

Para cada regla: abre la fuente, comprueba lo que se indica y, si todo cuadra, cambia en el YAML
`verified: false` por `verified: true` y añade `verified_by: Rodrigo` y `verified_on: <fecha>`.
Después, `make rules-check` y `make test`.

## 1. ITP de inmuebles en la Comunidad de Madrid · `madrid-itp-inmuebles-2014`

- **Fichero:** `services/api/data/rules/madrid.yaml`
- **Fuente:** [DL 1/2010 de la Comunidad de Madrid, art. 28](https://www.boe.es/buscar/act.php?id=BOCM-m-2010-90068#a28)
- **Texto leído:** «Con carácter general, en la transmisión de inmuebles […] se aplicará el tipo
  del 6 por 100.» Redacción de la Ley 6/2013, en vigor el 01/01/2014.
- **Comprueba:**
  - [ ] Que el tipo es 6 % y la vigencia desde el 01/01/2014.
  - [ ] Que los tipos reducidos de los arts. 29 y 30 no aplican a un inversor particular.

## 2. Reducción del alquiler, régimen de la Ley 12/2023 · `irpf-reduccion-alquiler-ley-12-2023`

- **Fichero:** `services/api/data/rules/irpf.yaml`
- **Fuente:** [Ley 12/2023, disp. final 2.1](https://www.boe.es/buscar/act.php?id=BOE-A-2023-12203#df-2),
  que da la redacción del art. 23.2 de la Ley del IRPF.
- **Casos cargados:** 90 % (nuevo contrato en zona tensionada con rebaja de renta de más del 5 %),
  70 % (primer alquiler en zona tensionada con arrendatario de 18 a 35 años; Administración o
  renta limitada), 60 % (rehabilitación en los dos años anteriores), 50 % («en cualquier otro caso»).
- **Comprueba:**
  - [ ] Los cinco casos y sus porcentajes.
  - [ ] La vigencia: en vigor el 01/01/2024, para contratos celebrados desde el 26/05/2023.
  - [ ] Que la disposición transitoria 38.ª de la Ley del IRPF, en la redacción del RDL 29/2026,
        la mantiene para contratos celebrados hasta el 01/12/2026.

## 3. Reducción del alquiler, régimen del RDL 29/2026 · `irpf-reduccion-alquiler-rdl-29-2026`

- **Fichero:** `services/api/data/rules/irpf.yaml`
- **Fuente:** [RDL 29/2026, art. 6](https://www.boe.es/buscar/act.php?id=BOE-A-2026-20823#a6) y el
  [art. 23.2 consolidado](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764#a23).
- **Cargada como:** `pendiente_convalidacion`, desde el 01/12/2026 (fecha del contrato). El plan base
  sigue usando la Ley 12/2023 y este régimen solo entra en escenarios.
- **Comprueba:**
  - [ ] Los 20 casos y sus porcentajes (los comentarios del YAML dicen a qué letra corresponde cada uno).
  - [ ] Que no hay un caso residual para el gran tenedor: si lo es, solo le quedan c) y d).
  - [ ] **Si ya se ha convalidado** (resolución del Congreso o de la Diputación Permanente en el BOE):
        pasar esta regla a `vigente` y cerrar la de la Ley 12/2023 con `effective_to: 2026-12-01`.
        **Si se deroga:** pasarla a `derogada`.

## 4. Amortización del inmueble · `irpf-amortizacion-inmueble`

- **Fichero:** `services/api/data/rules/irpf.yaml`
- **Fuentes:** [Ley del IRPF, art. 23.1.b](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764#a23) y
  [Reglamento del IRPF, art. 14.2.a](https://www.boe.es/buscar/act.php?id=BOE-A-2007-6820#a14).
- **Texto leído:** «el 3 por ciento sobre el mayor de los siguientes valores: el coste de adquisición
  satisfecho o el valor catastral, sin incluir el valor del suelo».
- **Comprueba:**
  - [ ] El 3 % y la base. Vigencia cargada desde el 01/01/2007 (texto original de la ley).

## 5. IBI urbano del municipio de Madrid, 2026 · `madrid-ibi-urbana-2026`

- **Fichero:** `services/api/data/rules/madrid.yaml`
- **Fuente:** [BOCM núm. 307, de 26/12/2025, pp. 232–235](https://www.bocm.es/boletin/CM_Orden_BOCM/2025/12/26/BOCM-20251226-63.PDF),
  Ordenanza 9/2025 que modifica el art. 8.2 de la ordenanza fiscal del IBI.
- **Texto leído:** «El tipo de gravamen aplicable a los bienes inmuebles de naturaleza urbana queda
  fijado en el 0,414 por ciento». En vigor el 01/01/2026.
- **Comprueba:**
  - [ ] El 0,414 % y la vigencia.
  - [ ] Que no hay tipos diferenciados que afecten a una vivienda (la exposición de motivos dice que
        el tipo general afecta a la totalidad de los inmuebles de uso residencial).

## Decisiones para ti

1. **Real Decreto-ley pendiente de convalidación. Decidido (2026-10-28, Rodrigo):** el plan base usa
   la Ley 12/2023 y el RDL 29/2026 solo entra en escenarios hasta que se convalide, aunque
   jurídicamente ya esté en vigor. Motivo: el RDL 26/2026 se derogó a los pocos días. La misma
   pauta vale para cualquier real decreto-ley futuro (ver `services/api/data/rules/README.md`).
2. **Las reducciones dependen de datos del contrato** que el plan aún no pide: si es primer alquiler o
   nuevo contrato, la renta anterior, el índice de referencia, la zona tensionada, la edad del
   arrendatario y si el arrendador es gran tenedor. Para un inversor que compra para alquilar, el caso
   habitual es «primer alquiler». Esto entra en F2.7 (conectar `TaxParams`) y en el perfil (F6.2).
