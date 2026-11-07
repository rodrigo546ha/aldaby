# F7 · Proveedor y modelo del LLM: servidor propio frente a API (2026-11-04)

Pregunta de Rodrigo: en qué procesos interviene hoy el LLM, si tener un modelo abierto en un servidor
propio (ADR-0014, ADR-0028) es la mejor opción o conviene OpenRouter o similar, y qué modelo da la
mejor relación coste/calidad en cada tarea, sin renunciar a prestaciones.

**Conclusión corta:** a nuestro volumen, el LLM cuesta céntimos al mes. Lo que decide es la calidad,
la latencia, la ventana de contexto y el RGPD, no el precio por token, y en las cuatro cosas gana una
API con endpoints en la UE frente al GEX45. Propuesta: **Claude Haiku 5.5 con endpoint en la UE
para todas las tareas**, con el esfuerzo de razonamiento ajustado a cada una, y un servidor sin GPU.
Es una decisión de Rodrigo y cambia ADR-0014 y ADR-0028: si se acepta, va en un ADR nuevo.

**Actualización (2026-11-04).** Rodrigo despliega en Vercel, no usará AWS y admite que el proveedor
guarde datos por seguridad. Con eso, la mejor vía es **Vercel AI Gateway** (§ 9), y Haiku 5.5 se
compara en la misma prueba con DeepSeek V4 Flash, que es más barato.

## 1. Dónde interviene hoy el LLM

Siete llamadas, todas con el mismo `LLMClient` (`agent/llm.py`). Tamaños medidos con las
instrucciones y los esquemas reales; los de documento, con la prueba de ADR-0014.

| # | Tarea | Código | Cuándo | Datos | Entrada / salida aprox. por unidad |
|---|---|---|---|---|---|
| 1 | Extracción de anuncios (BOE sección V, Patrimonio, enlace pegado) | `agent/extraction.py` ← `offers/extract.py`, `offers/pasted.py` | Cola diaria (10:00 y 10:30, hasta 30 al día) y al pegar un enlace | Públicos o texto del anuncio | 4.000 / 2.000 tokens |
| 2 | Condiciones, cargas y ocupación de una subasta del Portal | `agent/boe_auction_extraction.py` ← `api/boe.py` | A demanda (`/boe/subastas/*`) | Públicos, con datos personales de terceros (titular registral, ejecutado) | Hoy 7.000 (corpus cortado a 24.000 caracteres) / 3.000; completo serían unos 30.000 |
| 3 | Perfilado: datos de la respuesta libre | `agent/profiling.py` ← `profiles/interview.py` | Síncrono, una llamada por respuesta (≈ 10 por entrevista) | **Personales** (ingresos, deudas, edad) | 2.000 / 300 por respuesta |
| 4 | Nómina, declaración y extracto | `agent/documents.py` ← `api/profiles.py` | Síncrono, al subir un documento | **Personales sensibles** (texto del OCR) | 7.000 / 500 |
| 5 | Argumentos para no comprar | `agent/plan_arguments.py` ← `api/plans.py` | Con cada plan | Cifras del plan, sin números para el modelo | 2.000 / 500 |
| 6 | Explicación del plan en fichas | `agent/loop.py` ← `advisor/tools.py:383` | Al pedirla, con progreso por SSE (ADR-0052) | Cifras del plan y respuestas del perfil | ≈ 4 turnos, 24.000 / 2.000 |
| 7 | Preguntas libres al asesor | `agent/loop.py` ← `advisor/tools.py:395` | Al preguntar | Igual que la 6 | ≈ 24.000 / 1.500 |

No usan el LLM: los motores, la normativa, `agent/sense.py` (reglas fijas), la coherencia del plan,
el riesgo de las subastas del canal diario (ADR-0053, con reglas), los feeds de agencias ni la
vigilancia del BOE y del BOCM. Las evaluaciones (`make evaluar`) llaman a las tareas 1, 6 y 7.

### Lo que hoy limita el modelo local (qwen3:14b en el Mac)
- **Latencia:** 110 s por anuncio, 30 a 70 s por respuesta de la entrevista, ≈ 40 s por pregunta
  del asesor (ADR-0014, ADR-0020, banco de F6.0). El proxy de la web espera hasta tres minutos.
- **Ventana:** 16.384 tokens. Por eso hay recortes en el código: `MAX_CORPUS_CHARS = 24_000` en
  las subastas (la certificación de cargas se lee a medias y queda la nota «Se ha leído solo una
  parte de…»), `MAX_CHARS = 20_000` en los documentos, `PART_CHARS = 12_000` en los anuncios y
  `SEARCH_SHOWN = 5` en la búsqueda del asesor.
- **Calidad:** el banco de F6.0 dio 4/5 herramientas correctas y 2/5 respuestas a la primera.
  Copia valores, se equivoca en claves y la entrevista necesitó muchos parches en código
  (ADR-0020, ADR-0021). La comprobación lo frena, pero el usuario ve más «no se ha podido».

## 2. Calidad de los candidatos

Índice de Artificial Analysis v5.0.1 (consultado el 2026-11-04). Mide razonamiento general y tareas
de agente: sirve para ordenar, no sustituye a nuestra evaluación. Qwen3 14B no aparece; está por
debajo de Qwen3.8 27B.

| Modelo | Índice | Pesos abiertos | ¿Cabe en el GEX45 (24 GB)? |
|---|---|---|---|
| Claude Haiku 5.5 (low / medium / high) | 19 / 25 / 30 | No | — |
| DeepSeek V4.1 Flash (sin razonamiento / high) | 19 / 29 | Sí | No (modelo grande) |
| Gemini 3.8 Flash (low / high) | 23 / 31 | No | — |
| Gemini 3.5 Flash-Lite | 12 | No | — |
| Qwen3.8 27B (sin razonamiento / medium) | 10 / 17 | Sí, Apache 2.0 | Sí, cuantizado a 4 bits (16–19 GB) |
| Mistral Small 4 | 4 | Sí, Apache 2.0 | Justo |
| gpt-oss-120b, Gemma 4 31B, Qwen3.6 35B-A3B | sin puntuar | Sí | Gemma y Qwen3.6, cuantizados |

Lo mejor que cabe en la GPU del GEX45 (Qwen3.8 27B) queda claramente por debajo de Haiku 5.5 o
DeepSeek V4.1 Flash, y con su tiempo por tarea (16,9 min frente a 2,1 de Haiku low en el índice)
la latencia tampoco mejora lo suficiente. Un 27B denso cuantizado en esa tarjeta da del orden de
decenas de tokens por segundo por petición (estimación, sin medir), y tras los pesos quedan unos
5–8 GB para la caché: la ventana útil sigue siendo corta para las subastas.

## 3. Precios (OpenRouter, API pública, 2026-11-04)

En dólares por millón de tokens, entrada / salida. «UE» = endpoint servido en la UE/EEE por
`eu.openrouter.ai` (plan Business: 8 % sobre la compra de créditos, sin mínimo ni contrato).

| Modelo | Más barato (cualquier región) | Endpoint en la UE | Herramientas y `json_schema` |
|---|---|---|---|
| Claude Haiku 5.5 | 0,10 / 0,50 | 0,11 / 0,55 (Bedrock y Google) | Sí |
| DeepSeek V4 Flash 0731 | 0,05 / 0,10 | 0,13 / 0,495 (solo Inceptron) | Sí |
| gpt-oss-120b | 0,027 / 0,101 | 0,15 / 0,60 (Bedrock) | **No** en Bedrock |
| Mistral Small 4 | 0,15 / 0,60 | 0,165 / 0,66 (Mistral) | Sí |
| Gemini 3.1 Flash-Lite | 0,25 / 1,50 | 0,275 / 1,65 (Google) | Sí, pero sin retención cero (Google exige *Safety Retention* desde el 18/10/2026) |
| Qwen3.8 27B | 0,035 / 1,25 | no encontrado | Sí |

Servidor propio: GEX45 a 214 €/mes + 209 € de alta (ADR-0028, confirmado en la nota de prensa de
Hetzner). Sin GPU, la web, la API, el worker y la base caben en un servidor de nube de 16 GB
(CX43, unos 16 €/mes según terceros tras las subidas de 2026; **comprobar en la página oficial**).

## 4. Coste mensual por escenario

Supuestos (unidades al mes): beta, 5 profesionales con ≈ 20 clientes (100 perfiles, 300 anuncios
pegados, 600 explicaciones y preguntas, 100 subastas); lanzamiento, 1.000 usuarios activos;
escala, 10.000. Las subastas con el corpus completo y razonamiento medio; el asesor con
razonamiento bajo.

| | Tokens/mes (entrada / salida) | Haiku 5.5 UE (OpenRouter) | Haiku 5.5 UE (Bedrock directo) | GEX45 |
|---|---|---|---|---|
| Beta | 24 M / 4 M | ≈ 5 $ | ≈ 5 $ | 214 € + 209 € alta |
| Lanzamiento | 281 M / 51 M | ≈ 64 $ | ≈ 59 $ | 214 € |
| Escala | 2.810 M / 510 M | ≈ 640 $ | ≈ 590 $ | 2–3 GPU (≈ 430–640 €): 510 M de salida al mes son ≈ 200 tokens/s de media, más los picos |

Por unidad con Haiku 5.5 UE: anuncio 0,002 $, subasta 0,008 $, entrevista completa 0,004 $,
documento 0,001 $, explicación del plan 0,005 $.

- **Total del primer año de beta:** API + servidor sin GPU ≈ 260 €; GEX45 ≈ 2.780 €.
- **Punto de equilibrio:** el GEX45 solo sale más barato por encima de unas 45.000 explicaciones de
  plan al mes, y a ese volumen una GPU ya no da abasto.
- La caché de prompts de Anthropic (lecturas al 10 %) abarataría más el asesor, que reenvía el
  historial en cada turno. No hace falta para decidir.

## 5. RGPD

Las tareas 3, 4, 6 y 7 envían datos personales (ADR-0019). En los dos caminos hay un encargado del
tratamiento:
- **GEX45:** Hetzner (Alemania), con su contrato de encargo. Los datos no salen del servidor.
- **API:** el proveedor del modelo (AWS o Google en la UE) y, si se usa OpenRouter, también
  OpenRouter.
  - Con `eu.openrouter.ai` la petición se descifra y procesa en la UE y no sale de la región: si no
    hay endpoint en la UE, falla.
  - Con retención cero (`provider.zdr: true` o el ajuste de la cuenta) solo va a endpoints que no
    guardan el contenido.
  - OpenRouter es una empresa de EE. UU.: la cuenta, la facturación y los metadatos de abuso pueden
    tratarse allí. Hay DPA con cláusulas contractuales tipo.
  - Desde finales de octubre filtra todo el tráfico en busca de CSAM y lo marcado puede guardarse
    para revisión. No afecta a nuestro contenido, pero hay que contarlo en la evaluación de impacto.
- **Bedrock en la UE con cuenta de AWS propia:** quita el intermediario de EE. UU. y el 8 %. A
  cambio, hay que crear y gestionar la cuenta de AWS. ADR-0014 descartó Bedrock solo porque la
  única cuenta disponible era de otra organización.
  - Lo sirve AWS sin acceso de operadores de Anthropic. Tiene el perfil de inferencia `EU`: entre
    sus regiones están Fráncfort, Irlanda, París y España. El endpoint regional cuesta un 10 % más
    que el global.
  - Habla la API de mensajes de Anthropic (`/anthropic/v1/messages`), no la compatible con OpenAI:
    hace falta un cliente nativo en `agent/llm.py` o un proxy de traducción.
  - El acceso a Haiku 5.5 se pide en la consola de Bedrock; no está abierto por defecto.
- **API de Anthropic directa:** solo procesa en `global` o en `us`, sin opción de la UE. Sirve para
  probar con datos sintéticos, no para datos de usuarios.
- **Vertex AI (Google):** desde el 18/10/2026 Google exige *Safety Retention* en sus modelos, así
  que no hay retención cero.

Para la consulta legal de F0.6 y la evaluación de impacto de F7.4: el criterio es el contrato y la
retención, no que el servidor sea «nuestro». Una API en la UE con retención cero y DPA es un
encargado como Hetzner.

## 6. Modelo por tarea

Un solo modelo para todo, con el esfuerzo de razonamiento por tarea. Un modelo más barato para el
BOE ahorraría menos de un dólar al mes, y tener un solo modelo simplifica la evaluación, la línea
base y el contrato.

| Tarea | Modelo | Razonamiento | Por qué |
|---|---|---|---|
| 1. Anuncios | Haiku 5.5 UE | ninguno | Extracción literal con cita; en qwen3 el razonamiento empeoró (ADR-0014) |
| 2. Subastas | Haiku 5.5 UE | medio | Cargas y ocupación piden leer y relacionar textos jurídicos largos; con 1 M de contexto se lee la certificación entera |
| 3. Perfilado | Haiku 5.5 UE | ninguno | Respuestas cortas y síncronas: lo que importa es la latencia |
| 4. Documentos | Haiku 5.5 UE | ninguno | Extracción con cita sobre el texto del OCR (se mantiene el OCR local de ADR-0021) |
| 5. Argumentos | Haiku 5.5 UE | ninguno | Texto corto sin cifras |
| 6–7. Asesor | Haiku 5.5 UE | bajo | Elegir herramientas y escribir el JSON de fichas; subir a medio si la evaluación lo pide |

**Alternativas, por si la evaluación de Haiku falla:**
- **DeepSeek V4 Flash en la UE:** precio parecido, pero un solo proveedor en la UE (Inceptron) y
  una versión anterior a la V4.1.
- **Gemini 3.8 Flash o un modelo mayor solo para las subastas:** si las cargas salen mal.
- **Mistral Small 4 directo (francés):** la opción más soberana, pero con un índice de 4 es un paso
  atrás.

## 7. Qué cambia en el código
- **Casi todo es configuración.** El cliente ya habla la API compatible con OpenAI:
  `LLM_BASE_URL=https://eu.openrouter.ai/api/v1`, `LLM_MODEL_ID=anthropic/claude-haiku-5.5` y
  `LLM_API_KEY`.
- **Temperatura.** El cliente envía `temperature: 0`. La documentación de Anthropic dice que, en los
  modelos Claude 4.7 y posteriores, cualquier valor por debajo de 1 devuelve un error 400. Hay que
  poder omitirla por configuración: Haiku 5.5 es posterior a 4.7.
- **Razonamiento por la capa compatible con OpenAI de Anthropic.** Con la API de Anthropic directa
  (`https://api.anthropic.com/v1/`), `reasoning_effort` se ignora y Haiku 5.5 razona por defecto
  con esfuerzo medio. `response_format` solo acepta `json_schema` con `strict: true`, que es lo que
  enviamos. El `strict` de las herramientas se ignora, pero los argumentos ya se validan con
  Pydantic. Anthropic presenta esa capa como pensada para probar y comparar modelos, no para
  producción.
- **El esfuerzo por tarea es nuevo.** Hoy `LLM_REASONING_EFFORT` es global. Hace falta pasarlo por
  llamada y comprobar cómo lo acepta OpenRouter (`reasoning_effort` o `reasoning.effort`).
- **Esquemas estrictos.** Comprobar que los `json_schema` estrictos de Pydantic los acepta el
  modo estricto de Anthropic: sin `additionalProperties`, algunos formatos o límites pueden fallar.
  Lo destapa `make evaluar`.
- **Subir los recortes de contexto** (`MAX_CORPUS_CHARS`, `MAX_CHARS`, `PART_CHARS`,
  `SEARCH_SHOWN`) cuando el modelo de producción lo permita.
- **Infraestructura:** quitar el perfil `modelo` (Ollama con GPU) de `infra/produccion/`, cambiar
  la comprobación de Ollama de la vigilancia por una del endpoint y contratar un servidor sin GPU
  en lugar del GEX45. Ollama sigue en el Mac para desarrollar sin red.

## 8. Siguiente paso
1. **Prueba con la API de Anthropic directa** (o con OpenRouter normal): sin plan Business ni
   comisión, con una clave con tope de gasto. El juego de evaluación no tiene datos personales.
   Antes, hacer opcional la temperatura en el cliente.
2. `make evaluar` con Haiku 5.5 frente a la línea base de qwen3:14b: juego de anuncios, banco del
   asesor, entrevista y una subasta con certificación larga. Coste: céntimos.
3. **Si mejora, elegir el camino de producción con datos personales:**
   - Bedrock en la UE: cliente nativo, sin intermediario.
   - OpenRouter UE: sin código nuevo, con un 8 % de comisión y un intermediario de EE. UU.

   La elección va en un ADR nuevo que sustituya la parte de proveedor de ADR-0014 y el servidor de
   ADR-0028, antes de contratar en F7.5.

## 9. Con el despliegue en Vercel: Vercel AI Gateway

Catálogo público (`https://ai-gateway.vercel.sh/v1/models`) y documentación de Vercel, consultados el
2026-11-04:
- **Sin comisión:** «no markup and no platform fee on tokens»; se paga el precio de lista del
  proveedor más la comisión del medio de pago. Hay un crédito gratuito mensual hasta la primera
  compra de créditos, con un subconjunto de modelos y límites de uso más bajos. La documentación no
  da la cantidad.
- **Compatible con nuestro cliente:**
  - Base `https://ai-gateway.vercel.sh/v1`, con la clave en `Authorization: Bearer`.
  - `response_format` con `json_schema` y herramientas funcionan.
  - `reasoning_effort` es un alias de `reasoning.effort`, y Haiku 5.5 admite `none`: el
    `LLM_REASONING_EFFORT` actual funciona tal cual.
- **Retención cero por petición** con `providerOptions.gateway.zeroDataRetention: true`, sin coste
  extra. Exige cuenta de pago o créditos comprados. Haiku 5.5 tiene retención cero y sin
  entrenamiento en todos sus proveedores. No hace falta, pero conviene para los datos personales.
- **Una sola clave para comparar modelos:**

| Modelo | $/M entrada / salida | Retención cero |
|---|---|---|
| Claude Haiku 5.5 | 0,10 / 0,50 | todos los proveedores |
| DeepSeek V4 Flash | 0,084 / 0,169 | algunos |
| DeepSeek V4.1 Flash | 0,195 / 0,78 | algunos |
| gpt-oss-120b | 0,10 / 0,50 | algunos |
| Gemini 3.8 Flash | 0,75 / 3,75 | algunos |

- **Temperatura:** el catálogo marca Haiku 5.5 sin `temperature`. Hay que poder omitirla, como en
  § 7.

### Cómo lanzar la comparación
1. Crear una clave de AI Gateway en Vercel y añadirla al `.env` local: `AI_GATEWAY_API_KEY=…`. El
   `.env` está fuera de git.
2. Una pasada por modelo, sin tocar el `.env`. Cada informe queda en `informes-modelos/`, también
   fuera de git:

```bash
make evaluar SALIDA=informes-modelos/haiku-5.5.md LLM_BASE_URL=https://ai-gateway.vercel.sh/v1 LLM_API_KEY='$(AI_GATEWAY_API_KEY)' LLM_TEMPERATURE=none LLM_MODEL_ID=anthropic/claude-haiku-5.5
make evaluar SALIDA=informes-modelos/deepseek-v4-flash.md LLM_BASE_URL=https://ai-gateway.vercel.sh/v1 LLM_API_KEY='$(AI_GATEWAY_API_KEY)' LLM_MODEL_ID=deepseek/deepseek-v4-flash
make evaluar SALIDA=informes-modelos/gpt-oss-120b.md LLM_BASE_URL=https://ai-gateway.vercel.sh/v1 LLM_API_KEY='$(AI_GATEWAY_API_KEY)' LLM_MODEL_ID=openai/gpt-oss-120b LLM_REASONING_EFFORT=low
```

- **Línea base:** cada pasada se compara con la de qwen3:14b (`data/evaluation/linea_base.json`);
  sin `BASE=1` no se sobrescribe.
- **Razonamiento:** `LLM_REASONING_EFFORT` sigue en `none` desde el `.env`. gpt-oss no lo admite,
  por eso va con `low`.
- **Contenido de la prueba:** las 16 extracciones del juego etiquetado, las 8 preguntas del asesor
  con el perfil de «Desarrollo local» y la coherencia del plan.

Con el despliegue en Vercel, el resto de ADR-0028 y ADR-0040 también cambia: la API Python, el
worker, la cola y PostgreSQL con PostGIS no viven en Vercel tal cual. Eso pide su propio ADR.

## 10. DeepSeek con su propia API (2026-11-07)

Rodrigo quiere probar DeepSeek primero.
- **Modelo:** `deepseek-flash`, que hoy sirve DeepSeek-V4.1-Flash.
- **Base:** `https://api.deepseek.com`.
- **Salida:** solo `json_object`, así que se evalúa con `LLM_STRUCTURED_OUTPUT=json_object`
  (ADR-0014).
- **Precio:** la tabla oficial es una imagen. El 16/08/2026 entraron precios de hora punta y valle,
  y en valle cuestan la mitad.

La evaluación solo envía el juego etiquetado (anuncios sintéticos y públicos del BOE) y el perfil
ficticio «Inversora ficticia (demo)». Procesa en China: para datos de usuarios habría que usar el
mismo modelo en otro proveedor.

```bash
make evaluar SALIDA=informes-modelos/deepseek-flash.md LLM_BASE_URL=https://api.deepseek.com LLM_API_KEY='$(DEEPSEEK_API_KEY)' LLM_MODEL_ID=deepseek-flash LLM_STRUCTURED_OUTPUT=json_object LLM_REASONING_EFFORT=none LLM_TIMEOUT_S=180
```

## Fuentes
- Vercel AI Gateway: https://vercel.com/docs/ai-gateway/pricing,
  https://vercel.com/docs/ai-gateway/sdks-and-apis/openai-chat-completions (y sus páginas
  `reasoning`, `structured-outputs` y `tool-calling`),
  https://vercel.com/docs/ai-gateway/security-and-compliance/zdr y el catálogo
  `https://ai-gateway.vercel.sh/v1/models`.
- Precios y proveedores: API pública de OpenRouter (`/api/v1/models` y
  `/api/v1/models/{id}/endpoints`), consultada el 2026-11-04.
- Enrutado en la UE y retención cero: https://openrouter.ai/docs/guides/features/sovereign-ai,
  https://openrouter.ai/business/eu, https://openrouter.ai/docs/features/zdr,
  https://openrouter.ai/docs/guides/features/in-region-routing,
  https://openrouter.ai/assets/data-processing-agreement.pdf
- Anthropic: https://platform.claude.com/docs/en/api/openai-sdk.md (capa compatible con OpenAI) y
  https://platform.claude.com/docs/en/build-with-claude/claude-in-amazon-bedrock.md (Bedrock:
  regiones, perfiles de inferencia y modelos).
  - Haiku 5.5 cuesta 0,10 / 0,50 $ hasta 100.000 tokens de entrada y 0,50 / 2,50 $ por encima.
- Calidad: https://artificialanalysis.ai/models y https://artificialanalysis.ai/leaderboards/models
  (índice v5.0.1).
- GEX45: https://www.hetzner.com/pressroom/hetzner-expands-its-gpu-portfolio-with-the-gex45/
- Nube de Hetzner (sin confirmar en la página oficial): https://www.bitdoze.com/es/hetzner-cloud-precios-2026/
- Tamaños de tarea: instrucciones y esquemas medidos en el código; tiempos de ADR-0014, ADR-0020 y
  `docs/research/f6-0-banco-agente.md`.
