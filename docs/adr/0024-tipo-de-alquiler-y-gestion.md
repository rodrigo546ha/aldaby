# ADR-0024: Recomendación de tipo de alquiler y de gestión

- **Estado:** aceptada (decisiones de Rodrigo, 2026-10-31)
- **Fecha:** 2026-10-31
- **Tarea:** F6.6

## Contexto
F6.6 pide recomendar el tipo de alquiler (habitual, temporada, habitaciones o turístico) y la
gestión activa o pasiva según la ubicación, con las reglas de F2.4. Solo el alquiler habitual
tiene renta pública (SERPAVI, ADR-0018). Antes de decidir se buscó una fuente pública para los
otros tres tipos y no la hay (`docs/research/f6-6-rentas-otros-tipos.md`): el INE da oferta y
ocupación sin precio, y los precios de Dataestur son de un proveedor privado cuyo aviso legal
prohíbe reutilizarlos.

## Decisión
- **Normativa de cada tipo, como datos.** Para cada tipo: si se puede ejercer en el municipio,
  su régimen y los requisitos que suman el Estado, la comunidad y el ayuntamiento
  (`rental_regime`, F2.4). La regla de régimen dice además si la renta tiene la reducción del
  art. 23.2 de la Ley del IRPF (`irpf_reduction`: sí, no o por confirmar) y, si hace falta, una
  nota fiscal (`tax_note`). El código no decide qué tipo es vivienda a efectos del IRPF.
  «Por confirmar» se calcula sin reducción y se avisa (prudencia, como `RentalFacts`).
- **Cifras: habitual con el SERPAVI; los demás, con la renta del usuario.** El usuario puede
  escribir, en cada oferta, lo que espera sacar con otro tipo: el ingreso medio mensual a lo
  largo del año, con los meses vacíos y descontados la limpieza, los suministros y las comisiones
  de las plataformas. Es un supuesto suyo (`SourceRef("assumption", …, provisional=True)`), se
  guarda por oferta (`offer_rent_expectations`) y no lleva vacío aparte. Sin esa renta, el tipo
  sale con su normativa y sin cifras.
- **El plan de cada tipo pasa por `planning.simulate`** (D4), con `RentalInput.housing_lease`: si
  la renta no tiene la reducción, la reducción vale cero y se cita la regla del régimen.
- **Gestión.** Por cada tipo con cifras se calcula el cash flow con gestión activa y con
  gestión pasiva. La diferencia es `management.delegation_cost`, lo que cuesta delegar al mes,
  después de impuestos. Se recomienda **pasiva** si el tipo exige mucha dedicación (temporada y
  turístico: cambios de inquilino, anuncios, entradas y limpieza) o si la vivienda está fuera
  de la comunidad donde vive el usuario. Si no se da ninguna de las dos cosas, se recomienda lo
  que él haya elegido, o activa si no lo ha dicho. Sin lo que cobra la gestión no hay coste de
  delegar: el cash flow va con gestión activa y se avisa.
- **Tipo.** Entre los tipos que se pueden ejercer y tienen cifras, el de mayor cash flow mensual
  tras impuestos, cada uno con su gestión recomendada. Si empatan, gana el primero de la lista
  (habitual primero). Con riesgo bajo se recomienda el habitual siempre que se pueda: los otros
  dependen de una renta supuesta y de normativa que cambia. Si solo el habitual tiene cifras, la
  recomendación lo dice así: «es el único con renta pública».
- **Escenario normativo** (F2.5): debajo, lo que cambiaría en cada tipo si se convalidan las
  reglas pendientes (régimen, requisitos que entran o salen, reducción).
- **Zona tensionada:** se dice si el municipio está declarado y hasta qué resolución se ha
  revisado. Si lo está, se avisa de que los límites de renta del alquiler habitual no se modelan.
- **Dónde:** en cada oferta puntuada de la búsqueda (`Scored.advice`, `/busqueda`) y en la
  herramienta del agente `recomendar_alquiler`, que recibe el identificador del marcador
  `{{oferta:…}}`. El orden de la búsqueda no cambia: sigue con el alquiler habitual y la gestión
  del usuario (ADR-0023).

## Opciones consideradas
- **Rentas de MABRIAN vía Dataestur:** proveedor comercial (regla 3) y sin permiso para
  reutilizarlas. Además, son precios de anuncio por provincia, sin ocupación.
- **Rentas de portales de media estancia:** privadas y sin fuente oficial. Descartadas.
- **Solo normativa, sin la renta del usuario:** no deja comparar los tipos aunque el usuario sepa
  lo que se paga en su edificio.
- **Que el código decida qué tipos tienen reducción:** contradice la regla 2; va en la regla.

## Consecuencias
- Hasta que Rodrigo verifique las reglas de régimen, las recomendaciones salen provisionales,
  como el resto del plan.
- La reducción del alquiler por habitaciones con la LAU vigente queda por confirmar en la
  consulta legal (F0.6).
- Cada oferta cuesta hasta dos simulaciones más por tipo con cifras.
