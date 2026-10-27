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
    engines/cashflow.py   cash flow y rentabilidad personal
    engines/term.py       plazo recomendado con cash flow en estrés
    engines/irr.py        TIR de la inversión con revalorización y venta
    regulation/rules.py   motor de normativa versionada (RuleBook)
    params/               parámetros con fecha (ParamBook): criterios bancarios, tipos
    ingestion/boe.py      sumario diario del BOE (esquema por verificar, fase 4)
    api/main.py           endpoints HTTP
  data/rules/             reglas de normativa en YAML
  data/params/            parámetros con fecha en YAML (ADR-0005)
  tests/                  pytest; un test por regla de negocio
db/migrations/            SQL de PostgreSQL + PostGIS
infra/docker-compose.yml  base de datos local
docs/                     ROADMAP, ARCHITECTURE, DATA_SOURCES, ADRs y plantillas
```

## Comandos

```bash
make setup     # entorno Python (.venv) y dependencias web
make db        # PostgreSQL + PostGIS en Docker (aplica db/migrations al crear)
make test      # pytest de la API
make lint      # ruff
make api       # API en http://localhost:8000 (docs en /docs)
make web       # web en http://localhost:3000
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
