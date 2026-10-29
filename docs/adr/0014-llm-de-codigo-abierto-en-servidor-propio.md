# ADR-0014: Modelo de código abierto en un servidor propio

**Estado:** Aceptada · **Fecha:** 2026-10-29 · **Decide:** Rodrigo
**Sustituye** la parte de proveedor de ADR-0013 (Claude en Bedrock). La extracción con evidencia
comprobada y la confirmación del usuario de ADR-0013 siguen vigentes.

## Contexto
ADR-0013 llamaba a Claude en Amazon Bedrock. Rodrigo decide usar modelos de pesos abiertos servidos
desde un servidor virtual propio: el texto de las ofertas no sale a un tercero, el coste no depende
de cada llamada y no hace falta una cuenta de AWS con Bedrock (la única cuenta de AWS de este
equipo es de otra organización y no debe usarse).

## Decisión
- **Protocolo:** la API de chat compatible con OpenAI (`POST {LLM_BASE_URL}/chat/completions`), que
  sirven vLLM, llama.cpp (`llama-server`) y Ollama. El cliente (`OpenAICompatibleLLMClient` en
  `housefinder/agent/llm.py`) usa `httpx`, que ya es dependencia: no se añade ningún SDK.
- **Salida estructurada:** `response_format` con `json_schema` (el esquema del modelo Pydantic) y
  decodificación restringida en el servidor. El cliente vuelve a validar con Pydantic; si la
  respuesta no valida o se corta por longitud, `LLMOutputError` y la oferta sigue pendiente.
- **Determinismo:** `temperature: 0` en la extracción.
- **Configuración** (sin valores por defecto que llamen a la red):
  `LLM_PROVIDER` (`openai_compatible`; `fake` solo en tests), `LLM_BASE_URL`, `LLM_MODEL_ID`,
  `LLM_API_KEY` (opcional, cabecera `Authorization: Bearer`), `LLM_TIMEOUT_S` (por defecto 600) y
  `LLM_REASONING_EFFORT` (opcional, para modelos con razonamiento).
- **Se retiran** el cliente de Bedrock y la dependencia `anthropic[bedrock]`.
- **Servidor:** en la UE (RGPD), accesible solo por TLS con clave o por red privada; nunca abierto a
  internet sin autenticación. Solo recibe el texto de las ofertas, nunca datos del usuario
  (ADR-0011).
- **Modelo:** pesos con licencia permisiva (Apache 2.0 o MIT), buen español y salida estructurada.
  Se elige con una prueba sobre anuncios reales del BOE y páginas pegadas, midiendo campos
  verificados, rechazados y atribuidos al lote equivocado. En desarrollo: `qwen3:8b` en Ollama
  (Apache 2.0), el que ya estaba descargado.

## Prueba inicial (2026-10-29)
`qwen3:8b` (Q4_K_M) en Ollama 0.34 sobre un Apple M5 de 16 GB, anuncio real BOE-B-2026-35273 (dos
parcelas de la TGSS), sin razonamiento:
- 2.387 tokens de entrada y 2.050 de salida en 110 s. La salida estructurada valida sin errores.
- Lote 1: dirección, municipio, referencia catastral, tipo de licitación y garantía verificados.
  Falta la superficie y el tipo sale como `edificio` en lugar de `suelo`.
- **Lote 2: el modelo copió los datos del lote 1.** La comprobación de evidencia los da por buenos
  porque las citas sí están en el documento. La evidencia garantiza que una cifra está en la fuente,
  no que sea del lote al que se asigna.
- Con el razonamiento del modelo activado fue peor: 344 s y 3.914 tokens de salida, más campos
  rechazados (referencia catastral, superficie, garantía), el mismo lote 2 copiado y la planta `0`
  dada por buena porque el carácter «0» está en la cita. Un texto muy corto pasa la comprobación de
  texto con demasiada facilidad. En desarrollo: `LLM_REASONING_EFFORT=none`.

## Comprobación endurecida (2026-10-29)
Dos comprobaciones nuevas en `agent/extraction.py`, además de las de ADR-0013:
- **Tramo del lote.** Con varios lotes, cada cita tiene que estar en el tramo de su lote: desde la
  cita de su etiqueta («Lote 2: Urbana») hasta la etiqueta del lote siguiente; el último llega
  hasta el final del documento. Un lote sin etiqueta verificada, o en la misma posición que otro, no
  tiene tramo y se rechaza entero. Con un solo lote, vale todo el documento.
- **Palabras enteras.** Un texto tiene que estar en la cita como palabras enteras: «0» ya no pasa
  por estar dentro de «28-30».

Repetida la prueba con `qwen3:8b`: el modelo devuelve la misma copia y ahora se rechazan la
referencia catastral, el tipo de licitación y la garantía del lote 2 («la cita no está en el tramo
de su lote»). Su dirección y su municipio se quedan, porque son correctos y también están escritos
en el tramo del lote 2. El lote 1 no cambia.

Límites: el último lote incluye las condiciones comunes que van detrás, y un documento que nombra
los lotes en un índice antes de describirlos tendrá tramos equivocados; en los dos casos el error
es rechazar datos buenos, no aceptar datos de otro lote.

## Opciones consideradas
- **Seguir con Claude en Bedrock:** mejor calidad de extracción, pero requiere una cuenta de AWS
  propia y envía el texto a un tercero. Descartado por decisión de Rodrigo.
- **SDK de OpenAI (`openai`):** cómodo, pero es una dependencia más para una sola llamada HTTP.
  Descartado.
- **API nativa de Ollama:** ata el código a un servidor concreto; la compatible con OpenAI permite
  cambiar a vLLM en producción sin tocar el código. Descartado.

## Consecuencias
- Hay que elegir proveedor de servidor virtual (con o sin GPU) y modelo antes de F7. Sin GPU, cada
  anuncio tarda minutos: aceptable para la ingesta diaria del BOE (pocos al día), no para el enlace
  pegado si el usuario espera la respuesta en la pantalla.
- Un modelo pequeño se equivoca más: la comprobación de evidencia y la confirmación del usuario pesan
  más que con Claude, y ADR-0012 (el agente escribe referencias a cifras, no cifras) se mantiene
  para las explicaciones de G7.
- Desaparece el riesgo de facturar a una cuenta de AWS ajena.
