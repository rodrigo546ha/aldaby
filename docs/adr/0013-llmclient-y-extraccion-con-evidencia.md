# ADR-0013: Cliente del LLM propio y extracción con evidencia comprobada

**Estado:** Aceptada (F6.1 adelantada a G5); el proveedor (Bedrock) lo sustituye ADR-0014 ·
**Fecha:** 2026-10-29 · **Decide:** Rodrigo

## Contexto
Dos canales de oferta traen texto libre que hay que convertir en datos: los anuncios de la sección V
del BOE (lotes con dirección, referencia catastral, superficie, tipo de licitación, garantía) y la
página que pega el usuario (F4.1). Las reglas no bastan: el formato varía demasiado
(`docs/research/f4-volumen-boe.md`). Hace falta un LLM, y la regla de oro 1 dice que ninguna cifra
que vea el usuario la genera un LLM.

## Decisión
- **`LLMClient`** (`housefinder/agent/llm.py`): protocolo propio con una operación, «devuélveme este
  modelo Pydantic a partir de estas instrucciones y este texto». Dos implementaciones:
  - **Bedrock:** SDK oficial de Anthropic (`anthropic[bedrock]`, cliente `AnthropicBedrockMantle`),
    modelo `anthropic.claude-opus-5-5` por defecto, configurable con `LLM_MODEL_ID`, región
    `AWS_REGION`.
  - **Falsa:** respuestas preparadas para los tests; nunca llama a la red.
  - Se elige con `LLM_PROVIDER` (`bedrock` o `fake`). Nada fuera de `agent/` importa `anthropic` (test
    de dependencias).
- **Salida estructurada** con `messages.parse` y el modelo Pydantic como formato (Claude Opus 5.5 no
  admite forzar una herramienta). Pensamiento adaptativo y esfuerzo por defecto del modelo (`medium`).
  Instrucciones y esquema son fijos, así que van primero y se cachean (`cache_control`).
- **Negativas:** si el modelo declina (`stop_reason: refusal`), el SDK reintenta con otro modelo
  (middleware `BetaRefusalFallbackMiddleware`, porque Bedrock no tiene el parámetro de servidor); si
  también declina, la extracción falla y la oferta sigue pendiente para una persona.
- **Extracción con evidencia comprobada** (`housefinder/agent/extraction.py`): el LLM devuelve cada
  campo con su **cita literal** del texto. Después, sin LLM, cada campo se comprueba:
  1. la cita aparece en el texto original (con espacios normalizados);
  2. el valor sale de la cita: un importe o una superficie tiene que ser uno de los números de la cita;
     una referencia catastral tiene que estar en la cita y tener el formato del Catastro; un texto
     (dirección, municipio) tiene que estar contenido en la cita.
  3. ADR-0014 añade: con varios lotes, la cita tiene que estar en el tramo de su lote, y un texto
     tiene que estar en la cita como palabras enteras.

  Lo que no pasa la comprobación se descarta con su motivo. Así ninguna cifra extraída es inventada:
  todas están escritas en la fuente.
- **Confirmación:** lo extraído queda como `extraida` y no entra en un cálculo hasta que el usuario lo
  confirma (`confirmada`). Las ofertas del BOE se confirman cuando un usuario las elige para un plan.
- **Qué se envía al LLM:** solo el texto de la oferta (un anuncio público o la página que el usuario
  pega). Nunca el perfil del usuario ni sus datos (ADR-0011).

## Opciones consideradas
- **boto3 `Converse`:** otra forma de llamar a Bedrock, pero sin los ayudantes del SDK de Anthropic
  (salida estructurada validada con Pydantic, tipos, middleware de negativas). Descartado.
- **API de Anthropic directa:** igual de válida; Bedrock se eligió en el plan para tener todo en AWS
  (datos en la UE y una sola factura). El protocolo permite cambiar sin tocar el resto.
- **Confiar en el LLM sin comprobar la evidencia:** contra la regla de oro 1. Descartado.

## Consecuencias
- Hace falta una cuenta de AWS de HouseFinder con Bedrock y el modelo habilitado; hasta entonces, solo
  la implementación falsa.
- Un campo bien leído pero mal citado se descarta: preferimos perder un dato a dar uno inventado.
- `anthropic[bedrock]` pasa a ser dependencia de la API.
