# Plan de diseño e implementación por grupos

**Fecha:** 2026-10-27 · **Estado:** borrador para revisar con Rodrigo · **Base:** `CLAUDE.md`,
`docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, ADR-0001 a 0003 y el código de `services/api`.

Este documento ordena el roadmap en **grupos de features** que se construyen uno detrás de otro.
Cada grupo cierra con algo verificable y deja preparado el siguiente. El roadmap sigue mandando en
las tareas; aquí se decide **cómo** se construyen y **en qué orden**.

---

## 0. Punto de partida

| Pieza | Estado real |
| --- | --- |
| `core/figures.py` | `Figure` (valor, unidad, fórmula, fuentes, fecha) y `money()`. |
| `engines/mortgage.py` | F1.1–F1.3 hechas: cuota francesa, cuadro, capacidad, estrés. |
| `engines/cashflow.py` | F1.4 hecha: cash flow, impuesto, rentabilidad bruta, cash-on-cash. |
| `regulation/rules.py` | F2.1 hecha: `RuleBook` con territorio, vigencia, estado y verificación. |
| `ingestion/boe.py` | Esqueleto tolerante; esquema del BOE sin verificar (F4.2). |
| `api/main.py` | `/health` y `POST /simulate/affordability`. |
| `db/migrations/0001_init.sql` | Esquema inicial sin aplicar nunca. |
| `apps/web` | Next.js vacío. |
| Entorno | **No es un repositorio git** y no hay `.venv`: hoy no se puede ejecutar `make test` ni `make lint`, ni hacer «un commit por tarea». |

### Desajustes encontrados en el código (se corrigen en G0)

1. **Porcentajes ×100.** `gross_yield` y `cash_on_cash` devuelven `7.20` con unidad `"%"`
   (`engines/cashflow.py:84` y `:88`), contra la convención «porcentajes en tanto por uno».
2. **Fuentes que no son fuentes.** `"escenario-estres"` (`mortgage.py:179`) y
   `"tasa-enviada-por-cliente"` (`api/main.py:42`) son cadenas libres. Nada distingue una regla
   verificada, un dato del INE, un parámetro `PROVISIONAL` o una entrada del usuario.
3. **Lo `PROVISIONAL` no se propaga.** `BankCriteria` es provisional, pero la `Figure` del precio
   máximo no lo dice; la web no podría avisar (regla de oro 4).
4. **`Figure` sin identificador.** El criterio de F6 («ninguna cifra del texto del agente falta en
   los `Figure`») necesita poder referirse a cada cifra por una clave estable.
5. **`Figure` sin rango.** `ARCHITECTURE.md` exige que los modelos estadísticos den intervalo
   (F5: P25–P75), y `Figure` solo tiene un valor.
6. **Esquema SQL** (se corrige en G4, antes de cargar datos):
   - `census_sections.code` es clave primaria pero hay columna `vintage`: dos cartografías del INE
     con el mismo código chocan.
   - `user_profiles.data JSONB` «cifrado a nivel de app»: un texto cifrado no es JSON.
   - `plans` no guarda versión del motor ni de las reglas: no es reproducible al 100 %.
   - No hay `org_id` para separar datos por profesional (F7.1) ni tabla de trabajos (F4.7).
   - Las migraciones solo se aplican al crear el volumen de Docker (`docker-entrypoint-initdb.d`).

---

## 1. Requisitos

### Funcionales (resumen por capas)

- **Dinero del usuario:** capacidad de compra, hipotecas fija / variable / mixta, estrés, cash flow
  tras impuestos, TIR, plazo recomendado.
- **Normativa:** impuestos de compra, IRPF del alquiler, regulación de alquiler, escenarios
  «con / sin» normas pendientes, vigilancia del BOE y BOCM.
- **Territorio:** sección censal de una dirección con renta, población y tendencias.
- **Oferta:** enlaces pegados, BOE (subastas y sección V), servicers con acuerdo.
- **Valoración:** renta y precio con rango; escenarios de revalorización.
- **Plan:** perfilado, búsqueda inversa, plan explicado, PDF con fuentes.
- **Producto:** cuentas de profesional con varios clientes y marca propia; pase para particulares.

### No funcionales

| Requisito | Objetivo | Consecuencia de diseño |
| --- | --- | --- |
| Exactitud | Plan manual de F0 reproducido con diferencia < 1 € | `Decimal`, tests de valor conocido, redondeo solo con `money()` |
| Trazabilidad | Toda cifra con fórmula, fuentes y estado | `Figure` v2 con fuentes tipadas (G0) |
| Reproducibilidad | Mismas entradas + mismas reglas + mismo motor = mismo plan | El plan guarda versión del motor y huella de reglas y parámetros (G4) |
| Privacidad (RGPD) | Datos financieros cifrados, fuera de logs, separados por cliente | Cifrado de sobre, `org_id`, redacción en logs (G4, G8) |
| Coste y operación | Una persona a tiempo parcial | Mínimo de piezas: un proceso API, un proceso worker, PostgreSQL |
| Escala | Supuesto, sin medir: beta de 3–5 profesionales con decenas de clientes; ingesta diaria del orden de cientos de anuncios | Un servidor basta. No se diseña para escala, se diseña para auditoría |
| Latencia | Simulador interactivo; plan completo en < 10 min de trabajo humano (F6) | Motores en memoria; el LLM es el único paso lento |

### Restricciones

Un desarrollador en tardes y fines de semana; beta a mediados de enero de 2027 (≈ 11 semanas);
stack fijado (Next.js, FastAPI, PostgreSQL + PostGIS, modelo abierto en servidor propio (ADR-0014), AWS en F7); sin proveedores
comerciales de datos (ADR-0002); normativa como datos (ADR-0003).

---

## 2. Diseño de alto nivel

```
                ┌──────────────────────────── apps/web (Next.js) ───────────────────────────┐
                │ Simulador · Perfil · Ofertas · Plan · PDF        (solo formatea Figure)    │
                └───────────────────────────────┬───────────────────────────────────────────┘
                                                │ HTTP/JSON (tipos TS generados desde OpenAPI)
┌───────────────────────────────────────────────▼────────────────────────────────────────────┐
│ services/api  (FastAPI)                                                                     │
│                                                                                             │
│  api/ ──▶ agent/ ──(herramientas)──▶ planning/ ──▶ engines/     (puros, sin E/S, sin LLM)    │
│            │  LLMClient (servidor propio)│    └──▶ regulation/  (RuleBook + resolutores)     │
│            │                             │    └──▶ params/      (criterios bancarios, tipos) │
│            │                             │    └──▶ valuation/   (renta y precio con rango)   │
│            │                             └──▶ territory/        (sección censal, indicadores)│
│            └──▶ ingestion/ (canales → normalización → duplicados)                           │
│  jobs/ worker: ingesta diaria, cargas del INE, vigilancia BOE/BOCM, reintentos y alertas    │
└──────────────┬──────────────────────────────────────────┬──────────────────────────────────┘
               │                                          │
     PostgreSQL 16 + PostGIS                    data/rules/*.yaml · data/params/*.yaml
     (sources, secciones, ofertas,              (versionados en git, verificados por Rodrigo)
      perfiles cifrados, planes, jobs)
```

### Dirección de dependencias (se comprueba con un test de imports)

```
core  ◀──  engines  ◀──  planning  ◀──  agent  ◀──  api
             ▲              │
regulation ──┘ (solo tipos) ├──▶ regulation, params, valuation, territory
```

- `engines/` no importa nada salvo `core/`. Recibe parámetros ya resueltos.
- `regulation/` y `params/` leen datos y devuelven parámetros con su `SourceRef`; no calculan
  rentabilidades.
- `planning/` es la **orquestación determinista**: perfil + oferta + fecha + escenario → `Plan`
  con todas sus `Figure` y `rule_ids`. No llama al LLM. Es lo que usan tanto la API del simulador
  como las herramientas del agente, así hay un solo camino de cálculo.
- `agent/` solo llama a `planning/` y redacta.

### Flujo de un plan (detalle de `ARCHITECTURE.md`)

```
perfil validado ─┐
oferta normaliz. ┼─▶ planning.build_plan(perfil, oferta, fecha, escenarios)
fecha + escenario┘        │
                          ├─ regulation: gastos de compra, IRPF, regulación de alquiler → rule_ids
                          ├─ params: criterios bancarios, trayectoria de tipos           → param_ids
                          ├─ valuation: renta P25/P50/P75                                → model_id
                          ├─ engines: hipoteca, cash flow, estrés, TIR, plazo            → Figure
                          ▼
                    Plan {figures{key→Figure}, rule_ids, engine_version, digests}
                          │
                    agent.narrate(plan) → texto con marcadores {{fig:clave}}, sin cifras
                          ▼
                    render web / PDF sustituye cada marcador por su Figure formateada
```

---

## 3. Decisiones transversales

Cada una con su compromiso. Las marcadas **ADR** se escriben en `docs/adr/` antes de implementarse.

### D1 · Contrato `Figure` v2 (G0) — ADR-0004

```python
@dataclass(frozen=True)
class SourceRef:
    kind: Literal["rule", "param", "dataset", "model", "user_input", "assumption"]
    id: str
    provisional: bool = False      # parámetro PROVISIONAL, regla sin verificar o supuesto

@dataclass(frozen=True)
class Figure:
    key: str                       # estable: "cashflow.monthly_after_tax"
    value: Decimal
    unit: str                      # "EUR", "EUR/mes", "ratio", "años"
    formula: str
    sources: tuple[SourceRef, ...]
    as_of: date | None = None
    low: Decimal | None = None     # rango (F5): P25
    high: Decimal | None = None    # rango (F5): P75

    @property
    def provisional(self) -> bool: ...   # True si alguna fuente lo es
```

- **Por qué ahora:** solo hay 4 ficheros de tests que tocar. Cuando haya planes guardados en base
  de datos y una web que los lea, cambiar el contrato cuesta una migración de datos.
- **Propagación de lo provisional:** una `Figure` derivada hereda las fuentes de sus entradas, así
  que el precio máximo calculado con `BankCriteria` provisional sale `provisional=True` y la web lo
  marca sin lógica propia.
- **Compromiso:** `Figure` crece; a cambio, F5 (rangos), F6.9 (claves) y la regla de oro 4
  (`PROVISIONAL` visible) salen del contrato y no de convenciones.

### D2 · Porcentajes en tanto por uno también en las salidas (G0)

`gross_yield` y `cash_on_cash` pasan a unidad `"ratio"` (0.072). La web y el PDF formatean
(`7,20 %`). Así el motor no mezcla escalas y la TIR (G1) sigue la misma regla.

### D3 · Parámetros con fecha como datos: `ParamBook` (G1) — ADR-0005

Los criterios bancarios (F1.5) y la trayectoria del Euríbor (F1.7) no son normativa, pero tienen la
misma forma: valor con fuente, fecha y estado. Se guardan en `data/params/*.yaml` y se cargan con
el mismo lector que las reglas.

- **Opción A — meterlos en `RuleBook`:** menos código, pero `verified: true` significa «Rodrigo leyó
  la fuente oficial», y un criterio bancario no tiene fuente oficial. Mezclaría significados.
- **Opción B — `ParamBook` separado con lector común (elegida):** misma forma de YAML, otro
  directorio y otro estado: `provisional: true` hasta que exista fuente documentada (un banco, un
  intermediario, una serie publicada).

### D4 · Un solo camino de cálculo: `planning/` (G3)

El endpoint del simulador, el plan completo y las herramientas del agente llaman a las mismas
funciones de `planning/`. Evita que el simulador y el plan den cifras distintas para lo mismo.

### D5 · Migraciones con un ejecutor propio (G4) — ADR-0008

- **Alembic:** estándar, pero arrastra SQLAlchemy y su modelo cuando aquí el SQL es explícito.
- **yoyo / sqitch:** dependencias pequeñas, otra herramienta que aprender.
- **Ejecutor propio (elegido):** ~40 líneas; aplica `db/migrations/NNNN_*.sql` en orden dentro de
  una transacción y apunta cada una en `schema_migrations`. `make db` deja de depender de que el
  volumen sea nuevo. Revisar si aparecen migraciones de datos complejas.

### D6 · Acceso a datos con psycopg 3 y SQL explícito (G4)

Las consultas importantes son de PostGIS (punto en polígono, cercanía para duplicados), que con
ORM acaban en SQL igualmente. Funciones de repositorio pequeñas por dominio, tipadas, con tests
contra la base de Docker. Compromiso: más SQL escrito a mano; a cambio, ninguna magia entre la
consulta y la cifra.

### D7 · Cola de trabajos en PostgreSQL (G4) — ADR-0010

- **Celery + Redis:** potente, pero otra pieza que operar.
- **AWS EventBridge + Lambda:** ata el diseño a AWS antes de F7.
- **Tabla `jobs` con `SELECT … FOR UPDATE SKIP LOCKED` (elegida):** un proceso worker del mismo
  código, reintentos con espera creciente, `job_runs` con resultado y error, programación tipo cron
  en una tabla. Revisar si se superan decenas de miles de trabajos al día o hace falta paralelismo
  entre máquinas.

### D8 · Datos personales cifrados de verdad (G4) — ADR-0011

`user_profiles` pasa a `data_enc BYTEA` + `key_id`, con cifrado de sobre: una clave de datos por
perfil, cifrada con una clave maestra (fichero local en desarrollo, AWS KMS en F7). Solo van en
claro los metadatos que hacen falta para filtrar (`org_id`, fechas). Los modelos de perfil se
redactan al convertirse en texto, y un test comprueba que los logs de un flujo completo no
contienen ingresos ni deudas.

### D9 · Reproducibilidad del plan (G4)

`plans` guarda `engine_version` (versión del paquete + commit), `rules_digest` y `params_digest`
(huella de los YAML cargados), `inputs_enc` (entradas cifradas) y `figures` con claves. Rehacer un
plan antiguo = cargar ese commit y esas reglas y comparar.

### D10 · Multi-cliente desde el esquema (G4, se usa en G8)

`org_id` en `user_profiles`, `plans` y ofertas privadas (enlaces pegados). Añadirlo con las tablas
vacías cuesta una línea; añadirlo con datos de la beta cuesta una migración delicada.
Row-Level Security de PostgreSQL se activa en G8.

### D11 · Contrato web ↔ API (G3)

La web importa tipos generados desde el OpenAPI de FastAPI (`openapi-typescript`). Los `Decimal`
viajan como texto (ya lo hace `Figure.to_dict`). Un componente `<FigureView>` muestra valor,
rango, fórmula, fuentes y el aviso `PROVISIONAL`. La web nunca calcula, solo formatea.

### D12 · El agente no escribe cifras: escribe referencias (G7) — ADR-0012

El texto del agente usa marcadores `{{fig:cashflow.monthly_after_tax}}` y el render los sustituye
por la `Figure`. La evaluación de F6.9 se convierte en una comprobación mecánica: el texto en bruto
del agente no contiene dígitos fuera de marcadores, y cada marcador existe en el plan. Compromiso:
redacción algo más rígida; a cambio, la regla de oro 1 se cumple por construcción y no por muestreo.

---

## 4. Grupos de features, en orden

Ruta crítica: **G0 → G1 → G2 → G3** (dinero del usuario) y **G4 → G5 → G6** (datos y oferta),
que se juntan en **G7**. Con una sola persona, los grupos de código van en serie; lo que corre en
paralelo son las tareas humanas (F0, verificación de reglas, calibración bancaria, consulta legal).

### G0 · Cimientos del contrato de cifras · ≈ 3–4 tardes · dentro de F1

**Objetivo.** Dejar el contrato de cifras definitivo antes de que lo consuma nadie más.

| Tarea | Detalle |
| --- | --- |
| G0.1 | `git init`, `make setup`, `make lint` y `make test` en verde tal como está hoy. |
| G0.2 | ADR-0004 (`Figure` v2) y aprobación. |
| G0.3 | `SourceRef` y `Figure` v2 (D1) con tests: propagación de `provisional`, serialización. |
| G0.4 | Migrar `mortgage.py`, `cashflow.py` y `api/main.py` al contrato v2: claves estables, fuentes tipadas, porcentajes en ratio (D2). |
| G0.5 | Test de dirección de dependencias (`engines` solo importa `core`). |

**Hecho cuando:** todas las salidas actuales son `Figure` v2 con clave, el precio máximo sale
`provisional=True` por `BankCriteria`, lint y tests en verde.
**Fuera de roadmap:** G0.3–G0.5 no son tareas del roadmap; propongo añadirlas como **F1.0**.

### G1 · Motor financiero completo · ≈ 2 semanas · F1.5–F1.9

**Objetivo.** Todo lo que depende del dinero del usuario, con trazabilidad.

Diseño:

- `params/` con `ParamBook` (D3): `criterios_bancarios` (sustituye los valores por defecto de
  `BankCriteria`) y `trayectoria_euribor` (lista de `(desde, tipo)` con fecha de publicación).
- `engines/rates.py`: `RatePath` = tramos de tipo en el tiempo. Una hipoteca variable o mixta se
  calcula recalculando la cuota francesa con el capital pendiente en cada revisión.
- `engines/mortgage.py`:
  - `compare_mortgages(fija, variable, mixta, trayectoria, estrés)` → coste total esperado y peor
    cuota de cada una (F1.6).
- `engines/term.py`: `recommended_term(...)` → menor plazo con cash flow ≥ 0 en estrés (F1.8).
  Como la cuota baja al alargar el plazo, el cash flow crece con el plazo: búsqueda binaria entre 1
  y el plazo máximo por edad. Si ningún plazo funciona, devuelve un resultado explícito «ningún
  plazo da cash flow positivo en estrés», nunca `None` silencioso.
- `engines/irr.py`: TIR a 10 años (F1.9) con `Decimal` por bisección (robusta, sin derivadas); la
  revalorización entra como parámetro con `SourceRef(kind="assumption")` hasta que F5 la aporte.

Tests de valor conocido: cada uno anota de dónde sale el valor (cálculo a mano o calculadora de
referencia, con la fecha de consulta).

**Bloqueos humanos:**
- **F1.5:** calibrar criterios con 2–3 bancos o un intermediario. Hasta entonces, `provisional: true`.
- **F1.7:** hay que elegir **qué serie pública** da la trayectoria esperada del Euríbor. No la fijo
  de memoria: es una pregunta abierta (§7).

**Hecho cuando:** F1.5–F1.9 con tests de valor conocido y todas las salidas como `Figure` v2.

### G2 · Normativa y fiscalidad de Madrid · ≈ 2 semanas de código + verificación · F2.2–F2.5, F2.7

**Objetivo.** Que el motor resuelva por sí mismo los gastos de compra y el IRPF del alquiler.

Diseño:

- `regulation/kinds.py`: catálogo de `kind` con el esquema de `params` de cada uno (pydantic). Al
  cargar, una regla con parámetros mal formados falla.
- **Validador de reglas en CI** (`make rules-check`): esquema por `kind`, territorios válidos,
  `source_url` presente, y **solapes**: dos reglas del mismo `kind`, territorio y estado con
  vigencias que se cruzan son un error. Hoy `resolve()` desempata en silencio por fecha de inicio.
- Campos nuevos en la regla: `verified_by` y `verified_on`, para que la verificación quede
  registrada y no sea solo un booleano.
- Resolutores (`regulation/resolvers.py`), que devuelven `Figure` + `rule_ids`:
  - `purchase_costs(precio, territorio, fecha, tipo_inmueble, situación_comprador)` → impuesto +
    notaría + registro + gestoría; alimenta a `affordability` y elimina `purchase_cost_rate`
    enviado por el cliente.
  - `tax_params(perfil, territorio, fecha)` → `TaxParams` (F2.7).
- Escenarios (F2.5): `Scenario(nombre, reglas_pendientes_incluidas)`; `planning/` calcula el plan
  base y cada escenario y devuelve la diferencia por clave de `Figure`.
- Regulación del alquiler (F2.4): reglas con efecto sobre la recomendación (zona tensionada,
  temporada, habitaciones, turístico), consumidas en G7.

**Decisión de diseño a tomar al empezar G2 (D-G2-1).** Hoy el impuesto se calcula como
`rendimiento × tipo marginal`. Si el rendimiento del alquiler hace saltar de tramo al usuario, el
resultado es inexacto. Alternativa: calcular la **cuota incremental** = IRPF con el alquiler − IRPF
sin él, con las escalas estatal y autonómica como reglas. Es más trabajo de inventario (F2.2) y es
justo el diferenciador del producto («la rentabilidad del usuario, con su IRPF»). Recomiendo la
cuota incremental. **Decidido el 2026-10-28: cuota incremental (ADR-0007).**

**Bloqueo humano:** cada regla entra con `verified: false` hasta que Rodrigo lea la fuente. El
desarrollo usa `allow_unverified=True`, y las `Figure` salen `provisional=True`, así que nunca se
confunde una cifra de desarrollo con una verificada.
**F2.6 (vigilancia del BOE/BOCM) pasa a G4**, porque necesita la cola de trabajos.

**Hecho cuando:** criterio de salida de F2.

### G3 · Simulador de inversión de punta a punta · ≈ 1 semana · F1.10 + criterio de salida de F1

**Objetivo.** Primera pieza que ve un usuario y primera prueba de que el motor reproduce un plan
manual de F0.

- `planning/simulate.py` (D4): compone capacidad, hipoteca, gastos de compra resueltos, cash flow,
  estrés, plazo recomendado y TIR.
- `POST /simulate/investment` con routers por dominio en `api/`.
- Web: página del simulador con `<FigureView>` (D11) y tipos generados desde OpenAPI.
- **Prueba de oro:** un plan manual de F0 como fixture en `tests/fixtures/private/` (tiene datos
  personales; ignorada por git) y su versión anonimizada en `tests/fixtures/`. Diferencia < 1 €.

**Hecho cuando:** criterio de salida de F1 cumplido y simulador usable en `make web`.

### G4 · Plataforma de datos y territorio · ≈ 2 semanas · F3 + F2.6 + F4.7

**Objetivo.** Base de datos real, cargas trazables y la sección censal de cualquier dirección.

- Ejecutor de migraciones (D5, ADR-0008) y `0002`: secciones con clave `(code, vintage)`,
  `org_id` (D10) y reproducibilidad de planes (D9). Cada pieza con ADR propio llega en su
  migración: `jobs` y `job_runs` (D7, ADR-0010), perfiles cifrados (D8, ADR-0011) y
  `review_tasks` con la vigilancia normativa. *Estado (2026-10-29):* hechas las migraciones 0002–0007.
- `db/` con psycopg 3 (D6) y tests contra la base de Docker en CI (servicio `postgis`).
- `jobs/`: worker, reintentos, programación y alerta de fallo (correo o log al principio).
- Cargadores idempotentes: cartografía de secciones (F3.2), Atlas de renta (F3.3), padrón (F3.4),
  indicadores de demanda (F3.5). Cada carga escribe su fila en `sources` con licencia y fecha (F3.7).
- Geocodificación con CartoCiudad y asignación de sección por punto en polígono, con caché (F3.6).
- `GET /territory?address=…` → sección + indicadores como `Figure` con `SourceRef(kind="dataset")`.
- Vigilancia BOE/BOCM (F2.6): trabajo diario que abre `review_tasks`; el resumen lo hará el LLM
  cuando exista `LLMClient` (G5), una persona decide.

**Hecho cuando:** criterio de salida de F3, y `make db` aplica migraciones sobre un volumen existente.

### G5 · Ingesta de oferta · ≈ 2 semanas · F4 (+ F6.1 adelantada)

**Objetivo.** Oferta real cada día por al menos dos canales legales.

- Interfaz `Channel`: `fetch → raw → parse → NormalizedOffer`; el `raw` se guarda siempre.
- **F6.1 se adelanta aquí:** el enlace pegado (F4.1) necesita el LLM para extraer precio,
  superficie, planta y estado. `agent/llm.py` con `LLMClient` (protocolo), implementación para un servidor propio (ADR-0014) y
  una falsa para tests. La extracción devuelve cada campo con confianza y **siempre** pasa por
  confirmación del usuario antes de usarse en un cálculo.
- BOE: fijar el esquema con un sumario real guardado como fixture (F4.2), sección V (F4.4),
  subastas (F4.3, con ADR si no hay vía de datos abiertos).
- Servicers (F4.5): un ADR por servicer, condicionado a la consulta legal de F0.6.
- Duplicados (F4.6): primero por referencia catastral; si no hay, cercanía (PostGIS) + superficie.

**Riesgo:** los dos canales del BOE pueden cumplir el criterio técnico con muy poco volumen de
vivienda en Madrid. Conviene medirlo pronto (un mes de sumarios) para saber cuánto pesa el enlace
pegado en la propuesta.
**Hecho cuando:** criterio de salida de F4.

### G6 · Valoración · ≈ 2 semanas · F5

**Objetivo.** Renta y precio estimados con rango honesto.

- Cada estimación es una `Figure` con `low`/`high` y `SourceRef(kind="model", id="renta-v1@fecha")`.
- Modelo base: por sección censal, con vuelta al municipio cuando hay pocos datos (contracción
  hacia la media de la zona), y cuantiles para P25–P75. Elegir librería (scikit-learn,
  statsmodels…) es una dependencia importante: ADR antes.
- Banco de pruebas de backtesting (F5.6): entrenar con un año, evaluar con el siguiente.
- Escenarios de revalorización (F5.5) que sustituyen al supuesto de la TIR de G1.

**Hecho cuando:** criterio de salida de F5 (el umbral de error lo fija F0).

### G7 · Agente y plan de inversión · ≈ 2–3 semanas · F6

**Objetivo.** Del perfil al plan completo, explicado y exportable.

- Perfilado (F6.2) → `Profile` validado con pydantic; lectura de documentos (F6.3) con confirmación.
- Herramientas del agente (F6.4) = funciones de `planning/`; nunca cálculo propio.
- Búsqueda inversa (F6.5): puntuación determinista en `planning/` sobre las ofertas; el agente solo
  ordena y explica.
- Recomendación de tipo de alquiler y gestión (F6.6) con las reglas de F2.4.
- Plan completo (F6.7) con marcadores de cifras (D12) y argumentos para no comprar.
- PDF (F6.8): elegir motor de PDF (desde la propia web con impresión del navegador, o en Python):
  ADR.
- Evaluaciones (F6.9): extracción de anuncios contra un juego etiquetado, ausencia de dígitos
  fuera de marcadores, coherencia del plan.

**Hecho cuando:** criterio de salida de F6.

### G8 · Beta con profesionales · F7

Autenticación (ADR: Cognito, Auth.js o un servicio gestionado), Row-Level Security por `org_id`,
varios perfiles por profesional, marca en el plan, avisos legales y consentimiento, despliegue en
AWS (contenedor de API + worker y PostgreSQL gestionado con PostGIS), copias de seguridad y
monitorización básica. Detalle cuando G7 esté en marcha.

### G9 · Particulares · F8 · y G10 · Medir y decidir · F9

Se diseñan después de la beta, con lo aprendido en F7.

---

## 5. Calendario y la cuenta que no sale

| Grupo | Semanas (desde el 2 nov) | Encaje con el roadmap |
| --- | --- | --- |
| G0 | 1 | F1 |
| G1 | 1–3 | F1 (2–29 nov) |
| G2 | 3–5 | F2 (23 nov–13 dic) |
| G3 | 5 | cierre de F1 |
| G4 | 6–7 | F3 (30 nov–20 dic), un poco tarde |
| G5 | 8–9 | F4 (14 dic–3 ene) |
| G6 | 10–11 | F5 (21 dic–10 ene) |
| G7 | 11–13 | F6 (28 dic–17 ene), **tarde** |
| G8 | 13–17 | F7 (11 ene–14 feb), **tarde** |

En serie y a tiempo parcial, G7 termina un par de semanas después del inicio previsto de la beta,
y la semana de Navidad cae en medio. Opciones, de menor a mayor recorte:

1. **Beta con un plan por oferta** (recomendada): el profesional pega un enlace o elige una oferta
   del BOE y obtiene el plan. La búsqueda inversa (F6.5) y los escenarios de revalorización (F5.5)
   llegan durante el piloto.
2. Valoración mínima en G6: solo renta con rango; el precio, después de la beta.
3. Mover la beta a febrero.

Es una decisión de alcance: la tomas tú.

---

## 6. Riesgos y qué revisar al crecer

| Riesgo | Mitigación |
| --- | --- |
| La verificación humana de reglas es el cuello de botella | Inventario de F2.2 cuanto antes; trabajar con reglas sin verificar marcadas `provisional` |
| Criterios bancarios sin calibrar invalidan la capacidad | Visibles como `PROVISIONAL` en cada cifra; F1.5 en paralelo desde la semana 1 |
| Poco volumen de oferta por canales legales | Medir el BOE pronto; reforzar el enlace pegado como canal principal |
| El LLM inventa una cifra | Marcadores (D12) + evaluación mecánica |
| Fuga de datos personales | Cifrado de sobre, `org_id`, RLS, test de logs |
| Un plan antiguo no se puede rehacer | Versión del motor y huellas de reglas y parámetros en cada plan |

Qué revisaría al crecer:

- **Cola en PostgreSQL** → servicio de colas si la ingesta pasa a decenas de miles de trabajos
  diarios o hacen falta varios workers en varias máquinas.
- **Reglas en YAML dentro del repositorio** → tabla en base de datos con flujo de revisión cuando
  las reglas las mantenga alguien que no programa, o cuando haya varias comunidades autónomas.
- **Un único proceso de API** → separar el agente (lento, con LLM) de los motores (rápidos) si la
  latencia del simulador empieza a sufrir.
- **Modelo de valoración por sección** → modelos más ricos solo si el backtesting lo justifica.

---

## 7. Preguntas abiertas para Rodrigo

1. ¿Apruebas añadir **F1.0** (contrato `Figure` v2) al roadmap y empezar por G0?
2. ¿Inicio el repositorio git ahora? Sin él no se cumple «un commit por tarea».
3. **F1.7:** ¿qué serie pública quieres usar para la trayectoria esperada del Euríbor? Necesito que
   la elijas tú o que la investiguemos con la fuente delante; no la fijo de memoria.
4. ~~**D-G2-1:** ¿cuota incremental de IRPF o tipo marginal?~~ Cuota incremental (ADR-0007).
5. **Alcance de la beta (§5):** ¿opción 1, 2 o 3?

## 8. ADRs propuestos

| ADR | Tema | Grupo |
| --- | --- | --- |
| 0004 | Contrato `Figure` v2 y fuentes tipadas | G0 |
| 0005 | Parámetros con fecha como datos (`ParamBook`) | G1 |
| 0006 | Trayectoria esperada del Euríbor a un año | G1 |
| 0007 | El IRPF del alquiler es la cuota incremental | G2 |
| 0008 | Migraciones con ejecutor propio | G4 |
| 0009 | Geocodificación con CartoCiudad y caché | G4 |
| 0010 | Cola de trabajos en PostgreSQL | G4 |
| 0011 | Cifrado de datos personales y separación por cliente | G4 |
| 0012 | El agente escribe referencias a cifras, no cifras | G7 |
| 0013 | Cliente del LLM propio y extracción con evidencia comprobada | G5 |
| 0014 | Modelo de código abierto en un servidor propio | G5 |
| 0015 | Enlace pegado por el usuario | G5 |
| 0016 | Ubicación de ofertas por referencia catastral | G5 |
| — | Librería de modelos estadísticos | G6 |
| — | Motor de PDF | G7 |
| — | Autenticación y despliegue | G8 |
