# CLAUDE.md — HouseFinder

Contexto e instrucciones para trabajar en este repositorio con Claude Code.
Léelo entero al empezar cada sesión, y después `docs/ROADMAP.md` para saber en qué fase estamos.

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
    regulation/rules.py   motor de normativa versionada (RuleBook)
    regulation/kinds.py   catálogo de tipos de regla y esquema de sus parámetros
    regulation/resolvers.py  de reglas a entradas de los motores (TaxParams, ITP, IBI, IRPF)
                          y regulación del alquiler (zona tensionada, régimen por tipo)
    regulation/transactions.py  gastos y tributos de compra y venta (ITP, IVA, AJD, notaría,
                          registro, escala del ahorro, plusvalía)
    params/               parámetros con fecha (ParamBook): criterios bancarios, Euríbor (ADR-0006)
    planning/simulate.py  simulación de punta a punta: el único camino de cálculo del plan (D4)
    planning/scenarios.py escenarios normativos: comparación con / sin reglas pendientes
    db/migrate.py         ejecutor de migraciones (ADR-0008); solo db/ importa psycopg
    db/sections.py        fuentes (`sources`) y secciones censales; sección de un punto
    db/indicators.py      indicadores por sección y cartografía (renta, demografía)
    db/geocache.py        caché de geocodificación (sin datos del usuario)
    db/connection.py      conexión para la API y los trabajos (DATABASE_URL)
    db/jobs.py            SQL de la cola de trabajos (ADR-0010)
    jobs/                 worker, reintentos, programaciones, alertas y tipos de trabajo
    db/review_tasks.py    tareas de revisión de la vigilancia normativa
    db/profiles.py        organizaciones y perfiles (solo bytes cifrados)
    crypto/               cifrado de sobre AES-256-GCM y claves maestras (ADR-0011)
    profiles/             perfil del inversor: modelo que se redacta y almacén cifrado
    db/offers.py          ofertas, versiones de lo recibido e inmuebles (deduplicación)
    offers/               canales de oferta (interfaz Channel), ingesta, ubicación y deduplicación
    offers/channels/      canales: BOE sección V (anuncios) y sección IV (avisos de subastas judiciales, ADR-0017)
    offers/corrections.py correcciones del BOE: cita, página y anuncio que corrigen (F4.4)
    offers/link.py        descarga única del enlace pegado: robots.txt, bloqueos y veto a la red interna (ADR-0015)
    offers/pasted.py      enlace o texto pegado: oferta privada, extracción en la cola y confirmación
    agent/llm.py          cliente del LLM (modelo abierto en servidor propio, API compatible con OpenAI) y cliente falso (ADR-0014); solo agent/ llama al LLM
    agent/extraction.py   extracción con cita literal comprobada: ninguna cifra extraída es inventada
    watch/                vigilancia del BOE y del BOCM: filtros, lectura y tareas (F2.6)
    geo/cartociudad.py    geocodificador de CartoCiudad (ADR-0009); solo geo/ e ingestion/ usan la red
    geo/catastro.py       centroide de una parcela por referencia catastral (Catastro, ADR-0016)
    territory/            sección, renta, población y tendencias de una dirección como Figure
    ingestion/boe.py      sumario diario del BOE (esquema comprobado con sumarios reales)
    ingestion/bocm.py     sumarios del BOCM (RSS y XML de cada boletín)
    ingestion/ine_sections.py  cartografía de secciones del INE (API OGC Features, CC BY 4.0)
    ingestion/ine_adrh.py Atlas de renta del INE por sección; el año t va sobre el seccionado t+1
    api/main.py           aplicación FastAPI; un router por dominio (simulate, territory, offers)
  data/rules/             reglas de normativa en YAML
  data/params/            parámetros con fecha en YAML (ADR-0005)
  data/watch/             filtros de la vigilancia del BOE y del BOCM
  data/offers/            sedes de partidos judiciales para los avisos de subastas (sin verificar)
  tests/                  pytest; un test por regla de negocio
  tests/fixtures/planes/  prueba de oro: planes de F0 anonimizados (los reales, en private/)
db/migrations/            SQL de PostgreSQL + PostGIS (NNNN_nombre.sql; no se editan una vez aplicadas)
infra/docker-compose.yml  base de datos local
docs/                     ROADMAP, ARCHITECTURE, DATA_SOURCES, ADRs y plantillas
```

## Comandos

```bash
make setup     # entorno Python (.venv) y dependencias web
make db        # PostgreSQL + PostGIS en Docker (127.0.0.1:5442) y migraciones pendientes
make migrate   # solo las migraciones pendientes (DATABASE_URL)
make sections  # carga las secciones censales del INE (YEAR=2025 PROVINCE=28)
make adrh      # carga el Atlas de renta del INE 2015–2024 (PROVINCE=28)
make worker    # worker de la cola; encolar con `python -m housefinder.jobs enqueue …`
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
