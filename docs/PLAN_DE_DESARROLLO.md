# HouseFinder · Plan de desarrollo

Documento maestro con todo lo decidido hasta el 31 de octubre de 2026: producto, arquitectura,
entorno, fases, calendario, costes, riesgos y forma de trabajar.
El **estado de cada tarea** se marca en [ROADMAP.md](ROADMAP.md) y cada decisión de arquitectura
está en su [ADR](adr/); este plan explica el porqué y el cómo. Donde el plan propone algo que aún no
tiene ADR, lo dice: **propuesta, pendiente de ADR**.

---

## 1. Resumen

| | |
| --- | --- |
| **Qué es** | Plataforma con IA que encuentra oportunidades de inversión inmobiliaria y genera, para cada usuario, un plan de inversión personal y verificable |
| **Diferenciador** | Se calcula la rentabilidad **del usuario** (con su hipoteca, su IRPF, su tiempo y la normativa vigente), no la del inmueble. Independiente: no vende activos |
| **Clientes** | Profesionales (intermediarios hipotecarios, asesores, agencias) con plan mensual; particulares con pase de compra y suscripción de propietario |
| **MVP** | Madrid y área metropolitana; oferta por enlace del usuario, BOE (subastas y sección V) y grandes servicers |
| **Competencia directa** | Invisor y Cassandra AI: rastrean portales y recogen preferencias, pero no calculan la rentabilidad personal ni modelan la normativa por inmueble |
| **Hitos** | Validación en noviembre · beta privada con profesionales a mediados de enero de 2027 · pase para particulares en febrero · decisión a finales de marzo |
| **Modo actual** | Todo en local (Mac M5, 16 GB): PostgreSQL + PostGIS en Docker, worker con launchd y `qwen3:14b` en Ollama. El despliegue de F7 está por decidir (sección 3.3) |

---

## 2. Decisiones de arquitectura

| ADR | Decisión | Consecuencia práctica |
| --- | --- | --- |
| [0001](adr/0001-ia-explica-motores-calculan.md) | La IA explica; los motores calculan | Ninguna cifra la escribe el modelo de lenguaje; todas son `Figure` con fórmula y fuente |
| [0002](adr/0002-fuentes-publicas-nativas.md) | Fuentes públicas y desarrollo propio | Sin proveedores comerciales de datos ni scraping de portales sin ADR |
| [0003](adr/0003-normativa-como-datos.md) | La normativa son datos versionados | Una ley nueva = una regla YAML verificada, no un cambio de código |
| [0004](adr/0004-contrato-figure-v2.md) | Contrato `Figure` v2 | Clave estable, fuentes tipadas, rango opcional y marca `PROVISIONAL` propagada |
| [0005](adr/0005-parametros-con-fecha-como-datos.md) | Parámetros con fecha como datos | Criterios bancarios, Euríbor y contracción de la renta en YAML, sin valores en el código |
| [0006](adr/0006-trayectoria-euribor.md) | Trayectoria del Euríbor desde la curva publicada | Sin predicciones propias de tipos |
| [0007](adr/0007-cuota-incremental-irpf.md) | IRPF del alquiler como cuota incremental | Escalas, mínimos, límite de intereses y arrastre, también en la TIR |
| [0008](adr/0008-migraciones-y-acceso-a-datos.md) | Migraciones propias y psycopg 3 | Solo `db/` habla con la base |
| [0009](adr/0009-geocodificacion-cartociudad.md) | Geocodificación con CartoCiudad | Caché en PostgreSQL, sin datos del usuario |
| [0010](adr/0010-cola-de-trabajos-en-postgresql.md) | Cola de trabajos en PostgreSQL | Reintentos, programaciones diarias y alertas sin servicios externos |
| [0011](adr/0011-cifrado-de-datos-personales.md) | Cifrado de sobre de los datos personales | Perfil y documentos cifrados; clave maestra en fichero local, gestor de claves en F7 |
| [0012](adr/0012-el-agente-escribe-referencias-a-cifras.md) | El agente escribe marcadores, no cifras | Un texto con un dígito fuera de `{{fig:clave}}` no se muestra |
| [0013](adr/0013-llmclient-y-extraccion-con-evidencia.md) | Cliente del LLM propio y extracción con evidencia | Cada dato extraído lleva una cita literal comprobada |
| [0014](adr/0014-llm-de-codigo-abierto-en-servidor-propio.md) | Modelo abierto en servidor propio | Un único cliente compatible con OpenAI; cambiar de entorno = cambiar `.env` |
| [0015](adr/0015-enlace-pegado-por-el-usuario.md) | Enlace pegado por el usuario | Una descarga a petición suya, con `robots.txt` y sin esquivar bloqueos |
| [0016](adr/0016-ubicacion-por-referencia-catastral.md) | Ubicación por referencia catastral | Centroide de la parcela del Catastro antes que la dirección |
| [0017](adr/0017-subastas-judiciales-por-el-boe.md) | Subastas por los avisos del BOE | El Portal de Subastas no se lee; el usuario pega el lote |
| [0018](adr/0018-referencias-de-alquiler-y-precio.md) | Referencias de alquiler y precio | SERPAVI por sección; precio estimado desde la renta |
| [0019](adr/0019-herramientas-del-agente.md) | Herramientas del agente | Solo lectura, argumentos sin números; datos del usuario al modelo con las condiciones del RGPD |

---

## 3. Arquitectura

### 3.1 Capas

```
Ingesta ──▶ Enriquecimiento ──▶ Motores ──▶ Plan
(enlaces,    (geocodificación,    (hipoteca,    (agente que orquesta,
 BOE,         duplicados, sección   fiscalidad,   explica y genera
 servicers)   censal, INE, Catastro) normativa,   web y PDF)
                                     valoración)
──────── Base común: PostgreSQL + PostGIS · cola de trabajos · registro de fuentes ────────
```

### 3.2 Subagentes

Un subagente es un **rol del mismo modelo**, no un modelo distinto. No hay un registro central:
cada rol es un módulo de `agent/` o de `advisor/` que usa el mismo `LLMClient`.

| Subagente | Hace | Datos personales | Estado |
| --- | --- | --- | --- |
| Orquestador | Decide qué herramientas y motores llamar | Sí | Base hecha: `agent/loop.py` y `advisor/` (F6.4) |
| Perfilador | Conversa y produce un perfil estructurado | Sí | F6.2 |
| Extractor de anuncios | Anuncio o entrada del BOE → datos con cita comprobada | No | Hecho: `agent/extraction.py` (F4.1, F4.4) |
| Lector de documentos | Nóminas, extractos y declaraciones, con confirmación del usuario | Sí | F6.3 |
| Analista visual | Estado del inmueble y reforma a partir de fotos | No | Propuesta, sin tarea en el roadmap |
| Vigilante normativo | Resume el BOE y el BOCM; decide una persona | No | Filtros y tareas hechos (F2.6); falta el resumen del modelo |
| Redactor del plan | Explica cifras ya calculadas | Sí | F6.7 |
| Verificador | Rechaza el texto con cifras fuera de un marcador | — (es **código**) | Hecho: `agent/references.py` (ADR-0012) |

Los datos personales solo llegan al modelo con minimización por tarea y las demás condiciones de
ADR-0019. Embeddings para duplicados y búsqueda semántica en normativa (pgvector): **propuesta,
pendiente de ADR**; hoy la deduplicación es por referencia catastral y distancia (F4.6).

### 3.3 Despliegue por etapas

| Pieza | Ahora (local) | Desde F7 |
| --- | --- | --- |
| Web | `make web` (Next.js) | Por decidir |
| Motores y API | `make api` (FastAPI) | Por decidir |
| Trabajos | `make worker-install` (launchd) | Por decidir |
| Base de datos | PostgreSQL + PostGIS en Docker | Por decidir |
| Modelos | `qwen3:14b` en Ollama (Homebrew) | Servidor propio en la UE (ADR-0014) |
| Claves | Clave maestra en fichero local (ADR-0011) | Gestor de claves (ADR-0011 dice AWS KMS) |

Lo documentado hoy para F7 es AWS (ADR-0011, PLAN_DISENO y F7.5). **Propuesta de este plan,
pendiente de ADR antes de F7:** web y API en Vercel Pro (funciones en `fra1`), base en Supabase en
la UE y un servidor GPU privado en la UE con vLLM, TEI y Caddy, con el orquestador junto a los
modelos y el progreso en la base. El orquestador no iría en funciones de Vercel porque tienen
límite de duración (300 s en Hobby, hasta 800 s en Pro) y un plan completo puede superarlo. El ADR
tiene que resolver también dónde corre el worker de la cola y qué sustituye a AWS KMS.

---

## 4. Entorno de desarrollo

### 4.1 Máquina

MacBook con M5, 16 GB de memoria unificada y 512 GB de disco. La GPU comparte memoria con el
sistema, Docker, el editor y el navegador: quedan **unos 8–10 GB útiles para el modelo**.

### 4.2 Modelos en local

| Uso | Modelo | Servidor | Licencia |
| --- | --- | --- | --- |
| Extracción y agente | `qwen3-14b-hf`: `qwen3:14b` (Q4_K_M, 9,3 GB) con ventana de 16.384 tokens | Ollama en `localhost:11434` | Apache 2.0 |
| Alternativa con poca memoria | `qwen3-hf`: `qwen3:8b` (5,2 GB), misma ventana; extrae, pero no sirve para el agente | Ollama | Apache 2.0 |

Sin razonamiento (`LLM_REASONING_EFFORT=none`): con él la extracción fue más lenta y peor (ADR-0014).
El modelo de producción se elige en F6.0 (sección 6); los candidatos más grandes se prueban en una
GPU alquilada, no en este Mac.

### 4.3 Puesta en marcha

```bash
cd ~/Documents/housefinder
cp .env.example .env
make setup        # entorno Python y dependencias web
brew install tesseract tesseract-lang   # OCR de escaneos y fotos (ADR-0021)
make db           # PostgreSQL + PostGIS en Docker
make test         # motores en verde
```

Modelo: `brew services start ollama`, `ollama pull qwen3:14b` y
`ollama create qwen3-14b-hf -f infra/ollama/qwen3-14b-hf.Modelfile` (misma descarga, ventana de
16.384 tokens; sin ella Ollama recorta la conversación a 4.096 en silencio). En `.env`:

```
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL_ID=qwen3-14b-hf
LLM_REASONING_EFFORT=none
```

Para probar el agente: `python -m housefinder.advisor preguntar "…"`.

### 4.4 Reglas del entorno

- Solo datos inventados: nada de nóminas ni extractos reales (`tests/fixtures/private/`, fuera de git).
- Para comparar modelos grandes, alquilar una GPU por horas y apuntar `LLM_BASE_URL` allí: el código no cambia.
- Ollama es compartido: si otro proyecto lo usa (por ejemplo, una campaña larga), las peticiones de
  HouseFinder esperan en cola y pueden agotar `LLM_TIMEOUT_S`. Antes de probar el agente o lanzar
  la extracción, comprobar que está libre.

---

## 5. Fases

Fechas orientativas con dedicación parcial (tardes y fines de semana) desde el 2 de noviembre.
Manda el **criterio de salida**, no la fecha. Tareas detalladas y su estado en [ROADMAP.md](ROADMAP.md).

**Estado a 31 de octubre:** el código de F1 a F5 está casi terminado antes de su fecha. Lo que
bloquea sus criterios de salida son tareas humanas: planes reales de F0, el umbral de error de la
renta, la verificación de reglas y la calibración bancaria.

### F0 · Validación (sin código) — 2 al 22 de noviembre

- **Objetivo:** comprobar que un plan personal genera confianza y acción antes de construirlo.
- **Trabajo:** plantilla de plan manual; 10 planes hechos a mano; 20 entrevistas (12 inversores,
  8 profesionales); probar Invisor y Cassandra AI con 3 perfiles; consulta legal (scraping,
  Ley 5/2019, RGPD, avisos del plan y envío de datos del usuario al modelo, ADR-0019); elegir
  3–5 profesionales para el piloto.
- **Salida:** al menos 5 de 10 planes llevan a una acción y al menos 3 profesionales se
  comprometen al piloto.

### F1 · Motor financiero — 2 al 29 de noviembre

- **Hecho:** cuota y cuadro de amortización, capacidad de compra con plazo por edad, estrés de
  tipos, cash flow y cash-on-cash, criterios bancarios como datos, comparación fija / variable /
  mixta, trayectoria del Euríbor, plazo recomendado, TIR a 10 años, endpoint y simulador web.
- **Pendiente:** calibrar criterios bancarios con 2–3 bancos o un intermediario (hoy `PROVISIONAL`).
- **Salida:** un plan manual de F0 reproducido por el motor con diferencias menores de 1 €
  (el arnés pasa con un plan sintético; falta un plan real).

### F2 · Normativa y fiscalidad — 23 de noviembre al 13 de diciembre

- **Hecho:** `RuleBook` y validador, inventario de reglas de Madrid, normativa de alquiler, escenarios
  con normas pendientes de convalidación, vigilancia del BOE y del BOCM, fiscalidad del cash flow
  conectada a las reglas y cuota incremental del IRPF.
- **Pendiente:** verificar las reglas cargadas (tandas 1 a 5) contra la fuente oficial y completar
  las filas pendientes del inventario.
- **Salida:** un plan de Madrid con todas sus reglas citadas y verificadas.

### F3 · Datos territoriales — 30 de noviembre al 20 de diciembre

- **Hecho:** secciones censales del INE, Atlas de renta y demografía 2015–2024, geocodificación con
  CartoCiudad y `GET /territory`. El criterio de salida se cumple.
- **Pendiente:** decidir si hace falta el padrón continuo además del Atlas; indicadores de demanda
  (universidades, hospitales, afiliación); registrar cada cargador nuevo en `sources`.
- **Salida:** una dirección de Madrid devuelve su sección censal con renta, población y
  tendencias, cada dato con su fuente.

### F4 · Ingesta de oferta — 14 de diciembre al 3 de enero

- **Hecho:** enlace pegado con extracción y confirmación, sumario del BOE verificado, sección V con
  correcciones, avisos de subastas judiciales de Madrid, normalización y deduplicación, ubicación por
  referencia catastral y trabajos programados.
- **Pendiente:** servicers (términos de uso, ADR por servicer y contacto comercial); verificar los
  partidos judiciales y enviar la consulta a la AEBOE.
- **Salida:** ofertas diarias de al menos dos canales, sin duplicados, con sección censal.

### F5 · Valoración — 21 de diciembre al 10 de enero

- **Hecho:** referencias de alquiler (SERPAVI) y de precio (valor tasado, IPV); renta con rango
  P25–P75; precio desde la renta; escenarios de revalorización; backtesting; valoración de cada oferta
  confirmada frente a lo que pide.
- **Pendiente:** cerrar F5.4. El margen de negociación sobre el precio pedido **no tiene fuente
  pública**: la diferencia con el anuncio se muestra, pero no como margen.
- **Salida:** error medio de la renta estimada por debajo del umbral fijado en F0.

### F6 · Agente y plan — 28 de diciembre al 17 de enero

- **Hecho:** cliente único de modelos (F6.1), verificador de cifras (ADR-0012) y herramientas del
  agente sobre los motores (F6.4).
- **F6.0 Evaluación de modelos** (sección 6): es lo que queda de F6.1, elegir servidor y modelo
  con una prueba real, antes de fijar el de producción.
- **Pendiente:** perfilado conversacional; lectura de documentos; búsqueda inversa con puntuación por
  perfil; recomendación de alquiler y gestión; plan completo con escenarios, argumentos para no
  comprar y hoja de ruta; PDF con fuentes; evaluaciones automáticas.
- **Salida:** los 10 planes de F0 se reproducen en menos de 10 minutos cada uno, sin cifras
  sin respaldo.

### F7 · Beta privada con profesionales — 11 de enero al 14 de febrero

- Cuentas y separación de datos por cliente; varios perfiles por profesional; planes con su marca;
  avisos legales y consentimiento; **despliegue según el ADR de la sección 3.3** con copias de
  seguridad y monitorización; servidor del modelo en la UE; piloto de 4 semanas con feedback
  semanal; propuesta de precio.
- **Salida:** al menos 3 de 5 profesionales pagan al terminar.

### F8 · Pase de compra para particulares — 1 al 28 de febrero

- Página de presentación y alta; nivel gratuito; pase con pasarela de pago; derivación a
  intermediario hipotecario registrado; condiciones y privacidad revisadas por abogado; analítica
  respetuosa con la privacidad.
- **Salida:** primeros pases vendidos y embudo de conversión medido.

### F9 · Medir y decidir — marzo

- Revisar los tres criterios de validación, comparar rentas estimadas con reales y decidir:
  seguir, ajustar o pivotar. Decisión escrita en un ADR.

---

## 6. Evaluación de modelos (F6.0)

| Paso | Detalle |
| --- | --- |
| Conjunto de pruebas | 30 anuncios reales pegados a mano y anuncios del BOE, 10 nóminas y 10 extractos **inventados**, 10 conversaciones de perfil simuladas, 10 casos de llamada a herramientas |
| Candidatos | `qwen3:14b` (desarrollo; el 8B no pide las herramientas, ver `research/f6-0-banco-agente.md`), Gemma 4 12B, Gemma 4 26B-A4B, Qwen3.6-35B-A3B, gpt-oss-20b |
| Dónde | Los que quepan en el Mac (8–10 GB útiles), en local; el resto en una GPU alquilada por horas (24–48 GB) |
| Métricas | Campos extraídos verificados, rechazados y atribuidos al lote equivocado (ADR-0014); JSON válido; llamadas a herramientas correctas; textos que pasan el verificador a la primera; calidad del español; latencia |
| Decisión | Mejor relación calidad / memoria que quepa en el servidor de F7, con licencia comprobada en su archivo LICENSE (ADR-0014 pide Apache 2.0 o MIT) |

Coste estimado: unas pocas horas de GPU alquilada, del orden de unos euros. Lo visto con
`qwen3:8b`: extrae con citas pero puede copiar los datos de un lote en otro, y en el agente no
pide las herramientas de forma fiable. Con `qwen3:14b` el agente acierta las herramientas en cuatro
de cinco preguntas, pero copia valores y se equivoca de clave (`research/f6-0-banco-agente.md`).

---

## 7. Calendario

| Semana | Fechas | Foco principal |
| --- | --- | --- |
| 1 | 2–8 nov | F0 entrevistas y plantilla · F1 calibración bancaria |
| 2 | 9–15 nov | F0 planes manuales · F2 verificación de reglas |
| 3 | 16–22 nov | F0 cierre y consulta legal · F1 criterio de salida con un plan real |
| 4 | 23–29 nov | F2 criterio de salida · F6 perfilado |
| 5 | 30 nov–6 dic | F3 indicadores de demanda · F6 lectura de documentos |
| 6 | 7–13 dic | Margen (semana con viaje previsto) |
| 7 | 14–20 dic | F4 servicers · F6 búsqueda inversa |
| 8 | 21–27 dic | F5 cierre · F6 recomendación de alquiler y gestión |
| 9 | 28 dic–3 ene | F6.0 evaluación de modelos · ADR de despliegue |
| 10 | 4–10 ene | F6 plan completo |
| 11 | 11–17 ene | F6 PDF y evaluaciones · F7 cuentas y despliegue |
| 12–15 | 18 ene–14 feb | F7 piloto con profesionales |
| 14–17 | 1–28 feb | F8 pase de compra |
| 18–21 | marzo | F9 medir y decidir |

El calendario se ha movido porque el código de F1–F5 va por delante de su fecha. Si algo se retrasa,
se recorta alcance de F4 (un solo servicer) y de F6 (búsqueda inversa y recomendación más simples),
nunca los criterios de salida de F1 y F2.

---

## 8. Infraestructura y costes

| Etapa | Concepto | Coste orientativo |
| --- | --- | --- |
| Desarrollo (ahora) | Mac propio, datos públicos, Ollama | 0 € |
| Desarrollo (ahora) | GPU alquilada por horas para F6.0 | Unos euros |
| Beta (F7) | Servidor GPU dedicado en la UE (referencia: Hetzner GEX44, 20 GB) | ~185–235 €/mes + alta |
| Beta (F7), propuesta | Vercel Pro | ~20 $/mes |
| Beta (F7), propuesta | Supabase (gratuito al inicio, Pro si hace falta) | 0–25 $/mes |
| Escala | GPU de 32–48 GB (RTX 5090, L40S) o 96 GB (RTX PRO 6000) | ~300–1.200 €/mes según opción |
| Una vez | Asesoría legal inicial | [€__] |
| Una vez | Constitución y gestoría | [€__] |

Los precios de GPU cambian a menudo: revisarlos el día de contratar. A volumen de MVP, pagar por
uso a un proveedor sería más barato; el servidor propio se elige por privacidad de los datos
financieros, coste fijo e independencia (ADR-0014). Se revisa en F9.

Para el plan profesional se usa el modelo de F6.0 que quepa en la GPU contratada; con 20 GB, un
modelo de unos 26B con pocos parámetros activos a 4 bits y contexto moderado.

---

## 9. Modelo de negocio y validación

| Nivel | Precio orientativo | Contenido |
| --- | --- | --- |
| Gratis | 0 € | Perfil, capacidad de compra, pocos análisis |
| Pase de compra | 49–99 € | 3–6 meses de búsqueda, planes y hoja de ruta |
| Propietario | 4–9 €/mes | Rentabilidad real, actualización de renta, avisos legales y fiscales |
| Profesional | 99–299 €/mes por usuario | Volumen, varios clientes, planes con su marca |

Más ingresos por compra: derivación a intermediario hipotecario registrado, gestoras y reformas.
Precios a validar en F0 y F7.

**Criterios para seguir (fijados antes de empezar):**

1. Al menos 5 de 10 planes manuales llevan a una acción (visita, preaprobación u oferta).
2. Al menos 3 de 5 profesionales del piloto pagan al terminarlo.
3. Error medio de la renta estimada frente a la real por debajo del ±10 % (umbral propuesto; el
   roadmap deja que lo fije F0).

---

## 10. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Acceso a anuncios de portales | Canales públicos, enlaces del usuario, acuerdos con agencias y servicers |
| Normativa cambiante | Reglas versionadas, escenarios con normas pendientes, vigilancia del BOE y del BOCM |
| Asesoramiento hipotecario regulado | Escenarios y criterios; producto concreto vía intermediario registrado |
| Cifras erróneas del modelo | Motores deterministas, `Figure` con fuente, verificador que bloquea el texto |
| Calidad del modelo local | Evaluación F6.0 en GPU alquilada antes de fijar el de producción |
| Fuentes públicas que fallan | Reintentos de la cola; un fallo de un elemento no debe tumbar el lote entero |
| Competencia (Invisor, Cassandra) | Plan personal, independencia, datos de resultados reales con el tiempo |
| Tiempo disponible | Alcance acotado, criterios de salida por fase, recortes definidos de antemano |

---

## 11. Legal y privacidad

- [ ] Consulta legal en F0: reutilización de datos y scraping, Ley 5/2019 de crédito inmobiliario,
      RGPD de datos financieros, avisos legales del plan y envío de datos del usuario al modelo.
- [ ] Términos de uso de cada fuente revisados antes de integrarla (ADR por fuente sensible).
- [ ] Datos personales cifrados (ADR-0011), fuera de logs y solo en la UE.
- [ ] Modelo con datos del usuario (ADR-0019): minimización por tarea, sin extraer categorías
      especiales (art. 9), servidor en la UE con TLS y autenticación, sin conversaciones en logs,
      contrato de encargado (art. 28), evaluación de impacto (art. 35) e información al usuario
      (art. 13) antes de la beta.
- [ ] Consentimiento explícito para subir documentos; el usuario confirma lo extraído.
- [ ] Aviso de interacción con IA en la interfaz.
- [ ] Licencia de cada modelo comprobada en su archivo LICENSE.

---

## 12. Cómo trabajar con Claude Code

1. Abrir la carpeta: `cd ~/Documents/housefinder && claude`.
2. Pedir trabajo por tarea: «Lee CLAUDE.md y docs/ROADMAP.md y trabaja en la tarea F6.2».
3. Un commit por tarea, con la tarea marcada `[x]` en el roadmap en el mismo commit.
4. Antes de cerrar: `make lint` y `make test` en verde; si la tarea toca el modelo, una prueba real
   con Ollama libre.
5. Decisiones nuevas de arquitectura, fuentes o dependencias: primero un ADR en `docs/adr/`.
6. Revisión semanal (domingo): estado del roadmap, criterio de salida de la fase activa y ajuste
   del calendario.
