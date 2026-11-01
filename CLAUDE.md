# CLAUDE.md — HouseFinder

Contexto e instrucciones para trabajar en este repositorio con Claude Code.
Léelo entero al empezar cada sesión, y después `docs/ROADMAP.md` para saber en qué fase estamos.
El contexto completo (producto, arquitectura, entorno, calendario, costes) está en `docs/PLAN_DE_DESARROLLO.md`.

## Qué es HouseFinder

Plataforma con IA que encuentra oportunidades de inversión inmobiliaria en España y genera, para cada
usuario, un plan de inversión personal: capacidad de compra, hipoteca, cash flow tras impuestos, tipo
de alquiler, gestión activa o pasiva, pruebas de estrés, escenarios normativos y hoja de ruta de compra.

- **Diferenciador:** la rentabilidad que se calcula es la del usuario (con su hipoteca, su IRPF y su
  tiempo), no la del inmueble. Somos independientes: no vendemos activos.
- **Clientes:** particulares (pase de compra + suscripción de propietario) y profesionales
  (intermediarios hipotecarios, asesores, agencias) con plan mensual.
- **MVP:** Madrid y área metropolitana. Oferta de tres canales: enlaces pegados por el usuario,
  BOE (subastas y sección V) y los grandes servicers. Lanzamiento de beta privada: enero de 2027.

## Reglas de oro (no negociables)

1. **La IA explica; los motores calculan.** Ninguna cifra que vea el usuario la genera un LLM.
   Toda cifra es un `Figure` (`services/api/src/housefinder/core/figures.py`) con fórmula y fuentes.
   El agente recibe cifras ya calculadas y solo las explica o las ordena.
2. **La normativa son datos, no código.** Ningún porcentaje legal (impuestos, reducciones,
   topes de alquiler) se escribe en el código. Va en `services/api/data/rules/*.yaml` con vigencia,
   territorio, estado y fuente oficial (ver `data/rules/README.md`). Una regla solo se marca
   `verified: true` después de que Rodrigo haya leído la fuente.
3. **Fuentes propias y públicas.** No añadir dependencias de proveedores comerciales de datos.
   **No hacer scraping de portales inmobiliarios** (Idealista, Fotocasa, etc.) sin un ADR aprobado.
   Los anuncios de portales entran solo como enlace pegado por el usuario.
4. **Nada de cifras inventadas.** Si falta un dato o un parámetro (criterios bancarios, tipos
   impositivos), se deja como parámetro configurable marcado `PROVISIONAL` y se avisa, nunca se
   rellena "de memoria".
5. **Datos personales con cuidado (RGPD).** Ingresos, deudas y documentos del usuario: cifrados,
   nunca en logs, nunca en fixtures del repositorio (usar `tests/fixtures/private/`, ignorada por git).
   Se guardan con `profiles/store.py` (cifrado de sobre, ADR-0011); el modelo `UserProfile` nunca
   se muestra en texto y sus errores no repiten los valores.
6. **Dinero con `Decimal`**, nunca `float`. Redondeo con `money()`.

## Mapa del repositorio

```
apps/web/                 Next.js (App Router, TypeScript): interfaz
services/api/             Python 3.11+, FastAPI: motores, normativa, ingesta, agente
  src/housefinder/
    core/figures.py       Figure, SourceRef, money() y ratio(): trazabilidad de cifras
    core/dated.py         lector común de registros con fecha y territorio
    engines/mortgage.py   cuota, amortización, capacidad, estrés, comparación fija/variable/mixta
    engines/rates.py      trayectoria del índice (RatePath) y condiciones de tipo
    engines/cashflow.py   cash flow, límite de intereses y su arrastre, rentabilidad personal
    engines/irpf.py       escalas, mínimos y cuota incremental del IRPF (ADR-0007)
    engines/term.py       plazo recomendado con cash flow en estrés
    engines/irr.py        TIR de la inversión con revalorización y venta
    engines/taxes.py      formas de cálculo de aranceles, AJD por bandas y plusvalía municipal
    engines/lease.py      indemnización por no prorrogar el alquiler
    engines/valuation.py  contracción de la renta, renta por superficie, precio desde la renta e índice
    engines/appreciation.py  escenarios de revalorización: ventanas del IPV, percentiles y convergencia
    regulation/rules.py   motor de normativa versionada (RuleBook)
    regulation/kinds.py   catálogo de tipos de regla y esquema de sus parámetros
    regulation/resolvers.py  de reglas a entradas de los motores (TaxParams, ITP, IBI, IRPF)
                          y regulación del alquiler (zona tensionada, régimen por tipo)
    regulation/transactions.py  gastos y tributos de compra y venta (ITP, IVA, AJD, notaría,
                          registro, escala del ahorro, plusvalía)
    params/               parámetros con fecha (ParamBook): criterios bancarios, Euríbor (ADR-0006),
                          contracción de la renta (ADR-0018)
    planning/simulate.py  simulación de punta a punta: el único camino de cálculo del plan (D4)
    planning/scenarios.py escenarios normativos: comparación con / sin reglas pendientes
    planning/ranking.py   búsqueda inversa: restricciones por riesgo y orden por objetivo (ADR-0023)
    planning/arguments.py argumentos para no comprar: reglas fijas sobre las cifras (ADR-0025)
    planning/rental_advice.py  tipo de alquiler y gestión recomendados (ADR-0024)
    search/               búsqueda inversa: el plan del usuario en cada oferta (ADR-0023) y su
                          tipo de alquiler y gestión (rental.py, ADR-0024)
    plans/                plan completo de una oferta y hoja de ruta de compra (ADR-0025)
    reports/              PDF del plan con anexo de fuentes; solo aquí weasyprint (ADR-0026)
    plans/coherence.py    reglas de coherencia del plan; un fallo se avisa en el plan (ADR-0027)
    evaluations/          extracción contra el juego etiquetado, banco del asesor y línea base (ADR-0027)
    db/migrate.py         ejecutor de migraciones (ADR-0008); solo db/ importa psycopg
    db/sections.py        fuentes (`sources`) y secciones censales; sección de un punto
    db/indicators.py      indicadores por sección y cartografía (renta, demografía)
    db/geocache.py        caché de geocodificación (sin datos del usuario)
    db/connection.py      conexión para la API y los trabajos (DATABASE_URL)
    db/jobs.py            SQL de la cola de trabajos (ADR-0010)
    jobs/                 worker, reintentos, programaciones, alertas y tipos de trabajo
    db/review_tasks.py    tareas de revisión de la vigilancia normativa
    db/profiles.py        organizaciones y perfiles (solo bytes cifrados)
    db/accounts.py        cuentas, enlaces de contraseña y sesiones (solo hashes de tokens)
    db/clients.py         clientes de un profesional (nombre cifrado, ADR-0029)
    db/branding.py        marca del profesional (ADR-0030)
    branding/             marca del profesional: color con contraste y logotipo reescrito con Pillow (ADR-0030)
    accounts/             cuentas con argon2id, sesiones y altas por el administrador (ADR-0028)
    db/interviews.py      entrevistas de perfil (solo bytes cifrados)
    crypto/               cifrado de sobre AES-256-GCM y claves maestras (ADR-0011)
    profiles/             perfil del inversor: modelo que se redacta, almacén cifrado, entrevista
                          con preguntas fijas (interview.py, ADR-0020) y clientes (clients.py, ADR-0029)
    db/offers.py          ofertas, versiones de lo recibido e inmuebles (deduplicación)
    offers/               canales de oferta (interfaz Channel), ingesta, ubicación y deduplicación
    offers/channels/      canales: BOE sección V (anuncios) y sección IV (avisos de subastas judiciales, ADR-0017)
    offers/corrections.py correcciones del BOE: cita, página y anuncio que corrigen (F4.4)
    offers/link.py        descarga única del enlace pegado: robots.txt, bloqueos y veto a la red interna (ADR-0015)
    offers/pasted.py      enlace o texto pegado: oferta privada, extracción en la cola y confirmación
    agent/llm.py          cliente del LLM (modelo abierto en servidor propio, API compatible con OpenAI) y cliente falso (ADR-0014); solo agent/ llama al LLM
    agent/extraction.py   extracción con cita literal comprobada: ninguna cifra extraída es inventada
    agent/documents.py    campos de nómina, declaración y extracto con cita y etiqueta comprobadas (ADR-0021)
    agent/profiling.py    datos del perfil en la respuesta libre, con cita comprobada (ADR-0020)
    agent/plan_arguments.py  argumentos del asesor para no comprar, sin números (ADR-0025)
    agent/sense.py        contradicciones de sentido junto a los marcadores del asesor (ADR-0027)
    agent/references.py   el agente escribe marcadores {{fig:clave}}, no cifras: comprobación y segmentos (ADR-0012)
    agent/loop.py         bucle del agente con herramientas; el texto final se comprueba con references (ADR-0019)
    advisor/              herramientas del agente sobre los motores (solo lectura, argumentos sin números),
                          glosario de cifras para el modelo, banco de preguntas (evaluation.py) y CLI
    documents/            texto de un documento del usuario: PDF, escaneo o foto con OCR local; solo aquí
                          pypdf, pypdfium2 y pytesseract (ADR-0021)
    watch/                vigilancia del BOE y del BOCM: filtros, lectura y tareas (F2.6)
    geo/cartociudad.py    geocodificador de CartoCiudad (ADR-0009); solo geo/ e ingestion/ usan la red
    geo/catastro.py       centroide de una parcela por referencia catastral (Catastro, ADR-0016)
                          y referencia de una finca rústica por polígono y parcela (ADR-0031)
    geo/foral.py          parcelas de los catastros forales: País Vasco y Navarra (ADR-0032)
    territory/            sección, renta, población y tendencias de una dirección como Figure
    valuation/            renta y precio estimados de un inmueble como Figure con rango (ADR-0018)
                          y escenarios de revalorización (scenarios.py, F5.5); valoración de
                          una oferta confirmada frente a lo que pide (offer.py, F5.4); supuestos del
                          plan desde fuentes públicas (assumptions.py, ADR-0022)
    ingestion/boe.py      sumario diario del BOE (esquema comprobado con sumarios reales)
    ingestion/bocm.py     sumarios del BOCM (RSS y XML de cada boletín)
    ingestion/ine_sections.py  cartografía de secciones del INE (API OGC Features, CC BY 4.0)
    ingestion/ine_adrh.py Atlas de renta del INE por sección; el año t va sobre el seccionado t+1
    ingestion/serpavi.py  referencias de alquiler del SERPAVI por sección, distrito y municipio (ADR-0018)
    ingestion/xlsx.py     lector de .xlsx en streaming con la biblioteca estándar
    ingestion/valor_tasado.py  valor tasado de la vivienda libre por municipio (Ministerio, vía Comunidad de Madrid)
    ingestion/ine_ipv.py  índice de precios de vivienda del INE por comunidad, trimestral
    ingestion/ine_ipc_alquiler.py  componente de alquiler del IPC del INE por comunidad, mensual
    ingestion/bde_tipos.py, ine_hipotecas.py, catastro_urbana.py, ine_epf.py, hacienda_ibi.py
                          fuentes de los supuestos del plan (ADR-0022); hacienda_ibi genera reglas
    db/references.py      referencias de alquiler y de precio (market_references)
    api/main.py           aplicación FastAPI; un router por dominio (simulate, territory, offers, boe, valuation)
  data/rules/             reglas de normativa en YAML
  data/params/            parámetros con fecha en YAML (ADR-0005)
  data/watch/             filtros de la vigilancia del BOE y del BOCM
  data/jobs/              programaciones diarias de la cola (ADR-0010)
  data/profiles/          comunidades autónomas por código INE, para la residencia del perfil
  data/territory/         provincia → comunidad autónoma (códigos INE)
  data/plan/              hoja de ruta de compra: pasos con su fuente, sin verificar (ADR-0025)
  data/evaluation/        juego etiquetado de anuncios (sintéticos y BOE) y línea base de las evaluaciones
  data/offers/            sedes de partidos judiciales para los avisos de subastas (sin verificar)
                          y relación de provincias del INE (provincias.yaml, ADR-0031)
  tests/                  pytest; un test por regla de negocio
  tests/fixtures/planes/  prueba de oro: planes de F0 anonimizados (los reales, en private/)
db/migrations/            SQL de PostgreSQL + PostGIS (NNNN_nombre.sql; no se editan una vez aplicadas)
infra/docker-compose.yml  base de datos local
docs/                     ROADMAP, ARCHITECTURE, DATA_SOURCES, ADRs y plantillas
```

## Comandos

```bash
make setup     # entorno Python (.venv) y dependencias web; OCR: brew install tesseract tesseract-lang;
               # PDF del plan: brew install pango (ADR-0026)
make db        # PostgreSQL + PostGIS en Docker (127.0.0.1:5442) y migraciones pendientes
make migrate   # solo las migraciones pendientes (DATABASE_URL)
make sections  # carga las secciones censales del INE (YEAR=2025 PROVINCE=28)
make adrh      # carga el Atlas de renta del INE 2015–2024 (PROVINCE=28)
make serpavi   # carga las referencias de alquiler del SERPAVI 2011–2024 (PROVINCE=28)
make valor-tasado FICHERO=…  # valor tasado por municipio: CSV descargado a mano (su portal prohíbe el acceso automático)
make ipv       # índice de precios de vivienda del INE por comunidad (REGION=13)
make ipc-alquiler  # componente de alquiler del IPC del INE por comunidad, mensual (REGION=13)
make supuestos # supuestos del plan: tipos del BdE y del INE, Catastro, EPF y reglas del IBI (ADR-0022)
make backtest  # backtesting del modelo de renta y precio (F5.6)
make evaluar   # evaluaciones con el modelo de .env frente a la línea base (BASE=1 la guarda)
                 # cuentas de la beta: `python -m housefinder.accounts alta correo --organizacion …`
make worker    # worker de la cola; encolar con `python -m housefinder.jobs enqueue …`
make schedules # aplica data/jobs/programaciones.yaml (trabajos diarios; el Makefile lee .env)
make worker-install  # worker siempre en marcha en este Mac (launchd); logs: make worker-logs
                 # clave maestra local para cifrar perfiles: `python -m housefinder.crypto nueva-clave`
                 # tareas de revisión: `python -m housefinder.watch tareas`
make test      # pytest de la API (los tests `db` se saltan si la base no está arrancada)
make lint      # ruff
make rules-check  # valida data/rules (catálogo de tipos, vigencias, revisor)
make api       # API en http://localhost:8000 (docs en /docs)
make web       # web en http://localhost:3000 (llama a la API por /api)
make openapi   # regenera los tipos de la web desde el OpenAPI de la API
```

## Cómo trabajar

- **Por fases.** Antes de empezar, abre `docs/ROADMAP.md`, localiza la fase activa y trabaja solo en
  sus tareas. Al terminar una tarea, márcala `[x]` en el roadmap en el mismo commit.
- **Tests primero en los motores.** Cada cálculo nuevo llega con un test con un valor conocido
  (calculado a mano o con una calculadora de referencia, anotado en el test).
- **Cambios pequeños.** Un commit por tarea, mensaje en español y en imperativo
  (`Añade motor de estrés de tipos`).
- **Decisiones con ADR.** Cualquier decisión de arquitectura, nueva fuente de datos o dependencia
  importante va en `docs/adr/NNNN-titulo.md` antes de implementarse.
- **Antes de dar algo por terminado:** `make lint` y `make test` en verde.

## Convenciones

- Código e identificadores en inglés; dominio y textos de usuario en español. Glosario:
  cuota = `monthly_payment`, entrada = `down_payment`, capacidad de compra = `affordability`,
  gastos de compra = `purchase_costs`, rentabilidad bruta = `gross_yield`,
  servicer = `servicer`, sección censal = `census_section`, regla = `Rule`.
- Territorios con códigos INE jerárquicos: `ES`, `ES-13` (comunidad), `ES-13-28079` (municipio).
- Fechas en ISO 8601. Importes en euros con `Decimal`. Porcentajes en tanto por uno (0.03 = 3 %).
- Python: tipado estricto, `dataclass(frozen=True)` para resultados, funciones puras en `engines/`.

## Qué no hacer

- No llamar a un LLM desde `engines/` ni desde `regulation/`.
- No escribir tipos impositivos, topes legales ni criterios bancarios como constantes.
- No hacer scraping de portales ni de webs con términos que lo prohíban sin ADR.
- No guardar secretos ni datos personales reales en el repositorio.
- No ampliar el alcance fuera de la fase activa sin preguntar.
