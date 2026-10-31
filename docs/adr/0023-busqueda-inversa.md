# ADR-0023: Búsqueda inversa con el plan del usuario en cada oferta

- **Estado:** aceptada (decisiones de Rodrigo, 2026-10-31)
- **Fecha:** 2026-10-31
- **Tarea:** F6.5

## Contexto
F6.5 pide puntuar ofertas según el resultado esperado para el perfil y sus restricciones (cash flow
mínimo, riesgo, gestión). PLAN_DISENO fija que la puntuación es determinista y que el agente solo
ordena y explica. Los supuestos que el plan necesita y las ofertas no traen salen de fuentes
públicas (ADR-0022) o del usuario.

## Decisión
- **El plan del usuario en cada oferta:** `search/service.py` toma las ofertas ubicadas (las
  confirmadas del usuario y los lotes del BOE), estima su renta (F5), sus supuestos (ADR-0022) y la
  revalorización del escenario base (F5.5), y llama a `planning.simulate`, el único camino de
  cálculo (D4). Las reglas sin verificar se usan y las cifras salen PROVISIONALES.
- **Restricciones** (`planning/ranking.py`, puro): el precio cabe en la capacidad de compra, llega
  el ahorro y el cash flow mensual tras impuestos llega al mínimo del usuario (cero si no lo dice)
  en el escenario de su riesgo:
  - *bajo:* con la subida de tipos del estrés y la renta baja de la zona (P25);
  - *medio o sin decir:* con la subida de tipos y la renta mediana;
  - *alto:* solo en el escenario base.

  El cash flow en estrés es el del plan menos la diferencia de cuota con la subida de tipos, sin
  recalcular el IRPF (bajaría algo con más intereses): la fórmula lo dice.
- **Orden según el objetivo:** renta o sin decir, por cash flow mensual tras impuestos; patrimonio y
  mixto, por la TIR al horizonte con el escenario base (la TIR ya incluye el cash flow). Primero las
  que pasan; sin métrica, al final.
- **Lo que falta para puntuar lo dice la búsqueda** y no puntúa: la base liquidable (de la
  declaración, F6.3) y los supuestos sin fuente del perfil (vacío, gestoría y tasación, gastos de
  venta, si es gran tenedor y, con gestión delegada, lo que cobra). Una oferta que no se puede
  puntuar (otro tipo de inmueble, sin precio ni superficie, sin regla) sale aparte con su motivo.
  Sin regla de la plusvalía del municipio, el plan va sin ella y lo avisa; sin escenarios de
  revalorización, la TIR sale sin revalorizar y lo avisa.
- **Gran tenedor y cash flow mínimo** van al perfil con los demás supuestos de búsqueda: suponer
  que no es gran tenedor podría dar una reducción del IRPF que no corresponde (`RentalFacts`).
- **El agente nombra ofertas con `{{oferta:id}}`** (los ocho primeros caracteres del UUID), como
  las cifras con `{{fig:clave}}` (ADR-0012): los títulos del BOE llevan números y el agente no los
  copia; la web escribe el título. Un identificador que no dio ninguna herramienta se rechaza.
- **Herramienta `buscar_ofertas`:** devuelve el orden hecho por el código, con las cinco primeras
  ofertas, sus cifras clave con descripción y los motivos de las que no pasan. El modelo no ve los
  títulos.
- **API y web:** `GET /search` y la página `/busqueda`, con los supuestos de búsqueda editables
  (`PUT /profile/current/search`).

## Opciones consideradas
- **Puntuación compuesta con pesos:** mezcla unidades distintas y los pesos serían una opinión sin
  fuente. Descartada: restricciones claras y un solo criterio de orden por objetivo.
- **Que el agente ordene:** contradice ADR-0001; el agente solo explica.
- **Recalcular el IRPF en el estrés:** más exacto, pero duplica el cálculo del plan; la diferencia
  es pequeña y va a favor de la prudencia.

## Consecuencias
- Con los datos de hoy solo se puntúan dos ofertas (casi todos los lotes del BOE son suelo,
  locales o edificios): la búsqueda gana valor con más oferta (servicers, F4.5).
- Cada oferta cuesta una valoración y una o dos simulaciones; con cientos de ofertas hará falta
  precalcular en la cola (ADR-0010).
